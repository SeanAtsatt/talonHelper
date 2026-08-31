# Default-App Manager for Talon

**Date:** 2026-05-26
**Status:** Design approved, ready for implementation plan.

## Problem

Other applications periodically hijack the macOS default "open" handler for
file types I care about (e.g. `.txt`, `.md`, `.pdf`). I want voice commands in
Talon to inspect and restore the correct default, picking the target app from
a list to avoid typos.

## Scope

In scope:

- Operate on the **currently selected file** in Finder or Path Finder
  (whichever is frontmost).
- Three voice commands: `default show`, `default change`, `default refresh`.
- macOS only.

Out of scope (YAGNI):

- URL scheme handlers (`http://`, `mailto:`, etc.).
- Bulk operations across many extensions.
- Cross-machine persistence of preferences.
- Fallback to a "type the extension" mode when nothing is selected. (v1
  notifies and aborts.)

## Dependencies

**Correction (2026-05-28):** Talon's bundled Python has **no PyObjC** — `objc`,
`Foundation`, and `LaunchServices` all fail to import, and `talon.mac` only
exposes `applescript, ctrl, dock, headphone_motion, hotkey_system, runloop,
tap, ui`. The original design's plan to enumerate handlers via
`LSCopyAllRoleHandlersForContentType` is therefore impossible. Everything is
done with CLI tools via `subprocess` instead. This in turn collides with the
repo's own sandbox (`aaa_security.py`), resolved below.

- **`duti`** — Homebrew CLI (`brew install duti`). Used for all
  LaunchServices interaction:
  - `duti -x <ext>` → current default app (name, path, bundle id) — for `show`.
  - `duti -l <uti>` → all handler bundle IDs for a UTI — for `change`.
  - `duti -s <bundle_id> <uti> all` → set the default — for `pick`.
  - If missing, the script notifies with the install command and aborts.
- **`mdls`** — built-in. `mdls -name kMDItemContentType -raw <file>` reads the
  UTI of the selected file (needed for `duti -l`).
- **`mdfind`** — built-in. `mdfind "kMDItemCFBundleIdentifier == '<id>'"`
  resolves a bundle ID to its `.app` path, from which the picker derives a
  friendly display name. Best-effort: falls back to the bundle ID on failure.
- **`killall`** — built-in. `killall Finder` for `default refresh`.
- **`talon.mac.applescript`** — used to read the Finder / Path Finder
  selection (no subprocess).

### Sandbox interaction (`aaa_security.py`)

This feature runs inside the repo's own security sandbox, which blocks
`subprocess.Popen` / `os.system` from any file not in `TRUSTED_FILES` (swapping
the command for `false`). Because `default_app.py` legitimately needs `duti`,
`mdls`, `mdfind`, and `killall`, it is added to `TRUSTED_FILES`. This is more
secure than safelisting `duti` in `SAFE_COMMAND_EXECUTABLES`, which would let
*any* plugin silently change file associations (`duti -s` is state-changing).
The path-based trust check means a malicious plugin cannot impersonate
`default_app.py` by reusing the basename in another directory.

## File Layout

Two new files, matching the existing `mystuff/` convention of paired `.py`
and `.talon` files:

- `mystuff/default_app.py` — logic, picker GUI, Talon actions.
- `mystuff/default_app.talon` — voice command bindings.

## Voice Commands

| Command | Behavior |
|---|---|
| `default show` | Reads selected file. Logs and notifies: extension, UTI, current default app (name + bundle ID). No state change. |
| `default change` | Reads selected file. Enumerates candidate apps. Opens a numbered picker overlay. User says `pick <N>` to set that app as the default for the UTI. |
| `default refresh` | `killall Finder` to force LaunchServices reload. (Finder owns the system-wide association cache regardless of which file manager is frontmost.) Used if a change doesn't appear to take effect. |

## Picker Overlay

Matches the style of `mystuff/paths_panel.py`:

- `@imgui.open(y=10, x=500)` window.
- Title: `Default for .<ext> (<UTI>)`.
- One numbered row per candidate app: `<N>: <App Name>` — display-only
  truncation at ~30 chars.
- Current default marked with a leading `★`.
- Pagination via Next / Previous buttons if more than `DISPLAY_LIMIT` (20)
  candidates.
- Close button.
- Module-level `current_page` and `_candidates` (list of `(name, bundle_id)`
  tuples) hold picker state between the user's `default change` and their
  follow-up `pick <N>`.

The picker exposes a `user.default_app_pick(n: int)` action wired to a
`pick <number>` voice command (active only while the picker is showing,
guarded by an `imgui.GUI.showing` check or a context tag).

## Data Flow — `default change`

```
selected file path
    -> mdls -name kMDItemContentType -raw <path>
        -> UTI (e.g. public.plain-text)
            -> duti -l <uti>
                -> [bundle_id, ...]
                    -> mdfind "kMDItemCFBundleIdentifier == '<id>'"  (per id)
                        -> .app path -> basename minus ".app"
                            -> [(display_name, bundle_id), ...]
                                -> picker overlay
                                    -> on pick: duti -s <bundle_id> <UTI> all
```

Default bundle ID for the "*" mark comes from `duti -x <ext>` (3rd line).
Note: a `*` (asterisk) is used as the default marker rather than a Unicode
star, for reliable rendering in Talon's imgui.

## Selected-File Resolution

Frontmost-app dispatch via `talon.ui.active_app().name`:

- `Finder` → AppleScript:
  `tell application "Finder" to get POSIX path of (item 1 of (selection as alias list))`
- `Path Finder` → AppleScript:
  `tell application "Path Finder" to get POSIX path of (selection as alias list) item 1`
- Anything else → notify "Select a file in Finder or Path Finder first" and
  abort.

Empty selection → notify "No file selected" and abort.

## Error Handling

| Condition | Behavior |
|---|---|
| `duti` not on `PATH` | Notify: `default_app: install duti first — brew install duti`. Abort. |
| No file selected | Notify: `default_app: no file selected in Finder/Path Finder`. Abort. |
| `mdls` returns no UTI | Notify with the path it tried. Abort. |
| LaunchServices returns no handlers | Notify: `default_app: no apps registered for <UTI>`. Abort. |
| `duti -s` returns non-zero | Notify with stderr. Abort. |

All notifications go via `app.notify()` *and* `print()` (Talon log) so the
user has both a transient toast and a persistent record.

## Testing

Manual end-to-end:

1. Select a `.txt` file in Finder, say `default show`. Confirm log shows
   `public.plain-text` and the current default.
2. Say `default change`. Confirm picker lists TextEdit, BBEdit, VS Code, etc.
   Confirm current default has the ★.
3. Say `pick 3`. Confirm picker closes and the default updates (verify by
   re-issuing `default show`, or by `Get Info` in Finder).
4. Say `default refresh`. Confirm Finder relaunches.
5. Negative case: focus iTerm, say `default show`. Confirm "select a file"
   notification.
6. Negative case: temporarily rename `duti` on `PATH`, say `default change`.
   Confirm install-hint notification.

No automated tests — Talon scripts aren't unit-testable in isolation and the
feature is small enough that manual verification is appropriate.

## Files Touched

- **New:** `mystuff/default_app.py`
- **New:** `mystuff/default_app.talon`
- No edits to existing files.
