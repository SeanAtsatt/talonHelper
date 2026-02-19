import subprocess
from talon import Module

mod = Module()

def show_query_popup():
    """Show a macOS input dialog, send query to OpenAI, and display result"""
    try:
        # Show an input dialog and capture the query
        query = subprocess.run(
            ['osascript', '-e',
             'set query to text returned of (display dialog "Enter your OpenAI request:" '
             'default answer "" buttons {"Submit"} default button "Submit")'],
            capture_output=True, text=True
        ).stdout.strip()

        if not query:
            return  # User canceled, exit function

        # Call OpenAI via the shell script
        response = subprocess.run(
            ["/Users/seanatsatt/.bin/openAiQuery.sh", query],
            capture_output=True, text=True, shell=False
        )

        # Extract response text
        result_text = response.stdout.strip() if response.returncode == 0 else f"Error: {response.stderr}"

        # Display the OpenAI response in a macOS dialog (pass text via stdin to avoid injection)
        script = 'set msg to do shell script "cat" \n display dialog msg buttons {"OK"} default button "OK"'
        subprocess.run(['osascript', '-e', script], input=result_text, text=True)

    except Exception as e:
        # Display any errors that occur
        script = 'set msg to do shell script "cat" \n display dialog msg buttons {"OK"} default button "OK"'
        subprocess.run(['osascript', '-e', script], input=str(e), text=True)

@mod.action_class
class Actions:
    def show_query_popup():
        """Show the macOS popup input box for OpenAI"""
        show_query_popup()