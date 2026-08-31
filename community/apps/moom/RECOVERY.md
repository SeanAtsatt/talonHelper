# Moom setup for the Talon window commands

The moom.talon grammar drives Moom by opening its **keyboard controller**
(ctrl-alt-m) and sending single keys. Those key bindings live in Moom's own
preferences (~/Library/Preferences/com.manytricks.Moom.plist), **not in this
repo** - so reinstalling Moom wipes them and every letter-key command silently
stops working, while "window fill *" and "window center" keep working.

Three things must be restored. All were verified end-to-end on 2026-08-31
(Moom 4.6, macOS 26).

## 1. The keyboard controller hot key

Moom -> Settings -> **Keyboard** -> set "Control active window via hot key" to
**ctrl-alt-M**. Without this, nothing else works. Verify:

    defaults read com.manytricks.Moom "Keyboard Controls"
    # expect: Key Code 46, Modifier Flags 786432

## 2. The custom actions

Moom -> **File -> Import**, and choose talon-window-commands.moom (next to this
file). That restores all twelve single-key actions:

- q / w / a / s .... window top left, top right, bottom left, bottom right
- o / p / - / ; .... window screen left, right, up, down (other display)
- e / r / t / y .... window grow left, right, up, down

Verify (12 expected):

    osascript -e 'tell application "Moom" to list of actions' > /tmp/moom.txt
    grep -c "[.]talon" /tmp/moom.txt

## 3. Escape -> Revert

Needed for "window undo". Not a custom action, so the import does not restore it:

    osascript -e 'tell application "Moom" to quit'; sleep 2
    defaults write com.manytricks.Moom "Key Control: Escape" -int 1
    open -a Moom

## Notes

- **Grow is on e/r/t/y, not ctrl-arrows.** macOS owns all four ctrl-arrow combos
  (Mission Control, Application Windows, Move left/right a space), so the upstream
  community bindings never reach Moom.
- "window screen *" only does something with **two or more displays**; on a single
  display it can push a window off-screen.
- Editing the plist directly only works while **Moom is quit** - a running Moom
  rewrites its prefs from memory and discards outside changes. Use "defaults
  import", then relaunch.
- Actions are named with a leading dot so Moom hides them from its menus while the
  hot keys stay live.
- moom.py carries a local fix (2s cron timeout) for an upstream bug where one
  missed controller open wedges the plugin for the rest of the session. Re-apply
  it after any community update.
