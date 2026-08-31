# Default-App Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add three Talon voice commands — `default show`, `default change`, `default refresh` — that inspect and reset the macOS default-open app for the file currently selected in Finder or Path Finder, with an `imgui` picker matching `paths_panel.py` style.

**Architecture:** Two new files in `mystuff/`. Python module exposes Talon actions and an `imgui` picker overlay; `.talon` file binds voice commands. Selected file is read via AppleScript. UTI lookup uses `mdls`. Candidate enumeration uses PyObjC `LaunchServices`. Default is set via the `duti` CLI.

**Tech Stack:** Talon (Python 3.11 with PyObjC bundled), `talon.mac.applescript`, `talon.imgui`, macOS `mdls`, `duti` (Homebrew).

**Testing note:** Talon scripts can only run inside the live Talon process. There are no automated tests for this feature — every task ends with a manual verification step performed in Talon, with the exact voice command to say and the exact behavior to observe. Do not invent unit tests; the design rejected them.

---

## File Structure

- **New:** `mystuff/default_app.py` — all logic: selected-file resolution, UTI/handler lookup, picker GUI, Talon actions.
- **New:** `mystuff/default_app.talon` — three voice-command bindings plus the `pick <number>` binding (gated by picker visibility).

One Python file is appropriate because all the pieces are tightly coupled (the picker GUI holds module-level state read by the `pick` action). Splitting further would obscure the data flow.

---

## Prerequisites

### Task 0: Install duti

**Files:** None (system setup only).

- [ ] **Step 1: Check if duti is already installed**

Run: `which duti`
Expected: either a path like `/opt/homebrew/bin/duti`, or empty output.

- [ ] **Step 2: Install duti if missing**

Run: `brew install duti`
Expected: download + install completes; `which duti` now returns a path.

- [ ] **Step 3: Smoke-test duti**

Run: `duti -x txt`
Expected: prints the bundle ID of the current default app for `.txt` (e.g. `com.apple.TextEdit`), or an error if no default is set. Either is fine — we just need to confirm `duti` runs.

No commit (this task changes no repo files).

---

## Task 1: Skeleton module loads without errors

Goal: Create the empty Python and `.talon` files, confirm Talon loads them.

**Files:**
- Create: `mystuff/default_app.py`
- Create: `mystuff/default_app.talon`

- [ ] **Step 1: Create the Python module**

Write `mystuff/default_app.py`:

```python
from talon import Module

mod = Module()


@mod.action_class
class Actions:
    def default_app_show():
        """Show the current default app for the selected file's extension."""
        print("default_app_show: stub")

    def default_app_change():
        """Open a picker of candidate apps for the selected file's extension."""
        print("default_app_change: stub")

    def default_app_refresh():
        """Force LaunchServices to reload by restarting Finder."""
        print("default_app_refresh: stub")
```

- [ ] **Step 2: Create the Talon command file**

Write `mystuff/default_app.talon`:

```
default show: user.default_app_show()
default change: user.default_app_change()
default refresh: user.default_app_refresh()
```

- [ ] **Step 3: Manually verify Talon loads the module**

Tail the Talon log in a terminal:

Run: `tail -f ~/.talon/talon.log`

Save both new files. In the log, expect to see a line referencing `default_app.py` being loaded with no traceback. (If Talon is configured to not log every load, the absence of any traceback below the save event is sufficient.)

- [ ] **Step 4: Manually verify each stub command fires**

With the Talon log still tailing, say each command and watch for the matching `stub` print:

- Say `default show` → expect `default_app_show: stub`
- Say `default change` → expect `default_app_change: stub`
- Say `default refresh` → expect `default_app_refresh: stub`

If any command isn't recognized, fix the `.talon` file before proceeding.

- [ ] **Step 5: Commit**

```bash
git add mystuff/default_app.py mystuff/default_app.talon
git commit -m "Add default_app skeleton with stub voice commands"
```

---

## Task 2: Selected-file resolution

Goal: Add `_get_selected_file()` returning the POSIX path of the file selected in the frontmost file-manager app, or `None` if the frontmost app isn't a supported file manager or nothing is selected.

**Files:**
- Modify: `mystuff/default_app.py`

- [ ] **Step 1: Add the helper and wire it into `default_app_show`**

Replace the contents of `mystuff/default_app.py` with:

```python
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
```

- [ ] **Step 2: Manually verify happy path in Finder**

1. Bring Finder forward, click a `.txt` file in any folder so it's highlighted.
2. Say `default show`.
3. Expect a toast and a Talon log line: `default_app: selected: /Users/seanatsatt/.../<file>.txt`.

- [ ] **Step 3: Manually verify happy path in Path Finder**

1. Bring Path Finder forward, click any file.
2. Say `default show`.
3. Expect the same toast with the correct file path.

