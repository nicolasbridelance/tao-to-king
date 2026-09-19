# 003 — Typage des axes en quatre catégories

## Statut
Accepté

## Contexte
Un produit cartésien naïf sur des axes de natures différentes (quoi examiner / comment lire / quelle forme / quelle situation) est ce qui fait échouer l'approche, pas leur nombre.

## Décision
Quatre types d'axes, chacun avec une place fixe dans le prompt : `selector` (résout la requête corpus), `transformer` (consigne système), `constraint` (consigne de sortie, vérifiable mécaniquement), `instantiator` (consigne utilisateur, optionnel).

## Conséquences
- Le masque de compatibilité (§6) et le gabarit de prompt (§7) s'organisent autour de ce typage.
- Ajouter un axe implique de choisir son type avant sa liste de valeurs, pas après.
