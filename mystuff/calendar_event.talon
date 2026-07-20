calendar add <user.text> on {user.calendar_month} <user.calendar_day> at <user.prose_time>:
    user.calendar_add_event(user.text, calendar_month, user.calendar_day, user.prose_time)
calendar add <user.text> on {user.calendar_month} <user.calendar_day> at <user.prose_time> for <user.calendar_duration>:
    user.calendar_add_event(user.text, calendar_month, user.calendar_day, user.prose_time, user.calendar_duration)
