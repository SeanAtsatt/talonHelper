# Voice-Driven Apple Calendar Event Creation — Design Spec

**Date:** 2026-07-19
**Status:** Approved design, pending implementation plan

## Context

Apple Calendar is hard to drive by voice. The user has RSI and controls the Mac
with Talon; navigating Calendar's event form (title field, date pickers, time
fields) with the mouse/keyboard is painful. The existing `mystuff/calendar.talon`
only maps keyboard shortcuts (cmd-N, view switching) — it does nothing to fill in
an event, which is the actual pain point.

**Goal:** one spoken command that creates a timed event on a specific date,
speaking the title, date, time, and (optionally) duration in a single utterance,
with a confirmation step that allows correcting a mis-parse before the event is
committed — without re-speaking the whole command.

## Goals / Non-Goals

**In scope:**
- Timed events: title + date + time + duration.
- Date spoken as **month + day** ("July twentieth" / "July 20"). Year is inferred.
- Default duration of 1 hour when duration is omitted.
- A confirmation window that shows the parsed event and supports **edit-in-place**
  correction of individual fields before committing.
- Event created directly in Calendar via AppleScript (Calendar need not be focused).

**Out of scope (YAGNI):**
- All-day events, relative dates ("tomorrow", "next Tuesday"), day-of-current-month.
- Location, alerts/reminders, invitees, notes, recurrence.
- Choosing the target calendar per-event (fixed to a configurable default).

## Interaction Summary

```
"calendar add dentist appointment on July twentieth at two thirty pm for 45 minutes"
        │
        ▼
┌───────────────────────────────┐
│ New event                     │
│ ───────────────────────────── │
│ Dentist appointment           │
│ Mon Jul 20 2026               │
│ 2:30 PM – 3:15 PM             │
│ Calendar: Calendar            │
│                               │
│ "yes" create · "cancel" abort │
│ retitle / date / time /       │
│ duration <…> to correct       │
└───────────────────────────────┘
        │ "yes"
        ▼
  Event created in Calendar
```

## Files

Two new files, plus a one-line edit to the sandbox module:

- `mystuff/calendar_event.py` — engine: captures, parsing, state, confirmation
  window, AppleScript creation.
- `mystuff/calendar_event.talon` — grammar. **Global context** (NOT `app: Calendar`)
  so events can be created from any app. A tag-scoped block holds the confirmation
  and edit-in-place commands.
- `~/.talon/user/aaa_security.py` — add `mystuff/calendar_event.py` to
  `TRUSTED_FILES`. (See Sandbox note — likely unnecessary but kept for convention.)

The existing `mystuff/calendar.talon` keyboard-shortcut file is left untouched.

Repo copies are edited first, then `cp`'d to `~/.talon/user/mystuff/` per the
established sync workflow (sandbox-disabled `cp`).

## Grammar

Primary command (global context, `calendar_event.talon`). Two rules, because an
unmatched optional capture is *undefined* in Talonscript (not falsy) — so the
no-duration case is its own rule and the action defaults the duration:

```
calendar add <user.text> on {user.calendar_month} <user.calendar_day> at <user.prose_time>:
    user.calendar_add_event(text, calendar_month, calendar_day, prose_time)
calendar add <user.text> on {user.calendar_month} <user.calendar_day> at <user.prose_time> for <user.calendar_duration>:
    user.calendar_add_event(text, calendar_month, calendar_day, prose_time, calendar_duration)
```

The action signature defaults duration: `def calendar_add_event(title, month,
day, prose_time, duration_min: int = 60)`. The fixed words **on / at / for**
delimit the free-dictation title from the structured fields.

### Captures / lists

- `{user.calendar_month}` — **new** Talon list mapping month names → month number
  string ("january" → "1" … "december" → "12"). Defined in `calendar_event.py`.
- `<user.calendar_day>` — **new** capture wrapping community's `<user.ordinals>`
  (int 1–99, from `community/core/numbers/ordinals.py`) and cardinal
  `<user.number_small>` so both "twentieth" and "20"/"twenty" work. Returns int;
  range 1–31 validated downstream.
- `<user.prose_time>` — **reused** from
  `community/core/text/text_and_dictation.py`. Returns a string like `"2:30pm"`
  or `"2pm"`.
- `<user.calendar_duration>` — **new** capture returning **int minutes**. Rules:
  - `<number_small> (minute | minutes | min | mins)` → N
  - `<number_small> (hour | hours) [<number_small> (minute | minutes)]` → 60·H (+M).
    Explicitly covers multi-hour durations: "two hours" → 120, "three hours" → 180,
    "two hours thirty minutes" → 150, etc.
  - `(an | one) hour and (a half | thirty [minutes])` → 90
  - `half an hour` → 30 · `quarter hour` → 15 · `(an | one) hour` → 60
  Omitted in the command → default **60**.

Exact community capture names (`user.number_small`) to be confirmed at
implementation time; `<user.ordinals>` is confirmed present and returns int.

## Engine logic (`calendar_event.py`)

