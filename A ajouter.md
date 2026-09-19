Voici comment ces ajouts s'insèrent mécaniquement dans les différents étages de votre projet :

1. Dans le modèle de données et l'ingestion (Étage 1 & §3)
Comme pour le Tao-tö king et le Yi Jing, la règle stricte du domaine public s'applique.

Tchouang-tseu : Ingestion via la traduction de Séraphin Couvreur (1918, domaine public) ou Léon Wieger. Il intègre la table text_unit avec une granularité propre (chapter > anecdote).

L'Art de la guerre : Ingestion via la traduction du père Amiot (1772, domaine public). Granularité : chapter > maxim.

Le Neiye : Faisant partie du Guanzi, il peut être ingéré comme un chapitre unique découpé au vers.

2. Dans l'espace des axes et la génération (Étage 5 & §7)
L'apport majeur de ces textes est d'enrichir la combinatoire en devenant des filtres de lecture (les axes transformer) appliqués au Tao-tö king.

Nouvelle valeur d'axe tradition : Ajouter lecture par Tchouang-tseu. Le prompt demandera à DeepSeek d'éclairer un vers abstrait de Lao-tseu en utilisant une fable concrète du boucher ou du menuisier.

Nouvelle valeur d'axe discipline : Ajouter stratégie militaire. Le modèle, ancré sur Sun Tzu, décodera des chapitres du Tao comme le 68 ou le 69 sous l'angle strict de la gestion de conflit.

Densification de l'axe situation : Les fables de Lie-tseu fournissent un matériau parfait pour générer les réponses liées aux valeurs attente et échec.

3. Dans le catalogue de pratiques (Étage §12)
Le Neiye vient sourcer et légitimer le module de pratique.

Au lieu de rédiger vous-même les consignes pour tiaoxi (régler le souffle) ou zuowang (l'assise), les champs geste, mode_echec et signal de votre catalogue s'appuieront directement sur les vers du Neiye.

Dans l'app compagnon (§14), l'écran du minuteur affichera un vers du Neiye comme consigne d'ancrage avant de s'éteindre.

4. Dans la mécanique de jeu (Étage §16 - Aventures textuelles)
Votre spécification prévoit déjà des aventures textuelles par parseur privées des verbes d'action directe (forcer, attaquer, saisir). Le Tchouang-tseu est le moteur narratif clé en main de ce module :

Le jeu « Le cuisinier » et le jeu « L'eau » (§15) sont littéralement des mises en situation de ses paraboles. Le LLM maître du jeu piochera l'état initial, la cible et les contraintes physiques directement dans la table text_unit correspondante au Tchouang-tseu.

Impact sur la règle RAG du LLM compagnon (§13)
La contrainte non négociable de votre spec est : « Hors corpus, le modèle dit qu'il est hors corpus. Toute affirmation sinologique porte son témoin et son chapitre, tirés de la base. »
L'ingestion de ces textes permet d'élargir le RAG. Si vous demandez au LLM de l'app de discuter du non-agir, il ne sera plus limité à citer un chapitre cryptique du Tao-tö king : il pourra croiser la source en citant le chapitre 3 du Tchouang-tseu (le boucher) ou le chapitre 4 de L'Art de la guerre, tout en respectant strictement l'obligation de sourcer depuis le SQLite local.



Aussi : ajouter un module Yi Jing

## État de l'intégration du corpus (2026-09-19)

- Textes chinois complets importés : Tchouang-tseu (33 chapitres), Lie-tseu (8), Sunzi (13), Neiye (Guanzi 49), Zhouyi (64 hexagrammes et les Dix Ailes, réparties sur 9 pages).
- Traductions françaises importées séparément : Léon Wieger, édition de 1913, pour les 33 chapitres du Tchouang-tseu et les 8 du Lie-tseu.
- Chaque passage ajouté porte sa page Wikisource et son identifiant de révision ; `python -m taolab build-corpus` reconstruit une table SQLite `text_unit` consultable par œuvre, témoin et granularité.
- Le Yi Jing est présent comme corpus structuré (jugement, lignes, commentaires, ailes). L'interface de tirage ou de jeu reste à concevoir ; les textes de Mawangdui n'ont pas été trouvés en transcription complète dans la source consultée.
- La traduction Amiot n'est pas importée : la page française directement lisible de *L'Art de la guerre* correspond à une édition de 1996. Le fac-similé de 1772 existe, mais sa transcription Wikisource n'est pas complète ; le chinois de Sunzi est disponible pour l'essai.
- Les paragraphes du Tchouang-tseu et du Lie-tseu sont des unités de consultation ; le découpage en anecdotes reste une curation à faire, sans le déduire automatiquement des sauts de paragraphe.

## État de la planification (2026-09-19)

- Les cinq axes du premier essai (`discipline`, `scale`, `register`, `length`, `translation_layer`) et les règles de compatibilité sont définis dans `axes/`.
- `python -m taolab plan` prépare à blanc 600 cellules couvrant les 483 unités chinoises principales des six œuvres. La graine fixe le tirage ; `--write` persiste le plan en SQLite sans doublons.
- Les traductions sont fournies uniquement lorsqu'elles existent pour le même passage. La comparaison de deux traductions est actuellement disponible surtout pour le Tao-tö king. Les cellules gardent les hashes exacts des témoins utilisés.
- L'axe `tradition` envisagé ci-dessus demande encore un alignement vérifié entre passages des œuvres. Les autres étages de génération et d'évaluation ne sont pas encore branchés au plan.
