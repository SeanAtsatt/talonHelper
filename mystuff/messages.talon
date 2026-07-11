app.bundle: com.apple.MobileSMS
-
# --- Switch conversations ---
chat next: key(cmd-shift-])
chat last: key(cmd-shift-[)
chat recent: key(cmd-1)

# --- Search ---
find chat: key(cmd-f)

# --- Discrete transcript scroll ---
page down: user.messaging_page_down()
page up: user.messaging_page_up()
go top: key(cmd-up)
go bottom: key(cmd-down)

# --- Continuous transcript scroll ---
scroll down: user.messaging_scroll_start_down()
scroll up: user.messaging_scroll_start_up()
scroll stop: user.messaging_scroll_stop()
scroll faster: user.messaging_scroll_faster()
scroll slower: user.messaging_scroll_slower()
