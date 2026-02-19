app: apple_terminal
-
# Override tab close to require confirmation in Terminal
tab close: user.tab_close_confirm_start()

# Delete word to the left of cursor
clear word left: key(ctrl-w)

# Delete word to the right of cursor
clear word right:
    key(escape)
    key(d)

# Delete to beginning of line
clear line left: key(ctrl-u)

# Delete to end of line
clear line right: key(ctrl-k)

# Reverse search command history
history search: key(ctrl-r)

# Cancel history search
history cancel: key(ctrl-g)

# Transpose characters
swap chars: key(ctrl-t)

# Undo last edit
undo: key(ctrl-_)
