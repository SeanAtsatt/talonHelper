# close_confirm.py - Confirmation for close commands to prevent voice misinterpretation

from talon import Module, actions, imgui, ui, cron

mod = Module()
main_screen = ui.main_screen()
timeout_job = None
TIMEOUT_SECONDS = 5

def auto_cancel():
    """Auto-cancel after timeout"""
    global timeout_job
    timeout_job = None
    if close_confirm_gui.showing:
        close_confirm_gui.hide()

# Track whether we're confirming a tab or window close
pending_close_type = "window"

@imgui.open(x=main_screen.x + main_screen.width / 2.5, y=main_screen.y + main_screen.height / 3)
def close_confirm_gui(gui: imgui.GUI):
    gui.text(f"Close this {pending_close_type}?")
    gui.line()
    if gui.button("Yes close"):
        actions.user.close_confirm_yes()
    if gui.button("No close"):
        actions.user.close_confirm_no()

@mod.action_class
class Actions:
    def close_confirm_start():
        """Ask for confirmation before closing window"""
        global timeout_job, pending_close_type
        pending_close_type = "window"
        if timeout_job:
            cron.cancel(timeout_job)
        close_confirm_gui.show()
        timeout_job = cron.after(f"{TIMEOUT_SECONDS}s", auto_cancel)

    def tab_close_confirm_start():
        """Ask for confirmation before closing tab"""
        global timeout_job, pending_close_type
        pending_close_type = "tab"
        if timeout_job:
            cron.cancel(timeout_job)
        close_confirm_gui.show()
        timeout_job = cron.after(f"{TIMEOUT_SECONDS}s", auto_cancel)

    def close_confirm_yes():
        """Confirm and execute the close"""
        global timeout_job
        if timeout_job:
            cron.cancel(timeout_job)
            timeout_job = None
        close_confirm_gui.hide()
        actions.key("super-w")

    def close_confirm_no():
        """Cancel the pending close"""
        global timeout_job
        if timeout_job:
            cron.cancel(timeout_job)
            timeout_job = None
        close_confirm_gui.hide()
