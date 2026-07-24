> **SUPERSEDED (2026-07-24).** This custom-build approach was abandoned. On macOS Tahoe every write path to Apple Calendar failed: AppleScript was denied (TCC), pyobjc/EventKit was rejected by hardened-runtime library validation inside both Talon.app and its venv python, and CalDAV writes never persisted. The calendar need is now met via Claude's Google Calendar connector / Cowork — natural-language event management, verified working end-to-end. Kept as a decision record only.

# Voice Calendar Planner — Plan 1: Foundation & Voice Loop

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Voice-drive a single day of Apple Calendar — view its real events (numbered), stage add/edit/move/delete changes, and commit the batch to Calendar via EventKit — with an interim imgui window as the display. No web UI yet (Plan 2).

**Architecture:** All in Talon's Python process. A pure, Talon-free `calendar_core` owns the day model and the staged diff. A thin `calendar_eventkit` adapter is the only EventKit importer (reads the day, commits creates/updates/deletes). A `calendar_planner` Talon module wires voice actions to the core, commits through the adapter, and renders the numbered day in an imgui window. Grammar lives in `.talon` files. Reuses the existing, tested `calendar_logic.py` for time/date parsing.

**Tech Stack:** Python 3.13 (Talon venv), Talon (`Module`, `Context`, `imgui`, `mod.list`, `mod.capture`, `mod.tag`, `app`), `pyobjc-framework-EventKit` (EventKit + Foundation via PyObjC). Reuses community captures `<user.prose_time>`, `<user.ordinals>`, `<number_small>`, `<user.text>`.

## Global Constraints

- **Files sync manually:** repo at `~/gitHubRepository/talonHelper/`; Talon loads from `~/.talon/user/`. Edit repo copies, then `cp` to `~/.talon/user/mystuff/` (and `~/.talon/user/` for `aaa_security.py`). The `cp` needs the sandbox disabled (writes to `~/.talon/` are blocked in-sandbox).
- **EventKit is the only Calendar mechanism.** AppleScript to Calendar is blocked on macOS Tahoe — do not reintroduce it.
- **Target calendar:** `store.defaultCalendarForNewEvents()`. Constant `TARGET_CALENDAR_TITLE = "Calendar"` is used only to *report* the name; new events go to the default calendar.
- **Number addressing:** events are addressed by 1-based badge number as shown, ordered all-day first (in add order) then timed by start time.
- **Default duration:** 60 minutes when omitted. **Make-timed** requires an explicit time.
- **Test runner:** `~/.talon/.venv/bin/python`, prefixed `PYTHONDONTWRITEBYTECODE=1`. Pure-logic tests import `calendar_core` / `calendar_logic` directly (no talon).
- **REPL is single-line only:** pipe one-line commands: `echo 'stmt; stmt' | ~/.talon/.venv/bin/repl`.
- **Talon reload check:** after `cp`, `tail ~/.talon/talon.log` must show `DEBUG [~]`/`[+]` reload lines and **no `Traceback` / `ParseError`** for the changed files.
- **Commits:** main-based. End commit messages with:
  ```
  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU
  ```

---

## File Structure

- Create `mystuff/calendar_core.py` — pure day model + staged diff. No `talon`, no EventKit.
- Create `mystuff/test_calendar_core.py` — plain-Python tests for `calendar_core`.
- Create `mystuff/calendar_eventkit.py` — EventKit adapter (only EventKit importer).
- Create `mystuff/calendar_planner.py` — Talon module: actions, state, imgui window, tag.
- Create `mystuff/calendar_planner.talon` — global navigation/create grammar.
- Create `mystuff/calendar_planner_edit.talon` — tag-scoped edit/commit grammar.
- Reuse `mystuff/calendar_logic.py` — existing, tested; imported by `calendar_core`.
- Modify `aaa_security.py` (repo root) + `~/.talon/user/aaa_security.py` — add `calendar_planner.py` to `TRUSTED_FILES`; remove the retired `calendar_event.py` entry.
- Delete `mystuff/calendar_event.py`, `mystuff/calendar_event.talon`, `mystuff/calendar_event_confirm.talon` (retired AppleScript feature) — Task 8.

---

## Task 1: EventKit foundation spike (DECISION GATE)

**Purpose:** prove `pyobjc-framework-EventKit` installs into Talon's venv, imports in-process, the Calendars permission prompt appears under Talon's identity, and a read/create/delete round-trips. **If any step fails, STOP and report — the architecture depends on this.**

**Files:** none (environment + validation only).

- [ ] **Step 1: Install PyObjC EventKit into Talon's venv**

Run (sandbox disabled — network + venv write):
```bash
~/.talon/.venv/bin/python -m pip install --disable-pip-version-check pyobjc-framework-EventKit
```
Expected: installs `pyobjc-core`, `pyobjc-framework-Cocoa`, `pyobjc-framework-EventKit` (or reports already satisfied). Exit 0.

- [ ] **Step 2: Verify import in Talon's process (REPL)**

Run:
```bash
echo 'import EventKit, Foundation; print("EK_OK", EventKit.EKEventStore is not None, Foundation.NSDate is not None)' | ~/.talon/.venv/bin/repl 2>&1 | grep -iE 'EK_OK|Error'
```
Expected: `EK_OK True True`. If `ModuleNotFound`, the in-process interpreter differs from the pip target — STOP and report.

- [ ] **Step 3: Request Calendars access + read (REPL, triggers the one-time prompt)**

Run (a dialog "Talon would like to access Calendar" should appear — allow it):
```bash
echo 'import EventKit, threading; s=EventKit.EKEventStore.alloc().init(); ev=threading.Event(); res={}; \
cb=lambda ok,err:(res.__setitem__("ok",ok), ev.set()); \
(s.requestFullAccessToEventsWithCompletion_(cb) if hasattr(s,"requestFullAccessToEventsWithCompletion_") else s.requestAccessToEntityType_completion_(0,cb)); \
ev.wait(60); print("ACCESS", res.get("ok"), "STATUS", EventKit.EKEventStore.authorizationStatusForEntityType_(0), "DEFCAL", s.defaultCalendarForNewEvents().title() if res.get("ok") else None)' | ~/.talon/.venv/bin/repl 2>&1 | grep -iE 'ACCESS|Error'
```
Expected: `ACCESS 1 STATUS 3 DEFCAL <your default calendar name>` (status 3 = authorized; on some OS the full-access status enum may differ — any non-0/2 authorized value with `ACCESS 1` is a pass). If `ACCESS 0`/denied, STOP: the in-process permission path failed (fallback = signed helper app, out of scope for this plan).

