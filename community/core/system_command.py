import json
import logging
import os
import subprocess
from pathlib import Path

from talon import Module, actions, cron, imgui, ui

log = logging.getLogger("system_command")

mod = Module()
mod.tag("system_command_pending", desc="Active when a system command is awaiting approval")

main_screen = ui.main_screen()

# --- Persistent whitelist & blacklist ---
_DATA_DIR = Path(__file__).parent
WHITELIST_PATH = _DATA_DIR / "system_command_whitelist.json"
BLACKLIST_PATH = _DATA_DIR / "system_command_blacklist.json"
whitelisted_commands: set = set()
blacklisted_commands: set = set()


def _load_list(path: Path) -> set:
    try:
        if path.exists():
            with open(path) as f:
                return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        pass
    return set()


def _save_list(path: Path, data: set):
    try:
        with open(path, "w") as f:
            json.dump(sorted(data), f, indent=2)
    except OSError:
        log.error(f"[SYSTEM_CMD] Failed to save {path.name}")


whitelisted_commands = _load_list(WHITELIST_PATH)
blacklisted_commands = _load_list(BLACKLIST_PATH)

# --- Pending command state ---
pending_cmd: str | None = None
pending_blocking: bool = True
timeout_job = None
TIMEOUT_SECONDS = 30


def _auto_deny():
    """Auto-deny after timeout"""
    global timeout_job, pending_cmd
    cmd = pending_cmd
    timeout_job = None
    pending_cmd = None
    if confirm_gui.showing:
        confirm_gui.hide()
    _update_tag()
    log.warning(f"[SYSTEM_CMD] TIMEOUT denied: {cmd}")


def _execute_pending():
    """Execute the stored pending command"""
    global pending_cmd
    if pending_cmd is None:
        return
    cmd = pending_cmd
    blocking = pending_blocking
    pending_cmd = None
    _update_tag()
    log.info(f"[SYSTEM_CMD] EXECUTING: {cmd}")
    if blocking:
        os.system(cmd)
    else:
        subprocess.Popen(cmd, shell=True)


def _cleanup():
    """Hide GUI and cancel timeout"""
    global timeout_job
    if timeout_job:
        cron.cancel(timeout_job)
        timeout_job = None
    if confirm_gui.showing:
        confirm_gui.hide()
    _update_tag()


def _update_tag():
    """Enable/disable the pending tag based on state"""
    try:
        if pending_cmd is not None:
            ctx.tags = ["user.system_command_pending"]
        else:
            ctx.tags = []
    except Exception:
        pass


@imgui.open(
    x=main_screen.x + main_screen.width / 4,
    y=main_screen.y + main_screen.height / 3,
)
def confirm_gui(gui: imgui.GUI):
    gui.text("SYSTEM COMMAND REQUEST")
    gui.line()
    if pending_cmd:
        display = pending_cmd if len(pending_cmd) <= 120 else pending_cmd[:117] + "..."
        gui.text(f"Command: {display}")
    else:
        gui.text("(no command pending)")
    gui.line()
    if gui.button("Allow once"):
        actions.user.system_command_allow_once()
    if gui.button("Always allow"):
        actions.user.system_command_allow_always()
    if gui.button("Deny once"):
        actions.user.system_command_deny()
    if gui.button("Deny always"):
        actions.user.system_command_deny_always()


def _request_approval(cmd: str, blocking: bool):
    """Show approval GUI for a command, or auto-handle if listed"""
    global pending_cmd, pending_blocking, timeout_job

    # Auto-block blacklisted commands
    if cmd in blacklisted_commands:
        log.warning(f"[SYSTEM_CMD] BLACKLISTED - blocked: {cmd}")
        return

    # Auto-approve whitelisted commands
    if cmd in whitelisted_commands:
        log.info(f"[SYSTEM_CMD] WHITELISTED - auto-approved: {cmd}")
        if blocking:
            os.system(cmd)
        else:
            subprocess.Popen(cmd, shell=True)
        return

    # Replace any existing pending command
    log.info(f"[SYSTEM_CMD] PENDING approval: {cmd}")
    pending_cmd = cmd
    pending_blocking = blocking

    if timeout_job:
        cron.cancel(timeout_job)
    confirm_gui.show()
    _update_tag()
    timeout_job = cron.after(f"{TIMEOUT_SECONDS}s", _auto_deny)


# Context for tag management
from talon import Context

ctx = Context()


@mod.action_class
class Actions:
    def system_command(cmd: str):
        """execute a command on the system (requires approval)"""
        _request_approval(cmd, blocking=True)

    def system_command_nb(cmd: str):
        """execute a command on the system without blocking (requires approval)"""
        _request_approval(cmd, blocking=False)

    def system_command_allow_once():
        """Allow the pending system command this one time"""
        cmd = pending_cmd
        _cleanup()
        log.info(f"[SYSTEM_CMD] ALLOWED once: {cmd}")
        _execute_pending()

    def system_command_allow_always():
        """Allow the pending system command and remember it permanently"""
        global pending_cmd
        cmd = pending_cmd
        if pending_cmd:
            whitelisted_commands.add(pending_cmd)
            _save_list(WHITELIST_PATH, whitelisted_commands)
        _cleanup()
        log.info(f"[SYSTEM_CMD] WHITELISTED permanently: {cmd}")
        _execute_pending()

    def system_command_deny():
        """Deny the pending system command this one time"""
        global pending_cmd
        cmd = pending_cmd
        pending_cmd = None
        _cleanup()
        log.warning(f"[SYSTEM_CMD] DENIED once: {cmd}")

    def system_command_deny_always():
        """Deny the pending system command and blacklist it permanently"""
        global pending_cmd
        cmd = pending_cmd
        if pending_cmd:
            blacklisted_commands.add(pending_cmd)
            _save_list(BLACKLIST_PATH, blacklisted_commands)
        pending_cmd = None
        _cleanup()
        log.warning(f"[SYSTEM_CMD] BLACKLISTED permanently: {cmd}")

    def system_command_show_whitelist():
        """Show all permanently allowed commands"""
        if whitelisted_commands:
            for cmd in sorted(whitelisted_commands):
                print(f"  whitelisted: {cmd}")
        else:
            print("  (no whitelisted commands)")

    def system_command_show_blacklist():
        """Show all permanently denied commands"""
        if blacklisted_commands:
            for cmd in sorted(blacklisted_commands):
                print(f"  blacklisted: {cmd}")
        else:
            print("  (no blacklisted commands)")

    def system_command_clear_whitelist():
        """Remove all permanently allowed commands"""
        global whitelisted_commands
        whitelisted_commands.clear()
        _save_list(WHITELIST_PATH, whitelisted_commands)
        log.info("[SYSTEM_CMD] Whitelist cleared")

    def system_command_clear_blacklist():
        """Remove all permanently denied commands"""
        global blacklisted_commands
        blacklisted_commands.clear()
        _save_list(BLACKLIST_PATH, blacklisted_commands)
        log.info("[SYSTEM_CMD] Blacklist cleared")
