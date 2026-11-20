# claude-history

Retrouver et reprendre une conversation Claude Code depuis le terminal, quel que soit le dossier où elle a été lancée.

```
claude-history                         sélecteur interactif (fzf)
claude-history list                    liste des conversations
claude-history search <mots>           conversations qui contiennent <mots>
claude-history show <projet> <id>      lire une conversation
claude-history web [port] [--no-open]  interface navigateur sur 127.0.0.1
```

Lit `~/.claude/projects` en lecture seule. Dépend de Python 3 (bibliothèque standard) et de `fzf`.

## Installation

```
ln -sf "$PWD/claude-history" ~/.local/bin/claude-history
```

## Tests

```
python3 -m unittest discover -s tests -v
```
