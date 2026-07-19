import math
import os
import re
import shutil
import subprocess
import threading
from typing import Optional, Tuple

from talon import Module, app, cron, imgui, ui
from talon.mac import applescript

mod = Module()

DISPLAY_LIMIT = 20
STRING_LIMIT = 40

_state = {
    "ext": "",
    "uti": "",
    "default_bid": None,
    "candidates": [],  # list of (name, bundle_id)
    "page": 1,
}


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


def _run(args: list) -> Tuple[int, str, str]:
    """Run a command; return (returncode, stdout, stderr). Never raises.

    A timeout guards against a hung CLI tool blocking Talon's voice thread.
    """
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=10)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)


_DUTI_CANDIDATES = ("/opt/homebrew/bin/duti", "/usr/local/bin/duti")


def _duti_path() -> Optional[str]:
    """Locate the duti binary. Talon's PATH is minimal (/usr/bin:/bin:/usr/sbin:
    /sbin) and lacks Homebrew dirs, so fall back to explicit Homebrew locations.
    """
    found = shutil.which("duti")
    if found:
        return found
    for cand in _DUTI_CANDIDATES:
        if os.path.exists(cand):
            return cand
    return None


def _have_duti() -> bool:
    return _duti_path() is not None


def _file_uti(path: str) -> Optional[str]:
    """Return the UTI (kMDItemContentType) of a file, or None on failure."""
    rc, out, err = _run(["mdls", "-name", "kMDItemContentType", "-raw", path])
    if rc != 0 or not out or out == "(null)":
        if err:
            print(f"default_app: mdls failed for {path}: {err}")
        return None
    return out


def _default_app(ext: str) -> Optional[Tuple[str, str, str]]:
    """Return (app_name, app_path, bundle_id) for the ext's default, or None.

    Parses the three-line output of `duti -x <ext>`.
    """
    duti = _duti_path()
    if duti is None:
        return None
    rc, out, err = _run([duti, "-x", ext])
    if rc != 0 or not out:
        return None
    lines = out.splitlines()
    if len(lines) >= 3:
        return lines[0], lines[1], lines[2]
    return None


_BUNDLE_ID_RE = re.compile(r"^[A-Za-z0-9.\-]+$")


def _app_name_for_bundle(bundle_id: str) -> str:
    """Resolve a friendly app name from a bundle id; fall back to the id."""
    # Bundle ids should only contain these chars; reject anything that could
    # corrupt the mdfind query string rather than interpolating it blindly.
    if not _BUNDLE_ID_RE.match(bundle_id):
        return bundle_id
    rc, out, err = _run(["mdfind", f"kMDItemCFBundleIdentifier == '{bundle_id}'"])
    if rc == 0 and out:
        base = os.path.basename(out.splitlines()[0])
        if base.endswith(".app"):
            base = base[:-4]
        return base or bundle_id
    return bundle_id


# Apps to always offer in the picker even when they don't register for the
# file's UTI with LaunchServices (`duti -l` omits them). Shown only if the
# .app bundle exists on disk.
_PINNED_APPS = [
    ("Visual Studio Code", "com.microsoft.VSCode", "Visual Studio Code.app"),
]


def _pinned_candidates() -> list:
    """Return [(name, bundle_id), ...] for pinned apps that are installed."""
    items = []
    for name, bid, bundle in _PINNED_APPS:
        for apps_dir in ("/Applications", os.path.expanduser("~/Applications")):
            if os.path.exists(os.path.join(apps_dir, bundle)):
                items.append((name, bid))
                break
    return items


