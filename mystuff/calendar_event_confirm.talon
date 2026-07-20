tag: user.calendar_confirming
-
(yes | confirm): user.calendar_confirm()
(cancel | no): user.calendar_cancel()
retitle <user.text>: user.calendar_set_title(user.text)
date {user.calendar_month} <user.calendar_day>: user.calendar_set_date(calendar_month, user.calendar_day)
time <user.prose_time>: user.calendar_set_time(user.prose_time)
duration <user.calendar_duration>: user.calendar_set_duration(user.calendar_duration)
