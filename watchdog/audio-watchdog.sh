#!/usr/bin/env bash
# audio-watchdog.sh — keep the mic input alive on macOS Tahoe.
# Routine path (toggle) needs no root. See watchdog/README.md.
set -u

# ---- config -------------------------------------------------------------
TARGET_DEVICE="Sennheiser Profile"   # flaky USB mic to babysit (default input)
AWAY_INPUT="HD Pro Webcam C920"      # other USB input to bounce through
INTERVAL=300                         # seconds; keep in sync with the plist
LABEL="com.talon.audio-watchdog"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SETTLE=0.3                           # seconds between the two input switches

# ---- overridable for testing -------------------------------------------
SWITCHAUDIO="${SWITCHAUDIO_BIN:-SwitchAudioSource}"
LOG_FILE="${WATCHDOG_LOG:-$HOME/Library/Logs/talon-audio-watchdog.log}"
LOG_MAX_BYTES=1048576

# ---- logging ------------------------------------------------------------
rotate_log() {
  [ -f "$LOG_FILE" ] || return 0
  local size
  size=$(wc -c < "$LOG_FILE" 2>/dev/null | tr -d ' ')
  [ -n "$size" ] && [ "$size" -gt "$LOG_MAX_BYTES" ] && mv -f "$LOG_FILE" "$LOG_FILE.1"
  return 0
}

log() {
  local action="$1" detail="${2:-}" result="${3:-}"
  mkdir -p "$(dirname "$LOG_FILE")"
  rotate_log
  printf '%s\t%s\t%s\t%s\n' "$(date +%Y-%m-%dT%H:%M:%S%z)" "$action" "$detail" "$result" >> "$LOG_FILE"
}

usage() {
  cat >&2 <<EOF
usage: audio-watchdog.sh <toggle|reset|install|uninstall|status>
  toggle     bounce the babysat input device out-and-back (default; no root)
  reset      heavy CoreAudio reset (destructive, manual, prompts for sudo)
  install    load the launchd agent (every ${INTERVAL}s)
  uninstall  unload and remove the launchd agent
  status     show agent state and recent log
EOF
}

main() {
  local cmd="${1:-}"
  case "$cmd" in
    toggle)    shift; cmd_toggle "$@";;
    reset)     shift; cmd_reset "$@";;
    install)   shift; cmd_install "$@";;
    uninstall) shift; cmd_uninstall "$@";;
    status)    shift; cmd_status "$@";;
    *)         usage; exit 2;;
  esac
}

# Placeholder command functions (implemented in later tasks).
cmd_toggle()    { log toggle "not-implemented" skip; }
cmd_reset()     { :; }
cmd_install()   { :; }
cmd_uninstall() { :; }
cmd_status()    { :; }

# Run main only when executed directly (so tests can source this file).
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  main "$@"
fi
