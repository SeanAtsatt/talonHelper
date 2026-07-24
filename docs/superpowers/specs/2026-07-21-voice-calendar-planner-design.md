> **SUPERSEDED (2026-07-24).** This custom-build approach was abandoned. On macOS Tahoe every write path to Apple Calendar failed: AppleScript was denied (TCC), pyobjc/EventKit was rejected by hardened-runtime library validation inside both Talon.app and its venv python, and CalDAV writes never persisted. The calendar need is now met via Claude's Google Calendar connector / Cowork — natural-language event management, verified working end-to-end. Kept as a decision record only.

# Voice Calendar Planner — Design Spec

**Date:** 2026-07-21
**Status:** Approved design (pre-implementation)
**Supersedes:** the AppleScript-based voice-add feature
(`mystuff/calendar_event.py`, `calendar_event.talon`, `calendar_event_confirm.talon`)

---

## 1. Problem & Motivation

The user has RSI and drives their Mac by voice (Talon). Navigating and
editing Apple Calendar by voice is painful: finding an event, moving up and
down the day, opening it, and changing its time all mean fighting a
mouse-designed UI, or wrestling macOS Voice Control's generic numbered-grid
overlays.

**Prior art (researched 2026-07-21):**
- **Creating** events by voice is well-solved — Fantastical natural-language +
  macOS dictation, Apple Calendar's "Quick Event" natural-language field, Siri,
  and several App Store "voice scheduler" apps. We will *not* try to rival
  Fantastical's parser.
- **Navigating / editing / rescheduling** existing events by voice is *not*
  solved. The only option is macOS Voice Control's click-the-grid overlays.
  VO Calendar targets VoiceOver (blind users), not RSI voice control.

So the differentiated value is a **voice-first surface to view a day and
edit / reschedule / delete what's already there**, with a simple in-app
creation path for convenience.

**Why not the earlier AppleScript approach:** macOS Tahoe (26.x) refuses all
Apple events from Talon to Calendar — read and write — even with a valid
Automation grant identical to one that works for Chrome. Calendar is a
protected app requiring **Calendars data access**, which an AppleScript-only
client cannot obtain. Confirmed: fresh Talon process + valid `iCal=2` grant +
several user approvals → still `Not authorized`. EventKit (below) is the
supported path and gets a real, persistent Calendars permission.

---

## 2. Goals & Non-Goals

**Goals (v1):**
- View a single day's real events, read live from Calendar.
- Voice-first editing of that day, addressing events **by number badge**:
  retitle, move (change **day and/or time**), change duration, toggle
  all-day ↔ timed, delete / restore.
- Simple in-app creation of a timed or all-day event on the viewed day.
- **Staging model:** all changes accumulate as a pending diff; nothing touches
  the real Calendar until a single `commit`. `discard` throws staged changes
  away.
- An elegant local web UI that updates live as voice commands run.
- Everything auto-starts with Talon; one-time Calendars permission prompt.

**Non-goals (v1 — deferred):**
- Multi-day / week / month navigation (one day at a time).
- Recurring events, invitees, locations, alarms, notes.
- Multiple-calendar management (v1 reads/writes a single default calendar;
  see §9).
- Editing events by title or time phrase (number addressing only in v1;
  aliases can come later).
- Click-to-edit in the web UI (v1 is voice-driven; the page is display-first).

---

## 3. Architecture

Three cooperating pieces, all hosted **inside Talon's Python process**
(auto-starts with Talon):

```
Voice (Talon grammar)
      │
      ▼
Talon module ── mutates ──▶ Day model (pure, staged diff)
   │  (in Talon.app process)         │
   │                                 ▼
   ├── EventKit adapter ◀── commit ──┘   (reads/writes real Calendar)
   │
   └── localhost server ── websocket ──▶ Web UI (browser tab)
```

The browser tab is a pure live display. Voice never types into the browser;
commands hit the Talon module, which mutates the day model and pushes new
state to the page over a websocket, so the view updates regardless of browser
focus.

---

## 4. Components

Each is isolated, with a clear purpose, interface, and dependencies, and can be
understood and tested independently.

### 4.1 `calendar_core.py` — pure logic (no Talon, no EventKit)
**Purpose:** own the day model and the staging diff.
**Depends on:** `calendar_logic.py` (existing, tested) for time/date parsing;
stdlib only.
**Interface (indicative):**
- A `DayModel` holding the viewed `date` and an ordered list of `EventVM`.
- `EventVM`: `{ uid, title, all_day, start, end, status }` where `status ∈
  {unchanged, new, edited, deleted}`, plus an `original` snapshot for revert.
