# Foot switch integration for Whisper
# Foot down (Ctrl+Alt+Cmd+W): Drowse Talon and start Whisper
# Foot up (Ctrl+Alt+Cmd+T): Stop Whisper and wake Talon

# Voice command to toggle command mode for next foot press
whisper command:
    user.toggle_whisper_command_mode()

# Foot press down - drowse Talon, start Whisper (hold Fn)
# If command mode is toggled, sends alt-0 for Wispr command mode
key(ctrl-alt-cmd-w):
    user.foot_press_whisper()

# Foot release up - stop Whisper (release Fn or alt-0), wake Talon
key(ctrl-alt-cmd-t):
    user.foot_release_whisper()