- [ ] **Step 4: Create + read-back + delete a throwaway event (REPL)**

Run:
```bash
echo 'import EventKit, Foundation, threading; s=EventKit.EKEventStore.alloc().init(); ev=threading.Event(); \
(s.requestFullAccessToEventsWithCompletion_(lambda ok,e: ev.set()) if hasattr(s,"requestFullAccessToEventsWithCompletion_") else s.requestAccessToEntityType_completion_(0, lambda ok,e: ev.set())); ev.wait(30); \
import time; st=Foundation.NSDate.dateWithTimeIntervalSince1970_(time.time()+3600); en=Foundation.NSDate.dateWithTimeIntervalSince1970_(time.time()+7200); \
e=EventKit.EKEvent.eventWithEventStore_(s); e.setTitle_("EK spike test"); e.setStartDate_(st); e.setEndDate_(en); e.setCalendar_(s.defaultCalendarForNewEvents()); \
ok,err=s.saveEvent_span_error_(e, 0, None); uid=e.eventIdentifier(); print("SAVED", ok, "UID", uid[:12]); \
fetched=s.eventWithIdentifier_(uid); print("READBACK", fetched.title()); \
ok2,err2=s.removeEvent_span_error_(fetched, 0, None); print("DELETED", ok2)' | ~/.talon/.venv/bin/repl 2>&1 | grep -iE 'SAVED|READBACK|DELETED|Error'
```
Expected: `SAVED 1 UID <hex>`, `READBACK EK spike test`, `DELETED 1`. This confirms the exact adapter API used in Task 5.

- [ ] **Step 5: Commit a note recording the validated API**

No code to commit yet; record the outcome in the session and proceed. (The validated calls — `requestFullAccessToEventsWithCompletion_`, `saveEvent_span_error_(e,0,None)`, `eventWithIdentifier_`, `removeEvent_span_error_` — are what Task 5 uses.)

---

## Task 2: `calendar_core` — event model + load

**Files:**
- Create: `mystuff/calendar_core.py`
- Test: `mystuff/test_calendar_core.py`

**Interfaces:**
- Consumes: stdlib only (dataclasses, datetime). (`calendar_logic` is used by the Talon layer, not here.)
- Produces:
  - `EventVM` dataclass: `uid: str`, `title: str`, `all_day: bool`, `start: datetime`, `end: datetime`, `status: str` (`"unchanged"|"new"|"edited"|"deleted"`), `original: dict | None`, `moved_off: bool` (True when an edited event's start date differs from the model's day).
  - `RealEvent` = plain dict `{uid, title, all_day, start, end}` (what the adapter yields).
  - `DayModel` dataclass: `day: date`, `events: list[EventVM]`.
  - `load(day: date, real_events: list[dict]) -> DayModel` — build a model; every event `status="unchanged"`, `original=None`, ordered all-day-first then by `start`.
  - `ordered(model) -> list[EventVM]` — the display order (drives badge numbers); excludes nothing (deleted shown struck).

- [ ] **Step 1: Write the failing test**

Create `mystuff/test_calendar_core.py`:
```python
from __future__ import annotations

from datetime import date, datetime

import calendar_core as cc


def check(label, cond):
    if not cond:
        raise AssertionError(label)
    print(f"ok: {label}")


DAY = date(2026, 8, 15)


def real(uid, title, all_day, sh, sm, eh, em):
    return {
        "uid": uid, "title": title, "all_day": all_day,
        "start": datetime(2026, 8, 15, sh, sm),
        "end": datetime(2026, 8, 15, eh, em),
    }


# load orders all-day first, then timed by start
m = cc.load(DAY, [
    real("u2", "Standup", False, 9, 0, 9, 30),
    real("u3", "Lunch", False, 12, 0, 13, 0),
    real("u1", "Holiday", True, 0, 0, 0, 0),
])
order = [e.title for e in cc.ordered(m)]
check("all-day first then timed by start", order == ["Holiday", "Standup", "Lunch"])
check("loaded unchanged", all(e.status == "unchanged" for e in m.events))
check("day set", m.day == DAY)

print("ALL PASS")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/gitHubRepository/talonHelper/mystuff && PYTHONDONTWRITEBYTECODE=1 ~/.talon/.venv/bin/python test_calendar_core.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'calendar_core'`.

- [ ] **Step 3: Write minimal implementation**

Create `mystuff/calendar_core.py`:
```python
"""Pure day model + staged diff for the voice calendar planner. No talon,
no EventKit imports, so it is unit-testable with plain Python."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta


@dataclass
class EventVM:
    uid: str                      # real Calendar id, or "new-N" for staged-new
    title: str
    all_day: bool
    start: datetime
    end: datetime
    status: str = "unchanged"     # unchanged | new | edited | deleted
    original: dict | None = None  # snapshot for revert of edited/deleted
    moved_off: bool = False       # edited event whose start date left model.day


@dataclass
class DayModel:
    day: date
    events: list[EventVM] = field(default_factory=list)
    _new_seq: int = 0


def _sort_key(e: EventVM):
    # all-day first (0), then timed (1) by start time
    return (0 if e.all_day else 1, e.start)


def load(day: date, real_events: list[dict]) -> DayModel:
    evs = [
        EventVM(
            uid=r["uid"], title=r["title"], all_day=r["all_day"],
            start=r["start"], end=r["end"], status="unchanged",
        )
        for r in real_events
    ]
    evs.sort(key=_sort_key)
    return DayModel(day=day, events=evs)


def ordered(model: DayModel) -> list[EventVM]:
    return sorted(model.events, key=_sort_key)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/gitHubRepository/talonHelper/mystuff && PYTHONDONTWRITEBYTECODE=1 ~/.talon/.venv/bin/python test_calendar_core.py`
Expected: `ok:` lines ending `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_core.py mystuff/test_calendar_core.py
git commit -m "feat(planner): day model + load for voice calendar planner

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 3: `calendar_core` — mutators + status tracking

**Files:**
- Modify: `mystuff/calendar_core.py`
- Modify: `mystuff/test_calendar_core.py`

**Interfaces:**
- Consumes: `EventVM`, `DayModel`, `ordered` (Task 2).
- Produces (all raise `ValueError` on a bad 1-based `n`; all operate on display order):
  - `add_timed(model, title, start, dur_min) -> EventVM`
  - `add_all_day(model, title) -> EventVM`
  - `retitle(model, n, title)`
  - `move(model, n, new_start)` — shifts end to preserve duration; sets `moved_off`.
  - `set_duration(model, n, minutes)`
  - `make_all_day(model, n)`
  - `make_timed(model, n, new_start, dur_min=60)`
  - `delete(model, n)` — new events are removed outright; real events marked `deleted`.
  - `restore(model, n)` — revert a `deleted`/`edited` event to `original`.
  - helper `_nth(model, n) -> EventVM`.

- [ ] **Step 1: Write the failing test (append)**

Append to `mystuff/test_calendar_core.py` before `print("ALL PASS")`:
```python
# --- mutators -------------------------------------------------------------
def fresh():
    return cc.load(DAY, [
        real("u1", "Holiday", True, 0, 0, 0, 0),
        real("u2", "Standup", False, 9, 0, 9, 30),
    ])

