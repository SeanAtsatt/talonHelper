#!/usr/bin/env bash
# Fake SwitchAudioSource for tests. State dir via $STUB_STATE:
#   $STUB_STATE/current_input  - the current default input device name
#   $STUB_STATE/inputs         - newline list of available input device names
#   $STUB_STATE/calls          - appended one line per invocation
set -u
: "${STUB_STATE:?STUB_STATE required}"
printf '%s\n' "$*" >> "$STUB_STATE/calls"

has() { local needle="$1"; shift; case " $* " in *" $needle "*) return 0;; *) return 1;; esac; }

# value following -s
set_val=""; prev=""
for a in "$@"; do [ "$prev" = "-s" ] && set_val="$a"; prev="$a"; done

if has -c "$@"; then
  cat "$STUB_STATE/current_input"; exit 0
fi
if has -a "$@"; then
  cat "$STUB_STATE/inputs"; exit 0
fi
if [ -n "$set_val" ]; then
  printf '%s\n' "$set_val" > "$STUB_STATE/current_input"
  echo "input audio device set to \"$set_val\""; exit 0
fi
exit 0
