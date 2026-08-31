# Talon Helper

Custom Talon voice command enhancements: a security sandbox for plugin execution and a directory navigation system with named destinations.

## Features

### Directory Navigation with Named Destinations

Say **"paths show"** to display a GUI panel listing all your named destinations — the spoken-form names you can use with **"go \<name\>"** to jump to any directory. Names are pulled from `user.system_paths` and displayed alphabetically with pagination.

| Voice Command | Action |
|---------------|--------|
| `paths show` | Toggle the destinations panel |
| `paths close` | Hide the destinations panel |
| `go <name>` | Navigate to the named destination (Path Finder) |
| `save here as <name>` | Save the current directory as a new named destination |

Destinations are stored in `mystuff/system_paths.talon-list`. Edit that file directly or use the "save here as" voice command to add new entries.

### Security Sandbox

A monkey-patching sandbox that intercepts `os.system()` and `subprocess.Popen()` calls from untrusted Talon plugins, routing them through an approval GUI before execution.

#### Problem

Any `.py` file in `~/.talon/user/` can call `os.system()` or `subprocess.Popen()` to execute arbitrary shell commands with no oversight. The approval GUI in `system_command.py` exists but plugins bypass it by calling subprocess directly.

#### How It Works

`aaa_security.py` loads first (alphabetically before all other user modules) and patches Python's command execution functions at import time.

For every intercepted call, the sandbox checks the call stack:

1. **External callers** (Talon core, stdlib) - pass through unconditionally
2. **Trusted files** (audited first-party code) - pass through
3. **Safe commands** (read-only utilities like `osascript`, `ps`, `lsof`) - pass through
4. **Everything else** - blocked and routed to the approval GUI

The approval GUI (`system_command.py`) presents four options: Allow once, Always allow, Deny once, Deny always. Whitelisted/blacklisted commands are persisted to JSON files.

### Flex Mouse Grid

