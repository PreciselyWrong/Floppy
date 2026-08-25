# TODO

## Now

- [ ] Détecter les épisodes sautés sans inclure les spéciaux ni les sorties futures.
  - Tests à faire : épisodes aérés, spéciaux et sorties futures exclus, titres masqués selon le réglage.

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
- [ ] Ajouter un aperçu d’avis publics textuels sur les fiches, puis un écran complet triable; commencer par TMDB et Hardcover.
  - Enrichir ensuite avec BetaSeries sans mélanger les périmètres des fournisseurs.
  - Tests à rédiger : fournisseur indisponible, avis vide, limite de longueur, ordre et masquage configurés.
- [ ] Enrichir les cartes de distribution et d’équipe avec trois œuvres clés, en donnant la priorité aux titres réellement vus.
  - Tests à rédiger : aucun titre vu, titres vus mélangés, doublons et ordre stable.
- [ ] Séparer la distribution récurrente des invités sur les fiches d’épisodes.
  - Tests à rédiger : rôle principal, invité, rôle inconnu et absence de crédits.
- [ ] Enrichir les saisons avec notes publiques par épisode, tendance des notes personnelles et titres non vus masqués à la demande.
  - Tests à rédiger : épisode non noté, saison spéciale, tendance vide, spoiler activé et réglage désactivé.
- [ ] Ajouter les disponibilités Plex, Radarr et Sonarr aux fiches.
  - Ne jamais exposer de secret ni lancer d’inventaire lourd à l’ouverture.
  - Séparer présence Plex, présence serveur et recherche manuelle.
  - Rendre chaque intégration et section paramétrable dans les options.
  - Détailler la disponibilité par saison et ouvrir directement la fiche Plex quand sa clé est connue.
  - Tests à rédiger : lien direct, repli, absence, délai dépassé, erreur partielle et section désactivée.
- [ ] Ouvrir directement la fiche Plex correspondante quand sa clé est connue.
  - Tests à rédiger : clé valide, clé absente, lien invalide et repli local.
- [ ] Ajouter la barre d’actions persistante et les actions propres à chaque média.
  - Masquer les actions invalides sur les épisodes.
  - Prévoir les actions dédiées aux livres.
  - Rendre la barre et ses actions facultatives dans les options.
  - Tests à rédiger : action invalide masquée, action livre, barre désactivée, transition réussie et refus restauré.

## Ideas

- [ ] Estimer la date de fin d'une série depuis le rythme récent.
- [ ] Proposer un choix unique `Tonight` depuis Discover.
- [ ] Ajouter l'âge actuel ou au décès sur les fiches de personnes.
- [ ] Ajouter BetaSeries comme source d'avis, de notes et de visionnages.
- [ ] Piloter l'ajout, la recherche automatique et le choix manuel des versions dans Radarr/Sonarr.
- [ ] Envoyer les notes de Floppy vers Plex sans réimporter leur valeur arrondie.
- [ ] Relayer les bandes originales Tunefind et ouvrir les morceaux dans Spotify.

## Done

- Parité Home Screen avec Floppy Companion: étagères (Resume, Stale, Unstarted, Finished), journal d'activité chronologique, groupement en rafale (Binge grouping), seuil délaissé paramétrable et All media entièrement ouvert.
- Listes déroulantes des rangées Home toujours visibles au-dessus des contrôles voisins.
- Installation PWA guidée sur ordinateur, Android, iPhone et iPad.
- Glissement direct au doigt, à la souris, au stylet et au clavier sur les listes horizontales.
- Enrichissement des séries et saisons: reprise, sorties futures, ratings d'épisodes, tendance des notes personnelles et estimation sur 28 jours configurables.
- Enrichissement des crédits et fiches personne: invités séparés, œuvres clés, âge, titres suivis et sections configurables.
- Section Home `All media` déployée avec sa rangée `In progress` transversale.
- Sélection des familles média configurable dans les rangées Home `All media`.
- Options Home pour afficher `SxxExx` dans `Up Next` et ouvrir directement l’épisode depuis `Now Playing`.
- Logo centré, masquable ou personnalisable, avec typographie du mot-symbole réglable.
- Moyenne publique pondérée configurable avec détail des sources et des votes.
- Thèmes classiques et modernes distincts, avec mise en page configurable des fiches.
- Modales de suivi toujours centrées dans la fenêtre après les animations d’apparence.
- Affichage de `SxxExx` pour le prochain épisode connu dans `Up Next`.
- Regroupement des épisodes consécutifs dans l'historique.
- Rangée d'historique configurable sur Home avec chargement progressif.
- Rapprochement de la Home Web avec Floppy Companion grâce à cinq améliorations configurables.
- Recherche des sorties du calendrier par titre.

## Dropped
