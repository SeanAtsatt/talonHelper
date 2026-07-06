#!/usr/bin/env bash
# Dependency-free test runner for audio-watchdog.sh
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$HERE/../audio-watchdog.sh"
PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf 'ok   - %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf 'FAIL - %s\n   %s\n' "$1" "$2"; }
assert_eq()      { [ "$2" = "$3" ] && ok "$1" || bad "$1" "want [$3] got [$2]"; }
assert_contains(){ case "$2" in *"$3"*) ok "$1";; *) bad "$1" "[$2] lacks [$3]";; esac; }

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT

# --- logging & rotation ---
test_log_writes_line() {
  local log="$WORK/log1.log"
  ( export WATCHDOG_LOG="$log"; source "$SCRIPT"; log toggle "Sennheiser Profile" ok )
  assert_contains "log writes action" "$(cat "$log")" "toggle"
  assert_contains "log writes detail" "$(cat "$log")" "Sennheiser Profile"
  assert_contains "log writes result" "$(cat "$log")" "ok"
}
test_log_creates_dir() {
  local log="$WORK/nested/deep/log.log"
  ( export WATCHDOG_LOG="$log"; source "$SCRIPT"; log skip - - )
  [ -f "$log" ] && ok "log creates parent dir" || bad "log creates parent dir" "no file"
}
test_rotation() {
  local log="$WORK/rot.log"
  ( export WATCHDOG_LOG="$log"; source "$SCRIPT"
    LOG_MAX_BYTES=100
    head -c 200 /dev/zero | tr '\0' 'x' > "$log"
    log toggle x ok )
  [ -f "$log.1" ] && ok "rotation moves to .1" || bad "rotation moves to .1" "no .1"
}
test_unknown_subcommand() {
  local out rc
  out="$( "$SCRIPT" bogus 2>&1 )"; rc=$?
  assert_eq "unknown subcommand exit 2" "$rc" "2"
  assert_contains "unknown subcommand usage" "$out" "usage"
}

test_log_writes_line
test_log_creates_dir
test_rotation
test_unknown_subcommand

# --- toggle ---
setup_stub() {                 # $1 = current input, rest = available inputs
  local cur="$1"; shift
  STUB_STATE="$(mktemp -d)"
  printf '%s\n' "$cur" > "$STUB_STATE/current_input"
  : > "$STUB_STATE/calls"
  printf '%s\n' "$@" > "$STUB_STATE/inputs"
  export STUB_STATE
  export SWITCHAUDIO_BIN="$HERE/stub-switchaudio.sh"
  chmod +x "$HERE/stub-switchaudio.sh"
}

test_toggle_acts_on_target() {
  local log="$WORK/t2.log"
  setup_stub "Sennheiser Profile" "Sennheiser Profile" "HD Pro Webcam C920"
  ( export WATCHDOG_LOG="$log"; SETTLE=0; "$SCRIPT" toggle )
  assert_eq   "ends on target" "$(cat "$STUB_STATE/current_input")" "Sennheiser Profile"
  assert_contains "bounced through away" "$(cat "$STUB_STATE/calls")" "HD Pro Webcam C920"
  assert_contains "logs ok" "$(cat "$log")" "ok"
}
test_toggle_skips_other_device() {
  local log="$WORK/t2b.log"
  setup_stub "HD Pro Webcam C920" "Sennheiser Profile" "HD Pro Webcam C920"
  ( export WATCHDOG_LOG="$log"; SETTLE=0; "$SCRIPT" toggle )
  assert_contains "logs skip" "$(cat "$log")" "skip"
  # no -s call should have happened
  case "$(cat "$STUB_STATE/calls")" in *"-s"*) bad "skip does not switch" "found -s";; *) ok "skip does not switch";; esac
}
test_toggle_errors_without_away() {
  local log="$WORK/t2c.log" rc
  setup_stub "Sennheiser Profile" "Sennheiser Profile"   # away input absent
  ( export WATCHDOG_LOG="$log"; SETTLE=0; "$SCRIPT" toggle ); rc=$?
  assert_contains "logs error" "$(cat "$log")" "error"
  [ "$rc" -ne 0 ] && ok "away-missing exits non-zero" || bad "away-missing exits non-zero" "rc=$rc"
}

test_toggle_acts_on_target
test_toggle_skips_other_device
test_toggle_errors_without_away

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