# add_timed appends a new timed event, status new, uid new-*
m = fresh(); e = cc.add_timed(m, "Lunch", datetime(2026, 8, 15, 12, 0), 60)
check("add_timed new", e.status == "new" and e.uid.startswith("new-"))
check("add_timed end", e.end == datetime(2026, 8, 15, 13, 0))
check("add_timed ordered last", cc.ordered(m)[-1].title == "Lunch")

# add_all_day
m = fresh(); e = cc.add_all_day(m, "Trip")
check("add_all_day new all_day", e.status == "new" and e.all_day)

# retitle marks edited + snapshots original
m = fresh(); cc.retitle(m, 2, "Team Standup")
e = cc.ordered(m)[1]
check("retitle applied", e.title == "Team Standup")
check("retitle edited", e.status == "edited" and e.original["title"] == "Standup")

# move preserves duration, sets moved_off when day changes
m = fresh(); cc.move(m, 2, datetime(2026, 8, 20, 15, 0))
e = cc.ordered(m)[1]
check("move start", e.start == datetime(2026, 8, 20, 15, 0))
check("move keeps 30m", e.end == datetime(2026, 8, 20, 15, 30))
check("move moved_off", e.moved_off is True)

# move same day does not set moved_off
m = fresh(); cc.move(m, 2, datetime(2026, 8, 15, 16, 0))
check("move same day not moved_off", cc.ordered(m)[1].moved_off is False)

# set_duration
m = fresh(); cc.set_duration(m, 2, 90)
check("set_duration", cc.ordered(m)[1].end == datetime(2026, 8, 15, 10, 30))

# make_all_day / make_timed
m = fresh(); cc.make_all_day(m, 2)
check("make_all_day", cc.ordered(m)[0].all_day and cc.ordered(m)[0].title == "Standup" or
      any(e.all_day and e.title == "Standup" for e in m.events))
m = fresh(); cc.make_timed(m, 1, datetime(2026, 8, 15, 8, 0), 60)
e = [x for x in m.events if x.title == "Holiday"][0]
check("make_timed not all_day", e.all_day is False and e.start == datetime(2026, 8, 15, 8, 0))

# delete: real -> marked deleted; new -> removed
m = fresh(); cc.delete(m, 2)
check("delete real marks deleted", any(e.status == "deleted" for e in m.events))
m = fresh(); n = cc.add_timed(m, "Temp", datetime(2026, 8, 15, 17, 0), 60)
idx = cc.ordered(m).index(n) + 1; cc.delete(m, idx)
check("delete new removes it", all(e.title != "Temp" for e in m.events))

# restore reverts edited
m = fresh(); cc.retitle(m, 2, "X"); 
e = cc.ordered(m)[1]; ridx = cc.ordered(m).index(e) + 1; cc.restore(m, ridx)
check("restore reverts", cc.ordered(m)[1].title == "Standup" and cc.ordered(m)[1].status == "unchanged")

# bad index
try:
    cc.retitle(fresh(), 9, "x"); raise SystemExit("expected ValueError")
except ValueError:
    print("ok: bad index rejected")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/gitHubRepository/talonHelper/mystuff && PYTHONDONTWRITEBYTECODE=1 ~/.talon/.venv/bin/python test_calendar_core.py`
Expected: FAIL — `AttributeError: module 'calendar_core' has no attribute 'add_timed'`.

- [ ] **Step 3: Write minimal implementation (append to `calendar_core.py`)**

```python
def _nth(model: DayModel, n: int) -> EventVM:
    order = ordered(model)
    if not (1 <= n <= len(order)):
        raise ValueError(f"no event number {n}")
    return order[n - 1]


def _snapshot(e: EventVM) -> dict:
    return {
        "title": e.title, "all_day": e.all_day,
        "start": e.start, "end": e.end,
    }


def _mark_edited(model: DayModel, e: EventVM) -> None:
    if e.status == "unchanged":
        e.original = _snapshot(e)
        e.status = "edited"
    e.moved_off = (not e.all_day) and (e.start.date() != model.day)


def add_timed(model: DayModel, title: str, start: datetime, dur_min: int) -> EventVM:
    model._new_seq += 1
    e = EventVM(
        uid=f"new-{model._new_seq}", title=title, all_day=False,
        start=start, end=start + timedelta(minutes=dur_min), status="new",
    )
    model.events.append(e)
    return e


def add_all_day(model: DayModel, title: str) -> EventVM:
    model._new_seq += 1
    midnight = datetime.combine(model.day, datetime.min.time())
    e = EventVM(
        uid=f"new-{model._new_seq}", title=title, all_day=True,
        start=midnight, end=midnight + timedelta(days=1), status="new",
    )
    model.events.append(e)
    return e


def retitle(model: DayModel, n: int, title: str) -> None:
    e = _nth(model, n)
    _mark_edited(model, e)
    e.title = title


def move(model: DayModel, n: int, new_start: datetime) -> None:
    e = _nth(model, n)
    dur = e.end - e.start
    _mark_edited(model, e)
    e.all_day = False
    e.start = new_start
    e.end = new_start + (dur if dur else timedelta(minutes=60))
    e.moved_off = new_start.date() != model.day


def set_duration(model: DayModel, n: int, minutes: int) -> None:
    e = _nth(model, n)
    _mark_edited(model, e)
    e.all_day = False
    e.end = e.start + timedelta(minutes=minutes)


def make_all_day(model: DayModel, n: int) -> None:
    e = _nth(model, n)
    _mark_edited(model, e)
    e.all_day = True
    midnight = datetime.combine(model.day, datetime.min.time())
    e.start, e.end = midnight, midnight + timedelta(days=1)
    e.moved_off = False


def make_timed(model: DayModel, n: int, new_start: datetime, dur_min: int = 60) -> None:
    e = _nth(model, n)
    _mark_edited(model, e)
    e.all_day = False
    e.start = new_start
    e.end = new_start + timedelta(minutes=dur_min)
    e.moved_off = new_start.date() != model.day