- [ ] **Step 4: Manually verify "no file selected" case**

1. In Finder, click an empty area of the desktop or use `cmd-shift-a` to deselect.
2. Say `default show`.
3. Expect toast: `default_app: select a file in Finder or Path Finder first`.

- [ ] **Step 5: Manually verify "wrong app" case**

1. Bring iTerm (or any non-file-manager app) forward.
2. Say `default show`.
3. Expect toast: `default_app: select a file in Finder or Path Finder first`.

- [ ] **Step 6: Commit**

```bash
git add mystuff/default_app.py
git commit -m "Add selected-file resolution for Finder and Path Finder"
```

---

## Task 3: UTI + current-default lookup

Goal: Given a file path, return `(extension, uti, default_bundle_id, default_app_name)`. Wire it into `default_app_show` so the command reports all four.

**Files:**
- Modify: `mystuff/default_app.py`

- [ ] **Step 1: Extend the imports**

Replace the existing import block at the top of `mystuff/default_app.py` with:

```python
import os
import shutil
import subprocess
from typing import Optional, Tuple

from talon import Module, app, ui
from talon.mac import applescript
```

- [ ] **Step 2: Add the lookup helpers**

Add these helpers to `mystuff/default_app.py` (after `_notify`, before the `@mod.action_class`):

```python
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
```

- [ ] **Step 3: Update `default_app_show` to use the lookup**

Replace the body of `default_app_show` with:

```python
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
```

- [ ] **Step 4: Manually verify against a known file type**

1. In Finder, select a `.txt` file.
2. Say `default show`.
3. Expect toast like: `default_app: .txt (public.plain-text) -> TextEdit [com.apple.TextEdit]`.

Repeat for a `.pdf` and a `.png`. Confirm the toast format is correct and the values match what Finder's *Get Info → Open with* dropdown shows.

- [ ] **Step 5: Manually verify a file with no extension**

1. Select a file with no extension (e.g. a Unix executable).
2. Say `default show`.
3. Expect a sensible toast: extension will be empty, but the UTI lookup should still succeed (e.g. `public.unix-executable`).

If the UTI is unavailable, expect the `could not read UTI` toast. Either outcome is acceptable.

- [ ] **Step 6: Commit**

```bash
git add mystuff/default_app.py
git commit -m "Add UTI lookup and current-default reporting to default show"
```

---

## Task 4: Candidate enumeration

Goal: Given a UTI, return `[(display_name, bundle_id), ...]` for every app registered to handle it. Sort by display name (case-insensitive), but pin the current default to position 0.

**Files:**
- Modify: `mystuff/default_app.py`

- [ ] **Step 1: Add the enumeration helper**

Add this helper to `mystuff/default_app.py` (just below `_app_name_for_bundle`):

```python
def _candidate_apps(uti: str, default_bundle_id: Optional[str]) -> list:
    """Return [(display_name, bundle_id), ...] for apps that handle this UTI.

    Sorted case-insensitive by display name, with the current default (if any)
    moved to the front.
    """
    from LaunchServices import (
        LSCopyAllRoleHandlersForContentType,
        kLSRolesAll,
    )

    raw = LSCopyAllRoleHandlersForContentType(uti, kLSRolesAll) or []
    seen = set()
    items = []
    for bundle_id in raw:
        bid = str(bundle_id)
        if bid in seen:
            continue
        seen.add(bid)
        name = _app_name_for_bundle(bid) or bid
        items.append((name, bid))

    items.sort(key=lambda pair: pair[0].casefold())
    if default_bundle_id:
        front = [p for p in items if p[1] == default_bundle_id]
        rest = [p for p in items if p[1] != default_bundle_id]
        items = front + rest
    return items
```

- [ ] **Step 2: Add a temporary log-dump path in `default_app_change`**

Replace the stub `default_app_change` with this *interim* version. The real picker comes in Task 5, but printing candidates first lets us verify the enumeration before adding GUI complexity.

```python
    def default_app_change():
        """Open a picker of candidate apps for the selected file's extension."""
        path = _get_selected_file()
        if path is None:
            _notify("select a file in Finder or Path Finder first")
            return
        info = _file_info(path)
        if info is None:
            _notify(f"could not read UTI for {path}")
            return
        ext, uti, default_bid, _ = info
        candidates = _candidate_apps(uti, default_bid)
        if not candidates:
            _notify(f"no apps registered for {uti}")
            return
        print(f"default_app: candidates for .{ext} ({uti}):")
        for i, (name, bid) in enumerate(candidates, 1):
            marker = "*" if bid == default_bid else " "
            print(f"  {marker} {i}: {name} [{bid}]")
        _notify(f"{len(candidates)} candidates for .{ext} - see log")
```

- [ ] **Step 3: Manually verify candidate listing for a common type**

