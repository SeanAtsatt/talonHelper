from typing import Optional

from talon import Module, app, ui
from talon.mac import applescript

mod = Module()


def _get_selected_file() -> Optional[str]:
    """Return POSIX path of the file selected in the frontmost file manager.

    Supports Finder and Path Finder. Returns None for anything else, or if no
    file is selected.
    """
    active = ui.active_app().name
    try:
        if active == "Finder":
            script = (
                'tell application "Finder"\n'
                "  set sel to selection as alias list\n"
                "  if sel is {} then return \"\"\n"
                "  return POSIX path of (item 1 of sel)\n"
                "end tell"
            )
        elif active == "Path Finder":
            script = (
                'tell application "Path Finder"\n'
                "  set sel to selection\n"
                "  if sel is {} then return \"\"\n"
                "  return POSIX path of (item 1 of sel)\n"
                "end tell"
            )
        else:
            return None
        path = applescript.run(script).strip()
        return path or None
    except Exception as exc:
        print(f"default_app: selection lookup failed: {exc}")
        return None


def _notify(msg: str) -> None:
    """Send a transient toast and also print to Talon log."""
    print(f"default_app: {msg}")
    app.notify(body=msg)


@mod.action_class
class Actions:
    def default_app_show():
        """Show the current default app for the selected file's extension."""
        path = _get_selected_file()
        if path is None:
            _notify("select a file in Finder or Path Finder first")
            return
        _notify(f"selected: {path}")

    def default_app_change():
        """Open a picker of candidate apps for the selected file's extension."""
        print("default_app_change: stub")

    def default_app_refresh():
        """Force LaunchServices to reload by restarting Finder."""
        print("default_app_refresh: stub")
