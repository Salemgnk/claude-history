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

Lit `~/.claude/projects` en lecture seule. Dépend de Python 3 (bibliothèque standard). `fzf` est optionnel : il donne le sélecteur en direct, et sans lui le tool bascule sur un sélecteur intégré en Python.

## Installation

```
./install.sh
```

Le script pose le lien dans le PATH, construit l'index une fois, et propose d'installer `fzf` s'il manque (pacman, apt, dnf, zypper ou brew). Relançable sans risque.

### En paquet Python (pipx)

```
pipx install .
```

Installe la commande `claude-history` dans un environnement isolé, sur n'importe quelle machine.

### En paquet Arch (makepkg)

```
makepkg -si
```

Construit et installe le paquet via pacman (`pacman -Q claude-history`, désinstallation avec `pacman -R claude-history`).

### À la main

```
ln -sf "$PWD/claude_history.py" ~/.local/bin/claude-history
```

## Tests

```
python3 -m unittest discover -s tests -v
```

## Page de présentation

`docs/index.html` : une page web qui présente le projet, publiable via GitHub Pages.
