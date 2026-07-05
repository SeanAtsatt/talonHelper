# CoreAudio Watchdog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A background launchd watchdog that keeps the Mac's mic input alive on macOS Tahoe by preemptively bouncing the flaky USB input device out-and-back every 5 minutes, with a manual heavy-reset escape hatch.

**Architecture:** One subcommand-driven bash script (`toggle` / `reset` / `install` / `uninstall` / `status`). The routine `toggle` path uses only `SwitchAudioSource` (no root): if the current default input is the babysat device, it switches input to an alternate USB input and back, resetting the CoreAudio input stream. A launchd user agent fires `toggle` every 300s. The `reset` path is the destructive FR5 kill sequence, run manually with an interactive sudo prompt. Logic is factored into sourceable functions tested against a stub `SwitchAudioSource`.

**Tech Stack:** bash, launchd (`launchctl bootstrap`/`bootout`), `switchaudio-osx` (`SwitchAudioSource`), Homebrew.

## Global Constraints

- Target machine: **Mac Studio, macOS 26.4.1**, no built-in microphone.
- `TARGET_DEVICE="Sennheiser Profile"` — the flaky USB input to babysit.
- `AWAY_INPUT="HD Pro Webcam C920"` — the alternate USB input to bounce through.
- Default interval: **300 seconds**. Kept in sync between the script's `INTERVAL` and the plist's `StartInterval`.
- launchd label: **`com.talon.audio-watchdog`**. Plist at `~/Library/LaunchAgents/com.talon.audio-watchdog.plist`.
- Log file: `~/Library/Logs/talon-audio-watchdog.log`, single-generation size rotation at ~1 MB (`.1`).
- **Routine path (`toggle`) must never require root.** Root is confined to `reset` via interactive `sudo` only. No NOPASSWD sudoers.
- The script must be **overridable for testing** via env vars: `SWITCHAUDIO_BIN` (path to the SwitchAudioSource binary), `WATCHDOG_LOG` (log file path), `WATCHDOG_DRYRUN` (when `1`, `reset` echoes its destructive commands instead of running them).
- Repo location: everything under `watchdog/`. Deployed to `~/` via manual `cp` (documented, not automated).
- All device names are re-confirmed against `SwitchAudioSource -a` on the real machine in Task 6 before the agent is loaded.

---

## File Structure

- `watchdog/audio-watchdog.sh` — the entire CLI (config block + functions + dispatch). Sourceable: runs `main` only when executed directly.
- `watchdog/tests/stub-switchaudio.sh` — a fake `SwitchAudioSource` that reads/writes a state dir and logs its calls, used by the tests.
- `watchdog/tests/test_audio_watchdog.sh` — dependency-free bash test runner (asserts against the stub).
- `watchdog/README.md` — purpose, the two tiers, install/uninstall/disable, tuning knobs.
- (generated at runtime, not committed) `~/Library/LaunchAgents/com.talon.audio-watchdog.plist`.

---

### Task 1: Script scaffold — config, logging, rotation

**Files:**
- Create: `watchdog/audio-watchdog.sh`
- Create: `watchdog/tests/test_audio_watchdog.sh`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - Env overrides: `SWITCHAUDIO_BIN` (default `SwitchAudioSource`), `WATCHDOG_LOG` (default `$HOME/Library/Logs/talon-audio-watchdog.log`).
  - Config vars: `TARGET_DEVICE`, `AWAY_INPUT`, `INTERVAL`, `LABEL`, `PLIST`.
  - `log <action> <detail> <result>` — appends one line `ISO8601\taction\tdetail\tresult` to `$LOG_FILE`, creating its directory; calls `rotate_log` first.
  - `rotate_log` — if `$LOG_FILE` exceeds `LOG_MAX_BYTES` (1048576), `mv` it to `$LOG_FILE.1`.
  - `main "$@"` dispatches subcommands (only `toggle`/`reset`/`install`/`uninstall`/`status` accepted; anything else prints usage to stderr and exits 2). Runs only when the script is executed directly, not when sourced.

- [ ] **Step 1: Write the failing test**

Create `watchdog/tests/test_audio_watchdog.sh`:

