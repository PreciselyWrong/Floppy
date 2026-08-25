# TODO

## Now

- [ ] Committer, intégrer dans `custom`, puis déployer et tester la section configurable `All media` avec sa rangée `In progress` transversale.
  - Validation locale terminée : 50 tests Home, Ruff, contrôle Django et génération Tailwind stable.
  - Inclure uniquement la migration 0128; la migration 0129 appartient à l’autre feature active dans ce worktree partagé.
  - Tests à faire avant `Done` :
    - [ ] Ajouter, supprimer et réordonner une rangée `All media`.
    - [ ] Afficher `In progress` avec plusieurs types activés et vérifier le mélange des résultats.
    - [ ] Vérifier les filtres, la position sauvegardée et la migration d’un profil existant.
    - [ ] Tester l’absence de rangée quand aucun résultat ne correspond.

## Next

- [ ] Améliorer les performances générales, actuellement trop lentes.
  - Constats de départ sur petite base synthétique : Home froide 221 ms / 107 requêtes, rangée Home paginée 146 ms / 116 requêtes, liste personnalisée chaude 68 ms / 32 requêtes.
  - Objectifs : Home chaude sous 40 ms, rangée paginée sous 50 ms et 10 requêtes, liste personnalisée chaude sous 40 ms et 10 requêtes, aucun appel fournisseur pendant un affichage chaud.
  - [ ] P0 — Établir la référence réelle → vérifier : médiane et p95 sur Home, recherche, autocomplétion, fiches, saisons, listes, calendrier et synchronisations avec `benchmark_perf`, `scripts/bench.sh` et les journaux `slow_request`.
  - [ ] P0 — Mesurer séparément froid, chaud, Redis lent, Redis vide, grande bibliothèque et plusieurs requêtes concurrentes → vérifier : durée, requêtes SQL, appels externes, commandes Redis, taille des réponses et mémoire.
  - [ ] P1 — Refaire le cache Home autour d’un ordre compact d’IDs → vérifier : la pagination ne parcourt plus toute la bibliothèque et n’hydrate que les 14 cartes affichées.
    - Remplacer les objets Django complets en Redis par des IDs et les champs minimaux nécessaires aux cartes.
    - Remplacer le TTL artificiel de 60 secondes par une révision par utilisateur et une invalidation immédiate lors d’un changement.
    - Regrouper les lectures avec `get_many()` et les écritures avec `set_many()`; supprimer le registre Redis lu et réécrit à chaque rangée.
    - Servir l’ancienne valeur pendant la reconstruction et empêcher deux reconstructions simultanées avec un verrou court.
  - [ ] P1 — Rendre Home et les listes strictement en lecture → vérifier : aucun `save`, `bulk_create`, `bulk_update` ni appel fournisseur pendant un GET.
    - Déplacer la création et la mise à jour des épisodes vues depuis une fiche saison vers Celery.
    - Déplacer la promotion automatique d’une saison terminée hors du rendu Home.
    - Supprimer les appels fournisseur saison par saison dans le calcul de `max_progress`; utiliser les données locales puis rafraîchir en arrière-plan.
  - [ ] P2 — Borner la recherche locale en SQL → vérifier : jamais de `list(queryset)` sur une bibliothèque entière.
    - Appliquer filtre, tri et `LIMIT` avant matérialisation pour la recherche et l’autocomplétion.
    - Charger uniquement les champs nécessaires aux 24 résultats de recherche ou aux 8 suggestions.
    - Mesurer `EXPLAIN QUERY PLAN`; envisager FTS5 uniquement si la recherche de titre reste le goulet d’étranglement.
  - [ ] P2 — Ajouter stale-while-revalidate aux métadonnées → vérifier : une fiche sert la dernière donnée locale même si le fournisseur est lent ou indisponible.
    - Séparer cache principal, crédits, recommandations, saisons et disponibilités.
    - Inclure fournisseur, média, langue et édition dans les clés.
    - Rafraîchir via Celery avec un verrou par média et conserver les absences et erreurs temporaires avec un TTL adapté.
    - Réserver les appels synchrones à une recherche explicite ou à l’action « Refresh ».
  - [ ] P3 — Mettre les listes personnalisées au même modèle que les listes média → vérifier : ordre des IDs en cache, hydratation limitée à la page et recalcul uniquement après modification.
    - Mettre en cache séparément ordre, progression, répartition par type et statut.
    - Invalider lors d’une modification de liste, d’un statut, d’une collection ou d’un filtre de liste intelligente.
  - [ ] P3 — Réduire le coût visuel de Home → vérifier : le premier affichage reste sous 150 ko et les rangées éloignées sont chargées par lots au voisinage de l’écran.
    - Éviter un fragment unique contenant toutes les rangées restantes.
    - Conserver le chargement progressif sans multiplier les requêtes concurrentes.
  - [ ] P4 — Stabiliser Redis → vérifier : taux de succès, taux d’éviction, mémoire, p95 des commandes, nombre de commandes par page et comportement avec Redis indisponible.
    - Garder des payloads courts et expirables; ne pas augmenter tous les TTL sans invalidation.
    - Ne pas mettre en cache le HTML complet personnalisé ni des modèles Django en mémoire de processus.
    - Ne pas ajouter de requêtes Redis par carte; le limiteur fournisseur et le cache doivent rester groupés.
  - Tests à rédiger : seuils de durée et de requêtes, cache froid/chaud, pagination indépendante de la taille de bibliothèque, absence d’écriture en GET, absence d’appel fournisseur chaud, invalidation après modification, reconstruction concurrente, réponse périmée pendant panne et repli Redis indisponible.
