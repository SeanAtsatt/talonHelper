from talon import Module, actions, clip, imgui, cron

mod = Module()

# Store the copied content
copied_lines = []

@imgui.open()
def gui(gui: imgui.GUI):
    global copied_lines
    gui.text("Copied content - say 'lines <start> <end>' to select range:")
    gui.line()
    if copied_lines:
        for i, line in enumerate(copied_lines, 1):
            # Truncate long lines for display
            display_line = line[:100] + "..." if len(line) > 100 else line
            gui.text(f"{i:4}: {display_line}")
    else:
        gui.text("(no content)")
    gui.line()
    gui.spacer()
    if gui.button("Close (or say 'copy done')"):
        gui.hide()

def delayed_show_gui():
    """Read clipboard and show GUI after delay"""
    global copied_lines
    text = clip.text()
    if text:
        copied_lines = text.split('\n')
    else:
        copied_lines = ["(clipboard empty)"]
    gui.show()

@mod.action_class
class Actions:
    def iterm2_copy_up_lines(n: int):
        """Copy n lines from bottom of screen in copy mode"""
        actions.key("cmd-shift-c")
        actions.sleep("100ms")
        actions.key("shift-g")  # Go to bottom
        actions.key("shift-v")  # Line selection
        actions.insert(str(n))
        actions.key("k")        # Move up n lines
        actions.key("y")        # Yank
        # Delay to let clipboard update, then show GUI
        cron.after("300ms", delayed_show_gui)

    def iterm2_copy_until_word(word: str):
        """Copy from bottom up to a word in copy mode"""
        actions.key("cmd-shift-c")
        actions.sleep("100ms")
        actions.key("shift-g")  # Go to bottom
        actions.key("v")        # Start selection
        actions.key("?")        # Search backward
        actions.insert(word)
        actions.key("enter")
        actions.key("y")        # Yank
        # Delay to let clipboard update, then show GUI
        cron.after("300ms", delayed_show_gui)

    def iterm2_copy_range(start: int, end: int):
        """Copy a specific range of lines from the displayed content"""
        global copied_lines
        # Ensure start <= end
        if start > end:
            start, end = end, start
        if copied_lines and 1 <= start <= len(copied_lines) and 1 <= end <= len(copied_lines):
            selected = copied_lines[start-1:end]  # Convert to 0-indexed
            clip.set_text('\n'.join(selected))
            actions.app.notify(f"Copied lines {start}-{end} to clipboard")
        gui.hide()

    def iterm2_copy_done():
        """Close the copy GUI without changing clipboard"""
        gui.hide()

    def iterm2_show_copy_gui():
        """Show the copy GUI with current clipboard contents"""
        delayed_show_gui()
