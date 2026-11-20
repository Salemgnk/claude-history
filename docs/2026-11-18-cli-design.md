# claude-history en terminal : conception

Validée le 18 novembre 2026.

## But

Retrouver une conversation Claude Code quand on ne sait plus dans quel dossier
elle a été lancée, et la reprendre en une touche, sans navigateur.

## Approches envisagées

1. **Sélecteur interactif `fzf`** (retenue, choisie par l'utilisateur) : `fzf`
   fait le filtrage et l'affichage, le script fournit la liste, l'aperçu et la
   reprise. Peu de code, dépend de `fzf` (déjà installé).
2. Sous-commandes en texte brut : combinable avec d'autres commandes, mais trop
   d'étapes pour ce besoin (lire, copier un identifiant, relancer).
3. Interface curses maison : contrôle total, beaucoup de code pour refaire `fzf`.

## Comportement

| Action | Effet |
|---|---|
| `claude-history` | Liste de toutes les conversations, les plus récentes en haut : date, titre, dossier, nombre de messages |
| Taper du texte | Filtre sur le titre, le dossier et le premier message |
| Aperçu à droite | Dossier, date, puis l'échange : messages de l'utilisateur et réponses de Claude, actions résumées en une ligne (« 3 actions : Bash ×2, Read ») |
| `Entrée` | Se place dans le dossier d'origine et lance `claude --resume <id>` |
| `Ctrl-F` | Bascule en recherche dans tout le texte des messages, extraits trouvés dans l'aperçu ; `Ctrl-F` à nouveau pour revenir |
| `Ctrl-O` | Lit la conversation entière dans `less` |
| `Échap` | Quitte sans rien faire |

## Choix de réalisation (décidés par Claude, acceptés à la validation)

- Même fichier `~/.local/bin/claude-history`, Python, aucune dépendance nouvelle
  à part `fzf`. Le cache d'index `~/.cache/claude-history/index.json` est conservé.
- L'interface web reste disponible via `claude-history web [port] [--no-open]`.
  Le terminal devient le comportement par défaut.
- Recherche plein texte accélérée par `rg`, qui présélectionne les fichiers ;
  sans `rg`, tous les fichiers sont parcourus.
- Dossier d'origine disparu : la commande de reprise est affichée au lieu d'échouer.
- Sous-commandes utilisables à la main : `list`, `search <mot>`, `show <projet> <id>`.

## Hors périmètre

- Supprimer ou modifier des conversations : tout reste en lecture seule.
- Afficher les conversations des sous-agents.
- Copier dans le presse-papiers.

## Vérification

`list`, `search` et `show` testés sur les vraies données, filtrage `fzf` en mode
non interactif. La reprise par `Entrée` et les raccourcis sont confirmés à la
main par l'utilisateur.
