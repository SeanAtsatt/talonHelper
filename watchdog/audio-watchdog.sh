#!/usr/bin/env bash
# audio-watchdog.sh — keep the mic input alive on macOS Tahoe.
# Routine path (toggle) needs no root. See watchdog/README.md.
set -u

# launchd runs agents with a minimal PATH (/usr/bin:/bin:...) that omits
# Homebrew, so SwitchAudioSource would be "command not found". Prepend both
# Homebrew prefixes (Apple Silicon and Intel) so the agent finds it.
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

# ---- config -------------------------------------------------------------
TARGET_DEVICE="Sennheiser Profile"   # flaky USB mic to babysit (default input)
AWAY_INPUT="HD Pro Webcam C920"      # other USB input to bounce through
INTERVAL=300                         # seconds; keep in sync with the plist
LABEL="com.talon.audio-watchdog"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
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

current_input() { "$SWITCHAUDIO" -c -t input; }

input_present() {
  local name="$1" line
  while IFS= read -r line; do [ "$line" = "$name" ] && return 0; done < <("$SWITCHAUDIO" -a -t input)
  return 1
}

set_input() { "$SWITCHAUDIO" -s "$1" -t input >/dev/null; }

cmd_toggle() {
  local cur
  cur="$(current_input)"
  if [ -z "$cur" ]; then
    log error - "no-input-device"
    return 1
  fi
  if [ "$cur" != "$TARGET_DEVICE" ]; then
    log skip "$cur" "not-target"
    return 0
  fi
  if ! input_present "$AWAY_INPUT"; then
    log error "$AWAY_INPUT" "away-input-absent"
    return 1
  fi
  if ! set_input "$AWAY_INPUT"; then
    log error "$AWAY_INPUT" "switch-away-failed"
    return 1
  fi
  sleep "$SETTLE"
  if ! set_input "$TARGET_DEVICE"; then
    log error "$TARGET_DEVICE" "restore-failed"
    return 1
  fi
  log toggle "$TARGET_DEVICE" ok
  return 0
}

cmd_reset() {
  local assume_yes=0
  [ "${1:-}" = "--yes" ] && assume_yes=1

  echo "WARNING: this will kill audio for ALL apps (Talon, Superwhisper, etc.)." >&2
  echo "coreaudiod and every CoreAudio client process will be force-killed." >&2
  if [ "$assume_yes" -ne 1 ]; then
    printf 'Proceed? [y/N] ' >&2
    local ans; read -r ans
    if [ "$ans" != "y" ] && [ "$ans" != "Y" ]; then
      log reset - aborted
      echo "Aborted." >&2
      return 0
    fi
  fi

  if [ "${WATCHDOG_DRYRUN:-0}" = "1" ]; then
    echo "DRYRUN: lsof | grep CoreAudio | ... | xargs kill -9   (CoreAudio clients)"
    echo "DRYRUN: sudo killall -9 coreaudiod audiomxd audioclocksyncd audioanalyticsd audioaccessoryd AudioComponentRegistrar"
    log reset - done
    return 0
  fi

  lsof 2>/dev/null | grep CoreAudio | awk '{print $2}' | sort -un | xargs kill -9 2>/dev/null
  sudo killall -9 coreaudiod audiomxd audioclocksyncd audioanalyticsd audioaccessoryd AudioComponentRegistrar
  log reset - done
  echo "CoreAudio reset complete." >&2
  return 0
}

render_plist() {
  cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>$SCRIPT_PATH</string>
    <string>toggle</string>
  </array>
  <key>StartInterval</key><integer>$INTERVAL</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$LOG_FILE</string>
  <key>StandardErrorPath</key><string>$LOG_FILE</string>
</dict>
</plist>
EOF
}

cmd_install() {
  local dryrun="${WATCHDOG_DRYRUN:-0}"
  if [ "$dryrun" != "1" ]; then
    if ! command -v "$SWITCHAUDIO" >/dev/null 2>&1; then
      echo "error: SwitchAudioSource not found. Run: brew install switchaudio-osx" >&2
      return 1
    fi
    if ! input_present "$TARGET_DEVICE"; then
      echo "error: TARGET_DEVICE '$TARGET_DEVICE' not in current inputs." >&2; return 1
    fi
    if ! input_present "$AWAY_INPUT"; then
      echo "error: AWAY_INPUT '$AWAY_INPUT' not in current inputs." >&2; return 1
    fi
  fi
  mkdir -p "$(dirname "$PLIST")"
  render_plist > "$PLIST"
  if [ "$dryrun" = "1" ]; then
    echo "DRYRUN: wrote $PLIST (launchctl bootstrap skipped)"; return 0
  fi
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  echo "Loaded $LABEL (every ${INTERVAL}s). Log: $LOG_FILE" >&2
}

cmd_uninstall() {
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Unloaded and removed $LABEL." >&2
}

cmd_status() {
  if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
    echo "agent: LOADED ($LABEL)"
  else
    echo "agent: not loaded ($LABEL)"
  fi
  echo "--- last 10 log lines ($LOG_FILE) ---"
  tail -n 10 "$LOG_FILE" 2>/dev/null || echo "(no log yet)"
}

# Run main only when executed directly (so tests can source this file).
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  main "$@"
fi
