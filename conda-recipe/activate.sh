# This activates fzf-based fuzzy finding for happi searches.
# This is meant to be sourced from bash.

_fzf_complete_happi() {
  _fzf_complete --multi --reverse --prompt="happi> " -- "$@" < <(
    python `which happi` search '*' --json 2>/dev/null |python -c '
import json
import sys
items = json.load(sys.stdin)
for item in items:
    print(item["name"])
'

  )
}

[ -n "$BASH" ] && complete -F _fzf_complete_happi -o default -o bashdefault happi