def delete(model: DayModel, n: int) -> None:
    e = _nth(model, n)
    if e.status == "new":
        model.events.remove(e)
        return
    if e.original is None:
        e.original = _snapshot(e)
    e.status = "deleted"


def restore(model: DayModel, n: int) -> None:
    e = _nth(model, n)
    if e.original is None:
        return
    e.title = e.original["title"]
    e.all_day = e.original["all_day"]
    e.start = e.original["start"]
    e.end = e.original["end"]
    e.status = "unchanged"
    e.original = None
    e.moved_off = False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/gitHubRepository/talonHelper/mystuff && PYTHONDONTWRITEBYTECODE=1 ~/.talon/.venv/bin/python test_calendar_core.py`
Expected: all `ok:` lines through `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_core.py mystuff/test_calendar_core.py
git commit -m "feat(planner): staged mutators (add/retitle/move/duration/all-day/delete/restore)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 4: `calendar_core` — pending_changes + display_state

**Files:**
- Modify: `mystuff/calendar_core.py`
- Modify: `mystuff/test_calendar_core.py`

**Interfaces:**
- Consumes: `DayModel`, `EventVM`, `ordered` (Tasks 2-3).
- Produces:
  - `pending_changes(model) -> dict` with keys `create: list[EventVM]` (status new), `update: list[EventVM]` (status edited), `delete: list[EventVM]` (status deleted). Unchanged events excluded.
  - `has_pending(model) -> bool`.
  - `display_state(model) -> dict` — JSON-safe (used by imgui now, web later):
    `{ "day": "YYYY-MM-DD", "day_label": "Sat Aug 15 2026", "all_day": [row...], "timed": [row...], "pending": {"create":c,"update":u,"delete":d} }`
    where each row is `{ "n": int, "title": str, "time": str, "status": str, "moved_off": bool, "moved_to": str|"" }`. `time` is `"all-day"` for all-day, else `"9:00 AM - 9:30 AM"`. Badge numbers `n` follow `ordered`.

- [ ] **Step 1: Write the failing test (append)**

Append before `print("ALL PASS")`:
```python
# --- pending_changes + display_state -------------------------------------
m = fresh()
cc.add_timed(m, "Lunch", datetime(2026, 8, 15, 12, 0), 60)   # create
cc.retitle(m, 2, "Team Standup")                              # update (Standup)
cc.delete(m, 1)                                               # delete (Holiday)
pc = cc.pending_changes(m)
check("pending create 1", len(pc["create"]) == 1)
check("pending update 1", len(pc["update"]) == 1)
check("pending delete 1", len(pc["delete"]) == 1)
check("has_pending", cc.has_pending(m) is True)

ds = cc.display_state(m)
check("ds day_label", ds["day_label"] == "Sat Aug 15 2026")
check("ds numbers contiguous", [r["n"] for r in ds["all_day"] + ds["timed"]] == [1, 2, 3])
lunch = [r for r in ds["timed"] if r["title"] == "Lunch"][0]
check("ds lunch time", lunch["time"] == "12:00 PM - 1:00 PM" and lunch["status"] == "new")

m2 = fresh(); cc.move(m2, 2, datetime(2026, 8, 20, 15, 0))
ds2 = cc.display_state(m2)
moved = [r for r in ds2["timed"] if r["title"] == "Standup"][0]
check("ds moved_to", moved["moved_off"] and moved["moved_to"] == "Aug 20")
check("no pending when clean", cc.has_pending(fresh()) is False)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd ~/gitHubRepository/talonHelper/mystuff && PYTHONDONTWRITEBYTECODE=1 ~/.talon/.venv/bin/python test_calendar_core.py`
Expected: FAIL — `AttributeError: ... 'pending_changes'`.

- [ ] **Step 3: Write minimal implementation (append to `calendar_core.py`)**

```python
def pending_changes(model: DayModel) -> dict:
    out = {"create": [], "update": [], "delete": []}
    for e in model.events:
        if e.status == "new":
            out["create"].append(e)
        elif e.status == "edited":
            out["update"].append(e)
        elif e.status == "deleted":
            out["delete"].append(e)
    return out


def has_pending(model: DayModel) -> bool:
    return any(e.status != "unchanged" for e in model.events)


def _fmt_time(e: EventVM) -> str:
    if e.all_day:
        return "all-day"
    return f"{e.start.strftime('%-I:%M %p')} - {e.end.strftime('%-I:%M %p')}"


def display_state(model: DayModel) -> dict:
    order = ordered(model)
    rows = []
    for i, e in enumerate(order, start=1):
        rows.append({
            "n": i,
            "title": e.title,
            "time": _fmt_time(e),
            "status": e.status,
            "moved_off": e.moved_off,
            "moved_to": e.start.strftime("%b %-d") if e.moved_off else "",
        })
    pc = pending_changes(model)
    return {
        "day": model.day.isoformat(),
        "day_label": model.day.strftime("%a %b %d %Y"),
        "all_day": [r for r, e in zip(rows, order) if e.all_day],
        "timed": [r for r, e in zip(rows, order) if not e.all_day],
        "pending": {
            "create": len(pc["create"]),
            "update": len(pc["update"]),
            "delete": len(pc["delete"]),
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd ~/gitHubRepository/talonHelper/mystuff && PYTHONDONTWRITEBYTECODE=1 ~/.talon/.venv/bin/python test_calendar_core.py`
Expected: `ALL PASS`, exit 0.

- [ ] **Step 5: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_core.py mystuff/test_calendar_core.py
git commit -m "feat(planner): pending diff + display_state for the day model

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 5: `calendar_eventkit` — EventKit adapter

**Files:**
- Create: `mystuff/calendar_eventkit.py`

**Interfaces:**
- Consumes: `EventKit`, `Foundation` (validated in Task 1); `calendar_core.EventVM` shape via duck-typing (reads `.uid/.title/.all_day/.start/.end`).
- Produces:
  - `request_access(timeout=60) -> bool`
  - `authorized() -> bool`
  - `default_calendar_name() -> str | None`
  - `read_day(day: date) -> list[dict]` — `[{uid,title,all_day,start,end}]` for events intersecting `day`, timed by start.
  - `commit(changes: dict) -> dict` — apply `create/update/delete` lists of `EventVM`; return `{"ok": int, "failed": [(title, reason)...]}`.
  - module-level singleton store via `_store()`.

- [ ] **Step 1: Create the adapter**

