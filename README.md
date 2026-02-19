# Security Sandbox for Talon Plugin Execution

A monkey-patching sandbox that intercepts `os.system()` and `subprocess.Popen()` calls from untrusted Talon plugins, routing them through an approval GUI before execution.

## Problem

Any `.py` file in `~/.talon/user/` can call `os.system()` or `subprocess.Popen()` to execute arbitrary shell commands with no oversight. The approval GUI in `system_command.py` exists but plugins bypass it by calling subprocess directly.

## How It Works

`aaa_security.py` loads first (alphabetically before all other user modules) and patches Python's command execution functions at import time.

For every intercepted call, the sandbox checks the call stack:

1. **External callers** (Talon core, stdlib) - pass through unconditionally
2. **Trusted files** (audited first-party code) - pass through
3. **Safe commands** (read-only utilities like `osascript`, `ps`, `lsof`) - pass through
4. **Everything else** - blocked and routed to the approval GUI

The approval GUI (`system_command.py`) presents four options: Allow once, Always allow, Deny once, Deny always. Whitelisted/blacklisted commands are persisted to JSON files.

## Files

| File | Purpose |
|------|---------|
| `~/.talon/user/aaa_security.py` | The sandbox module - patches os.system and subprocess.Popen |
| `community/core/system_command.py` | Approval GUI - imports real functions as belt-and-suspenders bypass |

## Trusted Files

These files have been audited and are allowed to execute commands directly:

| File | Reason |
|------|--------|
| `community/core/system_command.py` | The approval GUI itself |
| `community/apps/apple_terminal/apple_terminal.py` | Terminal CWD detection |
| `community/apps/iterm/iterm.py` | iTerm CWD detection |
| `mystuff/myHelp.py` | Personal helper using osascript |
| `community/core/edit_text_file/edit_text_file.py` | File editing via subprocess |
| `community/core/app_switcher/app_switcher.py` | Application switching |
| `talon-ai-tools/lib/modelHelpers.py` | AI model integration |
| `aaa_security.py` | The sandbox itself |

Trust is based on **full file paths**, not basenames. A malicious plugin cannot gain trust by naming itself `apple_terminal.py` in a different directory.

## Safe Commands

These executables are allowed from any caller (read-only queries):

`osascript`, `lsof`, `ps`, `hostname`, `which`, `uname`

## Adding a New Trusted File

Edit `TRUSTED_FILES` in `aaa_security.py`:

```python
TRUSTED_FILES: set[str] = {
    # ... existing entries ...
    os.path.join(TALON_USER_DIR, "path", "to", "new_file.py"),
}
```

## Verification

| Test | Expected |
|------|----------|
| Talon starts | `[SANDBOX] Security sandbox installed` in talon.log |
| Voice command from trusted file | `[SANDBOX] PASS (trusted ...)` in log |
| REPL: `os.system("echo test")` | Blocked, approval GUI appears |
| REPL: `subprocess.run(["echo", "test"])` | Blocked, approval GUI appears |
| REPL: `subprocess.run(["osascript", ...])` | Passes through (safe command) |
| Existing voice commands | No regressions |

## Design Decisions

- **`["false"]` replacement for blocked Popen**: Can't raise an exception (would crash the plugin). Instead, replaces with `false` (Unix utility that exits with code 1). The Popen object is valid but the command doesn't run.
- **Thread-local reentrancy guard**: Prevents infinite loops if a patched call triggers another patched call.
- **Lazy import of Talon actions**: `system_command.py` loads after `aaa_security.py`, so actions are imported inside the function body.
- **Belt-and-suspenders in system_command.py**: Imports the real `os.system` from the sandbox module and uses it directly when executing approved commands, avoiding any stack inspection overhead.
