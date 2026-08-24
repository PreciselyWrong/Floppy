# Livraison des features du fork

## Sources de vérité

- `AGENTS.md` : règles et interdictions.
- `TODO.md` : une priorité `Now`, puis les prochains travaux.
- `CONTRIBUTIONS.md` sur `custom` : état de livraison, preuve Unraid, validation humaine et PR.
- Git : contenu technique et historique des commits.
- GitHub : discussion et état d'une PR après sa création.

## Démarrer

Depuis un worktree propre sur `custom` :

```powershell
.\scripts\feature-worktree.ps1 -Branch feat/short-name -Plan
.\scripts\feature-worktree.ps1 -Branch feat/short-name
```

Le script crée `.worktrees/feat-short-name` depuis `upstream/latest`, copie les instructions fork dans le worktree et masque cette copie du diff Git. Utiliser `fix/short-name` pour un correctif. Un agent reçoit un seul worktree et une seule feature.

Le coordinateur ajoute immédiatement une ligne `Development` à `CONTRIBUTIONS.md`. L'agent commence par confirmer sa branche, son diff vide et la vraie signature des fichiers qu'il modifiera.

## Développer

1. Écrire le test qui échoue.
2. Faire le plus petit changement qui le rend vert.
3. Valider selon le risque : test ciblé, migration, Ruff, puis suite rapide si nécessaire.
4. Ne modifier ni `custom`, ni `latest`, ni un autre worktree.
5. Après un milestone validé, vérifier l'absence de secret puis committer sans demander de confirmation supplémentaire.
6. Livrer au coordinateur : fichiers, comportement, tests, risques et commit.

Une migration part toujours du graphe de `upstream/latest`. Elle ne dépend jamais d'une autre feature non mergée. Si deux branches créent deux feuilles de même numéro, leur intégration dans `custom` reçoit une migration de fusion fork-only.

## Intégrer et tester

Le coordinateur, pas l'agent de feature :

1. Vérifie le commit et rejoue les validations.
2. Merge la branche dans `custom` sans réécrire son historique.
3. Résout uniquement sur `custom` les conflits entre features.
4. Publie l'image immuable avec `publish.ps1` après autorisation.
5. Inscrit le SHA d'image dans `CONTRIBUTIONS.md`.
6. Attend le verdict explicite de Nicolas et inscrit `Tested`, `Changes requested` ou `Approved`.

## Préparer une PR

Après `Approved`, créer une branche PR propre depuis le dernier `upstream/latest`. Cherry-pick uniquement les commits de la feature, adapter si upstream a évolué, puis rejouer les validations. Comparer le diff final à `upstream/latest`; il ne doit contenir ni tooling fork-only, ni migration de fusion `custom`, ni autre feature.

Présenter à Nicolas le titre, le résumé, les tests et le diff final. Créer la PR vers `dannyvfilms/Floppy:latest` seulement après son approbation de cette demande précise, puis enregistrer son URL dans `CONTRIBUTIONS.md`.

## Worktree mélangé

Ne jamais continuer à empiler. Inventorier les fichiers et hunks par feature, créer les worktrees propres, recopier chaque changement dans sa branche, puis vérifier que la somme des diffs isolés explique le diff initial. Garder le worktree mélangé intact jusqu'à validation des copies; aucun reset destructif ne sert de méthode de séparation.
