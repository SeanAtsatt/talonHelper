from talon import Module, actions, imgui, ui, cron

mod = Module()
main_screen = ui.main_screen()

# State to track if next foot press should trigger command mode
command_mode_next = False
command_mode_active = False  # Track if alt-0 is currently held down
timeout_job = None
TIMEOUT_SECONDS = 5
last_press_time = 0  # Track last press time to prevent bounce

def auto_cancel():
    """Auto-cancel command mode after timeout"""
    global timeout_job, command_mode_next
    timeout_job = None
    command_mode_next = False
    if command_mode_gui.showing:
        command_mode_gui.hide()

@imgui.open(x=main_screen.x + main_screen.width / 2.5, y=main_screen.y + main_screen.height / 3)
def command_mode_gui(gui: imgui.GUI):
    gui.text("🎤 WISPR COMMAND MODE 🎤")
    gui.line()
    gui.text("Next foot press = Command Mode")

@mod.action_class
class Actions:
    def toggle_whisper_command_mode():
        """Toggle command mode for next foot press"""
        global command_mode_next, timeout_job
        command_mode_next = True

        # Show GUI
        if timeout_job:
            cron.cancel(timeout_job)
        command_mode_gui.show()
        timeout_job = cron.after(f"{TIMEOUT_SECONDS}s", auto_cancel)

    def is_command_mode_next() -> bool:
        """Check if next foot press should be command mode"""
        global command_mode_next
        return command_mode_next

    def clear_command_mode():
        """Clear command mode flag"""
        global command_mode_next, timeout_job
        command_mode_next = False
        if timeout_job:
            cron.cancel(timeout_job)
            timeout_job = None
        if command_mode_gui.showing:
            command_mode_gui.hide()

    def test_alt_zero():
        """Test action: press alt-0, wait 3 seconds, release"""
        actions.key("alt:down 0:down")

        def release_keys():
            actions.key("0:up alt:up")

        cron.after("3s", release_keys)

    def foot_press_whisper():
        """Handle foot press with optional command mode"""
        global command_mode_next, command_mode_active, last_press_time
        import time

        # Debounce: ignore presses within 100ms of each other
        current_time = time.time()
        if current_time - last_press_time < 0.1:
            return
        last_press_time = current_time

        if command_mode_next:
            # Command mode: hold down alt-0 for Wispr command mode
            actions.speech.disable()  # Disable Talon speech in command mode too
            actions.key("alt:down 0:down")
            command_mode_next = False
            command_mode_active = True

            # Hide GUI
            if command_mode_gui.showing:
                command_mode_gui.hide()
            if timeout_job:
                cron.cancel(timeout_job)
        else:
            # Normal mode: drowse Talon and start Whisper dictation
            actions.speech.disable()
            actions.key("fn:down")

    def foot_release_whisper():
        """Handle foot release"""
        global command_mode_active

        if command_mode_active:
            # Release alt-0 for command mode and wake Talon
            actions.key("0:up alt:up")
            actions.speech.enable()  # Re-enable Talon speech
            command_mode_active = False
        else:
            # Normal mode: release Fn and wake Talon
            actions.key("fn:up")
            actions.speech.enable()
