# TODO

## Now

- [ ] Committer, intégrer dans `custom`, puis déployer et tester la section configurable `All media` avec sa rangée `In progress` transversale.
  - Validation locale terminée : 50 tests Home, Ruff, contrôle Django et génération Tailwind stable.
  - Inclure uniquement la migration 0128; la migration 0129 appartient à l’autre feature active dans ce worktree partagé.

## Next

- [ ] Améliorer les performances générales, actuellement trop lentes.
  - Mesurer les parcours Home, recherche, fiches et synchronisation avant chaque optimisation.
  - Réduire les requêtes, les appels externes et les chargements inutiles sans dégrader les fonctions visibles.
  - Ajouter des seuils de temps et des tests de non-régression pour les parcours principaux.
- [ ] Ajouter les avis publics TMDB, BetaSeries et Hardcover.
  - Respecter le périmètre exact de chaque fournisseur et isoler leurs pannes.
  - Fournir l’aperçu de deux avis et l’écran complet avec ses quatre tris.
  - Rendre l’aperçu visible, masquable et ordonnable dans les options.
  - Vérifier liste vide, panne, limites, réponses BetaSeries et critiques trop courtes.
- [ ] Ajouter les disponibilités Plex, Radarr et Sonarr aux fiches.
  - Ne jamais exposer de secret ni lancer d’inventaire lourd à l’ouverture.
  - Séparer présence Plex, présence serveur et recherche manuelle.
  - Rendre chaque intégration et section paramétrable dans les options.
  - Détailler la disponibilité par saison et ouvrir directement la fiche Plex quand sa clé est connue.
  - Vérifier liens directs, replis, absences, délais et erreurs partielles.
- [ ] Ajouter la barre d’actions persistante et les actions propres à chaque média.
  - Masquer les actions invalides sur les épisodes.
  - Prévoir les actions dédiées aux livres.
  - Rendre la barre et ses actions facultatives dans les options.
  - Vérifier les transitions de statut et la restauration après refus.

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
