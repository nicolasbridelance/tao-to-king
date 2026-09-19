# 009 — Flutter comme client de l'app compagnon

## Statut
Accepté

## Contexte
L'app compagnon (§13) doit être testable en boucle rapide sur le poste de dev (Codespace), sans matériel iOS disponible, avec pour cible finale un usage sur téléphone Android personnel.

## Décision
Front en Flutter, développé et testé dans le Codespace (`flutter run -d linux` ou `-d web-server`, hot reload) contre l'API FastAPI locale, packagé en APK Android une fois une fonctionnalité stabilisée. Pas de cible iOS.

## Conséquences
- Un seul langage/framework front à maintenir pour desktop (dev) et Android (déploiement).
- Le build APK et l'installation sur appareil réel restent hors de la boucle d'itération courante — ils ne servent qu'à valider ce que Linux/web ne peut pas simuler (notifications, capteurs, écran réel).
- Le devcontainer n'a pas besoin du SDK Flutter avant d'attaquer le jalon de l'app compagnon ; ADR à revoir si un besoin de test iOS apparaît (matériel requis).
