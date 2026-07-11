app.bundle: net.whatsapp.WhatsApp
-
# --- Switch chats (native app uses Ctrl, not Cmd, for these) ---
chat next: key(ctrl-tab)
chat last: key(ctrl-shift-tab)

# --- Search ---
find chat: key(cmd-f)
find here: key(cmd-shift-f)
mark unread: key(cmd-shift-u)

# --- Discrete transcript scroll ---
# WhatsApp has no jump-to-edge shortcut; top/bottom are large scroll bursts.
# Older messages load lazily, so "go top" reaches "as far up as loaded".
page down: user.messaging_page_down()
page up: user.messaging_page_up()
go bottom: user.messaging_page_bottom()
go top: user.messaging_page_top()

# --- Continuous transcript scroll ---
scroll down: user.messaging_scroll_start_down()
scroll up: user.messaging_scroll_start_up()
scroll stop: user.messaging_scroll_stop()
scroll faster: user.messaging_scroll_faster()
scroll slower: user.messaging_scroll_slower()