- [ ] Ajouter les avis publics TMDB, BetaSeries et Hardcover.
  - Respecter le périmètre exact de chaque fournisseur et isoler leurs pannes.
  - Fournir l’aperçu de deux avis et l’écran complet avec ses quatre tris.
  - Rendre l’aperçu visible, masquable et ordonnable dans les options.
  - Vérifier liste vide, panne, limites, réponses BetaSeries et critiques trop courtes.
  - Tests à rédiger : fournisseur indisponible, avis vide, limite de longueur, ordre et masquage configurés.
- [ ] Ajouter les disponibilités Plex, Radarr et Sonarr aux fiches.
  - Ne jamais exposer de secret ni lancer d’inventaire lourd à l’ouverture.
  - Séparer présence Plex, présence serveur et recherche manuelle.
  - Rendre chaque intégration et section paramétrable dans les options.
  - Détailler la disponibilité par saison et ouvrir directement la fiche Plex quand sa clé est connue.
  - Vérifier liens directs, replis, absences, délais et erreurs partielles.
  - Tests à rédiger : lien direct, repli, absence, délai dépassé, erreur partielle et section désactivée.
- [ ] Ajouter la barre d’actions persistante et les actions propres à chaque média.
  - Masquer les actions invalides sur les épisodes.
  - Prévoir les actions dédiées aux livres.
  - Rendre la barre et ses actions facultatives dans les options.
  - Vérifier les transitions de statut et la restauration après refus.
  - Tests à rédiger : action invalide masquée, action livre, barre désactivée, transition réussie et refus restauré.

## Ideas

- [ ] Synchroniser les commentaires d’épisodes avec une persistance privée multi-appareils.
- [ ] Proposer un choix unique `Tonight` depuis Discover.
- [ ] Étendre BetaSeries aux notes et aux visionnages sans réimporter les notes arrondies.
- [ ] Piloter l’ajout, la recherche automatique et le choix manuel des versions dans Radarr/Sonarr.
- [ ] Envoyer les notes de Floppy vers Plex sans réimporter leur valeur arrondie.
- [ ] Ajouter une traduction automatique après choix explicite du moteur et de sa confidentialité.
- [ ] Relayer les bandes originales Tunefind et ouvrir les morceaux dans Spotify.
- [ ] Étudier un cache dynamique et une file de rejeu avant de promettre le mode hors ligne.

## Done

- Enrichissement des séries et saisons: reprise, sorties futures, ratings d’épisodes, spoilers, épisodes sautés et estimation sur 28 jours configurables.
- Enrichissement des crédits et fiches personne: invités séparés, œuvres clés, âge, titres suivis et sections configurables.
- Logo masquable ou personnalisable, avec mouvements et arrondis adaptés à chaque thème.
- Moyenne publique pondérée configurable avec détail des sources et des votes.
- Thèmes classiques et modernes distincts, avec mise en page configurable des fiches.
- Affichage de `SxxExx` pour le prochain épisode connu dans `Up Next`.
- Regroupement des épisodes consécutifs dans l’historique.
- Rangée d’historique configurable sur Home avec chargement progressif.
- Rapprochement de la Home Web avec Floppy Companion grâce à cinq améliorations configurables.
- Recherche des sorties du calendrier par titre.

## Dropped
