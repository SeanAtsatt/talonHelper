os: mac
app: iterm2
-
tag(): terminal
tag(): user.file_manager
tag(): user.generic_unix_shell
tag(): user.git
tag(): user.kubectl
tag(): user.tabs
tag(): user.readline

# Custom navigation
go back: "cd -\n"
save here as <user.text>: user.save_current_path_as(text)

# VS Code
code here: "code -n .\n"
code this: "code -n .\n"
edit <user.text>: "code -n {text}\n"
