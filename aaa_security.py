"""
Security sandbox for Talon plugin execution.

Loads first (alphabetically) and monkey-patches os.system and subprocess.Popen
so that untrusted plugins cannot execute arbitrary shell commands without
approval through the system_command GUI.

Trusted files and Talon core code pass through unimpeded.

Reload-safe: originals are captured once and stored on the functions themselves
so that subsequent hot-reloads don't stack patches.
"""

import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

log = logging.getLogger("sandbox")

# ---------------------------------------------------------------------------
# 1. Save the real (unpatched) implementations — only on first load
# ---------------------------------------------------------------------------
# On hot-reload, os.system is already our patch. We stash the true originals
# as attributes so we can recover them across reloads.
if hasattr(os.system, "_sandbox_original"):
    _real_os_system = os.system._sandbox_original
else:
    _real_os_system = os.system

if hasattr(subprocess.Popen.__init__, "_sandbox_original"):
    _real_popen_init = subprocess.Popen.__init__._sandbox_original
else:
    _real_popen_init = subprocess.Popen.__init__

# ---------------------------------------------------------------------------
# 2. Constants
# ---------------------------------------------------------------------------
TALON_USER_DIR = str(Path.home() / ".talon" / "user")

# Full paths of files we trust to call subprocess/os.system directly.
# A malicious plugin cannot gain trust by reusing a basename in another dir.
TRUSTED_FILES: set[str] = {
    os.path.join(TALON_USER_DIR, "community", "core", "system_command.py"),
    os.path.join(TALON_USER_DIR, "community", "apps", "apple_terminal", "apple_terminal.py"),
    os.path.join(TALON_USER_DIR, "community", "apps", "iterm", "iterm.py"),
    os.path.join(TALON_USER_DIR, "mystuff", "myHelp.py"),
    os.path.join(TALON_USER_DIR, "mystuff", "default_app.py"),
    os.path.join(TALON_USER_DIR, "community", "core", "edit_text_file", "edit_text_file.py"),
    os.path.join(TALON_USER_DIR, "community", "core", "app_switcher", "app_switcher.py"),
    os.path.join(TALON_USER_DIR, "talon-ai-tools", "lib", "modelHelpers.py"),
    os.path.abspath(__file__),  # this file
}

# Executables considered safe (read-only queries, UI scripting).
# Matched against the first token / basename of the command.
SAFE_COMMAND_EXECUTABLES: set[str] = {
    "osascript",
    "lsof",
    "ps",
    "hostname",
    "which",
    "uname",
}

# Thread-local reentrancy guard
_tls = threading.local()

# When False, safe-command pass-throughs are not logged
verbose = False

# ---------------------------------------------------------------------------
# 3. Helpers
# ---------------------------------------------------------------------------

# Sentinel returned when the caller is an interactive/eval context (REPL,
# exec, etc.) — these should be treated as untrusted.
_INTERACTIVE_CALLER = "<interactive>"

# Filenames that indicate an interactive or dynamic-eval context.
_INTERACTIVE_FILENAMES = {"<console>", "<stdin>", "<string>", "<input>"}


def _frame_file(frame) -> str | None:
    """Best-effort source path for a frame.

    On current Talon builds, voice-action frames raise AttributeError on
    frame.f_code.co_filename, so fall back to the module's __file__ via
    f_globals (which remains accessible). Returns None for frames with no
    identifiable source — i.e. eval/exec/REPL contexts."""
    try:
        return frame.f_code.co_filename
    except Exception:
        pass
    try:
        return frame.f_globals.get("__file__")
    except Exception:
        return None


def _get_caller_file() -> str | None:
    """Walk the call stack and return the first frame that lives under
    TALON_USER_DIR.  Returns None if the caller is external (Talon core,
    stdlib, etc.) — external callers are unconditionally allowed.

    Returns _INTERACTIVE_CALLER if the call originates from a REPL or
    eval/exec context — these are treated as untrusted.

    Uses sys._getframe() instead of inspect.stack() to avoid crashes on
    Talon's C extension frames that lack f_code. Source paths come from
    _frame_file(), which falls back to f_globals['__file__'] because
    f_code.co_filename is unavailable on Talon voice-action frames."""
    try:
        frame = sys._getframe(2)  # skip _get_caller_file + patched wrapper
    except ValueError:
        return None
    saw_interactive = False
    while frame is not None:
        filename = _frame_file(frame)
        if filename:
            if filename.startswith(TALON_USER_DIR):
                return filename
            if filename in _INTERACTIVE_FILENAMES:
                saw_interactive = True
        else:
            # No identifiable source path → eval/exec/REPL frame. Treat as
            # interactive (untrusted) unless a trusted user-dir frame is
            # found deeper in the stack.
            saw_interactive = True
        frame = frame.f_back
    if saw_interactive:
        return _INTERACTIVE_CALLER
    return None


