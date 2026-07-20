"""Pure logic for the voice calendar-event feature. No talon imports so it is
unit-testable with plain Python."""

from __future__ import annotations

import re
from datetime import datetime, timedelta

_TIME_RE = re.compile(r"^\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\s*$", re.IGNORECASE)


def parse_prose_time(s: str) -> tuple[int, int]:
    """Parse community prose_time output ("2:30pm", "2pm", "9:05") to (h24, m)."""
    m = _TIME_RE.match(s or "")
    if not m:
        raise ValueError(f"could not parse time: {s!r}")
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = (m.group(3) or "").lower()
    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"time out of range: {s!r}")
    return hour, minute


def combine_duration(pairs: list[tuple[int, str]]) -> int:
    """Sum (number, 'h'|'m') pairs into total minutes."""
    return sum(n * 60 if unit == "h" else n for n, unit in pairs)


def next_valid_start(
    month: int, day: int, hour: int, minute: int, now: datetime
) -> datetime:
    """Earliest datetime matching month/day/time that is >= now (minute
    precision). Scans forward up to 9 years so Feb 29 lands on a leap year.
    Raises ValueError if the date never exists (e.g. Feb 30)."""
    floor = now.replace(second=0, microsecond=0)
    for year in range(now.year, now.year + 9):
        try:
            cand = datetime(year, month, day, hour, minute)
        except ValueError:
            continue
        if cand >= floor:
            return cand
    raise ValueError(f"no such date: month {month} day {day}")


def resolve_event_datetimes(
    month: int, day: int, hour: int, minute: int, duration_min: int, now: datetime
) -> tuple[datetime, datetime]:
    start = next_valid_start(month, day, hour, minute, now)
    return start, start + timedelta(minutes=duration_min)


def escape_applescript(s: str) -> str:
    """Escape a string for embedding inside an AppleScript double-quoted literal."""
    s = (s or "").replace("\\", "\\\\").replace('"', '\\"')
    return "".join(ch for ch in s if ch == "\t" or ch >= " ").strip()


def build_calendar_applescript(
    calendar_name: str, title: str, start: datetime, end: datetime
) -> str:
    """Build a Calendar 'make new event' script, setting date components
    numerically (locale-safe). day is set to 1 before month/year to avoid
    month-overflow, then set to the real day."""
    cal = escape_applescript(calendar_name)
    summary = escape_applescript(title)

    def date_block(var: str, dt: datetime) -> str:
        return (
            f"set {var} to current date\n"
            f"set day of {var} to 1\n"
            f"set year of {var} to {dt.year}\n"
            f"set month of {var} to {dt.month}\n"
            f"set day of {var} to {dt.day}\n"
            f"set hours of {var} to {dt.hour}\n"
            f"set minutes of {var} to {dt.minute}\n"
            f"set seconds of {var} to 0\n"
        )

    return (
        'tell application "Calendar"\n'
        f'tell calendar "{cal}"\n'
        f"{date_block('d', start)}"
        f"{date_block('e', end)}"
        f'make new event with properties {{summary:"{summary}", '
        "start date:d, end date:e}\n"
        "end tell\n"
        "end tell"
    )


def format_for_display(
    title: str, start: datetime, end: datetime, calendar_name: str
) -> list[str]:
    return [
        title,
        start.strftime("%a %b %d %Y"),
        f"{start.strftime('%-I:%M %p')} - {end.strftime('%-I:%M %p')}",
        f"Calendar: {calendar_name}",
    ]