def _candidate_apps(uti: str, default_bid: Optional[str]) -> list:
    """Return [(name, bundle_id), ...] handlers for uti, default pinned first.

    Sorted case-insensitive by display name, with the current default (if any)
    moved to the front.
    """
    duti = _duti_path()
    if duti is None:
        return []
    rc, out, err = _run([duti, "-l", uti])
    if rc != 0:
        out = ""  # no registered handlers; still offer the pinned apps below
    seen = set()
    items = []
    for bid in out.splitlines():
        bid = bid.strip()
        if not bid or bid in seen:
            continue
        seen.add(bid)
        items.append((_app_name_for_bundle(bid), bid))
    for name, bid in _pinned_candidates():
        if bid not in seen:
            seen.add(bid)
            items.append((name, bid))
    items.sort(key=lambda pair: pair[0].casefold())
    if default_bid:
        front = [p for p in items if p[1] == default_bid]
        rest = [p for p in items if p[1] != default_bid]
        items = front + rest
    return items


def _bundle_id_for_app(app_path: str) -> Optional[str]:
    """Read CFBundleIdentifier straight from the bundle's Info.plist.

    mdls/Spotlight is not reliable for this, so ask `defaults` instead.
    """
    rc, out, err = _run(
        ["defaults", "read", os.path.join(app_path, "Contents", "Info"),
         "CFBundleIdentifier"]
    )
    if rc == 0 and out:
        return out
    return None


def _browse_and_set(uti: str) -> None:
    """Show the macOS application chooser and set the pick as default for uti.

    The chooser blocks until dismissed, so this must run on a worker thread,
    never on Talon's voice thread.
    """
    # NSOpenPanel restricted to .app bundles, starting in /Applications. Much
    # faster than `choose application`, which enumerates every app on the
    # system before it can render. `activate` keeps the panel from opening
    # behind other windows.
    script = (
        "activate\n"
        'POSIX path of (choose file of type {"com.apple.application-bundle"} '
        "default location (path to applications folder) "
        'with prompt "Choose the app to set as default")'
    )
    try:
        p = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except Exception as exc:
        _notify(f"app chooser failed: {exc}")
        return
    if p.returncode != 0:
        err = p.stderr.strip()
        if "-128" in err:  # user pressed Cancel
            return
        _notify(f"app chooser failed: {err or p.returncode}")
        return
    app_path = p.stdout.strip().rstrip("/")
    bid = _bundle_id_for_app(app_path)
    if not bid:
        _notify(f"could not read bundle id for {app_path}")
        return
    name = os.path.basename(app_path)
    if name.endswith(".app"):
        name = name[:-4]
    if _set_default(bid, uti):
        _state["default_bid"] = bid
        _notify(f"set default for {uti} -> {name}")
        cron.after("0ms", gui_default_picker.hide)


def _set_default(bundle_id: str, uti: str) -> bool:
    """Set bundle_id as the default handler for uti. Returns True on success."""
    duti = _duti_path()
    if duti is None:
        _notify("install duti first - brew install duti")
        return False
    rc, out, err = _run([duti, "-s", bundle_id, uti, "all"])
    if rc != 0:
        _notify(f"duti failed: {err or rc}")
        return False
    return True


@imgui.open(y=10, x=500)
def gui_default_picker(gui: imgui.GUI):
    ext = _state["ext"]
    uti = _state["uti"]
    default_bid = _state["default_bid"]
    candidates = _state["candidates"]

    total_pages = max(1, math.ceil(len(candidates) / DISPLAY_LIMIT))
    if _state["page"] > total_pages:
        _state["page"] = 1
    page = _state["page"]

    gui.text(f"Default for .{ext} ({uti})  ({page}/{total_pages})")
    gui.line()

    start = (page - 1) * DISPLAY_LIMIT
    for offset, (name, bid) in enumerate(candidates[start : start + DISPLAY_LIMIT], 1):
        n = start + offset
        display = name if len(name) <= STRING_LIMIT else name[: STRING_LIMIT - 2] + ".."
        star = "*" if bid == default_bid else " "
        gui.text(f"{star} {n}: {display}")

    gui.spacer()
    gui.text('say "pick <number>" to set as default')
    gui.text('say "default browse" to choose any app')
    gui.text('(reopen anytime with "default choose")')
    gui.spacer()
    if total_pages > 1:
        if gui.button("Next"):
            _state["page"] = (page % total_pages) + 1
        if gui.button("Previous"):
            _state["page"] = ((page - 2) % total_pages) + 1
        gui.spacer()
    if gui.button("Default close"):
        gui_default_picker.hide()