### Parsing & validation
1. `prose_time` → (hour24, minute). Accept both `"H:MMam/pm"` and `"Ham/pm"`.
2. Resolve the year: build `datetime(this_year, month, day, hour, minute)`; if it is
   earlier than `datetime.now()`, use `this_year + 1`.
3. Validate the calendar date via the `datetime` constructor. On `ValueError`
   (e.g. "February thirtieth"), notify and abort — **no window shown**. Special
   case Feb 29: if invalid this year, scan forward up to 8 years for the next leap
   year rather than rejecting.
4. `end = start + timedelta(minutes=duration)`.

### State & confirmation window
- Module-level `_pending` dict holds `{title, start, end, duration_min}` plus the
  raw components needed for re-editing.
- Confirmation window uses `@imgui.open` (same pattern as `default_app.py`),
  rendering title, weekday-formatted date, start–end times, and target calendar.
- A `mod.tag("calendar_confirming")` is activated (`ctx.tags`) while the window is
  open and cleared when it hides, so confirmation/edit commands only match then.

### Edit-in-place actions (tag-scoped talon block)
```
tag: user.calendar_confirming
-
(yes | confirm): user.calendar_confirm()
(cancel | no): user.calendar_cancel()
retitle <user.text>: user.calendar_set_title(text)
date {user.calendar_month} <user.calendar_day>: user.calendar_set_date(calendar_month, calendar_day)
time <user.prose_time>: user.calendar_set_time(prose_time)
duration <user.calendar_duration>: user.calendar_set_duration(calendar_duration)
```
Each setter mutates `_pending`, re-runs year-inference/validation/end-recompute,
and re-renders the window. `calendar_confirm` creates the event and hides the
window; `calendar_cancel` discards `_pending` and hides the window.

### AppleScript creation
- Uses `talon.mac.applescript.run()` (native, same mechanism as the Finder
  selection code in `default_app.py`) — not `subprocess`/`os.system`.
- Start and end datetimes are fully computed in Python; the script sets date
  components **numerically** to avoid locale parsing issues, setting `day` to 1
  before changing `month`/`year` to avoid month-overflow, then setting the real day:
  ```applescript
  tell application "Calendar"
    tell calendar "Calendar"
      set d to current date
      set day of d to 1
      set year of d to <Y> ▸ set month of d to <Mo> ▸ set day of d to <D>
      set hours of d to <h> ▸ set minutes of d to <m> ▸ set seconds of d to 0
      -- same for end date e --
      make new event with properties {summary:"<TITLE>", start date:d, end date:e}
    end tell
  end tell
  ```
- **Title escaping:** backslashes and double-quotes in the dictated title are
  escaped, and control characters/newlines stripped, before interpolation — so a
  title like `Bob's "1-on-1"` cannot break or inject into the script.

### Target calendar
- Constant `TARGET_CALENDAR = "Calendar"` at the top of the module (the user's only
  writable personal calendar; system calendars are read-only). One-line change to
  retarget.

## Error handling

- Impossible date → toast ("no such date: February 30"), abort, no window.
- Empty/blank title → toast, abort.
- AppleScript failure (e.g. Calendar automation permission denied, calendar name not
  found) → toast surfacing the error; nothing is created.
- **First-run permission:** macOS shows a one-time "Talon wants to control Calendar"
  prompt on the first create; must be allowed once. Documented for the user.

## Sandbox note

The engine uses `applescript.run()` (native Talon binding), not `subprocess` or
`os.system`, so it should not trip the sandbox in `aaa_security.py` at all. The file
is nonetheless added to `TRUSTED_FILES` for consistency with `default_app.py` and to
cover any future subprocess use. No approval-GUI interaction is expected.

## Verification

1. **Syntax:** `python3 -c "compile(open(f).read(), f, 'exec')"` on `calendar_event.py`.
2. **Deploy:** `cp` both files to `~/.talon/user/mystuff/`; `tail ~/.talon/talon.log`
   shows two `DEBUG [~]` reload lines, no tracebacks.
3. **REPL unit checks** (`~/.talon/.venv/bin/repl`, no calendar writes):
   - Year inference: a month/day already past resolves to next year; a future one to
     this year.
   - `"February", 30` → rejected (returns error/None, no window).
   - Feb 29 resolves to the next leap year.
   - Duration parse: "45 minutes"→45, "one hour"→60, "two hours"→120,
     "three hours"→180, "an hour and a half"→90, "half an hour"→30; omitted→60.
   - Title escaping: `Bob's "1-on-1"` round-trips into a safe script string.
4. **End-to-end:** speak a real command for an event ~3 days out → confirmation window
   shows correct parse → "yes" → event appears in Calendar. Then exercise one
   edit-in-place correction (e.g. "retitle …") on a second event before "yes". Delete
   the test events afterward (voice "delete event" or via Calendar).

## Resolved decisions

- Fields: title + date + time + **duration** (duration added at user request).
- Date form: month + day only.
- Behavior: one-shot utterance → **confirm first** → **edit-in-place** correction of
  individual fields; "cancel" discards as the escape hatch.
- Creation: Approach A — **AppleScript direct-create**.
- Target calendar: **"Calendar"** (configurable constant).
