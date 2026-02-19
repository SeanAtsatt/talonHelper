app: iterm2
-
# Override tab close to require confirmation in iTerm2
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

# ============ Copy Mode ============

# Enter copy mode (may need to configure in iTerm2 Preferences → Keys)
copy mode: key(cmd-shift-c)

# Select output of last command
grab last: key(cmd-shift-a)

# Exit copy mode
copy exit: key(escape)

# Start character selection
copy start: key(v)

# Start line selection
copy lines: key(shift-v)

# Yank (copy) selection and exit
copy yank: key(y)

# Copy mode navigation
copy top: key(g g)
copy bottom: key(shift-g)
copy line start: key(0)
copy line end: key(shift-4)

# Search in copy mode
copy search: key(/)
copy search back: key(shift-/)

# Copy N lines from bottom of screen (shows GUI for refinement)
copy up <number_small>: user.iterm2_copy_up_lines(number_small)

# Copy from bottom up to a specific word (shows GUI for refinement)
copy until <user.text>: user.iterm2_copy_until_word(text)

# Select a range of lines from the GUI (e.g., "lines 5 10")
lines <number_small> <number_small>$: user.iterm2_copy_range(number_small_1, number_small_2)

# Close the copy GUI without changing clipboard
copy done: user.iterm2_copy_done()

# Show copy GUI with current clipboard contents
copy show: user.iterm2_show_copy_gui()