Create `mystuff/calendar_eventkit.py`:
```python
"""EventKit adapter — the only module that imports EventKit. Converts between
Python datetimes and NSDate and applies the staged diff to real Calendar."""

from __future__ import annotations

import threading
import time
from datetime import date, datetime, timedelta

import EventKit
import Foundation

_ENTITY_EVENT = 0  # EKEntityTypeEvent
_SPAN_THIS = 0     # EKSpanThisEvent
_store_obj = None


def _store():
    global _store_obj
    if _store_obj is None:
        _store_obj = EventKit.EKEventStore.alloc().init()
    return _store_obj


def _ns(dt: datetime):
    return Foundation.NSDate.dateWithTimeIntervalSince1970_(dt.timestamp())


def _py(nsdate) -> datetime:
    return datetime.fromtimestamp(nsdate.timeIntervalSince1970())


def authorized() -> bool:
    st = EventKit.EKEventStore.authorizationStatusForEntityType_(_ENTITY_EVENT)
    return st in (3, 4)  # 3=authorized, 4=fullAccess (OS-dependent)


def request_access(timeout: int = 60) -> bool:
    s = _store()
    ev = threading.Event()
    box = {}

    def cb(ok, err):
        box["ok"] = bool(ok)
        ev.set()

    if hasattr(s, "requestFullAccessToEventsWithCompletion_"):
        s.requestFullAccessToEventsWithCompletion_(cb)
    else:
        s.requestAccessToEntityType_completion_(_ENTITY_EVENT, cb)
    ev.wait(timeout)
    return box.get("ok", False) or authorized()


def default_calendar_name():
    cal = _store().defaultCalendarForNewEvents()
    return cal.title() if cal else None


def read_day(day: date) -> list[dict]:
    s = _store()
    start = _ns(datetime.combine(day, datetime.min.time()))
    end = _ns(datetime.combine(day, datetime.min.time()) + timedelta(days=1))
    pred = s.predicateForEventsWithStartDate_endDate_calendars_(start, end, None)
    out = []
    for e in s.eventsMatchingPredicate_(pred):
        out.append({
            "uid": e.eventIdentifier(),
            "title": e.title() or "",
            "all_day": bool(e.isAllDay()),
            "start": _py(e.startDate()),
            "end": _py(e.endDate()),
        })
    out.sort(key=lambda r: (0 if r["all_day"] else 1, r["start"]))
    return out


def _apply_fields(ek_event, vm) -> None:
    ek_event.setTitle_(vm.title)
    ek_event.setAllDay_(bool(vm.all_day))
    ek_event.setStartDate_(_ns(vm.start))
    ek_event.setEndDate_(_ns(vm.end))


def commit(changes: dict) -> dict:
    s = _store()
    ok = 0
    failed = []
    cal = s.defaultCalendarForNewEvents()

    for vm in changes.get("create", []):
        try:
            e = EventKit.EKEvent.eventWithEventStore_(s)
            e.setCalendar_(cal)
            _apply_fields(e, vm)
            saved, err = s.saveEvent_span_error_(e, _SPAN_THIS, None)
            ok += 1 if saved else 0
            if not saved:
                failed.append((vm.title, str(err)))
        except Exception as exc:  # noqa: BLE001
            failed.append((vm.title, str(exc)))

    for vm in changes.get("update", []):
        try:
            e = s.eventWithIdentifier_(vm.uid)
            if e is None:
                failed.append((vm.title, "event no longer exists"))
                continue
            _apply_fields(e, vm)
            saved, err = s.saveEvent_span_error_(e, _SPAN_THIS, None)
            ok += 1 if saved else 0
            if not saved:
                failed.append((vm.title, str(err)))
        except Exception as exc:  # noqa: BLE001
            failed.append((vm.title, str(exc)))

    for vm in changes.get("delete", []):
        try:
            e = s.eventWithIdentifier_(vm.uid)
            if e is None:
                ok += 1  # already gone
                continue
            removed, err = s.removeEvent_span_error_(e, _SPAN_THIS, None)
            ok += 1 if removed else 0
            if not removed:
                failed.append((vm.title, str(err)))
        except Exception as exc:  # noqa: BLE001
            failed.append((vm.title, str(exc)))

    return {"ok": ok, "failed": failed}
```

- [ ] **Step 2: Syntax-check**

Run:
```bash
cd ~/gitHubRepository/talonHelper
~/.talon/.venv/bin/python -c "import ast,sys; ast.parse(open('mystuff/calendar_eventkit.py').read()); print('OK')"
```
Expected: `OK`.

- [ ] **Step 3: Live round-trip via REPL** (needs Task 1 access granted)

Deploy then exercise:
```bash
cp ~/gitHubRepository/talonHelper/mystuff/calendar_eventkit.py ~/.talon/user/mystuff/
sleep 3
echo 'import sys; from datetime import date, datetime, timedelta; m=sys.modules["user.mystuff.calendar_eventkit"]; \
print("AUTH", m.request_access()); \
class V: pass
v=V(); v.uid="new-1"; v.title="EK adapter test"; v.all_day=False; v.start=datetime.now()+timedelta(days=2); v.end=v.start+timedelta(hours=1); \
r=m.commit({"create":[v],"update":[],"delete":[]}); print("COMMIT", r); \
today_plus=v.start.date(); rows=m.read_day(today_plus); print("READ", [x["title"] for x in rows if x["title"]=="EK adapter test"])' | ~/.talon/.venv/bin/repl 2>&1 | grep -iE 'AUTH|COMMIT|READ|Error'
```
Expected: `AUTH True`, `COMMIT {'ok': 1, 'failed': []}`, `READ ['EK adapter test']`.

- [ ] **Step 4: Delete the test event (sandbox disabled)**

```bash
echo 'import sys; from datetime import datetime, timedelta; m=sys.modules["user.mystuff.calendar_eventkit"]; \
d=(datetime.now()+timedelta(days=2)).date(); rows=[r for r in m.read_day(d) if r["title"]=="EK adapter test"]; \
class V: pass
outs=[]
for r in rows:
    v=V(); v.uid=r["uid"]; v.title=r["title"]; v.all_day=r["all_day"]; v.start=r["start"]; v.end=r["end"]; outs.append(v)
print("DEL", m.commit({"create":[],"update":[],"delete":outs}))' | ~/.talon/.venv/bin/repl 2>&1 | grep -iE 'DEL|Error'
```
Expected: `DEL {'ok': 1, 'failed': []}` (or more if duplicates). Confirm none remain.

- [ ] **Step 5: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_eventkit.py
git commit -m "feat(planner): EventKit adapter (access, read_day, commit)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 6: `calendar_planner` Talon module + imgui display + sandbox trust

**Files:**
- Create: `mystuff/calendar_planner.py`
- Modify: `aaa_security.py` (repo root)

