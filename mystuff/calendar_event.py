"""Voice-driven Apple Calendar event creation. Talon glue over calendar_logic."""

from datetime import datetime

from talon import Context, Module, actions, app, imgui
from talon.mac import applescript

from . import calendar_logic as cl

mod = Module()
ctx = Context()

TARGET_CALENDAR = "Calendar"

mod.tag("calendar_confirming", desc="Active while the new-event confirmation window is open")

# --- lists -----------------------------------------------------------------
_MONTHS = {
    "january": "1", "february": "2", "march": "3", "april": "4",
    "may": "5", "june": "6", "july": "7", "august": "8",
    "september": "9", "october": "10", "november": "11", "december": "12",
}
mod.list("calendar_month", desc="Month name to month number")
mod.list("calendar_time_unit", desc="Duration unit -> h/m")
mod.list("calendar_duration_special", desc="Special duration phrases -> minutes")
ctx.lists["user.calendar_month"] = _MONTHS
ctx.lists["user.calendar_time_unit"] = {
    "hour": "h", "hours": "h",
    "minute": "m", "minutes": "m", "min": "m", "mins": "m",
}
ctx.lists["user.calendar_duration_special"] = {
    "half an hour": "30",
    "quarter hour": "15",
    "an hour and a half": "90",
    "one hour and a half": "90",
}


# --- captures --------------------------------------------------------------
@mod.capture(rule="<user.ordinals> | <number_small>")
def calendar_day(m) -> int:
    """A day of the month, spoken as an ordinal ('twentieth') or number ('20')."""
    return int(m[0])


@mod.capture(
    rule="{user.calendar_duration_special} "
    "| <number_small> {user.calendar_time_unit} "
    "[<number_small> {user.calendar_time_unit}]"
)
def calendar_duration(m) -> int:
    """A spoken duration -> total minutes."""
    if hasattr(m, "calendar_duration_special"):
        return int(m.calendar_duration_special)
    nums = list(m.number_small_list)
    units = list(m.calendar_time_unit_list)
    return cl.combine_duration(list(zip(nums, units)))


# --- state -----------------------------------------------------------------
_state = {
    "title": "", "month": 0, "day": 0, "hour": 0, "minute": 0,
    "duration": 60, "start": None, "end": None, "error": "",
}


def _recompute() -> None:
    try:
        start, end = cl.resolve_event_datetimes(
            _state["month"], _state["day"], _state["hour"],
            _state["minute"], _state["duration"], datetime.now(),
        )
        _state["start"], _state["end"], _state["error"] = start, end, ""
    except ValueError as exc:
        _state["start"], _state["end"], _state["error"] = None, None, str(exc)


def _notify(msg: str) -> None:
    print(f"calendar_event: {msg}")
    app.notify(body=msg)


def _open_window() -> None:
    ctx.tags = ["user.calendar_confirming"]
    gui_confirm.show()


def _close_window() -> None:
    gui_confirm.hide()
    ctx.tags = []


@imgui.open(y=10, x=500)
def gui_confirm(gui: imgui.GUI):
    if _state["error"] or _state["start"] is None:
        gui.text("New event - problem")
        gui.line()
        gui.text(_state["error"] or "incomplete event")
    else:
        gui.text("New event")
        gui.line()
        for line in cl.format_for_display(
            _state["title"], _state["start"], _state["end"], TARGET_CALENDAR
        ):
            gui.text(line)
    gui.spacer()
    gui.text('"yes" create - "cancel" abort')
    gui.text('correct: retitle / date / time / duration <...>')
    gui.spacer()
    if gui.button("Calendar cancel"):
        actions.user.calendar_cancel()


@mod.action_class
class Actions:
    def calendar_add_event(
        title: str, month: str, day: int, prose_time: str, duration_min: int = 60
    ):
        """Parse a spoken event and open the confirmation window."""
        title = (title or "").strip()
        if not title:
            _notify("event needs a title")
            return
        try:
            hour, minute = cl.parse_prose_time(prose_time)
        except ValueError as exc:
            _notify(str(exc))
            return
        _state.update(
            title=title, month=int(month), day=int(day),
            hour=hour, minute=minute, duration=int(duration_min),
        )
        _recompute()
        if _state["error"]:
            _notify(_state["error"])
            _close_window()
            return
        _open_window()

    def calendar_set_title(title: str):
        """Correct the title of the pending event."""
        if not gui_confirm.showing:
            return
        title = (title or "").strip()
        if title:
            _state["title"] = title

    def calendar_set_date(month: str, day: int):
        """Correct the date of the pending event."""
        if not gui_confirm.showing:
            return
        _state["month"], _state["day"] = int(month), int(day)
        _recompute()
        if _state["error"]:
            _notify(_state["error"])

    def calendar_set_time(prose_time: str):
        """Correct the time of the pending event."""
        if not gui_confirm.showing:
            return
        try:
            _state["hour"], _state["minute"] = cl.parse_prose_time(prose_time)
        except ValueError as exc:
            _notify(str(exc))
            return
        _recompute()

    def calendar_set_duration(duration_min: int):
        """Correct the duration of the pending event."""
        if not gui_confirm.showing:
            return
        _state["duration"] = int(duration_min)
        _recompute()

    def calendar_confirm():
        """Create the pending event in Calendar."""
        if not gui_confirm.showing:
            return
        if _state["error"] or _state["start"] is None:
            _notify(_state["error"] or "cannot create: incomplete event")
            return
        script = cl.build_calendar_applescript(
            TARGET_CALENDAR, _state["title"], _state["start"], _state["end"]
        )
        try:
            applescript.run(script)
        except Exception as exc:  # noqa: BLE001 - surface any AppleScript failure
            _notify(f"create failed: {exc}")
            return
        _notify(f"created: {_state['title']}")
        _close_window()

    def calendar_cancel():
        """Discard the pending event and close the window."""
        _state["error"] = ""
        _close_window()
