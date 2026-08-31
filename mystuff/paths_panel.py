import math

from talon import Module, actions, imgui, registry

mod = Module()

DISPLAY_LIMIT = 20
STRING_LIMIT = 20

current_page = 1


@imgui.open(y=10, x=500)
def gui_destinations(gui: imgui.GUI):
    global current_page

    try:
        paths_dict = registry.lists["user.system_paths"][-1]
        names = sorted(paths_dict.keys(), key=str.casefold)
    except (KeyError, IndexError):
        names = []

    total_pages = max(1, math.ceil(len(names) / DISPLAY_LIMIT))
    if current_page > total_pages:
        current_page = 1

    gui.text(f"Destinations ({current_page}/{total_pages})")
    gui.line()

    start = (current_page - 1) * DISPLAY_LIMIT
    page_names = names[start : start + DISPLAY_LIMIT]
    for i, name in enumerate(page_names, 1):
        display = name if len(name) <= STRING_LIMIT else name[:STRING_LIMIT] + ".."
        gui.text(f"{i}: {display}")

    gui.spacer()
    gui.text('say "save here as <name>" to add path')
    gui.spacer()
    if total_pages > 1:
        if gui.button("Next"):
            current_page = (current_page % total_pages) + 1
        if gui.button("Previous"):
            current_page = ((current_page - 2) % total_pages) + 1
        gui.spacer()
    if gui.button("Paths close"):
        actions.user.paths_hide()


@mod.action_class
class Actions:
    def paths_toggle():
        """Toggle the paths/destinations panel"""
        if gui_destinations.showing:
            gui_destinations.hide()
        else:
            gui_destinations.show()

    def paths_hide():
        """Hide the paths/destinations panel"""
        gui_destinations.hide()
