# CoreAudio Watchdog — Design

**Date:** 2026-07-04
**Status:** Approved (design), pending implementation plan
**Requirements:** `watchdog-requirements.md`

## Problem

On macOS Tahoe (macOS 26, confirmed on this machine at 26.4.1) a CoreAudio
regression silently kills the microphone input stream: the device is still
detected, output still works, meters can look normal, but capture returns
all-zero samples. Talon (and other mic apps like Superwhisper) then behave as
if there is no input. Because the mic is dead, **a voice command cannot be the
recovery trigger** — recovery must be mic-independent and automatic.

## Hardware (this machine)

- **Mac Studio** running macOS 26.4.1. **No built-in microphone** — so the input
  toggle bounces between the two USB inputs, not a built-in mic.
- Inputs (from System Settings → Sound → Input):
  - `Sennheiser Profile` (USB) — the flaky device to babysit (`TARGET_DEVICE`).
  - `HD Pro Webcam C920` (USB) — the alternate input to bounce through
    (`AWAY_INPUT`).
- Default output: `Mac Studio Speakers`.
- Exact `SwitchAudioSource -a` strings are confirmed at implementation time
  (System Settings labels usually match, but are verified).

## Goal

A background watchdog that keeps the mic input alive by **preemptively** running
the cheap, no-root "device toggle" on a schedule, with no voice input and no
user interaction. A separate, manually-invoked heavy reset exists as an escape
hatch for when the toggle is not enough.

## Decisions (resolved open questions)

| Question | Decision |
|---|---|
| Preemptive vs detect-then-act | **Preemptive toggle only.** No silent-capture detection. |
| Toggle interval | **Every 5 minutes** (`StartInterval 300`). Inside the ~10–60 min reset window; easy to retune. |
| Device targeting | **Hardcoded target device**, used as a *filter* (see below), not a forced destination. |
| Heavy reset (FR5) | **Manual only.** Run by hand when the user notices the toggle isn't working. No hotkey, no auto-escalation. |
| Sudo for heavy reset | **Interactive password prompt.** No NOPASSWD sudoers is installed. |
| Detection/RMS logging | **None.** Log the toggle action only. |

### Why the heavy reset is not the routine action

The FR5 command force-kills every process holding a CoreAudio connection
(`lsof … kill -9`) plus the audio daemons (`sudo killall`). That is disruptive
by design — it severs audio for Talon, Superwhisper, etc., which is exactly the
behavior observed when the user ran it manually. It only belongs in a
deliberate, manual fallback tier, never on a timer.

### The hardcoded device is a filter, not a destination (resolves FR7)

FR7 requires the watchdog not to interfere with intentional device switching.
A naive hardcoded toggle would fight the user: if they switch to AirPods, a
timer-driven toggle would force them back onto the hardcoded device.

Instead, each `toggle` run:

1. Reads the **current default input** device.
2. If it is **not** the hardcoded `TARGET_DEVICE` → **no-op** (the user is on a
   different device on purpose; leave it alone), log the skip.
3. If it **is** `TARGET_DEVICE` → perform the toggle and log it.

So the hardcoded name scopes *which* device gets babysat; the toggle always
restores that same device. Intentional switches to any other device are never
disturbed.

## Architecture

Standalone shell + launchd. Not Talon code. Lives in a new `watchdog/` directory
in the repo and is deployed to `~/` via the existing manual `cp` sync.

### Components

**1. `watchdog/audio-watchdog.sh`** — single subcommand-driven script.

- `toggle` (default; invoked by launchd):
  - Read current default input via `SwitchAudioSource -c -t input`.
  - If it != `TARGET_DEVICE` → log `skip` and exit 0.
  - Else perform the toggle:
    - **input (core action):** switch input to `AWAY_INPUT`, then back to
      `TARGET_DEVICE`. This directly stops and restarts the failing input
      device's stream — the resource that dies in this bug.
    - A brief settle delay (~0.3 s) between the two switches so coreaudiod
      fully tears the stream down before it is re-selected.
  - Log the action and result. Never requires root.

  Output is intentionally **not** cycled. The failing resource is the input
  stream; cycling input is the direct fix and needs only the two USB inputs
  that are always present. An output cycle would add a dependency on a second
  output device for no clear benefit. If the input cycle proves insufficient in
  practice, an optional output cycle is a documented future knob (see Tuning).
- `reset` — FR5 heavy reset:
  - Print a clear warning that it will kill audio for **all** apps.
  - Require an explicit confirmation (typed `y`), unless `--yes` is passed.
  - Run:
    ```
    lsof 2>/dev/null | grep CoreAudio | awk '{print $2}' | sort -un | xargs kill -9 2>/dev/null
    sudo killall -9 coreaudiod audiomxd audioclocksyncd audioanalyticsd audioaccessoryd AudioComponentRegistrar
    ```
    `sudo` prompts for the password interactively.
  - Log the invocation and outcome.
