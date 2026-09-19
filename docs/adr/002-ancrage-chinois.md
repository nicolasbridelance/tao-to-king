# 002 — Ancrage chinois plutôt que traduction

## Statut
Accepté

## Contexte
Ancrer la génération sur une traduction française revient à commenter une interprétation en croyant commenter le texte source.

## Décision
Le chinois est la source ; les traductions sont des données dérivées, toujours étiquetées comme telles. Chaque prompt porte le texte chinois du témoin retenu ; les traductions viennent en contexte.

## Conséquences
- Nécessite d'ingérer et d'aligner plusieurs témoins chinois (Wang Bi, Heshanggong, Mawangdui, Guodian) avant toute génération.
- Le modèle doit avoir un avantage réel sur le chinois (cf. choix de `deepseek-v4-flash`, §7) pour que cet ancrage ait un sens.
