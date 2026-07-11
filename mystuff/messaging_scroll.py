"""Transcript scrolling for Messages and WhatsApp.

These apps don't respond to PageUp/PageDown because keyboard focus stays in the
compose box and the message transcript isn't a paging control. Real scroll-wheel
events *do* reach the transcript, so we synthesize them at the pointer location
(same trick as terminal_scroll.py). The pointer is parked over the center of the
active window first, which lands inside the transcript in both apps' layouts.
"""

from talon import Module, actions, cron, ctrl, ui

mod = Module()

# Bundle ids this module is allowed to drive. Continuous scroll auto-stops if
# focus moves to anything else.
MESSAGING_BUNDLES = {"com.apple.MobileSMS", "net.whatsapp.WhatsApp"}

# Discrete "page" = this many wheel notches. Roughly half a screen.
PAGE_NOTCHES = 3
# "top"/"bottom" burst for apps with no jump-to-end shortcut (WhatsApp).
EDGE_NOTCHES = 40

# Per-app continuous-scroll profiles. Messages bounces on sparse tiny scrolls
# but reads a rapid stream of small ticks as one smooth gesture, so it gets a
# small tick at a fast interval. Everything else scrolls fine on the slower,
# gentler default.
SCROLL_PROFILES = {
    "com.apple.MobileSMS": {"interval": 30, "tick": 0.15},
    "net.whatsapp.WhatsApp": {"interval": 30, "tick": 0.15},
}
DEFAULT_PROFILE = {"interval": 300, "tick": 0.1}

# Continuous-scroll state
scroll_job = None
scroll_direction = 1  # 1 = down, -1 = up
saved_mouse_pos = None
scroll_interval_ms = 300
scroll_tick = 0.1


def _in_messaging_app() -> bool:
    try:
        return ui.active_app().bundle in MESSAGING_BUNDLES
    except Exception:
        return False


def _burst(direction: int, notches: float):
    """Center the pointer over the transcript, scroll, then restore the pointer."""
    if not _in_messaging_app():
        return
    pos = ctrl.mouse_pos()
    actions.user.mouse_move_center_active_window()
    if direction < 0:
        actions.user.mouse_scroll_up(notches)
    else:
        actions.user.mouse_scroll_down(notches)
    actions.mouse_move(pos[0], pos[1])


def do_one_scroll():
    """One continuous-scroll tick. Stops if we've left Messages/WhatsApp."""
    if not _in_messaging_app():
        actions.user.messaging_scroll_stop()
        return
    if scroll_direction < 0:
        actions.user.mouse_scroll_up(scroll_tick)
    else:
        actions.user.mouse_scroll_down(scroll_tick)


def _start(direction: int):
    global scroll_job, scroll_direction, saved_mouse_pos, scroll_interval_ms, scroll_tick
    if scroll_job:
        cron.cancel(scroll_job)
    saved_mouse_pos = ctrl.mouse_pos()
    actions.user.mouse_move_center_active_window()
    scroll_direction = direction
    try:
        profile = SCROLL_PROFILES.get(ui.active_app().bundle, DEFAULT_PROFILE)
    except Exception:
        profile = DEFAULT_PROFILE
    scroll_interval_ms = profile["interval"]
    scroll_tick = profile["tick"]
    scroll_job = cron.interval(f"{scroll_interval_ms}ms", do_one_scroll)


@mod.action_class
class Actions:
    # --- discrete ---
    def messaging_page_down():
        """Scroll the transcript down about half a screen"""
        _burst(1, PAGE_NOTCHES)

    def messaging_page_up():
        """Scroll the transcript up about half a screen"""
        _burst(-1, PAGE_NOTCHES)

    def messaging_page_bottom():
        """Jump toward the bottom of the transcript (newest messages)"""
        _burst(1, EDGE_NOTCHES)

    def messaging_page_top():
        """Jump toward the top of the transcript (older messages load lazily)"""
        _burst(-1, EDGE_NOTCHES)

    # --- continuous ---
    def messaging_scroll_start_down():
        """Start scrolling the transcript down continuously"""
        _start(1)

    def messaging_scroll_start_up():
        """Start scrolling the transcript up continuously"""
        _start(-1)

    def messaging_scroll_stop():
        """Stop continuous scrolling and restore the pointer"""
        global scroll_job, saved_mouse_pos
        if scroll_job:
            cron.cancel(scroll_job)
            scroll_job = None
        if saved_mouse_pos:
            actions.mouse_move(saved_mouse_pos[0], saved_mouse_pos[1])
            saved_mouse_pos = None

    def messaging_scroll_faster():
        """Speed up continuous scrolling"""
        global scroll_job, scroll_interval_ms
        if scroll_job:
            cron.cancel(scroll_job)
            scroll_interval_ms = max(10, scroll_interval_ms // 2)
            scroll_job = cron.interval(f"{scroll_interval_ms}ms", do_one_scroll)

    def messaging_scroll_slower():
        """Slow down continuous scrolling"""
        global scroll_job, scroll_interval_ms
        if scroll_job:
            cron.cancel(scroll_job)
            scroll_interval_ms = min(1000, scroll_interval_ms * 2)
            scroll_job = cron.interval(f"{scroll_interval_ms}ms", do_one_scroll)
