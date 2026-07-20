from __future__ import annotations

from datetime import datetime

import calendar_logic as cl


def check(label, cond):
    if not cond:
        raise AssertionError(label)
    print(f"ok: {label}")


# parse_prose_time
check("2:30pm -> 14:30", cl.parse_prose_time("2:30pm") == (14, 30))
check("2pm -> 14:00", cl.parse_prose_time("2pm") == (14, 0))
check("12am -> 0:00", cl.parse_prose_time("12am") == (0, 0))
check("12pm -> 12:00", cl.parse_prose_time("12pm") == (12, 0))
check("9:05 24h -> 9:05", cl.parse_prose_time("9:05") == (9, 5))
try:
    cl.parse_prose_time("banana")
    raise SystemExit("expected ValueError for 'banana'")
except ValueError:
    print("ok: bad time rejected")

# combine_duration
check("45 min", cl.combine_duration([(45, "m")]) == 45)
check("one hour", cl.combine_duration([(1, "h")]) == 60)
check("two hours", cl.combine_duration([(2, "h")]) == 120)
check("three hours", cl.combine_duration([(3, "h")]) == 180)
check("1h30m", cl.combine_duration([(1, "h"), (30, "m")]) == 90)

# next_valid_start: future date this year stays this year
now = datetime(2026, 7, 19, 10, 0)
check("future same year", cl.next_valid_start(12, 25, 9, 0, now) == datetime(2026, 12, 25, 9, 0))
# past date rolls to next year
check("past rolls forward", cl.next_valid_start(1, 1, 9, 0, now) == datetime(2027, 1, 1, 9, 0))
# impossible date rejected
try:
    cl.next_valid_start(2, 30, 9, 0, now)
    raise SystemExit("expected ValueError for Feb 30")
except ValueError:
    print("ok: Feb 30 rejected")
# Feb 29 resolves to next leap year (2028)
check("Feb 29 -> leap", cl.next_valid_start(2, 29, 9, 0, now) == datetime(2028, 2, 29, 9, 0))

# resolve_event_datetimes: end = start + duration
s, e = cl.resolve_event_datetimes(7, 20, 14, 30, 45, now)
check("start", s == datetime(2026, 7, 20, 14, 30))
check("end +45", e == datetime(2026, 7, 20, 15, 15))

# escape_applescript
check("quote escaped", cl.escape_applescript('Bob\'s "1-on-1"') == 'Bob\'s \\"1-on-1\\"')
check("backslash escaped", cl.escape_applescript("a\\b") == "a\\\\b")
check("newline stripped", "\n" not in cl.escape_applescript("a\nb"))

# build_calendar_applescript contains numeric components and escaped title
script = cl.build_calendar_applescript("Calendar", 'Team "sync"', s, e)
check("has make new event", "make new event" in script)
check("has month set", "set month of d to 7" in script)
check("title escaped in script", '\\"sync\\"' in script)

# format_for_display
lines = cl.format_for_display("Dentist", s, e, "Calendar")
check("display title", lines[0] == "Dentist")
check("display has calendar", any("Calendar: Calendar" == ln for ln in lines))

print("ALL PASS")