**Interfaces:**
- Consumes: `calendar_core` (Tasks 2-4), `calendar_eventkit` (Task 5), `calendar_logic` (existing) for `parse_prose_time`; community captures via grammar (Task 7).
- Produces (used by Task 7 grammar): lists `user.calendar_month`; captures `user.calendar_day -> int`, `user.calendar_duration -> int`; tag `user.calendar_planner_open`; actions listed below.

- [ ] **Step 1: Create the module**

Create `mystuff/calendar_planner.py`:
```python
"""Voice calendar planner — Talon glue: navigation, staged edits, commit,
and an interim imgui window showing the numbered day."""

from datetime import date, datetime, timedelta

from talon import Context, Module, actions, app, imgui

from . import calendar_core as cc
from . import calendar_eventkit as ek
from . import calendar_logic as cl

mod = Module()
ctx = Context()

mod.tag("calendar_planner_open", desc="Active while the planner window is open")

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}
mod.list("calendar_month", desc="Month name to number")
ctx.lists["user.calendar_month"] = {k: str(v) for k, v in _MONTHS.items()}

ctx.lists["user.calendar_time_unit"] = {
    "hour": "h", "hours": "h", "minute": "m", "minutes": "m",
    "min": "m", "mins": "m",
}
mod.list("calendar_time_unit", desc="Duration unit -> h/m")


@mod.capture(rule="<user.ordinals> | <number_small>")
def calendar_day(m) -> int:
    return int(m[0])


@mod.capture(rule="<number_small> {user.calendar_time_unit} [<number_small> {user.calendar_time_unit}]")
def calendar_duration(m) -> int:
    nums = list(m.number_small_list)
    units = list(m.calendar_time_unit_list)
    return cl.combine_duration(list(zip(nums, units)))


_state = {"model": None, "day": date.today(), "msg": ""}


def _notify(msg: str) -> None:
    _state["msg"] = msg
    print(f"calendar_planner: {msg}")
    app.notify(body=msg)


def _reload(day: date) -> None:
    if not ek.authorized() and not ek.request_access():
        _state["model"] = None
        _notify("grant Calendar access in System Settings > Privacy > Calendars")
        return
    rows = ek.read_day(day)
    _state["model"] = cc.load(day, rows)
    _state["day"] = day


def _model() -> "cc.DayModel | None":
    return _state["model"]


@imgui.open(y=10, x=500)
def gui(gui: imgui.GUI):
    m = _model()
    if m is None:
        gui.text("Calendar planner")
        gui.line()
        gui.text(_state["msg"] or "no calendar access")
        if gui.button("Planner close"):
            actions.user.planner_close()
        return
    ds = cc.display_state(m)
    gui.text(f"Planner — {ds['day_label']}")
    gui.line()
    if ds["all_day"]:
        gui.text("all-day:")
        for r in ds["all_day"]:
            gui.text(f"  {r['n']}. [{r['status'][:3]}] {r['title']}")
    for r in ds["timed"]:
        suffix = f"  -> {r['moved_to']}" if r["moved_off"] else ""
        gui.text(f"{r['n']}. [{r['status'][:3]}] {r['time']}  {r['title']}{suffix}")
    gui.spacer()
    p = ds["pending"]
    gui.text(f"pending  +{p['create']} ~{p['update']} -{p['delete']}")
    gui.text('"commit" save · "discard" undo · "next day"/"previous day"')
    if _state["msg"]:
        gui.text(_state["msg"])
    if gui.button("Planner close"):
        actions.user.planner_close()


def _require_open() -> "cc.DayModel | None":
    m = _model()
    if m is None or not gui.showing:
        return None
    return m


@mod.action_class
class Actions:
    def planner_show():
        """Open the planner on today (or refresh)."""
        _state["msg"] = ""
        _reload(_state["day"] or date.today())
        ctx.tags = ["user.calendar_planner_open"]
        gui.show()

    def planner_day(month: str, day: int):
        """Open/switch the planner to a specific month/day (year inferred >= today)."""
        now = date.today()
        y = now.year
        try:
            target = date(y, int(month), int(day))
            if target < now:
                target = date(y + 1, int(month), int(day))
        except ValueError:
            _notify("no such date")
            return
        _state["msg"] = ""
        _reload(target)
        ctx.tags = ["user.calendar_planner_open"]
        gui.show()

    def planner_shift(delta: int):
        """Move the viewed day by delta days (+1 next, -1 previous, 0 today)."""
        base = date.today() if delta == 0 else (_state["day"] + timedelta(days=delta))
        _state["msg"] = ""
        _reload(base)

    def planner_add_timed(title: str, prose_time: str, duration_min: int = 60):
        """Stage a new timed event on the viewed day."""
        m = _require_open()
        if m is None:
            return
        try:
            h, mi = cl.parse_prose_time(prose_time)
        except ValueError as exc:
            _notify(str(exc))
            return
        start = datetime.combine(m.day, datetime.min.time()).replace(hour=h, minute=mi)
        cc.add_timed(m, title.strip(), start, int(duration_min))
        _state["msg"] = f"added {title.strip()}"

    def planner_add_all_day(title: str):
        """Stage a new all-day event on the viewed day."""
        m = _require_open()
        if m is None:
            return
        cc.add_all_day(m, title.strip())
        _state["msg"] = f"added {title.strip()} (all-day)"

    def planner_retitle(n: int, title: str):
        """Retitle event n."""
        m = _require_open()
        if m is None:
            return
        try:
            cc.retitle(m, int(n), title.strip())
        except ValueError as exc:
            _notify(str(exc))

    def planner_move(n: int, month: str = "", day: int = 0, prose_time: str = ""):
        """Move event n to a new time and/or day. month/day optional (keep day)."""
        m = _require_open()
        if m is None:
            return
        try:
            e = cc._nth(m, int(n))
            new_day = e.start.date()
            if month and day:
                yy = m.day.year
                nd = date(yy, int(month), int(day))
                new_day = nd if nd >= date.today() else date(yy + 1, int(month), int(day))
            hh, mm = (e.start.hour, e.start.minute)
            if prose_time:
                hh, mm = cl.parse_prose_time(prose_time)
            cc.move(m, int(n), datetime.combine(new_day, datetime.min.time()).replace(hour=hh, minute=mm))
        except ValueError as exc:
            _notify(str(exc))

    def planner_duration(n: int, minutes: int):
        """Set duration of event n (minutes)."""
        m = _require_open()
        if m is None:
            return
        try:
            cc.set_duration(m, int(n), int(minutes))
        except ValueError as exc:
            _notify(str(exc))

    def planner_make_all_day(n: int):
        """Convert event n to all-day."""
        m = _require_open()
        if m is None:
            return
        try:
            cc.make_all_day(m, int(n))
        except ValueError as exc:
            _notify(str(exc))

    def planner_make_timed(n: int, prose_time: str):
        """Convert event n to a timed event at prose_time (default 60m)."""
        m = _require_open()
        if m is None:
            return
        try:
            hh, mm = cl.parse_prose_time(prose_time)
            start = datetime.combine(m.day, datetime.min.time()).replace(hour=hh, minute=mm)
            cc.make_timed(m, int(n), start, 60)
        except ValueError as exc:
            _notify(str(exc))

    def planner_delete(n: int):
        """Delete (stage) event n."""
        m = _require_open()
        if m is None:
            return
        try:
            cc.delete(m, int(n))
        except ValueError as exc:
            _notify(str(exc))

    def planner_restore(n: int):
        """Restore event n."""
        m = _require_open()
        if m is None:
            return
        try:
            cc.restore(m, int(n))
        except ValueError as exc:
            _notify(str(exc))

    def planner_commit():
        """Apply all staged changes to Calendar, then reload."""
        m = _require_open()
        if m is None:
            return
        if not cc.has_pending(m):
            _notify("nothing to commit")
            return
        res = ek.commit(cc.pending_changes(m))
        _reload(m.day)
        if res["failed"]:
            _notify(f"committed {res['ok']}, {len(res['failed'])} failed")
        else:
            _notify(f"committed {res['ok']}")

    def planner_discard():
        """Throw away staged changes (reload from Calendar)."""
        m = _require_open()
        if m is None:
            return
        _reload(m.day)
        _state["msg"] = "discarded"

    def planner_close():
        """Close the planner window."""
        gui.hide()
        ctx.tags = []
```

