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
- Toute nouvelle présentation, section ou option d’affichage doit mettre à jour les réglages de thème concernés et leurs six états; tout comportement ou seuil qui peut varier doit être exposé dans les settings plutôt que codé en dur.
- Chaque feature doit inscrire dans `TODO.md` les tests à rédiger, les vérifications à exécuter et leur résultat avant de passer dans `Done`.
- La baseline tests/Ruff/lint est zéro : confirmer puis corriger toute régression observée, même préexistante, sauf risque disproportionné explicité.

## ⛔ Interdits

- ⛔ Créer une PR sans validation et accord explicite de Nicolas — le fork doit d'abord être testé sur son serveur.
- ⛔ Committer sans demande explicite — les changements locaux peuvent appartenir à Nicolas.
- ⛔ Oublier de créer ou mettre à jour la ligne `CONTRIBUTIONS.md` d’une feature — ce registre est la source unique de son état de livraison.
- ⛔ Marquer une feature `Done` sans tests prévus et vérifiés dans `TODO.md` — les régressions doivent être visibles avant la livraison.
- ⛔ Tenir la feuille de route canonique dans `.worktrees/**` — elle vit dans le `TODO.md` à la racine du dépôt pour rester visible depuis le projet principal.
- ⛔ Amender un commit que Nicolas n'a pas vu — corriger avec un nouveau commit.
- ⛔ Modifier `.github/workflows/**` dans une PR ordinaire — les gardes CI rejettent ces changements.
- ⛔ Inclure `TODO.md` dans une PR upstream — la feuille de route est interne au fork et doit toujours rester hors du diff proposé au projet source.
- ⛔ Copier une migration du projet source ou son étape intermédiaire — le graphe et les données du fork divergent.
- ⛔ Mettre SQLite sur NFS, SMB/CIFS ou un partage réseau — le mode WAL ne le supporte pas.
- ⛔ Ajouter `celery` aux queues du worker `interactive` — les tâches longues bloqueraient les actions utilisateur.
- ⛔ Déplacer l'installation du filtre de logs ou élargir son `except` — une panne peut alors exposer des secrets silencieusement.
- ⛔ Utiliser une classe Tailwind `dark:` — elle suit l'OS et contredit le choix de thème explicite de l'utilisateur.
- ⛔ Lire, afficher ou committer `.env`, clés, jetons ou données de production — ce sont des secrets hors périmètre.
- ⛔ Prioriser l'i18n ou la traduction française sans réactivation explicite — la parité Home avec Floppy Companion reste prioritaire.
- ⛔ Ajouter du texte d'interface ou des valeurs par défaut en français — l'interface et les défauts restent en anglais.
- ⛔ Déployer une branche autre que `custom` sur Unraid — la recette personnelle doit rester distincte des branches proposées au projet source.
- ⛔ Accumuler les anciennes images Floppy sur Unraid — conserver uniquement l'image active et une image de retour arrière, l'espace Docker est limité.
- ⛔ Regrouper plusieurs changements révisables dans une PR ou partager leur worktree — chaque PR doit être la plus petite tranche indépendante, testable et extractible possible; empiler des PR seulement si une dépendance est inévitable.
- ⛔ Interpréter « finir les TODO du worktree » comme toute la roadmap racine — ne traiter que la feature portée par la branche active afin de préserver l'isolation des contributions.
- ⛔ Coder une rangée Home hors de la configuration existante — chaque rangée doit rester ajoutable, supprimable et ordonnable.
- ⛔ Afficher globalement une option propre à une rangée Home — la placer dans le menu de cette rangée pour garder son contexte clair.
- ⛔ Inventer la signature d’un cache ou la couvrir uniquement par un mock — vérifier l’appel réel et tester le GET Home avec la rangée configurée pour éviter un 500.
- ⛔ Chaîner `default` avec une clé facultative de dictionnaire dans un template Django — résoudre les replis sans argument manquant pour éviter un 500 au rendu.
- ⛔ Classer une série rattrapée dans `Stale` — exiger un épisode régulier déjà diffusé et non vu; les spéciaux ne comptent pas.
- ⛔ Remplacer le besoin « In progress » transversal par une rangée par média — un seul endroit doit couvrir toutes les familles activées.
- ⛔ Remplacer l’identité d’un prochain épisode par sa seule date — conserver `SxxExx` quand les numéros sont connus.
- ⛔ Laisser une série rattrapée dans `All media / In progress` — les séries sans épisode diffusé restant à voir doivent être exclues, contrairement aux autres médias réellement en cours.
- ⛔ Réduire un groupe d’épisodes en cache à son seul total — Activity Journal et History doivent conserver les épisodes membres pour afficher le compteur, le chevron et le détail dépliable.
- ⛔ Tester le regroupement d’épisodes uniquement avec des objets Django — le journal Home consomme les dictionnaires sérialisés du cache.
- ⛔ Faire entrer une lecture non terminée dans History — exiger à la fois le statut `Completed` et une date de fin, car une ancienne date peut survivre à un retour vers `In progress`.
- ⛔ Donner à `/history` une identité visuelle distincte de l’application — la page doit hériter de la couleur principale, de la police et des autres tokens du thème général.
- ⛔ Remplir les contrôles History avec une couleur personnalisable — utiliser les surfaces et textes du thème, avec la couleur principale seulement en bordure ou focus, pour garantir la lisibilité.
- ⛔ Rendre History obligatoire dans la navigation — son entrée doit rester configurable dans les réglages Sidebar.
- ⛔ Forcer l’ouverture d’un épisode depuis une rangée `In Progress` — chaque rangée épisodique doit exposer l’option dans son propre menu, activée par défaut.
- ⛔ Afficher les balises `[spoiler]` BetaSeries brutes ou leur contenu sans action — les avis doivent masquer chaque passage et permettre sa révélation volontaire au clavier comme au clic.
- ⛔ Superposer l’enrichissement des crédits aux portraits ou le limiter aux films — les photos restent intactes et les mêmes cartes enrichies servent films, séries, saisons et épisodes.
- ⛔ Présenter une prévisualisation non enregistrée comme une capture de résultat — sauvegarder, recharger et vérifier la barre avant d’illustrer le branding.
- ⛔ Supposer que le branding privé apparaît avant connexion — la page publique exige une publication explicite, puis une vérification déconnectée.
- ⛔ Tronquer le nom de démonstration dans le logo texte — vérifier sa largeur réelle sur la barre latérale et dans les captures.
- ⛔ Laisser un nom de logo libre occuper la navigation — borner les nouvelles saisies côté formulaire et serveur, sans effacer les noms déjà sauvegardés.
- ⛔ Publier un instantané avant d’enregistrer les valeurs envoyées par le formulaire Appearance — « Publish saved branding » doit sauvegarder puis publier le même branding, vérifié déconnecté.
- ⛔ Limiter la publication de la page de connexion au seul logo — le thème et sa palette personnalisée doivent être publiés avec le branding et vérifiés déconnecté.
- ⛔ Exiger une seconde action de publication après « Save appearance » pour le propriétaire de l’instance — son enregistrement doit mettre à jour en une fois l’interface privée et la connexion publique.
- ⛔ Supposer que le rebuild Unraid laisse Floppy démarré — si autostart est désactivé, Unraid arrête le conteneur reconstruit; démarrer explicitement avant le contrôle de santé, en activation comme en retour arrière.

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

- Branche active : `feat/home-all-media-in-progress`; le worktree contient des changements Home/Apparence non commités à préserver.
- Prochaine étape : committer sur demande, intégrer dans `custom`, déployer sur `unraid-server`, puis laisser Nicolas tester avant toute proposition de PR.
