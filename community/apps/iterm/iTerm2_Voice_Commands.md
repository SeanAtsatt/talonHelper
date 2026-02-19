# iTerm2 Voice Commands Reference

Complete list of Talon voice commands available in iTerm2.

## Setup Requirements

1. **Disable vi mode in shell** - Remove or comment out `set -o vi` in `~/.zprofile` or `~/.zshrc`
2. **iTerm2 Shell Integration** - Install via iTerm2 menu → Install Shell Integration (required for file manager)
3. **Option key as Esc+** - In iTerm2 Preferences → Profiles → Keys → set Left/Right Option to "Esc+"

---

## Navigation & Directory

| Command | Action |
|---------|--------|
| `lisa` | List directories (`ls`) |
| `lisa all` | List all including hidden (`ls -a`) |
| `katie [dir] [name]` | Change directory (`cd`) |
| `katie root` | Go to root directory |
| `katie up` / `katie back` | Parent directory (`cd ..`) |
| `go <path>` | cd to a system path |
| `path <path>` | Insert a quoted path |
| `clear screen` | Clear terminal (ctrl-l) |

---

## Line Editing

| Command | Action |
|---------|--------|
| `head` / `go line start` | Beginning of line |
| `tail` / `go line end` | End of line |
| `go word left` | Move one word left |
| `go word right` | Move one word right |
| `go way left` | Beginning of line |
| `go way right` | End of line |
| `go way up` / `go top` | Beginning of buffer |
| `go way down` / `go bottom` | End of buffer |

---

## Editing & Clipboard

| Command | Action |
|---------|--------|
| `copy that` | Copy selection |
| `cut that` | Cut selection |
| `paste that` | Paste |
| `copy paste` | Copy then paste |
| `undo that` | Undo |
| `cut line` | Cut entire line |
| `cut word left` | Cut word before cursor |
| `cut word right` | Cut word after cursor |
| `clone line` | Duplicate current line |
| `slap` / `new line below` | Insert line below |

---

## Command History

| Command | Action |
|---------|--------|
| `run last` | Run previous command |
| `rerun [text]` | Search history and rerun |
| `rerun search` | Open history search |
| `kill all` | Kill all processes |

---

## Tabs

| Command | Action |
|---------|--------|
| `tab new` / `tab open` | Open new tab |
| `tab next` | Next tab |
| `tab last` / `tab previous` | Previous tab |
| `tab close` | Close current tab |
| `tab reopen` / `tab restore` | Reopen closed tab |
| `go tab <number>` | Jump to tab 1-9 |
| `go tab final` | Jump to last tab |

---

## Git Commands

| Command | Action |
|---------|--------|
| `git status` | `git status` (runs immediately) |
| `git diff` | `git diff` |
| `git diff cached` | `git diff --cached` |
| `git add patch` | `git add --patch` |
| `git show head` | `git show HEAD` |
| `git <command>` | Any git command |
| `git commit message [text]` | `git commit --message "text"` |
| `git clone clipboard` | Clone URL from clipboard |

---

## Kubectl (Kubernetes)

| Command | Action |
|---------|--------|
| `cube get` | `kubectl get ` |
| `cube describe` | `kubectl describe ` |
| `cube logs` | `kubectl logs ` |
| `cube apply` | `kubectl apply ` |
| `cube delete` | `kubectl delete ` |
| `cube exec` | `kubectl exec ` |
| `cube shell` | `kubectl exec -it <pod> -- /bin/bash` |

---

## Scrolling

| Command | Action |
|---------|--------|
| `scroll up` / `go page up` | Page up |
| `scroll down` / `go page down` | Page down |

---

*Generated for iTerm2 + Talon Voice*