```bash
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

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash watchdog/tests/test_audio_watchdog.sh`
Expected: FAIL — `audio-watchdog.sh` does not exist yet (source errors / no such file).

- [ ] **Step 3: Write minimal implementation**

Create `watchdog/audio-watchdog.sh`:

```bash
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash watchdog/tests/test_audio_watchdog.sh`
Expected: PASS — all four assertions ok, `0 failed`.

- [ ] **Step 5: Commit**

```bash
chmod +x watchdog/audio-watchdog.sh watchdog/tests/test_audio_watchdog.sh
git add watchdog/audio-watchdog.sh watchdog/tests/test_audio_watchdog.sh
git commit -m "feat(watchdog): scaffold script with logging, rotation, dispatch"
```

---

### Task 2: `toggle` — filtered input bounce

**Files:**
- Create: `watchdog/tests/stub-switchaudio.sh`
- Modify: `watchdog/audio-watchdog.sh` (replace the `cmd_toggle` placeholder; add helpers)
- Modify: `watchdog/tests/test_audio_watchdog.sh` (add toggle tests)

**Interfaces:**
- Consumes: `log`, config vars, `$SWITCHAUDIO` from Task 1.
- Produces:
  - `current_input` — echoes `SwitchAudioSource -c -t input`.
  - `input_present <name>` — returns 0 if `<name>` appears in `SwitchAudioSource -a -t input`, else 1.
  - `set_input <name>` — runs `SwitchAudioSource -s "<name>" -t input`.
  - `cmd_toggle` — no-ops with a `skip` log unless current input == `TARGET_DEVICE`; errors with `error` log if `AWAY_INPUT` absent; otherwise switches to `AWAY_INPUT`, sleeps `$SETTLE`, switches back to `TARGET_DEVICE`, logs `toggle … ok`. Exit 0 on skip/ok, non-zero on error.

- [ ] **Step 1: Write the failing test**

Create `watchdog/tests/stub-switchaudio.sh`:

```bash
#!/usr/bin/env bash
# Fake SwitchAudioSource for tests. State dir via $STUB_STATE:
#   $STUB_STATE/current_input  - the current default input device name
#   $STUB_STATE/inputs         - newline list of available input device names
#   $STUB_STATE/calls          - appended one line per invocation
set -u
: "${STUB_STATE:?STUB_STATE required}"
printf '%s\n' "$*" >> "$STUB_STATE/calls"

has() { case " $* " in *" $1 "*) return 0;; *) return 1;; esac; }

# value following -s
set_val=""; prev=""
for a in "$@"; do [ "$prev" = "-s" ] && set_val="$a"; prev="$a"; done

if has -c "$@"; then
  cat "$STUB_STATE/current_input"; exit 0
fi
if has -a "$@"; then
  cat "$STUB_STATE/inputs"; exit 0
fi
if [ -n "$set_val" ]; then
  printf '%s\n' "$set_val" > "$STUB_STATE/current_input"
  echo "input audio device set to \"$set_val\""; exit 0
fi
exit 0
```

Append to `watchdog/tests/test_audio_watchdog.sh` (before the summary `printf`):

```bash
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash watchdog/tests/test_audio_watchdog.sh`
Expected: FAIL — `cmd_toggle` still the placeholder (logs `not-implemented`, never switches), so the new assertions fail.

- [ ] **Step 3: Write minimal implementation**

In `watchdog/audio-watchdog.sh`, replace the `cmd_toggle()` placeholder line with:

```bash
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash watchdog/tests/test_audio_watchdog.sh`
Expected: PASS — toggle acts on target, skips other device, errors without away input; `0 failed`.

- [ ] **Step 5: Commit**

```bash
chmod +x watchdog/tests/stub-switchaudio.sh
git add watchdog/audio-watchdog.sh watchdog/tests/stub-switchaudio.sh watchdog/tests/test_audio_watchdog.sh
git commit -m "feat(watchdog): implement filtered input-bounce toggle"
```

---

### Task 3: `reset` — manual heavy CoreAudio reset

**Files:**
- Modify: `watchdog/audio-watchdog.sh` (replace `cmd_reset` placeholder)
- Modify: `watchdog/tests/test_audio_watchdog.sh` (add reset tests)

