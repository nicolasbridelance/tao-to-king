# 001 — SQLite plutôt que Postgres

## Statut
Accepté

## Contexte
Le projet tourne sur un Codespace mono-utilisateur, sans concurrence d'écriture ni besoin d'accès réseau à la base pendant la phase pipeline.

## Décision
SQLite en mode WAL, fichier unique hors Git, reconstructible depuis les scripts d'ingestion et les fichiers d'axes versionnés. Pas de Postgres tant que le volume ou la concurrence ne l'exigent pas.

## Conséquences
- Pas de service de base à faire tourner ni à sauvegarder séparément.
- La persistance dépend d'une sauvegarde explicite du fichier (`taolab backup`), le Codespace n'étant pas garanti dans la durée.
- Si l'app compagnon (§13) ou un accès concurrent l'exigeaient un jour, cette décision serait à rouvrir.