- `load(date, real_events) -> DayModel` — build a model from events read out of
  Calendar; all `unchanged`.
- Mutators returning a new/updated model and marking status:
  `add_timed(title, start, dur)`, `add_all_day(title)`, `retitle(n, title)`,
  `move(n, start)`, `set_duration(n, minutes)`, `make_all_day(n)`,
  `make_timed(n, start, dur=60)`, `delete(n)`, `restore(n)`.
  `move` takes a full start datetime, so it changes the **day, the time, or
  both**; the end shifts to preserve the event's duration. Moving an event to
  another day marks it `edited` and it leaves the current day's view on commit.
- `pending_changes(model) -> Changes` — the diff to commit (creates / updates /
  deletes), computed from statuses.
- `display_state(model) -> dict` — JSON the web UI renders (all-day row +
  timed list, per-event status/colors, the pending summary).
This is where **most logic lives and is unit-tested with plain Python.**

### 4.2 `calendar_eventkit.py` — EventKit adapter (the only EventKit importer)
**Purpose:** the boundary to real Calendar.
**Depends on:** `pyobjc-framework-EventKit` (installed into `~/.talon/.venv`).
**Interface:**
- `request_access() -> bool` — trigger/await the Calendars permission; used at
  startup and before first read.
- `read_day(date) -> list[RealEvent]` — events intersecting that day from the
  default calendar.
- `commit(changes) -> CommitResult` — apply creates/updates/deletes; return
  per-item success/failure.
- Maps `all_day ↔ EKEvent.allDay`; identifies events by
  `EKEvent.calendarItemIdentifier` (stored as `EventVM.uid`).
Isolated so `calendar_core` and the grammar are testable without Calendar
access (a fake adapter stands in for tests).

### 4.3 `calendar_server.py` — localhost UI server
**Purpose:** serve the web UI and broadcast day-model state.
**Interface:** `start(port)`, `stop()`, `broadcast(display_state)`,
`is_connected() -> bool` (any live tab?), plus an inbound channel for future
click actions (unused in v1).
**Lifecycle:** started when the Talon module loads; **cleanly stopped and
restarted on hot-reload** so no "port already in use." Binds `127.0.0.1` only.

### 4.4 `calendar_web/` — front-end (self-contained HTML/CSS/JS)
**Purpose:** the elegant day view. All-day row on top, time-ordered timed list
below, event **number badges**, staged-status colors
(**green=new, amber=edited, struck-through=to-delete, plain=unchanged**), a
pending-changes summary, and a clear "grant Calendar access" state. Connects
by websocket and re-renders on each broadcast. No external assets (works
offline).

### 4.5 `calendar_planner.py` — Talon module
**Purpose:** grammar-facing actions; owns server lifecycle and the current
`DayModel`.
**Interface:** actions `planner_show()`, `planner_day(month, day)`,
`planner_shift(delta)` (next/previous/today), `planner_add_timed(...)`,
`planner_add_all_day(title)`, `planner_retitle(n, title)`, `planner_move(n,
time)`, `planner_duration(n, minutes)`, `planner_make_all_day(n)`,
`planner_make_timed(n, time)`, `planner_delete(n)`, `planner_restore(n)`,
`planner_commit()`, `planner_discard()`. Each mutates the model via
`calendar_core`, then `broadcast`s; `show` opens the browser tab only if none
is connected.

### 4.6 `calendar_planner.talon` (+ tag-scoped file) — grammar
Global navigation/creation commands; the edit/commit commands gated by a
`user.calendar_planner_open` tag so bare words like `commit`, `discard`, and
`delete <n>` are only live while the planner is active. Reuses community
captures (`<user.prose_time>`, `<user.ordinals>`, `<number_small>`,
`<user.text>`) and the `calendar_month` list.

---

## 5. Voice Command Surface

Events are addressed **by number badge** (1, 2, 3 …) shown on each card.

- **Navigate:** `calendar show` (today) · `next day` / `previous day` /
  `tomorrow` / `today` · `calendar day august fifteenth`
- **Create (viewed day is the date):** `add lunch at noon` ·
  `add standup at nine for thirty minutes` · `add holiday all day`