**Interfaces:**
- Consumes: `log`, `WATCHDOG_DRYRUN`.
- Produces:
  - `cmd_reset [--yes]` — prints a warning; unless `--yes` (or stdin confirms `y`), aborts with `reset … aborted` log and exit 0. On confirm: runs the kill sequence, logs `reset … done`. When `WATCHDOG_DRYRUN=1`, echoes the two commands prefixed `DRYRUN:` instead of executing (and skips the real `sudo`), still logging `done`.

- [ ] **Step 1: Write the failing test**

Append to `watchdog/tests/test_audio_watchdog.sh` (before the summary `printf`):

```bash
# --- reset ---
test_reset_aborts_without_confirm() {
  local log="$WORK/r1.log" out
  out="$( export WATCHDOG_LOG="$log"; printf 'n\n' | "$SCRIPT" reset 2>&1 )"
  assert_contains "warns before reset" "$out" "kill audio"
  assert_contains "logs aborted" "$(cat "$log")" "aborted"
}
test_reset_dryrun_runs_sequence() {
  local log="$WORK/r2.log" out
  out="$( export WATCHDOG_LOG="$log" WATCHDOG_DRYRUN=1; "$SCRIPT" reset --yes 2>&1 )"
  assert_contains "dryrun kills clients" "$out" "CoreAudio"
  assert_contains "dryrun killall daemons" "$out" "coreaudiod"
  assert_contains "logs done" "$(cat "$log")" "done"
}

test_reset_aborts_without_confirm
test_reset_dryrun_runs_sequence
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash watchdog/tests/test_audio_watchdog.sh`
Expected: FAIL — `cmd_reset` is an empty placeholder; no warning, no log lines.

- [ ] **Step 3: Write minimal implementation**

In `watchdog/audio-watchdog.sh`, replace the `cmd_reset()` placeholder line with:

```bash
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash watchdog/tests/test_audio_watchdog.sh`
Expected: PASS — abort path and dry-run path both verified; `0 failed`.

- [ ] **Step 5: Commit**

```bash
git add watchdog/audio-watchdog.sh watchdog/tests/test_audio_watchdog.sh
git commit -m "feat(watchdog): add manual heavy-reset command with dry-run"
```

---

### Task 4: `install` / `uninstall` / `status` + plist generation

**Files:**
- Modify: `watchdog/audio-watchdog.sh` (replace `cmd_install`/`cmd_uninstall`/`cmd_status` placeholders; add `render_plist`)
- Modify: `watchdog/tests/test_audio_watchdog.sh` (add plist-render test)

**Interfaces:**
- Consumes: `LABEL`, `PLIST`, `INTERVAL`, `LOG_FILE`, `$SWITCHAUDIO`, `TARGET_DEVICE`, `AWAY_INPUT`, `input_present`.
- Produces:
  - `render_plist` — prints a valid launchd plist to stdout using `LABEL`, the absolute script path, `INTERVAL`, and `LOG_FILE` (stdout+stderr routed to the log).
  - `cmd_install` — verifies `SwitchAudioSource` on PATH and that `TARGET_DEVICE` and `AWAY_INPUT` are both present; writes `render_plist` to `$PLIST` and `launchctl bootstrap gui/$(id -u)` it (bootout first for idempotency). Refuses (exit 1) with a clear message on any missing prerequisite. Skips the real `launchctl`/PATH checks when `WATCHDOG_DRYRUN=1` (still writes the plist).
  - `cmd_uninstall` — `launchctl bootout` the label (ignore "not loaded") and `rm -f "$PLIST"`.
  - `cmd_status` — print whether the label is loaded (`launchctl print`) and `tail` the last 10 log lines.

- [ ] **Step 1: Write the failing test**

Append to `watchdog/tests/test_audio_watchdog.sh` (before the summary `printf`):