1. In Finder, select a `.txt` file.
2. Say `default change`.
3. In `tail -f ~/.talon/talon.log`, expect output like:

```
default_app: candidates for .txt (public.plain-text):
   * 1: TextEdit [com.apple.TextEdit]
     2: BBEdit [com.barebones.bbedit]
     3: Visual Studio Code [com.microsoft.VSCode]
     ...
```

The `*` should mark the current default, which should appear first.

- [ ] **Step 4: Cross-check against Finder's "Open With" menu**

1. In Finder, right-click the same `.txt` file → `Open With`.
2. Compare the apps Finder lists against the candidates printed in the log. Every app in Finder's submenu should appear in the candidate list (extras in the candidate list are OK — Finder filters; LaunchServices does not).

If a glaringly common app is missing from the candidate list (e.g. TextEdit doesn't show up for `.txt`), pause and debug — the UTI or enumeration is wrong.

- [ ] **Step 5: Commit**

```bash
git add mystuff/default_app.py
git commit -m "Add candidate app enumeration via LaunchServices"
```

---

## Task 5: Picker overlay and `pick <N>` action

Goal: Replace the log-dump with an `imgui` picker that matches `paths_panel.py`. Add a `default_app_pick(n: int)` action that calls `duti -s <bundle_id> <UTI> all`. Add a `pick <number>` voice binding gated by picker visibility.

**Files:**
- Modify: `mystuff/default_app.py`
- Modify: `mystuff/default_app.talon`

- [ ] **Step 1: Add the picker GUI, module state, and `_set_default` helper**

Extend the import block at the top of `mystuff/default_app.py`. The full block should now be:

```python
import math
import os
import shutil
import subprocess
from typing import Optional, Tuple

from talon import Module, app, imgui, ui
from talon.mac import applescript
```

Add these module-level globals just below the `mod = Module()` line:

```python
DISPLAY_LIMIT = 20
STRING_LIMIT = 30

_state = {
    "ext": "",
    "uti": "",
    "default_bid": None,
    "candidates": [],   # list of (name, bundle_id)
    "page": 1,
}
```

Add the picker GUI and the `duti`-setting helper just above the `@mod.action_class` block:

```python
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
    page_items = candidates[start : start + DISPLAY_LIMIT]
    for offset, (name, bid) in enumerate(page_items, 1):
        n = start + offset
        display = name if len(name) <= STRING_LIMIT else name[: STRING_LIMIT - 2] + ".."
        star = "*" if bid == default_bid else " "
        gui.text(f"{star} {n}: {display}")

    gui.spacer()
    gui.text('say "pick <number>" to set as default')
    gui.spacer()
    if total_pages > 1:
        if gui.button("Next"):
            _state["page"] = (page % total_pages) + 1
        if gui.button("Previous"):
            _state["page"] = ((page - 2) % total_pages) + 1
        gui.spacer()
    if gui.button("Default close"):
        gui_default_picker.hide()


def _set_default(bundle_id: str, uti: str) -> bool:
    """Set bundle_id as the default handler for uti. Returns True on success."""
    if shutil.which("duti") is None:
        _notify("install duti first - brew install duti")
        return False
    try:
        subprocess.run(
            ["duti", "-s", bundle_id, uti, "all"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        _notify(f"duti failed: {exc.stderr.strip() or exc}")
        return False
    return True
```

- [ ] **Step 2: Replace `default_app_change` body and add `default_app_pick`**

Replace the interim `default_app_change` with:

```python
    def default_app_change():
        """Open a picker of candidate apps for the selected file's extension."""
        path = _get_selected_file()
        if path is None:
            _notify("select a file in Finder or Path Finder first")
            return
        info = _file_info(path)
        if info is None:
            _notify(f"could not read UTI for {path}")
            return
        ext, uti, default_bid, _ = info
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
```

Add a new action method inside the same `Actions` class:

```python
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
```

- [ ] **Step 3: Wire the `pick <number>` voice command**

Replace `mystuff/default_app.talon` with this exact content:

```
default show: user.default_app_show()
default change: user.default_app_change()
default refresh: user.default_app_refresh()
pick <number>: user.default_app_pick(number)
```

The `default_app_pick` action no-ops when the picker isn't showing (Step 2 already added this guard), so a globally-active `pick <number>` is safe. If you find the global binding interferes with other commands, revisit and add a proper context tag.

- [ ] **Step 4: Manually verify the picker appears with correct contents**

1. In Finder, select a `.txt` file.
2. Say `default change`.
3. Expect a window in the top-right showing:

```
Default for .txt (public.plain-text)  (1/1 or 1/2)
-----------------------------------
* 1: TextEdit
  2: BBEdit
  3: Visual Studio Code
  ...
```

The `*` should mark the current default and that entry should be in position 1.

- [ ] **Step 5: Manually verify pagination (if >20 candidates)**

If a UTI like `public.html` has more than 20 candidates:

1. Trigger the picker against an `.html` file.
2. Confirm Next / Previous buttons appear.
3. Click Next, confirm page counter advances and rows show entries 21–40.

If no UTI on your system has >20 handlers, mark this step done and move on.

- [ ] **Step 6: Manually verify setting a default**

1. With the picker open from Step 4, look up the number of an app *other* than the current default. Say `pick <that number>`.
2. Expect the picker to close, a toast: `default_app: set default for public.plain-text -> <App Name>`.
3. Verify the change: in Finder, right-click the same file → *Get Info*. The *Open with* dropdown should now show the app you picked.
4. Say `default change` again. The new default should now appear with the `*` and at position 1.

- [ ] **Step 7: Manually verify out-of-range pick**

1. With the picker open, say `pick 999`.
2. Expect toast: `default_app: pick 999: out of range (1..N)`. Picker stays open.

- [ ] **Step 8: Manually verify duti-missing error**

This step is optional but recommended. Either:

(a) Temporarily rename duti: `sudo mv $(which duti) $(which duti).bak`. Trigger the picker, pick anything, expect the toast `default_app: install duti first - brew install duti`. Restore: `sudo mv $(which duti).bak $(which duti)`.

(b) Skip if you don't want to touch a Homebrew install.

- [ ] **Step 9: Commit**

```bash
git add mystuff/default_app.py mystuff/default_app.talon
git commit -m "Add default-app picker overlay and pick command"
```

---

## Task 6: `default refresh`

Goal: Implement the `default_app_refresh` action so it relaunches Finder. (Finder owns the system-wide LaunchServices cache; bouncing it forces a reload after a default change.)

**Files:**
- Modify: `mystuff/default_app.py`

- [ ] **Step 1: Implement `default_app_refresh`**

Replace the stub `default_app_refresh` body with:

```python
    def default_app_refresh():
        """Force LaunchServices to reload by restarting Finder."""
        try:
            subprocess.run(["killall", "Finder"], check=True)
            _notify("relaunched Finder")
        except subprocess.CalledProcessError as exc:
            _notify(f"killall Finder failed: {exc}")
```

- [ ] **Step 2: Manually verify Finder relaunches**

1. Bring Finder forward so you can see its windows.
2. Say `default refresh`.
3. Expect: Finder windows briefly disappear and reopen; toast `default_app: relaunched Finder`.

- [ ] **Step 3: Manually verify it works when Path Finder is frontmost**

1. Bring Path Finder forward.
2. Say `default refresh`.
3. Expect: Finder (in the background) relaunches; toast appears; Path Finder is unaffected.

- [ ] **Step 4: Commit**

```bash
git add mystuff/default_app.py
git commit -m "Implement default refresh via killall Finder"
```

---

## Task 7: End-to-end regression sweep

Goal: Run the full happy path once more on a clean session to confirm nothing regressed across the six tasks. Then sanity-check error paths.

**Files:** None (verification only).

- [ ] **Step 1: Restart Talon**

Quit Talon and relaunch it. This ensures the module is loaded fresh (not from cached state during development).

Tail the log: `tail -f ~/.talon/talon.log`. Confirm no traceback below the startup banner.

- [ ] **Step 2: Full happy-path sweep**

In Finder, select a `.txt` file. Run all four commands in sequence:

1. `default show` → toast with extension, UTI, current default. Passes.
2. `default change` → picker opens, current default starred and at top. Passes.
3. `pick 2` (or any non-default number) → picker closes, default updates, toast confirms. Passes.
4. `default show` → toast now shows the new default. Passes.
5. `default refresh` → Finder relaunches, toast confirms. Passes.
6. Revert to original default: `default change`, then `pick <number of original>`. Passes.

- [ ] **Step 3: Error-path sweep**

1. Bring iTerm forward. Say `default show`. Expect "select a file" toast.
2. In Finder, deselect everything (`cmd-shift-a`). Say `default change`. Expect "select a file" toast.
3. With the picker closed, say `pick 1`. Expect: nothing happens (no toast, no error). Picker action no-ops as designed.

- [ ] **Step 4: Final commit (if any cleanup needed)**

If you noticed any leftover debug prints or dead code while running the sweep, remove them now:

```bash
git diff mystuff/default_app.py
# fix anything you don't like, then:
git add mystuff/default_app.py
git commit -m "Clean up default_app debug output"
```

If the diff is empty, skip this step.

---

## Done

All three commands are functional, error paths give useful feedback, and the
picker matches the visual style of `paths_panel.py`. No automated tests
(intentional — see the spec). Future extensions (URL schemes, bulk ops,
typed-extension fallback) are out of scope and were explicitly deferred
in design.
