# Contexte agents — Floppy Fork

## Quoi

- Fork personnel de Floppy, un gestionnaire multimédia auto-hébergé destiné à l'usage quotidien sur le serveur de Nicolas et à des contributions proposées au projet source.
- Application Django 5.2 en Python 3.12, avec Redis, Celery et Tailwind CSS.
- Objectif de travail : améliorer le fork, valider localement, faire tester le déploiement privé, puis proposer les changements utiles en PR après accord explicite.

## Commandes

```bash
uv sync --locked
SECRET=test-only uv run --no-sync python src/manage.py migrate
SECRET=test-only uv run --no-sync python src/manage.py runserver
scripts/test.sh app.tests.views.test_media_details
scripts/test.sh
scripts/test.sh --full
uv run --no-sync ruff check src
SECRET=test-only uv run --no-sync python src/manage.py floppy_preflight
PYTHONPATH=src uv run --no-sync python -m app.domain_vocabulary --check
SECRET=test-only uv run --no-sync python src/manage.py spectacular --custom-settings api.schema_contract.STATIC_SPECTACULAR_SETTINGS --fail-on-warn --validate --file src/api/contracts/openapi.yaml
npx @tailwindcss/cli -i ./src/static/css/input.css -o ./src/static/css/main.css
docker build -t floppy:local .
docker compose up -d
```

- Tests réseau : `scripts/test.sh --network`; tests lents seuls : `scripts/test.sh --slow`.
- Les scripts `scripts/*.sh` nécessitent Bash (Git Bash ou WSL sous Windows).
- Après un changement de modèle : créer une migration Floppy puis exécuter `uv run --no-sync python src/manage.py migrate`.
- Celery utilise deux processus : `interactive` seul d'un côté; `celery` avec beat de l'autre. Voir `README.md` pour les commandes exactes.
- Serveur personnel : utiliser l'alias `ssh unraid-server`; le conteneur de production s'appelle `Floppy`.
- Depuis `custom` uniquement : prévisualiser avec `.\publish.ps1 -Plan -NonInteractive`, puis publier et déployer avec `.\publish.ps1 -NonInteractive -Confirm` après validation explicite.
- Diagnostic distant en lecture seule : `ssh unraid-server "docker exec Floppy python /floppy/manage.py floppy_preflight"`.
- Depuis `custom`, préparer un worktree isolé : `.\scripts\feature-worktree.ps1 -Branch feat/example`; prévisualiser avec `-Plan`.

## Carte

- `src/app/` — domaine média, modèles, vues et logique métier.
- `src/users/` — comptes, préférences et configuration de l'accueil.
- `src/lists/` — listes manuelles, publiques et intelligentes.
- `src/integrations/`, `src/events/` — fournisseurs, imports, webhooks et tâches.
- `src/config/`, `src/api/` — Django, exécution, contrats REST et OpenAPI.
- `src/templates/`, `src/static/` — interface et CSS Tailwind compilé.
- `scripts/` — tests, diagnostics, benchmarks et rejouage de migrations.
- `docs/agents/`, `docs/architecture/` — contrats techniques et guides spécialisés.
- `Dockerfile`, `docker-compose*.yml`, `entrypoint.sh`, `nginx.conf`, `supervisord.conf` — conteneur et exploitation.
- `wiki/` — dépôt Git distinct pour la documentation publique; ne jamais l'indexer ici.

## Décisions

