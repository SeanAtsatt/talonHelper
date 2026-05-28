import os
import shutil
import subprocess
from typing import Optional, Tuple

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


def _file_uti(path: str) -> Optional[str]:
    """Return the UTI (kMDItemContentType) of a file, or None on failure."""
    try:
        out = subprocess.run(
            ["mdls", "-name", "kMDItemContentType", "-raw", path],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as exc:
        print(f"default_app: mdls failed for {path}: {exc.stderr.strip()}")
        return None
    if not out or out == "(null)":
        return None
    return out


def _default_handler(uti: str) -> Optional[str]:
    """Return the bundle ID of the current default handler for a UTI."""
    from LaunchServices import (
        LSCopyDefaultRoleHandlerForContentType,
        kLSRolesAll,
    )

    bundle_id = LSCopyDefaultRoleHandlerForContentType(uti, kLSRolesAll)
    return str(bundle_id) if bundle_id else None


def _app_name_for_bundle(bundle_id: str) -> Optional[str]:
    """Return the localized display name for a bundle ID, or None if unknown."""
    from AppKit import NSWorkspace
    from Foundation import NSBundle

    ws = NSWorkspace.sharedWorkspace()
    url = ws.URLForApplicationWithBundleIdentifier_(bundle_id)
    if url is None:
        return None
    bundle = NSBundle.bundleWithURL_(url)
    if bundle is None:
        return os.path.basename(str(url.path()))
    info = bundle.localizedInfoDictionary() or bundle.infoDictionary() or {}
    name = info.get("CFBundleDisplayName") or info.get("CFBundleName")
    if name:
        return str(name)
    return os.path.splitext(os.path.basename(str(url.path())))[0]


def _file_info(path: str) -> Optional[Tuple[str, str, Optional[str], Optional[str]]]:
    """Return (extension, uti, default_bundle_id, default_app_name) for a file."""
    ext = os.path.splitext(path)[1].lstrip(".").lower()
    uti = _file_uti(path)
    if not uti:
        return None
    bundle_id = _default_handler(uti)
    name = _app_name_for_bundle(bundle_id) if bundle_id else None
    return ext, uti, bundle_id, name


@mod.action_class
class Actions:
    def default_app_show():
        """Show the current default app for the selected file's extension."""
        path = _get_selected_file()
        if path is None:
            _notify("select a file in Finder or Path Finder first")
            return
        info = _file_info(path)
        if info is None:
            _notify(f"could not read UTI for {path}")
            return
        ext, uti, bundle_id, name = info
        if bundle_id is None:
            _notify(f".{ext} ({uti}): no default app set")
        else:
            _notify(f".{ext} ({uti}) -> {name or '?'} [{bundle_id}]")

    def default_app_change():
        """Open a picker of candidate apps for the selected file's extension."""
        print("default_app_change: stub")

    def default_app_refresh():
        """Force LaunchServices to reload by restarting Finder."""
        print("default_app_refresh: stub")