[brollin/flex-mouse-grid](https://github.com/brollin/flex-mouse-grid) - voice-driven
mouse positioning via a letter/number grid overlay, named points, and OpenCV box
detection. Cloned to `~/.talon/user/flex-mouse-grid`; **not vendored into this repo**,
so the notes below are the recovery record.

#### Install

```sh
git clone https://github.com/brollin/flex-mouse-grid ~/.talon/user/flex-mouse-grid
```

`numpy` already ships inside Talon. `opencv-python-headless` is *not* needed in
Talon's own environment - see the interpreter note below.

#### Two local changes are required

Neither survives a `git pull`. Re-apply both after any upstream update.

**1. Trust entry in `aaa_security.py`.** Box detection shells out to
`.find_boxes.py` and parses its stdout. The approval GUI cannot serve this case:
`_execute_pending()` runs approved commands detached via
`subprocess.Popen(cmd, shell=True)` and discards stdout, so "allow always" can
never make `boxes` work. Only a `TRUSTED_FILES` entry can. The call is fixed-argv
with no shell and no user input, which is what makes it auditable - **re-audit that
subprocess call after every upstream pull.**

**2. Interpreter patch in `flex_mouse_grid.py`.** Upstream runs the box-detection
script under `sys.executable` (Talon's bundled python). That fails on macOS:

```
ImportError: dlopen(.../cv2/cv2.abi3.so): code signature not valid for use in
process: mapping process and mapped file (non-platform) have different Team IDs
```

Talon.app is signed with a hardened runtime (`flags=0x10000(runtime)`,
TeamIdentifier `D7SCFBXQXZ`) and does **not** carry the
`com.apple.security.cs.disable-library-validation` entitlement, so its python
refuses to load any native extension signed by a different team. Ad-hoc
re-signing does not help - library validation requires a *matching* Team ID, and
ad-hoc has none.

The patch replaces `sys.executable` with `_find_boxes_interpreter()`, which probes
`/usr/bin/python3` then `/opt/homebrew/bin/python3` for one that can import
`cv2` and `numpy`, falling back to `sys.executable`. System python is unhardened
(`flags=0x0`, no Team ID), so it loads cv2 fine.

Box detection therefore depends on cv2+numpy being installed for a *system*
python:

```sh
/usr/bin/python3 -m pip install --user opencv-python-headless numpy
```

Currently satisfied by cv2 5.0.0 / numpy 2.0.2 under
`~/Library/Python/3.9/lib/python/site-packages`. Note `/usr/bin/python3` comes
from Xcode Command Line Tools; removing CLT breaks `boxes` (the grid and named
points keep working).

#### Command distinctness

Checked against all 3,205 command rules in `~/.talon/user`. Flex's always-active
leading words - `box`, `boxes`, `flex`, `map`, `point`, `points`, `remap`,
`unmap` - are claimed by flex exclusively. Two overlaps, both benign:

| Overlap | Detail |
|---------|--------|
| `grid close` | Flex's is global; community's `grid (off/close/hide)` is gated on `user.mouse_grid_showing`, so they collide only when the community grid is open. **Say "flex grid close"** - the `flex` prefix is optional precisely for this. |
| `press <user.keys>` | Duplicated in `dictation_mode.talon`; both bind to `key(keys)`, so behavior is identical either way. Already global in `keys.talon`, making flex's copy redundant rather than conflicting. |

While the grid is showing, `flex_mouse_grid_active.talon` captures bare
`<letter>`, `<letter> <letter>`, and bare `<number>`. That shadows any other
single-letter or bare-number command until the grid closes - by design, but it
makes the grid effectively modal.

#### Removal

Delete `~/.talon/user/flex-mouse-grid` (`rm -rf -rf`-style removal of that one
directory), then drop the `flex-mouse-grid` line from `TRUSTED_FILES`.

## Files

| File | Purpose |
|------|---------|
| `aaa_security.py` | Security sandbox - patches os.system and subprocess.Popen |
| `community/core/system_command.py` | Approval GUI with whitelist/blacklist persistence |
| `mystuff/paths_panel.py` | Destinations panel (imgui), "paths show" / "paths close" |
| `mystuff/system_paths.talon-list` | Named destination definitions |
| `mystuff/path_finder.py` | Path Finder address support, backs "go <name>" |
| `community/apps/iterm/iterm.py` | Defines the "save here as" action |

#### Trusted Files

These files have been audited and are allowed to execute commands directly:

| File | Reason |
|------|--------|
| `community/core/system_command.py` | The approval GUI itself |
| `community/apps/apple_terminal/apple_terminal.py` | Terminal CWD detection |
| `community/apps/iterm/iterm.py` | iTerm CWD detection |
| `mystuff/myHelp.py` | Personal helper using osascript |
| `community/core/edit_text_file/edit_text_file.py` | File editing via subprocess |
| `community/core/app_switcher/app_switcher.py` | Application switching |
| `mystuff/default_app.py` | Default-app management via duti |
| `talon-ai-tools/lib/modelHelpers.py` | AI model integration |
| `flex-mouse-grid/flex_mouse_grid.py` | OpenCV box detection subprocess (see Flex Mouse Grid) |
| `aaa_security.py` | The sandbox itself |

Trust is based on **full file paths**, not basenames. A malicious plugin cannot gain trust by naming itself `apple_terminal.py` in a different directory.

#### Safe Commands

These executables are allowed from any caller (read-only queries):

`osascript`, `lsof`, `ps`, `hostname`, `which`, `uname`

#### Adding a New Trusted File

Edit `TRUSTED_FILES` in `aaa_security.py`:

```python
TRUSTED_FILES: set[str] = {
    # ... existing entries ...
    os.path.join(TALON_USER_DIR, "path", "to", "new_file.py"),
}
```

#### Verification

| Test | Expected |
|------|----------|
| Talon starts | `[SANDBOX] Security sandbox installed` in talon.log |
| Voice command from trusted file | `[SANDBOX] PASS (trusted ...)` in log |
| REPL: `os.system("echo test")` | Blocked, approval GUI appears |
| REPL: `subprocess.run(["echo", "test"])` | Blocked, approval GUI appears |
| REPL: `subprocess.run(["osascript", ...])` | Passes through (safe command) |
| Existing voice commands | No regressions |

#### Design Decisions

- **`["false"]` replacement for blocked Popen**: Can't raise an exception (would crash the plugin). Instead, replaces with `false` (Unix utility that exits with code 1). The Popen object is valid but the command doesn't run.
- **Thread-local reentrancy guard**: Prevents infinite loops if a patched call triggers another patched call.
- **Lazy import of Talon actions**: `system_command.py` loads after `aaa_security.py`, so actions are imported inside the function body.
- **Belt-and-suspenders in system_command.py**: Imports the real `os.system` from the sandbox module and uses it directly when executing approved commands, avoiding any stack inspection overhead.