```bash
# --- plist rendering ---
test_render_plist() {
  local out
  out="$( source "$SCRIPT"; render_plist )"
  assert_contains "plist has label"    "$out" "com.talon.audio-watchdog"
  assert_contains "plist has interval" "$out" "<integer>300</integer>"
  assert_contains "plist calls toggle" "$out" "<string>toggle</string>"
  assert_contains "plist is xml"       "$out" "<?xml"
}
test_install_dryrun_writes_plist() {
  local plist="$WORK/agent.plist"
  setup_stub "Sennheiser Profile" "Sennheiser Profile" "HD Pro Webcam C920"
  ( export WATCHDOG_DRYRUN=1; source "$SCRIPT"; PLIST="$plist"; cmd_install )
  [ -f "$plist" ] && ok "install writes plist" || bad "install writes plist" "no file"
  assert_contains "installed plist has label" "$(cat "$plist")" "com.talon.audio-watchdog"
}

test_render_plist
test_install_dryrun_writes_plist
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash watchdog/tests/test_audio_watchdog.sh`
Expected: FAIL — `render_plist` undefined; `cmd_install` empty placeholder writes nothing.

- [ ] **Step 3: Write minimal implementation**

In `watchdog/audio-watchdog.sh`, add `SCRIPT_PATH` resolution near the top of the config section (after `PLIST=`):

```bash
SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
```

Then replace the three placeholder lines (`cmd_install`, `cmd_uninstall`, `cmd_status`) with:

```bash
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `bash watchdog/tests/test_audio_watchdog.sh`
Expected: PASS — plist renders with label/interval/toggle/xml; dry-run install writes the plist; `0 failed`.

- [ ] **Step 5: Commit**

```bash
git add watchdog/audio-watchdog.sh watchdog/tests/test_audio_watchdog.sh
git commit -m "feat(watchdog): add install/uninstall/status and plist rendering"
```

---

### Task 5: README

**Files:**
- Create: `watchdog/README.md`

**Interfaces:**
- Consumes: the finished CLI.
- Produces: user-facing docs. No tests (prose); verified by the self-review checklist.

- [ ] **Step 1: Write the README**

Create `watchdog/README.md`:

```markdown
# CoreAudio Watchdog

Keeps the microphone input alive on macOS Tahoe (macOS 26), where a CoreAudio
regression silently kills the mic input stream (all-zero samples) while the
device still appears present. Talon and other mic apps then behave as if there
is no input. Because the mic is dead, recovery cannot be a voice command — this
watchdog runs on a timer with no voice input and no user interaction.

## How it works

Two tiers:

- **Toggle (routine, automatic, no root).** Every 5 minutes a launchd agent runs
  `audio-watchdog.sh toggle`. If the current default input is the babysat device
  (`Sennheiser Profile`), it switches the input to `HD Pro Webcam C920` and back,
  which stops and restarts the input stream and resets the CoreAudio state. If
  you are on any other input, it does nothing (it will not fight an intentional
  device switch).

- **Reset (manual, destructive, root).** If the toggle stops being enough, run
  `audio-watchdog.sh reset` by hand. It force-kills every CoreAudio client and
  the audio daemons (prompts for your sudo password). This *will* interrupt audio
  for all apps — that is the point; corrupted client state has to die too. Never
  run automatically.

## Dependencies

