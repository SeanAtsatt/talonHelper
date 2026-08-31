# Talon Helper — CoreAudio Watchdog Requirements

## Background

On macOS Tahoe (macOS 26) there is a CoreAudio regression in which the
microphone input stream silently dies: the input device is still detected,
speaker output still works, and mic level meters/logs can look normal, but
the input stream returns all-zero (silent) samples across every capture path.
The telltale system log line is `coreaudiod` reporting `No kDeviceInput
streams` for the device.

When this happens, **Talon receives no audio and behaves as though it is
getting no input**, even though nothing in Talon is wrong. The bug persists
through at least macOS 26.3 and is aggravated by CPU/memory pressure, docks,
and external monitors. It is more common with USB Audio Class 2.0 devices.

Because the failure kills Talon's input stream, **a Talon voice command cannot
be the recovery trigger** — by the time recovery is needed, Talon can't hear
it. Recovery must be mic-independent and, ideally, automatic.

## Goal

A background watchdog that keeps Talon's microphone input alive on macOS Tahoe
by detecting or preemptively preventing the dead-input-stream condition and
resetting the audio stack **without any voice input and without user
interaction**.

## Functional requirements

### FR1 — Mic-independent operation
The watchdog must run and recover audio with no dependency on Talon or on
microphone input of any kind. It must function specifically in the state where
the mic stream is already dead.

### FR2 — Automatic trigger
The watchdog must run on its own on a recurring schedule (e.g. a launchd agent
firing on a short interval, order of every 1–5 minutes — interval to be tuned).
No manual invocation should be required for the common case.

### FR3 — Preferred recovery: no-sudo device toggle
The primary recovery action must NOT require root. The preferred mechanism is
the "device toggle": switch the active audio device to the Mac's internal
output and immediately back to the current external device. This resets the
CoreAudio state for ~10–60 minutes and needs no privileges.
- Implement via `switchaudio-osx` (`SwitchAudioSource`).
- Toggle should be near-instant and non-disruptive.
- Consider running preemptively on the schedule rather than only on detection,
  since the toggle is cheap and harmless.

### FR4 — Optional detection (if not running purely preemptively)
If the watchdog detects rather than runs blindly, it must identify the
dead-stream condition reliably, e.g.:
- Poll for all-zero / silent capture on the active input device, and/or
- Watch the unified log for `coreaudiod` `No kDeviceInput streams` messages
  for the relevant device.
Detection must avoid false positives during legitimate silence (no speaking).
A short capture with an RMS/peak threshold, sustained across multiple polls,
is preferable to a single reading.

### FR5 — Escalation: full CoreAudio reset (manual/hotkey tier)
When the no-sudo toggle is insufficient, provide a heavier reset that kills
CoreAudio and all audio client processes (killing `coreaudiod` alone is
known to be inadequate — client processes hold corrupted state that
re-infects the restarted stack). Reference command set:

    lsof 2>/dev/null | grep CoreAudio | awk '{print $2}' | sort -un | xargs kill -9 2>/dev/null
    sudo killall -9 coreaudiod audiomxd audioclocksyncd audioanalyticsd audioaccessoryd AudioComponentRegistrar

- This tier requires root. For non-interactive use it needs a **scoped
  NOPASSWD sudoers entry** limited to exactly these commands — never blanket
  NOPASSWD.
- This tier is intended as a manual fallback (bound to a Karabiner-Elements or
  BetterTouchTool hotkey — both operate below Talon and work when the mic is
  dead), not as the routine automatic action.

### FR6 — Logging
The watchdog must log each run, what condition it observed, which action it
took, and the outcome, to a rotating local log file for later diagnosis and
for correlating with macOS point-release changes.

### FR7 — Safe start/stop
Provide a clean way to load/unload the launchd agent and to disable the
watchdog entirely (single command or documented steps). It must not interfere
with intentional device switching by the user.

## Non-functional requirements

- **No root for the routine path** (FR3). Root confined to the escalation tier
  (FR5) via scoped sudoers only.
- **Low overhead**: negligible CPU; short polls; no continuous audio capture.
- **Idempotent / safe to over-run**: running the toggle when audio is healthy
  must be harmless.
- **Tahoe-scoped but harmless elsewhere**: fine to run on future macOS; should
  degrade gracefully if the bug is eventually fixed.
- **Dependencies** kept minimal and documented (`switchaudio-osx` via Homebrew;
  optional log-parsing utilities).

## Dependencies / references

- `switchaudio-osx` (Homebrew: `brew install switchaudio-osx`) for FR3.
- launchd user agent (`~/Library/LaunchAgents/`) for FR2.
- Karabiner-Elements or BetterTouchTool for the FR5 manual hotkey tier
  (out of scope for the watchdog itself, but the escalation script should be
  hotkey-runnable).

## Open questions / to tune

- Poll interval and whether to run preemptively (FR3) vs detect-then-act (FR4).
- Silence-detection thresholds and sustain count to avoid false positives.
- Whether to auto-escalate from toggle to full reset after N failed toggles,
  or leave the full reset strictly manual.
- Which specific input device(s) to monitor (hardcode vs. "current default").

## Out of scope

- Fixing the underlying Apple bug (Apple-side; watch for a Tahoe point release).
- Any Talon `.talon` voice command as a trigger (defeated by the failure mode).
