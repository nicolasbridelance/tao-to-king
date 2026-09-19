# Taolab

Corpus de travail pour l'exégèse combinatoire du Tao-tö king et les textes voisins.

## Corpus

Les fichiers JSON de `corpus/` sont les sources versionnées. Chaque passage téléchargé
de Wikisource porte son titre de page, l'identifiant de révision de sa page et sa
date de récupération. Les témoins déjà présents du Tao-tö king ont une provenance au
niveau du fichier. Une traduction reste une donnée dérivée, distincte du texte chinois.
Les pages françaises de Wieger transcluent des pages de scan : leur identifiant de
révision ne fige pas à lui seul ces transclusions ; le JSON commité est le cliché du
texte réellement récupéré.

Le corpus additionnel comprend le Tchouang-tseu, le Lie-tseu, le Sunzi, le Neiye
(Guanzi 49) et le Zhouyi. Le Zhouyi sépare le texte des hexagrammes et les couches de
commentaire ; les « Dix Ailes » ont leurs propres unités. Les traductions françaises de
Wieger (édition de 1913) sont distinctes des textes chinois.

## Utilisation locale

Installer le paquet, puis reconstruire la base depuis les JSON :

```sh
python -m pip install -e .
python -m taolab build-corpus
python -m taolab list --work zhuangzi --kind paragraph --contains 庖丁
python -m taolab list --work zhouyi --kind hexagram --limit 3
python -m taolab show zhouyi:wikisource_received:hexagram:1:line:1
python -m taolab context zhuangzi 3
python -m taolab plan
python -m taolab plan --size 800 --seed 42 --write
```

La base est créée dans `data/corpus.sqlite` et ignorée par Git. La commande
`build-corpus` peut être relancée après un changement des JSON. Pour télécharger les
œuvres manquantes, exécuter `python scripts/fetch_additional_corpus.py` avec un accès
réseau ; le script vérifie la couverture attendue avant d'écrire chaque fichier.

## Planification locale

Les cinq axes du premier essai et leurs règles de compatibilité sont versionnés dans
`axes/`. `plan` lit les 483 unités chinoises principales du corpus (chapitres,
hexagrammes et Ailes), leur associe les traductions disponibles pour la même œuvre
et référence, puis propose 600 cellules par défaut. Chaque unité chinoise apparaît
au moins une fois ; les cellules supplémentaires répartissent les valeurs des axes.
La graine rend le tirage reproductible. Une comparaison n'est admise que si deux
traductions du passage existent. Les passages de moins de 80 caractères de texte source ne
reçoivent pas la consigne de réponse longue.

La commande est un **plan à blanc** par défaut : elle lit la base et affiche un résumé
JSON, sans appel API ni écriture. `--write` enregistre le plan, ses cellules et les
définitions d'axes dans SQLite. Une relance identique ne crée aucun doublon. L'ID
d'une cellule dépend du hash du chinois, des traductions effectivement sélectionnées,
des axes et de la version de gabarit ; une correction de source renouvelle donc les
cellules concernées. Le plan conserve les anciens hashes pour retracer leur origine.
Les nombres `rejected_candidates` comptent les rejets par règle ; une même
combinaison peut déclencher plusieurs règles.

## État

Ce dépôt fournit les textes, un index SQLite et la planification sans génération.
L'alignement au vers du Tao-tö king, les annotations philologiques et la génération
restent à implémenter. Les paragraphes du Tchouang-tseu et du Lie-tseu sont des
unités de page, pas encore des anecdotes établies par une édition critique.
