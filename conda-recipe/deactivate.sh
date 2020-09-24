# This deactivates fzf-based fuzzy finding for happi searches.
# This is meant to be sourced from bash.

[ -n "$BASH" ] && complete -r happi

unset _fzf_complete_happi