_show_lines: list = []


@imgui.open(y=10, x=500)
def gui_default_show(gui: imgui.GUI):
    gui.text("Default app")
    gui.line()
    for line in _show_lines:
        gui.text(line)
    gui.spacer()
    if gui.button("Default close"):
        gui_default_show.hide()


@mod.action_class
class Actions:
    def default_app_show():
        """Show the current default app for the selected file's extension
        in a small on-screen window. Say "default close" to dismiss."""
        global _show_lines
        path = _get_selected_file()
        if path is None:
            lines = ["No file selected.", "Pick a file in Finder or Path Finder."]
        elif not _have_duti():
            lines = ["duti not found.", "Install with: brew install duti"]
        else:
            ext = os.path.splitext(path)[1].lstrip(".").lower()
            if not ext:
                lines = [os.path.basename(path), "(file has no extension)"]
            else:
                info = _default_app(ext)
                if info is None:
                    lines = [f"Type: .{ext}", "No default app set."]
                else:
                    name, _app_path, bid = info
                    if name.endswith(".app"):
                        name = name[:-4]
                    lines = [
                        f"File:    {os.path.basename(path)}",
                        f"Type:    .{ext}",
                        f"Default: {name}",
                        f"Bundle:  {bid}",
                    ]
        _show_lines = lines
        print("default_app: " + " | ".join(lines))
        gui_default_show.show()

    def default_app_change():
        """Open a picker of candidate apps for the selected file's extension."""
        path = _get_selected_file()
        if path is None:
            _notify("select a file in Finder or Path Finder first")
            return
        if not _have_duti():
            _notify("install duti first - brew install duti")
            return
        uti = _file_uti(path)
        if not uti:
            _notify(f"could not read UTI for {path}")
            return
        ext = os.path.splitext(path)[1].lstrip(".").lower()
        default_info = _default_app(ext) if ext else None
        default_bid = default_info[2] if default_info else None
        candidates = _candidate_apps(uti, default_bid)
        if not candidates:
            _notify(f"no apps registered for {uti}")
            return
        _state["ext"] = ext
        _state["uti"] = uti
        _state["default_bid"] = default_bid
        _state["candidates"] = candidates
        _state["page"] = 1
        gui_default_picker.show()

    def default_app_pick(n: int):
        """Set the Nth candidate from the open picker as the default."""
        if not gui_default_picker.showing:
            return
        candidates = _state["candidates"]
        if n < 1 or n > len(candidates):
            _notify(f"pick {n}: out of range (1..{len(candidates)})")
            return
        name, bundle_id = candidates[n - 1]
        uti = _state["uti"]
        if _set_default(bundle_id, uti):
            _state["default_bid"] = bundle_id
            _notify(f"set default for {uti} -> {name}")
            gui_default_picker.hide()

    def default_app_browse():
        """Open the macOS application chooser to pick any app as the default
        for the selected file's type, even one missing from the picker list."""
        if not _have_duti():
            _notify("install duti first - brew install duti")
            return
        uti = _state["uti"] if gui_default_picker.showing else ""
        if not uti:
            path = _get_selected_file()
            if path is None:
                _notify("select a file in Finder or Path Finder first")
                return
            uti = _file_uti(path)
            if not uti:
                _notify(f"could not read UTI for {path}")
                return
            _state["uti"] = uti
            _state["ext"] = os.path.splitext(path)[1].lstrip(".").lower()
        threading.Thread(target=_browse_and_set, args=(uti,), daemon=True).start()

    def default_app_close():
        """Hide the default-app info and picker windows."""
        gui_default_show.hide()
        gui_default_picker.hide()

    def default_app_refresh():
        """Force LaunchServices to reload by restarting Finder."""
        rc, out, err = _run(["killall", "Finder"])
        if rc == 0:
            _notify("relaunched Finder")
        else:
            _notify(f"killall Finder failed: {err or rc}")
