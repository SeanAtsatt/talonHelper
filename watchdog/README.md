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
