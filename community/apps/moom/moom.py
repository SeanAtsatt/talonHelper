from dataclasses import dataclass
from typing import Union

from talon import Module, actions, cron, ui

mod = Module()


def moom_app():
    return ui.apps(bundle="com.manytricks.Moom")[0]


opened_handler = None
closed_handler = None
moom_controls = []
timeout_job = None


def cancel_timeout():
    global timeout_job
    if timeout_job:
        cron.cancel(timeout_job)
        timeout_job = None


def reset_state():
    """Drop a half-finished command.

    If Moom's controller never opens (hot key unassigned, Moom not running,
    keystroke swallowed by another app), the win_open handler stays registered
    forever and every later command silently queues up instead of firing.
    """
    global opened_handler, closed_handler, moom_controls
    cancel_timeout()
    if opened_handler:
        try:
            ui.unregister("win_open", opened_handler)
        except Exception:
            pass
        opened_handler = None
    if closed_handler:
        try:
            ui.unregister("win_close", closed_handler)
        except Exception:
            pass
        closed_handler = None
    moom_controls = []


@dataclass
class MoomControl:
    key: str
    dismisses: bool = False

    def __str__(self):
        return self.key


MOOM_DISMISS = MoomControl("return", dismisses=True)


def moom_controls_if_opened():
    global opened_handler

    def win_opened(win):
        global opened_handler, closed_handler, moom_controls

        if win.app.bundle != "com.manytricks.Moom":
            return

        if win.element.get("AXSubrole") != "AXSystemDialog":
            return

        cancel_timeout()
        ui.unregister("win_open", opened_handler)
        opened_handler = None

        for i, control in enumerate(moom_controls):
            if control.dismisses:
                dismissing_controls = moom_controls[: i + 1]
                del moom_controls[: i + 1]
                break
        else:
            dismissing_controls = moom_controls + [MOOM_DISMISS]
            moom_controls = []

        actions.key(" ".join(map(str, dismissing_controls)))
        if moom_controls:

            def win_closed(closed_win):
                global closed_handler
                if win != closed_win:
                    return
                ui.unregister("win_close", closed_handler)
                closed_handler = None
                moom_controls_if_opened()
                actions.key("ctrl-alt-m")

            closed_handler = win_closed
            ui.register("win_close", closed_handler)
            return

    global timeout_job
    opened_handler = win_opened
    ui.register("win_open", win_opened)
    cancel_timeout()
    timeout_job = cron.after("2s", reset_state)


@mod.action_class
class Actions:
    def moom(key: Union[str, MoomControl]):
        """Press the corresponding Moom control [key]"""
        global opened_handler, moom_controls
        if not opened_handler:
            moom_controls_if_opened()
            actions.key("ctrl-alt-m")
        moom_controls.append(
            MoomControl(key, dismisses=True) if isinstance(key, str) else key
        )

    def moom_keys(key: str, times: int = 1):
        """Press the corresponding Moom control key followed by Return"""
        actions.user.moom(MoomControl(f"{key}:{times}"))

    def moom_center_frontmost_window():
        """Tell Moom to center the frontmost window the way macOS would"""
        moom_app().appscript().center_frontmost_window()

    def moom_arrange_according_to_snapshot(snapshot: str):
        """Tell Moom to arrange windows according to the specified snapshot"""
        moom_app().appscript().arrange_windows_according_to_snapshot(snapshot)
