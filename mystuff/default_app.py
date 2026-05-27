from talon import Module

mod = Module()


@mod.action_class
class Actions:
    def default_app_show():
        """Show the current default app for the selected file's extension."""
        print("default_app_show: stub")

    def default_app_change():
        """Open a picker of candidate apps for the selected file's extension."""
        print("default_app_change: stub")

    def default_app_refresh():
        """Force LaunchServices to reload by restarting Finder."""
        print("default_app_refresh: stub")
