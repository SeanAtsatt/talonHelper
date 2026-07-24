> **SUPERSEDED (2026-07-24).** This custom-build approach was abandoned. On macOS Tahoe every write path to Apple Calendar failed: AppleScript was denied (TCC), pyobjc/EventKit was rejected by hardened-runtime library validation inside both Talon.app and its venv python, and CalDAV writes never persisted. The calendar need is now met via Claude's Google Calendar connector / Cowork — natural-language event management, verified working end-to-end. Kept as a decision record only.

# Voice-Driven Calendar Event Creation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Talon voice command that creates a timed Apple Calendar event from a single spoken utterance (title + month/day + time + optional duration), with a confirmation window that supports correcting individual fields before committing.

**Architecture:** Pure, Talon-free logic (date/year resolution, duration math, AppleScript-string building, title escaping) lives in `calendar_logic.py` and is unit-tested with plain Python. The Talon glue (captures, lists, actions, imgui confirmation window, a scoped tag) lives in `calendar_event.py` and delegates to `calendar_logic`. Grammar lives in `calendar_event.talon`. Events are created directly via `talon.mac.applescript` — Calendar need not be focused.

**Tech Stack:** Python 3.13 (Talon's venv), Talon (`Module`, `Context`, `imgui`, `mod.list`, `mod.capture`, `mod.tag`), macOS AppleScript via `talon.mac.applescript`. Reuses Talon community captures `<user.prose_time>`, `<user.ordinals>`, `<user.number_small>`.

## Global Constraints

- **Files sync manually:** repo lives at `~/gitHubRepository/talonHelper/`; Talon loads from `~/.talon/user/`. Edit repo copies, then `cp` to `~/.talon/user/mystuff/` (and `~/.talon/user/` for `aaa_security.py`). The `cp` needs the sandbox disabled (writes to `~/.talon/` are blocked in-sandbox).
- **Target calendar:** constant `TARGET_CALENDAR = "Calendar"` (the only writable personal calendar). One-line change to retarget.
- **Default duration:** 60 minutes when duration is omitted.
- **Date form:** month name + day only; **year is inferred** (next occurrence ≥ now). Reject impossible dates (e.g. Feb 30); Feb 29 resolves to the next leap year.
- **Test runner:** `~/.talon/.venv/bin/python` (Talon's Python 3.13). Prefix test commands with `PYTHONDONTWRITEBYTECODE=1`.
- **Talon reload check:** after `cp`, `tail ~/.talon/talon.log` must show `DEBUG [~]` reload lines for each file and **no traceback**.
- **REPL is single-line only:** pipe one-line commands: `echo 'stmt; stmt' | ~/.talon/.venv/bin/repl`.
- **Commits:** repo is main-based (match existing workflow). End commit messages with the two trailers used in this repo:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU
  ```

---

## File Structure

- Create `mystuff/calendar_logic.py` — pure functions, **no `talon` import**. Owns: `parse_prose_time`, `next_valid_start`, `resolve_event_datetimes`, `combine_duration`, `escape_applescript`, `build_calendar_applescript`, `format_for_display`.
- Create `mystuff/test_calendar_logic.py` — plain-Python assertions for `calendar_logic`.
- Create `mystuff/calendar_event.py` — Talon module: month list, day/duration captures, state, actions, imgui window, tag. Imports `calendar_logic`.
- Create `mystuff/calendar_event.talon` — grammar (global command + tag-scoped confirm/edit commands).
- Modify `aaa_security.py` (repo root) and `~/.talon/user/aaa_security.py` — add `calendar_event.py` to `TRUSTED_FILES` (defensive; the engine uses native `applescript.run()`, not subprocess).
- Untouched: `mystuff/calendar.talon` (existing keyboard shortcuts).

---

## Task 1: Pure logic module (`calendar_logic.py`)

**Files:**
- Create: `mystuff/calendar_logic.py`
- Test: `mystuff/test_calendar_logic.py`

**Interfaces:**
- Consumes: nothing (stdlib only).
- Produces:
  - `parse_prose_time(s: str) -> tuple[int, int]` — `(hour24, minute)`; raises `ValueError` on bad input.
  - `combine_duration(pairs: list[tuple[int, str]]) -> int` — sums `(n, 'h'|'m')` pairs to minutes.
  - `next_valid_start(month: int, day: int, hour: int, minute: int, now: datetime) -> datetime` — earliest valid datetime ≥ now (minute precision), scanning up to 9 years; raises `ValueError` if never valid.
  - `resolve_event_datetimes(month, day, hour, minute, duration_min, now) -> tuple[datetime, datetime]` — `(start, end)`.
  - `escape_applescript(s: str) -> str`.
  - `build_calendar_applescript(calendar_name: str, title: str, start: datetime, end: datetime) -> str`.
  - `format_for_display(title: str, start: datetime, end: datetime, calendar_name: str) -> list[str]`.

- [ ] **Step 1: Write the failing test**

Create `mystuff/test_calendar_logic.py`:

```python
from __future__ import annotations

from datetime import datetime

import calendar_logic as cl


def check(label, cond):
    if not cond:
        raise AssertionError(label)
    print(f"ok: {label}")


# parse_prose_time
check("2:30pm -> 14:30", cl.parse_prose_time("2:30pm") == (14, 30))
check("2pm -> 14:00", cl.parse_prose_time("2pm") == (14, 0))
check("12am -> 0:00", cl.parse_prose_time("12am") == (0, 0))
check("12pm -> 12:00", cl.parse_prose_time("12pm") == (12, 0))
check("9:05 24h -> 9:05", cl.parse_prose_time("9:05") == (9, 5))
try:
    cl.parse_prose_time("banana")
    raise SystemExit("expected ValueError for 'banana'")
except ValueError:
    print("ok: bad time rejected")

# combine_duration
check("45 min", cl.combine_duration([(45, "m")]) == 45)
check("one hour", cl.combine_duration([(1, "h")]) == 60)
check("two hours", cl.combine_duration([(2, "h")]) == 120)
check("three hours", cl.combine_duration([(3, "h")]) == 180)
check("1h30m", cl.combine_duration([(1, "h"), (30, "m")]) == 90)

# next_valid_start: future date this year stays this year
now = datetime(2026, 7, 19, 10, 0)
check("future same year", cl.next_valid_start(12, 25, 9, 0, now) == datetime(2026, 12, 25, 9, 0))
# past date rolls to next year
check("past rolls forward", cl.next_valid_start(1, 1, 9, 0, now) == datetime(2027, 1, 1, 9, 0))
# impossible date rejected
try:
    cl.next_valid_start(2, 30, 9, 0, now)
    raise SystemExit("expected ValueError for Feb 30")
except ValueError:
    print("ok: Feb 30 rejected")
# Feb 29 resolves to next leap year (2028)
check("Feb 29 -> leap", cl.next_valid_start(2, 29, 9, 0, now) == datetime(2028, 2, 29, 9, 0))

# resolve_event_datetimes: end = start + duration
s, e = cl.resolve_event_datetimes(7, 20, 14, 30, 45, now)
check("start", s == datetime(2026, 7, 20, 14, 30))
check("end +45", e == datetime(2026, 7, 20, 15, 15))

# escape_applescript
check("quote escaped", cl.escape_applescript('Bob\'s "1-on-1"') == 'Bob\'s \\"1-on-1\\"')
check("backslash escaped", cl.escape_applescript("a\\b") == "a\\\\b")
check("newline stripped", "\n" not in cl.escape_applescript("a\nb"))

# build_calendar_applescript contains numeric components and escaped title
script = cl.build_calendar_applescript("Calendar", 'Team "sync"', s, e)
check("has make new event", "make new event" in script)
check("has month set", "set month of d to 7" in script)
check("title escaped in script", '\\"sync\\"' in script)

# format_for_display
lines = cl.format_for_display("Dentist", s, e, "Calendar")
check("display title", lines[0] == "Dentist")
check("display has calendar", any("Calendar: Calendar" == ln for ln in lines))

print("ALL PASS")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/gitHubRepository/talonHelper/mystuff && PYTHONDONTWRITEBYTECODE=1 ~/.talon/.venv/bin/python test_calendar_logic.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'calendar_logic'`.

- [ ] **Step 3: Write minimal implementation**

Create `mystuff/calendar_logic.py`:

```python
"""Pure logic for the voice calendar-event feature. No talon imports so it is
unit-testable with plain Python."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

_TIME_RE = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*$", re.IGNORECASE)


def parse_prose_time(s: str) -> tuple[int, int]:
    """Parse community prose_time output ("2:30pm", "2pm", "9:05") to (h24, m)."""
    m = _TIME_RE.match(s or "")
    if not m:
        raise ValueError(f"could not parse time: {s!r}")
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = (m.group(3) or "").lower()
    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"time out of range: {s!r}")
    return hour, minute


def combine_duration(pairs: list[tuple[int, str]]) -> int:
    """Sum (number, 'h'|'m') pairs into total minutes."""
    return sum(n * 60 if unit == "h" else n for n, unit in pairs)


def next_valid_start(
    month: int, day: int, hour: int, minute: int, now: datetime
) -> datetime:
    """Earliest datetime matching month/day/time that is >= now (minute
    precision). Scans forward up to 9 years so Feb 29 lands on a leap year.
    Raises ValueError if the date never exists (e.g. Feb 30)."""
    floor = now.replace(second=0, microsecond=0)
    for year in range(now.year, now.year + 9):
        try:
            cand = datetime(year, month, day, hour, minute)
        except ValueError:
            continue
        if cand >= floor:
            return cand
    raise ValueError(f"no such date: month {month} day {day}")


def resolve_event_datetimes(
    month: int, day: int, hour: int, minute: int, duration_min: int, now: datetime
) -> tuple[datetime, datetime]:
    start = next_valid_start(month, day, hour, minute, now)
    return start, start + timedelta(minutes=duration_min)


def escape_applescript(s: str) -> str:
    """Escape a string for embedding inside an AppleScript double-quoted literal."""
    s = (s or "").replace("\\", "\\\\").replace('"', '\\"')
    return "".join(ch for ch in s if ch == "\t" or ch >= " ").strip()


def build_calendar_applescript(
    calendar_name: str, title: str, start: datetime, end: datetime
) -> str:
    """Build a Calendar 'make new event' script, setting date components
    numerically (locale-safe). day is set to 1 before month/year to avoid
    month-overflow, then set to the real day."""
    cal = escape_applescript(calendar_name)
    summary = escape_applescript(title)

    def date_block(var: str, dt: datetime) -> str:
        return (
            f"set {var} to current date\n"
            f"set day of {var} to 1\n"
            f"set year of {var} to {dt.year}\n"
            f"set month of {var} to {dt.month}\n"
            f"set day of {var} to {dt.day}\n"
            f"set hours of {var} to {dt.hour}\n"
            f"set minutes of {var} to {dt.minute}\n"
            f"set seconds of {var} to 0\n"
        )

    return (
        'tell application "Calendar"\n'
        f'tell calendar "{cal}"\n'
        f"{date_block('d', start)}"
        f"{date_block('e', end)}"
        f'make new event with properties {{summary:"{summary}", '
        "start date:d, end date:e}\n"
        "end tell\n"
        "end tell"
    )


def format_for_display(
    title: str, start: datetime, end: datetime, calendar_name: str
) -> list[str]:
    return [
        title,
        start.strftime("%a %b %d %Y"),
        f"{start.strftime('%-I:%M %p')} - {end.strftime('%-I:%M %p')}",
        f"Calendar: {calendar_name}",
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/gitHubRepository/talonHelper/mystuff && PYTHONDONTWRITEBYTECODE=1 ~/.talon/.venv/bin/python test_calendar_logic.py`
Expected: prints `ok: ...` lines ending with `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_logic.py mystuff/test_calendar_logic.py
git commit -m "feat(calendar): pure logic for voice event creation

Date/year resolution (incl. Feb 29 leap scan), duration math, prose-time
parsing, AppleScript-string building, and title escaping, with unit tests.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 2: Talon engine module (`calendar_event.py`) + sandbox trust

**Files:**
- Create: `mystuff/calendar_event.py`
- Modify: `aaa_security.py` (repo root) — add one entry to `TRUSTED_FILES`

**Interfaces:**
- Consumes: `calendar_logic` (Task 1). Community captures `<user.prose_time>`, `<user.ordinals>`, `<user.number_small>`.
- Produces (used by Task 3 grammar):
  - list `user.calendar_month` (month name → number string)
  - list `user.calendar_time_unit` (`"hour"/"hours"→"h"`, `"minute"/…→"m"`)
  - list `user.calendar_duration_special` (phrase → minutes string)
  - capture `user.calendar_day -> int`
  - capture `user.calendar_duration -> int`
  - tag `user.calendar_confirming`
  - actions: `calendar_add_event(title, month, day, prose_time, duration_min=60)`, `calendar_set_title(title)`, `calendar_set_date(month, day)`, `calendar_set_time(prose_time)`, `calendar_set_duration(duration_min)`, `calendar_confirm()`, `calendar_cancel()`

- [ ] **Step 1: Create the engine module**

Create `mystuff/calendar_event.py`:

```python
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
@mod.capture(rule="<user.ordinals> | <user.number_small>")
def calendar_day(m) -> int:
    """A day of the month, spoken as an ordinal ('twentieth') or number ('20')."""
    return int(m[0])


@mod.capture(
    rule="{user.calendar_duration_special} "
    "| <user.number_small> {user.calendar_time_unit} "
    "[<user.number_small> {user.calendar_time_unit}]"
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
```

- [ ] **Step 2: Add the module to the sandbox trust list**

In `aaa_security.py` (repo root), find the `TRUSTED_FILES` set (around line 45-51) containing `os.path.join(TALON_USER_DIR, "mystuff", "default_app.py"),` and add directly below it:

```python
    os.path.join(TALON_USER_DIR, "mystuff", "calendar_event.py"),
```

- [ ] **Step 3: Syntax-check both new/modified files**

Run:
```bash
cd ~/gitHubRepository/talonHelper
for f in mystuff/calendar_event.py aaa_security.py; do \
  ~/.talon/.venv/bin/python -c "import sys; compile(open(sys.argv[1]).read(), sys.argv[1], 'exec'); print('OK', sys.argv[1])" "$f"; done
```
Expected: `OK mystuff/calendar_event.py` and `OK aaa_security.py`.

- [ ] **Step 4: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_event.py aaa_security.py
git commit -m "feat(calendar): Talon engine for voice event creation

Month/day/duration captures, confirmation window with edit-in-place
setters, and AppleScript create. Trust calendar_event.py in the sandbox.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 3: Grammar file (`calendar_event.talon`)

**Files:**
- Create: `mystuff/calendar_event.talon`

**Interfaces:**
- Consumes: everything Produced by Task 2 (lists, captures, tag, actions) and community `<user.prose_time>`, `<user.text>`.
- Produces: the spoken command surface. No downstream consumers.

- [ ] **Step 1: Create the grammar file**

Create `mystuff/calendar_event.talon` (no `app:`/`os:` header → global context for the add command; the confirm/edit block is gated by the tag):

```talon
calendar add <user.text> on {user.calendar_month} <user.calendar_day> at <user.prose_time>:
    user.calendar_add_event(user.text, calendar_month, user.calendar_day, user.prose_time)
calendar add <user.text> on {user.calendar_month} <user.calendar_day> at <user.prose_time> for <user.calendar_duration>:
    user.calendar_add_event(user.text, calendar_month, user.calendar_day, user.prose_time, user.calendar_duration)

tag: user.calendar_confirming
-
(yes | confirm): user.calendar_confirm()
(cancel | no): user.calendar_cancel()
retitle <user.text>: user.calendar_set_title(user.text)
date {user.calendar_month} <user.calendar_day>: user.calendar_set_date(calendar_month, user.calendar_day)
time <user.prose_time>: user.calendar_set_time(user.prose_time)
duration <user.calendar_duration>: user.calendar_set_duration(user.calendar_duration)
```

- [ ] **Step 2: Deploy to the live Talon dir** (sandbox disabled — writes to `~/.talon` are blocked in-sandbox)

Run:
```bash
cp ~/gitHubRepository/talonHelper/mystuff/calendar_logic.py \
   ~/gitHubRepository/talonHelper/mystuff/calendar_event.py \
   ~/gitHubRepository/talonHelper/mystuff/calendar_event.talon \
   ~/.talon/user/mystuff/
cp ~/gitHubRepository/talonHelper/aaa_security.py ~/.talon/user/aaa_security.py
```

- [ ] **Step 3: Verify Talon loaded it cleanly**

Run: `sleep 4 && tail -25 ~/.talon/talon.log`
Expected: `DEBUG [~]` reload lines for `calendar_event.py`, `calendar_event.talon`, `aaa_security.py`; **no `Traceback` / `ERROR ... talon_script`** referencing these files. If a traceback appears, fix the file, re-`cp`, re-check before proceeding.

- [ ] **Step 4: Verify captures, lists, and actions registered (REPL)**

Run:
```bash
echo 'import sys; m = sys.modules["user.mystuff.calendar_event"]; print("july=", m._MONTHS["july"]); from talon import actions; print("add:", actions.user.calendar_add_event); print("confirm:", actions.user.calendar_confirm)' | ~/.talon/.venv/bin/repl
```
Expected: prints `july= 7` and the two action reprs with their docstrings (no `KeyError`/`AttributeError`).

- [ ] **Step 5: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_event.talon
git commit -m "feat(calendar): grammar for voice event creation + edit-in-place

Global 'calendar add ... on <month> <day> at <time> [for <duration>]' plus
tag-scoped yes/cancel/retitle/date/time/duration correction commands.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 4: End-to-end verification

**Files:** none (verification only).

**Interfaces:** exercises the full stack (Task 1-3) against real Calendar.

- [ ] **Step 1: Drive a real create through the engine's own code path (REPL)**

This exercises `build_calendar_applescript` + `applescript.run` and will trigger the **one-time macOS "Talon wants to control Calendar" prompt** — allow it when it appears.

Run:
```bash
echo 'import sys; from datetime import datetime, timedelta; from talon.mac import applescript; m = sys.modules["user.mystuff.calendar_event"]; cl = m.cl; s = (datetime.now()+timedelta(days=3)).replace(second=0, microsecond=0); e = s+timedelta(hours=1); applescript.run(cl.build_calendar_applescript(m.TARGET_CALENDAR, "Talon E2E test", s, e)); print("created at", s)' | ~/.talon/.venv/bin/repl
```
Expected: prints `created at <datetime>`, no exception.

- [ ] **Step 2: Confirm the event exists, then delete it**

Run (sandbox disabled — AppleScript/Automation):
```bash
osascript -e 'tell application "Calendar" to tell calendar "Calendar" to return summary of every event whose summary is "Talon E2E test"'
osascript -e 'tell application "Calendar" to tell calendar "Calendar" to delete (every event whose summary is "Talon E2E test")'
```
Expected: first line lists `Talon E2E test`; second removes it (no error).

- [ ] **Step 3: Manual voice test (user performs)**

Ask the user to run these live, since they require speech:
1. Say: **"calendar add dentist appointment on \<a month\> \<a near-future day\> at two thirty pm for 45 minutes"** → confirmation window shows the title, correct weekday/date, `2:30 PM - 3:15 PM`, `Calendar: Calendar`.
2. Say **"retitle eye doctor"** → title line updates in place.
3. Say **"duration two hours"** → end time updates to `4:30 PM`.
4. Say **"yes"** → toast `created: eye doctor`, window closes, event appears in Calendar.
5. Repeat once and say **"cancel"** → window closes, nothing created.
Then delete the test event(s) via Calendar or the existing `delete event` command.

- [ ] **Step 4: Update project memory**

Append a pointer in `~/.claude/projects/-Users-seanatsatt-gitHubRepository-talonHelper/memory/MEMORY.md` under a Calendar heading noting the new `mystuff/calendar_event.py` / `calendar_logic.py` / `calendar_event.talon` feature and the "calendar add" command surface, so future sessions know it exists.

---

## Self-Review

**Spec coverage:**
- Timed event title+date+time+duration → Tasks 1-3 (captures, resolve, create). ✓
- Month+day date form, year inference, Feb 30 reject / Feb 29 leap → `next_valid_start` (Task 1), tested. ✓
- Default duration 60 → two-rule grammar (Task 3) + action default (Task 2). ✓
- Multi-hour durations "two/three hours" → `calendar_duration` capture + `combine_duration`, tested. ✓
- Confirmation window → `gui_confirm` (Task 2). ✓
- Edit-in-place (retitle/date/time/duration) under a tag → Task 2 setters + Task 3 tag block. ✓
- yes/cancel escape hatch → Task 2/3. ✓
- AppleScript direct-create, numeric components, day-to-1 overflow guard, title escaping → `build_calendar_applescript` + `escape_applescript` (Task 1), tested. ✓
- Fixed target calendar "Calendar" constant → Task 2. ✓
- Error handling (bad date/empty title/AppleScript failure → toast, no create) → Task 2 actions. ✓
- First-run automation permission note → Task 4 Step 1. ✓
- Sandbox trust → Task 2 Step 2. ✓
- Global (non app-scoped) command file → Task 3. ✓

**Placeholder scan:** No TBD/TODO; every code step contains full code; commands have expected output. ✓

**Type consistency:** `calendar_add_event(title, month:str, day:int, prose_time:str, duration_min:int=60)` matches Task 3 call sites; `combine_duration(list[tuple[int,str]])`, `resolve_event_datetimes(...)->(start,end)`, `build_calendar_applescript(cal,title,start,end)`, `format_for_display(title,start,end,cal)` all match between Tasks 1 and 2. Capture names (`user.calendar_day`, `user.calendar_duration`, `user.calendar_month`, `user.calendar_time_unit`, `user.calendar_duration_special`) match between Tasks 2 and 3. ✓

**Known verification-time risk:** `date {user.calendar_month} ...` uses the reserved-feeling word "date"; if it collides with another tag-scoped command at reload, rename to "set date" (grammar-only change, Task 3). Confirm during Task 3 Step 3-4.
