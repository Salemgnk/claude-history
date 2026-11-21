# Complétion bash pour claude-history.
_claude_history() {
  local cur="${COMP_WORDS[COMP_CWORD]}"
  if [ "$COMP_CWORD" -eq 1 ]; then
    COMPREPLY=( $(compgen -W "$(claude-history _complete commands 2>/dev/null)" -- "$cur") )
    return
  fi
  case "${COMP_WORDS[1]}" in
    show|export)
      if [ "$COMP_CWORD" -eq 2 ]; then
        COMPREPLY=( $(compgen -W "$(claude-history _complete projects 2>/dev/null)" -- "$cur") )
      elif [ "$COMP_CWORD" -eq 3 ]; then
        COMPREPLY=( $(compgen -W "$(claude-history _complete ids "${COMP_WORDS[2]}" 2>/dev/null)" -- "$cur") )
      fi
      ;;
  esac
}
complete -F _claude_history claude-history
