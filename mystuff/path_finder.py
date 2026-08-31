from talon import Context, actions
from talon.mac import applescript

ctx = Context()
ctx.matches = r"""
app: path finder
"""


def _pf_get_path() -> str:
    return applescript.run(
        'tell application "Path Finder" to get the POSIX path of the target of the front finder window'
    ).strip()


def _pf_go(path: str):
    applescript.run(
        f'tell application "Path Finder" to reveal POSIX file "{path}"'
    )


@ctx.action_class("user")
class UserActions:
    def file_manager_current_path():
        return _pf_get_path()

    def file_manager_open_parent():
        actions.key("cmd-up")

    def file_manager_open_directory(path: str):
        _pf_go(path)

    def file_manager_select_directory(path: str):
        actions.insert(path)

    def file_manager_new_folder(name: str):
        actions.key("cmd-shift-n")
        actions.insert(name)

    def file_manager_open_file(path: str):
        actions.key("home")
        actions.insert(path)
        actions.key("cmd-o")

    def file_manager_select_file(path: str):
        actions.key("home")
        actions.insert(path)

    def file_manager_show_properties():
        actions.key("cmd-i")

    def address_focus():
        actions.key("cmd-shift-g")

    def address_copy_address():
        actions.key("shift-alt-cmd-c")

    def address_navigate(address: str):
        _pf_go(address)
