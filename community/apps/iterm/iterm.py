import os
import subprocess
from talon import Context, Module, actions, ui

ctx = Context()
mod = Module()

mod.apps.iterm2 = """
os: mac
and app.bundle: com.googlecode.iterm2
"""
ctx.matches = r"""
app: iterm2
"""

directories_to_remap = {}
directories_to_exclude = {}


def get_iterm_cwd():
    """Get current working directory from iTerm2 using AppleScript"""
    script = '''
    tell application "iTerm2"
        tell current session of current window
            return variable named "path"
        end tell
    end tell
    '''
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=1
        )
        path = result.stdout.strip()
        if path and os.path.isdir(path):
            return path
    except:
        pass
    return None


@mod.action_class
class ModuleActions:
    def save_current_path_as(name: str):
        """Save current directory to system paths with given name"""
        # Get current path from whichever terminal implements file_manager_current_path
        path = actions.user.file_manager_current_path()
        if not path:
            actions.app.notify("Could not get current path")
            return

        # Path to the system paths file (use hostname to find correct file)
        import socket
        hostname = socket.gethostname()
        paths_file = os.path.expanduser(
            f"~/.talon/user/community/core/system_paths-{hostname}.talon-list"
        )

        # Clean up the name (lowercase, strip)
        name = name.lower().strip()

        # Append to the file
        with open(paths_file, "a") as f:
            f.write(f"{name}: {path}\n")

        actions.app.notify(f"Saved: go {name} → {path}")


@ctx.action_class("edit")
class EditActions:
    def word_left():
        """Move cursor one word left using escape sequence"""
        actions.key("escape b")

    def word_right():
        """Move cursor one word right using escape sequence"""
        actions.key("escape f")


@ctx.action_class("user")
class UserActions:
    def file_manager_current_path():
        """Returns current path from iTerm2 using shell integration"""
        path = get_iterm_cwd()
        if path:
            if path in directories_to_remap:
                path = directories_to_remap[path]
            if path in directories_to_exclude:
                return None
            return path
        return None

    def file_manager_open_parent():
        """Go to parent directory"""
        actions.insert("cd ..\n")

    def file_manager_open_directory(path: str):
        """Opens the directory that's already visible in the view"""
        actions.insert(f'cd "{path}"\n')

    def file_manager_select_directory(path: str):
        """Selects the directory"""
        actions.insert(path)

    def file_manager_new_folder(name: str):
        """Creates a new folder"""
        actions.insert(f'mkdir "{name}"')

    def file_manager_open_file(path: str):
        """Opens the file"""
        actions.insert(path)
        actions.key("enter")

    def file_manager_select_file(path: str):
        """Selects the file"""
        actions.insert(path)

    def tab_jump(number: int):
        actions.key(f"cmd-{number}")

    def tab_final():
        actions.key("cmd-9")

    def terminal_clear_screen():
        """Clear screen"""
        actions.key("ctrl-l")