- [`switchaudio-osx`](https://github.com/deweller/switchaudio-osx):
  `brew install switchaudio-osx`

## Install

```bash
brew install switchaudio-osx
cp -r watchdog ~/talon-audio-watchdog        # or run from the repo checkout
~/talon-audio-watchdog/audio-watchdog.sh install
```

`install` verifies `SwitchAudioSource` is present and that both the target and
alternate input devices exist, writes the launchd agent to
`~/Library/LaunchAgents/com.talon.audio-watchdog.plist`, and loads it.

## Check status

```bash
audio-watchdog.sh status
```

Shows whether the agent is loaded and the last 10 log lines.

## Disable / uninstall

```bash
audio-watchdog.sh uninstall
```

Unloads the agent and removes the plist. To disable temporarily without
removing, `launchctl bootout gui/$(id -u)/com.talon.audio-watchdog`.

## Logs

`~/Library/Logs/talon-audio-watchdog.log` — one tab-separated line per run
(timestamp, action, device, result). Rotates to `.1` past ~1 MB.

## Tuning

Edit the config block at the top of `audio-watchdog.sh`:

- `TARGET_DEVICE` / `AWAY_INPUT` — device names (must match `SwitchAudioSource -a`).
- `INTERVAL` — seconds between toggles (re-run `install` to apply; it rewrites
  the plist's `StartInterval`).
- `SETTLE` — pause between the two input switches.

If the input-only toggle proves insufficient against the bug, add an output
cycle (switch default output to an alternate and back) as an extra step in
`cmd_toggle`. Not enabled by default.

## Tests

```bash
bash watchdog/tests/test_audio_watchdog.sh
```

Runs against a stub `SwitchAudioSource`; no real audio hardware required.
```

- [ ] **Step 2: Commit**

```bash
git add watchdog/README.md
git commit -m "docs(watchdog): add README covering tiers, install, tuning"
```

---

### Task 6: Live install on this machine (manual checkpoint)

**Files:** none changed (operational task). Confirms the real device names and loads the agent.

**Interfaces:**
- Consumes: the finished CLI + `switchaudio-osx`.
- Produces: a loaded, running agent and verified device names. No automated test — this is the human-in-the-loop verification the earlier stub tests cannot cover.

- [ ] **Step 1: Install the dependency**

Run: `brew install switchaudio-osx`
Expected: `SwitchAudioSource` on PATH (`which SwitchAudioSource` prints a path).

- [ ] **Step 2: Confirm real device names**

Run: `SwitchAudioSource -a -t input`
Expected: the list includes exactly the strings `Sennheiser Profile` and
`HD Pro Webcam C920`. If either differs (e.g. trailing model text), update
`TARGET_DEVICE` / `AWAY_INPUT` in `watchdog/audio-watchdog.sh` to match verbatim,
re-run `bash watchdog/tests/test_audio_watchdog.sh` (still green), and commit the
correction.

- [ ] **Step 3: Manual toggle smoke test (on the target device)**

Ensure the Mac's input is set to `Sennheiser Profile`, then run:
`watchdog/audio-watchdog.sh toggle`
Expected: input ends back on `Sennheiser Profile`; `audio-watchdog.sh status`
shows a `toggle … ok` line. Confirm audio input still works (mic level moves).

- [ ] **Step 4: Manual skip smoke test (off the target device)**

Set input to `HD Pro Webcam C920`, then run: `watchdog/audio-watchdog.sh toggle`
Expected: input stays on `HD Pro Webcam C920`; log shows a `skip … not-target`
line. Set input back to `Sennheiser Profile` afterward.

- [ ] **Step 5: Install and verify the agent**

Run: `watchdog/audio-watchdog.sh install`
Then: `watchdog/audio-watchdog.sh status`
Expected: `agent: LOADED`. After ~5 minutes, `status` shows fresh `toggle`/`skip`
log lines with no manual action.

- [ ] **Step 6: Record completion**

No commit needed (no file changes unless Step 2 corrected a name). Note in the
session that the agent is live, and — only if the toggle proves insufficient in
real use — revisit the optional output-cycle knob documented in the README.

---

## Self-Review

**Spec coverage:**
- FR1 mic-independent → Tasks 2 & 6 (toggle uses only device switching, no capture). ✓
- FR2 automatic trigger → Task 4 launchd agent, Task 6 load. ✓
- FR3 no-sudo device toggle → Task 2. ✓
- FR4 optional detection → explicitly declined in spec; not implemented (documented). ✓
- FR5 heavy reset, manual, sudo → Task 3. ✓
- FR6 logging + rotation → Task 1. ✓
- FR7 safe start/stop + no interference → Task 4 (install/uninstall), Task 2 (skip filter). ✓
- Non-functional (no root routine, low overhead, idempotent, harmless elsewhere, minimal deps) → Tasks 2/3/4, README. ✓

**Placeholder scan:** command bodies replaced in Tasks 2–4; no "TBD"/"handle edge cases" left. Task 1 intentionally ships placeholder command functions that later tasks *replace* — each is a named, testable step, not an unfilled blank. ✓

**Type/name consistency:** `TARGET_DEVICE`, `AWAY_INPUT`, `SETTLE`, `LABEL`, `PLIST`, `SCRIPT_PATH`, `LOG_FILE`, `LOG_MAX_BYTES`, `render_plist`, `current_input`, `input_present`, `set_input`, `cmd_*` used consistently across tasks. Stub state protocol (`current_input`/`inputs`/`calls`) consistent between Task 2 stub and Task 4 test. ✓
