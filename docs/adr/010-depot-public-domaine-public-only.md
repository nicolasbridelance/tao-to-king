# 010 — Dépôt public, sources domaine public uniquement

## Statut
Accepté

## Contexte
Le dépôt est public. La spec initiale prévoyait d'ingérer la traduction Gallimard (sous droits) en usage privé, jamais commitée. Même non commitée, le risque de fuite (citation involontaire dans un output généré, erreur de `.gitignore`, fichier oublié) n'est pas acceptable sur un dépôt visible de tous.

## Décision
Aucune source sous droits n'entre dans le projet, à aucun titre, même hors Git. Seules des sources domaine public sont ingérées : Wang Bi, Heshanggong, Mawangdui A/B, Guodian (chinois), Julien 1842 et Legge 1891 (traductions). Les sources brutes, étant domaine public, sont versionnées directement dans `corpus/` plutôt que reconstruites à chaque fois.

## Conséquences
- La traduction Gallimard est abandonnée comme source ; aucune traduction française moderne sous droits n'est utilisée comme référence.
- Le module "Ma traduction" (§14) devient la seule voie d'accès à un rendu français personnel non contraint par les droits.
- Simplifie `.gitignore` et le modèle de menace : plus qu'une seule catégorie de secret à protéger (les clés API), plus de fichier sous droits à faire cohabiter avec un dépôt public.
