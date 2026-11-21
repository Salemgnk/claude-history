# claude-history

Retrouver et reprendre une conversation Claude Code depuis le terminal, quel que soit le dossier où elle a été lancée.

```
claude-history                         sélecteur interactif (fzf)
claude-history last                    reprendre la conversation la plus récente
claude-history list                    liste des conversations
claude-history search <mots>           conversations qui contiennent tous ces <mots>
claude-history show <projet> <id>      lire une conversation
claude-history export <projet> <id>    exporter une conversation en Markdown
claude-history stats                   aperçu de tes conversations
claude-history web [port] [--no-open]  interface navigateur sur 127.0.0.1
```

## Recherche

Dans le sélecteur, tape des mots dans n'importe quel ordre. Ils sont cherchés à la fois dans le titre, le dossier et le texte des messages :

- sans tenir compte des majuscules ni des accents (`reseau` trouve « réseau ») ;
- un début de mot suffit (`brainstorm` trouve « brainstorme », mais `ui` ne trouve pas « suis ») ;
- les conversations dont le titre ou le dossier correspond viennent en premier, puis les autres par date.

`Entrée` reprend la conversation dans son dossier d'origine, `Ctrl-O` la lit en entier, `Échap` quitte.

L'index de recherche (`~/.cache/claude-history/text.json`) est construit au premier lancement, en quelques secondes, puis mis à jour à chaque lancement pour les seules conversations modifiées.

Lit `~/.claude/projects` en lecture seule. Dépend de Python 3 (bibliothèque standard) et de `fzf`.

## Installation

```
ln -sf "$PWD/claude-history" ~/.local/bin/claude-history
```

## Tests

```
python3 -m unittest discover -s tests -v
```

## Page de présentation

`docs/index.html` : une page web qui présente le projet, publiable via GitHub Pages.
