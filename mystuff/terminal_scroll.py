"""Apple Terminal continuous scroll - sends wheel-tick-sized events at readable pace."""

from talon import Module, actions, cron, ctrl

mod = Module()

# State
scroll_job = None
scroll_direction = 1  # 1 = down, -1 = up
saved_mouse_pos = None

# Timing: milliseconds between each scroll tick
scroll_interval_ms = 75  # Start at 75ms for smoother scrolling


def do_one_scroll():
    """Send one smooth scroll increment. Stops if Terminal loses focus."""
    from talon import ui

    # Stop scrolling if we've left Terminal
    active_app = ui.active_app()
    if active_app.bundle != "com.apple.Terminal":
        actions.user.terminal_scroll_stop()
        return

    # Use minimum working amount (0.1 = 12px) for smoothest scrolling
    if scroll_direction == -1:
        actions.user.mouse_scroll_up(0.1)
    else:
        actions.user.mouse_scroll_down(0.1)


@mod.action_class
class Actions:
    def terminal_scroll_start_up():
        """Start scrolling up continuously"""
        global scroll_job, scroll_direction, saved_mouse_pos, scroll_interval_ms

        if scroll_job:
            cron.cancel(scroll_job)

        saved_mouse_pos = ctrl.mouse_pos()
        actions.user.mouse_move_center_active_window()

        scroll_direction = -1
        scroll_interval_ms = 300
        scroll_job = cron.interval(f"{scroll_interval_ms}ms", do_one_scroll)

    def terminal_scroll_start_down():
        """Start scrolling down continuously"""
        global scroll_job, scroll_direction, saved_mouse_pos, scroll_interval_ms

        if scroll_job:
            cron.cancel(scroll_job)

        saved_mouse_pos = ctrl.mouse_pos()
        actions.user.mouse_move_center_active_window()

        scroll_direction = 1
        scroll_interval_ms = 300
        scroll_job = cron.interval(f"{scroll_interval_ms}ms", do_one_scroll)

    def terminal_scroll_stop():
        """Stop scrolling and restore mouse position"""
        global scroll_job, saved_mouse_pos

        if scroll_job:
            cron.cancel(scroll_job)
            scroll_job = None

        if saved_mouse_pos:
            actions.mouse_move(saved_mouse_pos[0], saved_mouse_pos[1])
            saved_mouse_pos = None

    def terminal_scroll_faster():
        """Speed up - shorter interval"""
        global scroll_job, scroll_interval_ms

        if scroll_job:
            cron.cancel(scroll_job)
            # Halve the interval for noticeable speed increase
            scroll_interval_ms = max(20, scroll_interval_ms // 2)
            scroll_job = cron.interval(f"{scroll_interval_ms}ms", do_one_scroll)

    def terminal_scroll_slower():
        """Slow down - longer interval"""
        global scroll_job, scroll_interval_ms

        if scroll_job:
            cron.cancel(scroll_job)
            # Double the interval for noticeable slowdown
            scroll_interval_ms = min(300, scroll_interval_ms * 2)
            scroll_job = cron.interval(f"{scroll_interval_ms}ms", do_one_scroll)
