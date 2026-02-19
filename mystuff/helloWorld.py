# example.py

from talon import Module, actions

# Create a new module
mod = Module()

# Define actions for the module
@mod.action_class
class Actions:
    def say_hello():
        """Prints 'Hello, world!' in the Talon log"""
        actions.app.notify("Hello, world!")
        print("Hello, world!")