import os
import subprocess

from talon import Context, actions, ui

ctx = Context()
ctx.matches = r"""
app: apple_terminal
"""
directories_to_remap = {}
directories_to_exclude = {}


def get_terminal_cwd():
    """Get CWD from Terminal.app via AppleScript + lsof.

    More reliable than parsing window titles, which vary by shell config.
    Gets the tty via AppleScript, finds the shell PID, then queries its CWD with lsof.
    """
    try:
        # Get the tty of Terminal's selected tab
        tty_result = subprocess.run(
            ["osascript", "-e",
             'tell application "Terminal" to return tty of selected tab of front window'],
            capture_output=True,
            text=True,
            timeout=1,
        )
        tty = tty_result.stdout.strip()
        if not tty:
            return _fallback_cwd()

        # Find the shell process using this tty, then get its cwd via lsof
        # lsof -a -d cwd -p <pid> gives us the working directory
        # First find the PID of the shell on this tty
        ps_result = subprocess.run(
            ["ps", "-t", tty.replace("/dev/", ""), "-o", "pid=,comm="],
            capture_output=True,
            text=True,
            timeout=1,
        )
        if ps_result.returncode != 0:
            return _fallback_cwd()

        # Find the shell PID (zsh, bash, fish, etc.)
        shell_pid = None
        for line in ps_result.stdout.strip().split("\n"):
            parts = line.strip().split()
            if len(parts) >= 2:
                pid, comm = parts[0], parts[-1]
                # Look for common shells
                if any(
                    shell in comm.lower()
                    for shell in ["zsh", "bash", "fish", "sh", "tcsh"]
                ):
                    shell_pid = pid
                    break

        if not shell_pid:
            return _fallback_cwd()

        # Now get the cwd using lsof
        lsof_result = subprocess.run(
            ["lsof", "-a", "-d", "cwd", "-p", shell_pid, "-Fn"],
            capture_output=True,
            text=True,
            timeout=1,
        )
        for line in lsof_result.stdout.strip().split("\n"):
            if line.startswith("n") and line != "n":
                path = line[1:]  # Strip the 'n' prefix
                if os.path.isdir(path):
                    return path

    except Exception:
        pass

    return _fallback_cwd()


def _fallback_cwd():
    """Fallback: parse the window title for CWD (less reliable)."""
    try:
        title = ui.active_window().title

        if " \u2014 " in title:
            title = title.split(" \u2014 ")[0]

        if "~" in title:
            title = os.path.expanduser(title)

        if os.path.isdir(title):
            return title
    except Exception:
        pass
    return None


@ctx.action_class("edit")
class EditActions:
    def delete_line():
        actions.key("ctrl-u")

    def word_left():
        """Move cursor one word left using escape sequence"""
        actions.key("escape b")

    def word_right():
        """Move cursor one word right using escape sequence"""
        actions.key("escape f")


@ctx.action_class("user")
class UserActions:
    def file_manager_current_path():
        path = get_terminal_cwd()
        if path:
            if path in directories_to_remap:
                path = directories_to_remap[path]
            if path in directories_to_exclude:
                return None
            return path
        return None

    def file_manager_show_properties():
        """Shows the properties for the file"""

    def file_manager_open_directory(path: str):
        """opens the directory that's already visible in the view"""
        actions.insert(f'cd "{path}"\n')

    def file_manager_open_parent():
        actions.insert("cd ..\n")

    def file_manager_select_directory(path: str):
        """selects the directory"""
        actions.insert(path)

    def file_manager_new_folder(name: str):
        """Creates a new folder in a gui filemanager or inserts the command to do so for terminals"""
        actions.insert(f'mkdir "{name}"')

    def file_manager_open_file(path: str):
        """opens the file"""
        actions.insert(path)
        actions.key("enter")

    def file_manager_select_file(path: str):
        """selects the file"""
        actions.insert(path)

    def file_manager_refresh_title():
        return

    def tab_jump(number: int):
        actions.key(f"cmd-{number}")

    def tab_final():
        actions.key("cmd-9")

    def terminal_clear_screen():
        """Clear screen"""
        actions.key("ctrl-l")


@ctx.action_class("app")
class app_actions:
    # other tab functions should already be implemented in
    # code/platforms/mac/app.py

    def tab_previous():
        actions.key("ctrl-shift-tab")

    def tab_next():
        actions.key("ctrl-tab")