- **Edit by number:** `retitle two eye doctor` · `duration two ninety minutes`
  · `make two all day` · `make two timed at nine am`
- **Move (day and/or time):** `move three to four pm` (same day, new time) ·
  `move three to august twentieth` (new day, same time) ·
  `move three to august twentieth at nine am` (new day and time). An event
  moved to another day shows staged with a "→ &lt;date&gt;" marker until
  commit, then leaves the view.
- **Delete / undo:** `delete two` · `restore two`
- **Commit / discard:** `commit` · `discard`

Exact phrasings will be tuned for comfort during implementation; the semantics
above are fixed.

---

## 6. Data Flow & Commit Semantics

1. `show` / navigate → `eventkit.read_day(date)` → `core.load(...)` →
   `broadcast`. All events `unchanged`.
2. Each voice edit mutates the **staged model only**, updates that event's
   status, and re-broadcasts. Real Calendar untouched.
3. `commit` → `core.pending_changes` → `eventkit.commit(changes)` →
   re-`read_day` (source of truth) → fresh `load` → `broadcast`. Successful
   items disappear from the pending set; any failed items stay staged and are
   flagged in the UI.
4. `discard` → reload the model from the last-read real events (drop staging).

---

## 7. Permission Model

- The EventKit adapter calls `request_access()` at startup; first run shows the
  one-time **"Talon would like to access Calendar"** prompt (real, persistent —
  unlike the AppleScript dead-end).
- If access is denied/undetermined, reads return empty and the UI shows a
  "grant access in System Settings → Privacy & Security → Calendars" state;
  no silent failures.
- **Dependency:** `pyobjc-framework-EventKit` installed once into
  `~/.talon/.venv`. This venv normally survives Talon app updates; a major
  update *may* require a one-line reinstall, which we document.

---

## 8. Error Handling

- **Permission denied/undetermined:** explicit UI state + toast (§7).
- **Commit failures (per item):** surfaced in the UI; failed items remain
  staged so the user can retry or discard.
- **Server port conflict on reload:** prevented by the clean stop/start
  lifecycle (§4.3).
- **Bad voice input** (unparseable time, out-of-range number, editing a
  non-existent event number): no-op with a toast; model unchanged.
- **No tab connected on an edit command:** the model still updates; the next
  `show` reflects it.

---

## 9. Testing Strategy

- **`calendar_core`:** thorough plain-Python unit tests — staging transitions
  (each mutator sets the right status), diff computation, revert/restore,
  all-day↔timed conversions, date math. Same TDD approach used for
  `calendar_logic.py`.
- **`calendar_eventkit`:** a fake adapter backs `core` tests; the real adapter
  is verified live once (create/edit/delete a throwaway event, then confirm and
  clean up).
- **`calendar_server` / UI:** verified by connecting a real browser tab and
  watching live updates; a create→edit→commit round-trip end-to-end.

---

## 10. Relationship to Existing Code

- **Reused:** `mystuff/calendar_logic.py` (+ its tests) — prose-time parsing,
  duration math, date/year resolution. No changes expected beyond possible
  additive helpers.
- **Retired:** the AppleScript voice-add feature
  (`mystuff/calendar_event.py`, `calendar_event.talon`,
  `calendar_event_confirm.talon`) and the sandbox-trust line for
  `calendar_event.py` in `aaa_security.py`. The planner replaces its
  functionality via EventKit. Removal handled in the implementation plan.
- **Untouched:** `mystuff/calendar.talon` (existing Calendar keyboard
  shortcuts).
- **Default calendar** target constant carries over (`"Calendar"`); a one-line
  change to retarget, and the natural seam for future multi-calendar support.

---

## 11. Risks & Open Questions

- **pyobjc-EventKit install** into Talon's venv must succeed against Talon's
  Python 3.13 and be importable in-process — validated as the first
  implementation step before building on it.
- **EventKit access from an in-process module** (vs. a standalone .app) must
  actually surface the Calendars prompt under Talon.app's identity —
  validated early; fallback is a tiny signed helper app if the in-process
  request misbehaves.
- **Websocket + server on a background thread inside Talon** must coexist with
  Talon's event loop and reload cleanly — the lifecycle in §4.3 is the
  mitigation; validated with a reload test.
- **All-day event day-boundary math** (timezones, events spanning midnight)
  kept simple in v1: an event is shown on a day if it intersects that day; the
  all-day row shows events whose `all_day` is true for that date.
