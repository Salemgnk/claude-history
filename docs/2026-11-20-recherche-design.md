# Recherche du terminal : conception

20 novembre 2026. L'utilisateur trouvait l'outil « pas forcément évident » et la recherche « pas super optimisée », puis a laissé les choix de réalisation à Claude.

## Constats de départ

- Recherche lente : 0,2 à 2,7 s, relancée à chaque frappe (relecture de 600 Mo de JSONL).
- Recherche littérale : phrase exacte, accents exacts ; « brainstorm ui » ne trouvait pas une conversation contenant « brainstorme » et « ui/ux ».
- Deux modes (titre, texte) reliés par `Ctrl-F`, signalé seulement dans l'en-tête ; un mot absent des titres vidait la liste sans explication.

## Ce qui a été fait

- **Un seul mode.** fzf tourne en `--disabled` ; chaque frappe relance `claude-history query`, qui cherche dans le titre, le dossier, le premier message et tous les messages visibles.
- **Index plein texte** dans `~/.cache/claude-history/text.json` (environ 12 Mo pour 5,6 M caractères) : texte d'origine et texte replié (minuscules, sans accents) de même longueur, pour surligner aux bonnes positions. Construit en environ 5 s au premier lancement, puis mis à jour à chaque lancement pour les fichiers modifiés. Les rechargements de fzf n'écrivent jamais l'index (ils peuvent tourner en parallèle) ; les écritures passent par un fichier temporaire puis `os.replace`.
- **Correspondance** : tous les mots doivent être présents, dans n'importe quel ordre, chacun au début d'un mot du texte.
- **Classement** : titre, dossier ou premier message d'abord, puis le reste ; par date dans chaque groupe.
- **Passages** : les messages qui contiennent tous les mots, ou à défaut au moins un ; aperçu limité aux 30 premiers.
- **Aucun résultat** : une ligne explicative ; `Entrée` dessus ne fait rien.

## Mesures

Même machine, mêmes requêtes, avant puis après : environ 0,2 s par frappe quelle que soit la requête, contre 0,2 à 2,7 s.

## Hors périmètre

- L'interface web garde sa recherche d'origine (phrase exacte) ; vérifié identique octet pour octet.
- Pas de tolérance aux fautes de frappe, pas de classement par pertinence.