def _is_safe_command(args) -> bool:
    """Return True if the command's executable is in the safe list.

    Handles both string commands (shell=True) and list commands.
    """
    if args is None:
        return False

    if isinstance(args, str):
        # Shell command string — extract the first token
        executable = args.strip().split()[0] if args.strip() else ""
    elif isinstance(args, (list, tuple)) and len(args) > 0:
        executable = str(args[0])
    else:
        return False

    # Compare basename (handles full paths like /usr/bin/osascript)
    basename = os.path.basename(executable)
    return basename in SAFE_COMMAND_EXECUTABLES


def _format_cmd_for_log(args) -> str:
    """Return a short string representation of a command for logging."""
    if isinstance(args, str):
        s = args.strip()
    elif isinstance(args, (list, tuple)):
        s = " ".join(str(a) for a in args)
    else:
        s = str(args)
    return s[:120] + "..." if len(s) > 120 else s


def _route_to_approval(cmd_str: str):
    """Send a blocked command to the approval GUI via Talon actions.

    Uses a lazy import because system_command.py loads after this module.
    """
    try:
        from talon import actions
        actions.user.system_command(cmd_str)
    except Exception as exc:
        log.error(f"[SANDBOX] Failed to route to approval GUI: {exc}")


# ---------------------------------------------------------------------------
# 4. Patched os.system
# ---------------------------------------------------------------------------

def _patched_os_system(cmd):
    # Reentrancy guard
    if getattr(_tls, "in_sandbox", False):
        return _real_os_system(cmd)
    _tls.in_sandbox = True
    try:
        caller = _get_caller_file()
        cmd_display = _format_cmd_for_log(cmd)

        # External caller (Talon core / stdlib) → allow
        if caller is None:
            return _real_os_system(cmd)

        # Trusted file → allow
        if caller in TRUSTED_FILES:
            if verbose:
                log.debug(f"[SANDBOX] PASS (trusted {os.path.basename(caller)}): {cmd_display}")
            return _real_os_system(cmd)

        # Safe command → allow
        if _is_safe_command(cmd):
            if verbose:
                log.debug(f"[SANDBOX] PASS (safe cmd): {cmd_display}")
            return _real_os_system(cmd)

        # --- BLOCKED ---
        log.warning(
            f"[SANDBOX] BLOCKED os.system from {os.path.basename(caller)}: {cmd_display}"
        )
        _route_to_approval(cmd if isinstance(cmd, str) else str(cmd))
        return 1  # non-zero exit code signals failure to caller
    finally:
        _tls.in_sandbox = False


# ---------------------------------------------------------------------------
# 5. Patched subprocess.Popen.__init__
# ---------------------------------------------------------------------------

def _patched_popen_init(self, args, **kwargs):
    # Reentrancy guard
    if getattr(_tls, "in_sandbox", False):
        return _real_popen_init(self, args, **kwargs)
    _tls.in_sandbox = True
    try:
        caller = _get_caller_file()
        cmd_display = _format_cmd_for_log(args)

        # External caller → allow
        if caller is None:
            return _real_popen_init(self, args, **kwargs)

        # Trusted file → allow
        if caller in TRUSTED_FILES:
            if verbose:
                log.debug(f"[SANDBOX] PASS (trusted {os.path.basename(caller)}): {cmd_display}")
            return _real_popen_init(self, args, **kwargs)

        # Safe command → allow
        if _is_safe_command(args):
            if verbose:
                log.debug(f"[SANDBOX] PASS (safe cmd): {cmd_display}")
            return _real_popen_init(self, args, **kwargs)

        # --- BLOCKED ---
        log.warning(
            f"[SANDBOX] BLOCKED Popen from {os.path.basename(caller)}: {cmd_display}"
        )

        # Build a string representation for the approval GUI
        if isinstance(args, str):
            cmd_str = args
        elif isinstance(args, (list, tuple)):
            cmd_str = " ".join(str(a) for a in args)
        else:
            cmd_str = str(args)

        _route_to_approval(cmd_str)

        # Replace the command with "false" so Popen still returns a valid
        # object but the dangerous command never executes.
        # "false" exits immediately with code 1, empty stdout.
        return _real_popen_init(self, ["false"], **kwargs)
    finally:
        _tls.in_sandbox = False


# ---------------------------------------------------------------------------
# 6. Install the patches (stash originals for reload-safety)
# ---------------------------------------------------------------------------
_patched_os_system._sandbox_original = _real_os_system
_patched_popen_init._sandbox_original = _real_popen_init

os.system = _patched_os_system
subprocess.Popen.__init__ = _patched_popen_init

log.info("[SANDBOX] Security sandbox installed — os.system and subprocess.Popen patched")