- [ ] **Step 2: Add module to sandbox trust list**

In `aaa_security.py`, below the `default_app.py` line add:
```python
    os.path.join(TALON_USER_DIR, "mystuff", "calendar_planner.py"),
```

- [ ] **Step 3: Syntax-check both**

```bash
cd ~/gitHubRepository/talonHelper
for f in mystuff/calendar_planner.py aaa_security.py; do ~/.talon/.venv/bin/python -c "import ast,sys; ast.parse(open(sys.argv[1]).read()); print('OK', sys.argv[1])" "$f"; done
```
Expected: `OK mystuff/calendar_planner.py`, `OK aaa_security.py`.

- [ ] **Step 4: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_planner.py aaa_security.py
git commit -m "feat(planner): Talon module + imgui numbered day view + sandbox trust

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 7: Grammar files

**Files:**
- Create: `mystuff/calendar_planner.talon`
- Create: `mystuff/calendar_planner_edit.talon`

**Interfaces:**
- Consumes: Task 6 actions/lists/captures + community `<user.prose_time>`, `<user.text>`.
- Produces: the spoken surface. No downstream consumers.

- [ ] **Step 1: Create the global grammar** (no header → global)

Create `mystuff/calendar_planner.talon`:
```talon
calendar show: user.planner_show()
calendar day {user.calendar_month} <user.calendar_day>: user.planner_day(calendar_month, user.calendar_day)
(next day | day forward): user.planner_shift(1)
(previous day | day back): user.planner_shift(-1)
(planner today | calendar today): user.planner_shift(0)
```

- [ ] **Step 2: Create the tag-scoped edit grammar**

Create `mystuff/calendar_planner_edit.talon`:
```talon
tag: user.calendar_planner_open
-
add <user.text> at <user.prose_time>: user.planner_add_timed(user.text, user.prose_time)
add <user.text> at <user.prose_time> for <user.calendar_duration>: user.planner_add_timed(user.text, user.prose_time, user.calendar_duration)
add <user.text> all day: user.planner_add_all_day(user.text)
retitle <user.calendar_day> <user.text>: user.planner_retitle(user.calendar_day, user.text)
move <user.calendar_day> to <user.prose_time>: user.planner_move(user.calendar_day, "", 0, user.prose_time)
move <user.calendar_day> to {user.calendar_month} <user.calendar_day>: user.planner_move(user.calendar_day_1, calendar_month, user.calendar_day_2)
move <user.calendar_day> to {user.calendar_month} <user.calendar_day> at <user.prose_time>: user.planner_move(user.calendar_day_1, calendar_month, user.calendar_day_2, user.prose_time)
duration <user.calendar_day> <user.calendar_duration>: user.planner_duration(user.calendar_day, user.calendar_duration)
make <user.calendar_day> all day: user.planner_make_all_day(user.calendar_day)
make <user.calendar_day> timed at <user.prose_time>: user.planner_make_timed(user.calendar_day, user.prose_time)
delete <user.calendar_day>: user.planner_delete(user.calendar_day)
restore <user.calendar_day>: user.planner_restore(user.calendar_day)
(commit | save): user.planner_commit()
(discard | cancel): user.planner_discard()
(planner close | close planner): user.planner_close()
```

- [ ] **Step 3: Deploy to live Talon dir** (sandbox disabled)

```bash
cp ~/gitHubRepository/talonHelper/mystuff/calendar_core.py \
   ~/gitHubRepository/talonHelper/mystuff/calendar_eventkit.py \
   ~/gitHubRepository/talonHelper/mystuff/calendar_planner.py \
   ~/gitHubRepository/talonHelper/mystuff/calendar_planner.talon \
   ~/gitHubRepository/talonHelper/mystuff/calendar_planner_edit.talon \
   ~/.talon/user/mystuff/
cp ~/gitHubRepository/talonHelper/aaa_security.py ~/.talon/user/aaa_security.py
```

- [ ] **Step 4: Verify clean reload**

Run: `sleep 4 && grep -E "$(date +%Y-%m-%d) 1" ~/.talon/talon.log | grep -iE 'calendar_planner|ParseError|Traceback' | tail -12`
Expected: `[+]`/`[~]` lines for the planner files; **no ParseError / Traceback**. Note the known risk: `move <n> to {month} <day>` vs `move <n> to <time>` share a prefix — if a `DFA`/parse warning appears, that is the collision; resolve by renaming the day-move to `reschedule <n> to {month} <day>` (grammar-only).

- [ ] **Step 5: Verify registration + a mimic dry-run** (no permission needed to open)

```bash
echo 'from talon import actions; import sys; m=sys.modules["user.mystuff.calendar_planner"]; print("MONTHS", m._MONTHS["august"]); print("add:", actions.user.planner_add_timed)' | ~/.talon/.venv/bin/repl 2>&1 | grep -iE 'MONTHS|add:|Error'
```
Expected: `MONTHS 8` and the action repr.

