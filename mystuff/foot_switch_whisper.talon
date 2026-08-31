# Foot switch integration for Superwhisper
# Foot down (Ctrl+Alt+Cmd+W): Drowse Talon and start Superwhisper
# Foot up (Ctrl+Alt+Cmd+T): Stop Superwhisper and wake Talon

# Voice command to toggle command mode for next foot press
whisper command:
    user.toggle_whisper_command_mode()

# Foot press down - drowse Talon, start Superwhisper (push-to-talk)
# If command mode is toggled, sends ctrl-alt-cmd-s to toggle Superwhisper
key(ctrl-alt-cmd-w):
    user.foot_press_whisper()

# Foot release up - stop Superwhisper, wake Talon
key(ctrl-alt-cmd-t):
    user.foot_release_whisper()