- `origin` est le fork `PreciselyWrong/Floppy`; `upstream` est le projet source `dannyvfilms/Floppy`. Garder ces rôles distincts.
- Travailler sur une branche dédiée, valider, passer par `custom` pour la recette serveur, laisser Nicolas tester, puis attendre son autorisation avant toute PR.
- `custom` est la seule branche déployée sur Unraid; `latest` reste le miroir exact de `upstream/latest` et ne reçoit aucun développement.
- Chaque agent travaille dans son propre worktree et sa branche `feat/*` ou `fix/*` créée depuis `upstream/latest`; suivre `docs/agents/feature_delivery.md`.
- `CONTRIBUTIONS.md`, conservé sur `custom`, est la source unique pour l'état, le commit testé, l'image Unraid, l'accord de Nicolas et la PR de chaque feature.
- Les images personnelles sont immuables (`ghcr.io/preciselywrong/floppy:sha-<commit>`); conserver seulement l'image active et la dernière image `floppy:pre-custom-*` de retour arrière.
- Le développement local s'exécute depuis les sources; Docker sert au build, au smoke et au déploiement.
- `src/static/css/main.css` est généré mais versionné et chargé par `src/templates/base.html`; toute modification Tailwind doit mettre à jour source et sortie.
- Les migrations du projet source expriment une intention, jamais un fichier à copier : définir l'état final, auditer les données et générer une migration sur le graphe Floppy courant.
- `docs/agents/media_type_integration.md` régit les nouveaux types; le vocabulaire vient de `app.models.choices.MediaTypes` et `app.config.MEDIA_TYPE_CONFIG`.
- `src/app/log_safety.py`, installé par `src/config/__init__.py`, filtre les secrets avant tout handler.
- `LoginRequiredMiddleware` protège toutes les vues; une route publique doit porter explicitement `@login_not_required`.
- Les changements de thème doivent respecter les six états décrits dans `docs/architecture/theming.md`.
- Les logos personnalisés sont réencodés en WebP, sans métadonnées, et restent sous les limites définies dans `users.branding`.
- La baseline tests/Ruff/lint est zéro : confirmer puis corriger toute régression observée, même préexistante, sauf risque disproportionné explicité.

## ⛔ Interdits