- [ ] **Step 6: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add mystuff/calendar_planner.talon mystuff/calendar_planner_edit.talon
git commit -m "feat(planner): grammar for navigation, staged edits, commit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Task 8: Retire the AppleScript feature + end-to-end verification

**Files:**
- Delete: `mystuff/calendar_event.py`, `mystuff/calendar_event.talon`, `mystuff/calendar_event_confirm.talon`
- Modify: `aaa_security.py` — remove the `calendar_event.py` trust line
- Delete live copies in `~/.talon/user/mystuff/`

- [ ] **Step 1: Remove retired files (repo + live) and the trust line**

```bash
cd ~/gitHubRepository/talonHelper
git rm mystuff/calendar_event.py mystuff/calendar_event.talon mystuff/calendar_event_confirm.talon
```
Edit `aaa_security.py`: delete the line
`os.path.join(TALON_USER_DIR, "mystuff", "calendar_event.py"),`.
Then remove the live copies (sandbox disabled):
```bash
rm -f ~/.talon/user/mystuff/calendar_event.py ~/.talon/user/mystuff/calendar_event.talon ~/.talon/user/mystuff/calendar_event_confirm.talon
cp ~/gitHubRepository/talonHelper/aaa_security.py ~/.talon/user/aaa_security.py
sleep 3
```

- [ ] **Step 2: Confirm clean reload after removal**

Run: `grep -E "$(date +%Y-%m-%d) 1" ~/.talon/talon.log | grep -iE 'ParseError|Traceback|calendar_event' | tail -6`
Expected: no errors; no lingering references loading `calendar_event`.

- [ ] **Step 3: Scripted end-to-end via mimic + real commit** (permission granted in Task 1/5)

```bash
echo 'from talon import actions; import sys; m=sys.modules["user.mystuff.calendar_planner"]; \
actions.user.planner_show(); \
actions.mimic("add dentist at nine am"); actions.mimic("add lunch at noon for thirty minutes"); \
import calendar_core as cc; ds=cc.display_state(m._state["model"]); print("STAGED", [(r["n"], r["title"], r["status"]) for r in ds["timed"]]); \
actions.user.planner_commit(); print("MSG", m._state["msg"])' | ~/.talon/.venv/bin/repl 2>&1 | grep -iE 'STAGED|MSG|Error'
```
Expected: `STAGED [... 'dentist' 'new' ... 'lunch' 'new' ...]` then `MSG committed 2` (today's events created). Then clean them up:
```bash
osascript -e 'tell application "Calendar" to tell calendar "Calendar" to delete (every event whose summary is "dentist")' 2>/dev/null; \
osascript -e 'tell application "Calendar" to tell calendar "Calendar" to delete (every event whose summary is "lunch")' 2>/dev/null; echo "cleaned (ignore automation errors — deletion is manual-safe)"
```
(If the osascript cleanup is blocked by the same Automation wall, delete the two test events in Calendar.app by hand, or via the planner: `calendar show` → `delete <n>` → `commit`.)

- [ ] **Step 4: Manual voice test (user performs)**

Ask the user to run live:
1. `calendar show` → imgui window shows today's numbered events.
2. `add dentist at two thirty pm for 45 minutes` → appears as `new`, green-ish (status `new`), badge number assigned.
3. `retitle <its number> eye doctor` → title updates in place.
4. `move <its number> to four pm` → time updates.
5. `move <its number> to <next month> <a day>` → shows `-> <date>` moved marker.
6. `commit` → toast `committed 1`; window reloads; event now in Calendar on the target day.
7. `calendar show` → find it → `delete <n>` → `commit` to clean up.

- [ ] **Step 5: Update project memory**

Append to `~/.claude/projects/-Users-seanatsatt-gitHubRepository-talonHelper/memory/MEMORY.md` a Calendar Planner entry: the new `mystuff/calendar_core.py` / `calendar_eventkit.py` / `calendar_planner.py` + grammar files, the `calendar show` command surface, the EventKit dependency in `~/.talon/.venv`, and that the AppleScript `calendar_event.*` feature was retired (macOS Tahoe blocks AppleScript→Calendar). Note Plan 2 (web UI) is the next step.

- [ ] **Step 6: Commit**

```bash
cd ~/gitHubRepository/talonHelper
git add -A
git commit -m "feat(planner): retire AppleScript calendar feature; E2E verified

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FAJei6wphhMh2pyxKz3yXU"
```

---

## Self-Review

**Spec coverage (Plan 1 portion):**
- View a day's real events → Task 5 `read_day` + Task 6 `_reload`/imgui. ✓
- Number addressing → `ordered`/`display_state` (Task 4) + imgui badges (Task 6). ✓
- Add timed/all-day → `add_timed`/`add_all_day` (Task 3) + grammar (Task 7). ✓
- Retitle / duration / all-day↔timed / delete / restore → Task 3 + Task 6/7. ✓
- Move day and/or time → `move` (Task 3), `planner_move` (Task 6), 3 grammar rules (Task 7). ✓
- Staging + single commit + discard → `pending_changes`/`has_pending` (Task 4) + `planner_commit`/`planner_discard` (Task 6). ✓
- EventKit permission (one-time) + dependency → Task 1 + `request_access` (Task 5). ✓
- Retire AppleScript feature → Task 8. ✓
- Reuse `calendar_logic` → Task 6 imports it for `parse_prose_time`/`combine_duration`. ✓
- **Deferred to Plan 2:** localhost server + web UI (imgui stands in as the interim display). ✓

**Placeholder scan:** No TBD/TODO; every code step has full code; every command has expected output. ✓

**Type consistency:** `EventVM` fields (`uid/title/all_day/start/end/status/original/moved_off`) are consistent across Tasks 2-6; the adapter reads exactly those attributes on the VMs passed to `commit`. `display_state` row keys (`n/title/time/status/moved_off/moved_to`) match the imgui reader (Task 6) and the Task 4 test. Capture names (`user.calendar_day`, `user.calendar_duration`, `user.calendar_month`, `user.calendar_time_unit`) match between Task 6 and Task 7. Action signatures (`planner_add_timed(title, prose_time, duration_min=60)`, `planner_move(n, month="", day=0, prose_time="")`) match their grammar call sites. ✓

**Known verification-time risks:**
- Grammar prefix collision on `move <n> to …` (Task 7 Step 4) — rename day-move to `reschedule` if a parse warning appears.
- `authorized()` status enum (3/4) may vary by OS — Task 1 Step 3 prints the real value to confirm; adjust the tuple if needed.
- imgui `number_small_list` accessor on the duration capture must resolve (as it did for the retired feature) — verified at Task 7 reload.