- `install` — FR7 start:
  - Verify `SwitchAudioSource` is present; if not, print the `brew install
    switchaudio-osx` instruction and exit non-zero.
  - Verify `TARGET_DEVICE` and `AWAY_INPUT` are both present in
    `SwitchAudioSource -a`; refuse with a clear message if not.
  - Write/refresh the plist into `~/Library/LaunchAgents/` and `launchctl
    bootstrap` (load) it.
- `uninstall` — FR7 stop: `launchctl bootout` (unload) and remove the plist.
- `status` — show whether the agent is loaded and tail the log.

**2. Config block (top of the script):**

```
TARGET_DEVICE="Sennheiser Profile"     # flaky USB mic to babysit (default input)
AWAY_INPUT="HD Pro Webcam C920"        # other USB input to bounce through
LOG_FILE="$HOME/Library/Logs/talon-audio-watchdog.log"
INTERVAL=300
```

Device names are confirmed against `SwitchAudioSource -a` on this machine at
implementation time (System Settings labels usually match verbatim, but are
verified). `AWAY_INPUT` must be a currently-present input other than
`TARGET_DEVICE`; if it is absent at runtime the toggle logs an error and
no-ops rather than leaving the input on the wrong device.

**3. `watchdog/com.talon.audio-watchdog.plist`** — launchd user agent template:
`StartInterval` 300, `RunAtLoad` true, `ProgramArguments` = the script path +
`toggle`, stdout/stderr routed to the log. Installed to
`~/Library/LaunchAgents/com.talon.audio-watchdog.plist`.

**4. Logging (FR6):** `~/Library/Logs/talon-audio-watchdog.log`, one line per
run: ISO timestamp, current default input, action (`toggle` / `skip` /
`reset`), and result (`ok` / error). Simple in-script size rotation: when the
file exceeds ~1 MB, move it to `.1` (single generation) and start fresh.

**5. `watchdog/README.md`** — purpose, the two tiers, install/uninstall/disable
steps, dependency, and tuning knobs (interval, device names).

### Dependency

`switchaudio-osx` (`brew install switchaudio-osx`) — provides
`SwitchAudioSource`. Currently **not installed**; `install` checks for it.

## Data flow

```
launchd (every 300s)
   -> audio-watchdog.sh toggle
        -> read current default input
        -> matches TARGET_DEVICE ?
             no  -> log skip, exit
             yes -> switch input to AWAY_INPUT
                    (settle ~0.3s)
                    switch input back to TARGET_DEVICE
                    log ok
```

Manual path:

```
user notices dead mic despite toggles
   -> audio-watchdog.sh reset
        -> confirm -> kill CoreAudio clients + daemons (sudo) -> log
```

## Error handling

- `SwitchAudioSource` missing → `install` refuses and prints the brew command;
  `toggle` logs an error and exits non-zero (launchd just retries next interval).
- `AWAY_INPUT` not present at runtime → log an error and no-op (do **not**
  leave the input parked on a missing/wrong device); exit non-zero.
- A switch command failing mid-toggle → log the error; best-effort restore to
  `TARGET_DEVICE`; exit non-zero. Next run re-attempts.
- `reset` without confirmation → abort, no action.
- Log directory missing → create `~/Library/Logs` if needed.

## Tuning (documented knobs)

- **Interval** — `INTERVAL` in the script + `StartInterval` in the plist
  (default 300s). Kept in sync by `install`.
- **Device names** — `TARGET_DEVICE`, `AWAY_INPUT`.
- **Settle delay** between the two input switches (default ~0.3s).
- **Optional output cycle** — not implemented by default. If an input-only
  cycle proves insufficient against the bug, add an output switch
  (default output → alternate → back) as an additional step. Documented here
  so the escalation path is known.

## Testing / verification

- **Unit-ish (shell):** run `toggle` manually while on the target device →
  verify the device returns to target and a log line is written. Run `toggle`
  while on a *different* device → verify no-op + `skip` log.
- **launchd:** `install`, confirm `status` shows the agent loaded, confirm log
  lines appear at the interval; `uninstall`, confirm the agent is gone.
- **reset:** dry review of the command; run once manually and confirm audio
  recovers and a log line is written. (Destructive — run intentionally.)
- **Idempotence:** running `toggle` repeatedly on healthy audio causes no
  audible disruption and no state change beyond logs.

## Non-functional coverage

- **No root on routine path** — `toggle` uses only `SwitchAudioSource`.
- **Low overhead** — sub-second switch calls, no continuous capture.
- **Idempotent / safe to over-run** — toggle on healthy audio is harmless.
- **Tahoe-scoped but harmless elsewhere** — cheap no-op toggle; disable via
  `uninstall`.
- **Minimal dependencies** — one Homebrew formula, documented.

## Out of scope

- Fixing the Apple bug.
- Any `.talon` voice command trigger.
- Silent-capture detection / RMS thresholds (explicitly declined).
- Karabiner/BTT hotkey and NOPASSWD sudoers (declined).
