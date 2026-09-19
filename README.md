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
```

La base est créée dans `data/corpus.sqlite` et ignorée par Git. La commande
`build-corpus` peut être relancée après un changement des JSON. Pour télécharger les
œuvres manquantes, exécuter `python scripts/fetch_additional_corpus.py` avec un accès
réseau ; le script vérifie la couverture attendue avant d'écrire chaque fichier.

## État

Ce dépôt fournit les textes et un index SQLite consultable. L'alignement au vers du
Tao-tö king, les annotations philologiques et le pipeline de génération restent à
implémenter. Les paragraphes du Tchouang-tseu et du Lie-tseu sont des unités de page,
pas encore des anecdotes établies par une édition critique.
