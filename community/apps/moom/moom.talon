os: mac
-
# move window absolute
window top right: user.moom_keys("w")
window top left: user.moom_keys("q")
window bottom left: user.moom_keys("a")
window bottom right: user.moom_keys("s")
window center: user.moom_center_frontmost_window()

# resize and move window
window fill left: user.moom("cmd-left")
window fill right: user.moom("cmd-right")
window fill top: user.moom("cmd-up")
window fill bottom: user.moom("cmd-down")

# resize window relative
# grow uses Moom custom actions on e/r/t/y: macOS Mission Control
# owns ctrl-arrows, so those keystrokes never reach Moom.
window grow left [<user.ordinals>]: user.moom_keys("e", ordinals or 1)
window grow right [<user.ordinals>]: user.moom_keys("r", ordinals or 1)
window grow up [<user.ordinals>]: user.moom_keys("t", ordinals or 1)
window grow down [<user.ordinals>]: user.moom_keys("y", ordinals or 1)
window shrink left [<user.ordinals>]: user.moom_keys("alt-right", ordinals or 1)
window shrink right [<user.ordinals>]: user.moom_keys("alt-left", ordinals or 1)
window shrink top [<user.ordinals>]: user.moom_keys("alt-down", ordinals or 1)
window shrink bottom [<user.ordinals>]: user.moom_keys("alt-up", ordinals or 1)

# move window relative
window move left [<user.ordinals>]: user.moom_keys("left", ordinals or 1)
window move right [<user.ordinals>]: user.moom_keys("right", ordinals or 1)
window move up [<user.ordinals>]: user.moom_keys("up", ordinals or 1)
window move down [<user.ordinals>]: user.moom_keys("down", ordinals or 1)

# move window between screens
window screen up [<user.ordinals>]: user.moom_keys("-", ordinals or 1)
window screen down [<user.ordinals>]: user.moom_keys(";", ordinals or 1)
window screen left [<user.ordinals>]: user.moom_keys("o", ordinals or 1)
window screen right [<user.ordinals>]: user.moom_keys("p", ordinals or 1)

# undo after moving or resizing
window undo: user.moom("esc")