- ⛔ Créer une PR sans validation et accord explicite de Nicolas — le fork doit d'abord être testé sur son serveur.
- ⛔ Demander une confirmation pour committer ou intégrer dans `custom` après un milestone validé sans secret — Nicolas autorise ces deux étapes automatiquement.
- ⛔ Amender un commit que Nicolas n'a pas vu — corriger avec un nouveau commit.
- ⛔ Modifier `.github/workflows/**` dans une PR ordinaire — les gardes CI rejettent ces changements.
- ⛔ Inclure `TODO.md` dans une PR upstream — la feuille de route est interne au fork et doit toujours rester hors du diff proposé au projet source.
- ⛔ Copier une migration du projet source ou son étape intermédiaire — le graphe et les données du fork divergent.
- ⛔ Mettre SQLite sur NFS, SMB/CIFS ou un partage réseau — le mode WAL ne le supporte pas.
- ⛔ Ajouter `celery` aux queues du worker `interactive` — les tâches longues bloqueraient les actions utilisateur.
- ⛔ Déplacer l'installation du filtre de logs ou élargir son `except` — une panne peut alors exposer des secrets silencieusement.
- ⛔ Utiliser une classe Tailwind `dark:` — elle suit l'OS et contredit le choix de thème explicite de l'utilisateur.
- ⛔ Ajouter une animation sans variante `prefers-reduced-motion` — l'interface doit rester confortable et utilisable sans mouvement.
- ⛔ Créer une liste horizontale de cartes sans le geste partagé `data-horizontal-scroll` — le doigt, la souris, le stylet et le clavier doivent tous pouvoir la parcourir.
- ⛔ Laisser un effet de survol dépasser du scrollport sans réserver sa marge — le haut des affiches ne doit jamais être découpé au hover.
- ⛔ Décaler horizontalement une rangée pour compenser son hover — la première carte doit rester alignée avec le titre.
- ⛔ Mettre en cache les pages, fragments ou données authentifiés dans la PWA — le service worker reste limité aux fichiers statiques publics.
- ⛔ Supposer que toutes les fiches exposent le même champ de titre — épisodes, numéros et autres variantes doivent conserver leurs replis propres.
- ⛔ Accepter un SVG comme logo personnalisé — son contenu actif et sa complexité ne doivent jamais entrer dans les préférences.
- ⛔ Placer les réglages du logo hors de `Settings > Appearance` ou laisser le logo de la sidebar se contracter — l'identité visuelle doit rester trouvable et lisible.
- ⛔ Aligner le logo ou le mot-symbole sur un bord du bandeau de sidebar — toutes les variantes restent centrées dans la colonne.
- ⛔ Laisser `prefers-color-scheme` cibler un thème explicite — seul `System default` peut suivre l'OS.
- ⛔ Afficher le switcher soleil/lune avec un thème autre que `System`, `Light` ou `Dark` — il écraserait le thème choisi.
- ⛔ Passer une chaîne JSON à `json_script` — le filtre sérialise déjà les objets et l'éditeur recevrait du texte inutilisable.
- ⛔ Lire, afficher ou committer `.env`, clés, jetons ou données de production — ce sont des secrets hors périmètre.
- ⛔ Prioriser l'i18n ou la traduction française sans réactivation explicite — la parité Home avec Floppy Companion reste prioritaire.
- ⛔ Ajouter du texte d'interface ou des valeurs par défaut en français — l'interface et les défauts restent en anglais.
- ⛔ Déployer une branche autre que `custom` sur Unraid — la recette personnelle doit rester distincte des branches proposées au projet source.
- ⛔ Accumuler les anciennes images Floppy sur Unraid — conserver uniquement l'image active et une image de retour arrière, l'espace Docker est limité.
- ⛔ Faire travailler deux features dans le même worktree ou faire dépendre leur migration l'une de l'autre — elles doivent rester extractibles en PR indépendantes.
- ⛔ Coder une rangée Home hors de la configuration existante — chaque rangée doit rester ajoutable, supprimable et ordonnable.
- ⛔ Remplacer le besoin « In progress » transversal par une rangée par média — un seul endroit doit couvrir toutes les familles activées.
- ⛔ Remplacer l'identité d'un prochain épisode par sa seule date — conserver `SxxExx` quand les numéros sont connus.
- ⛔ Ajouter un menu dans une rangée configurable sans promouvoir la rangée ouverte au-dessus de ses sœurs — leurs bordures et contrôles peuvent recouvrir la liste déroulante.

## Pièges

- `manage.py` échoue sans `SECRET` → charger `.env` ou définir une valeur de test.
- `src/static/css/tailwind.css` est une ancienne destination → générer `src/static/css/main.css`.
- Le build Tailwind scanne aussi sa propre sortie → relancer la commande jusqu'à ce que `main.css` ne change plus.
- `UPSTREAM_PORTS.md` référence encore `upstream/dev` de Yamtrack, absent de la configuration Git actuelle → ne pas utiliser ce range avant réconciliation explicite.
- `wiki/` paraît non suivi dans le dépôt principal → committer depuis `wiki/`, son propre dépôt Git.
- Le test rapide exclut `slow` et `network`; `--full` dure plus de 20 minutes et nécessite Playwright.
- `docker compose up -d` utilise l'image préconstruite `ghcr.io/dannyvfilms/floppy` → ce n'est pas un déploiement du build local `floppy:local`.
- `publish.ps1` est absent des branches de contribution → basculer sur `custom` avant toute prévisualisation ou publication vers Unraid.
- Deux migrations portent le même numéro après intégration → garder chaque migration indépendante sur sa branche et créer uniquement sur `custom` une migration de fusion dépendant des deux feuilles.

## État

- Coordination active sur `custom`; les features Home et Appearance vivent dans des worktrees indépendants.
- Le centrage et la typographie réglable du logo sont déployés sur `unraid-server` avec l'image `sha-ba463cdd`; attendre le verdict de Nicolas avant toute proposition de PR.
