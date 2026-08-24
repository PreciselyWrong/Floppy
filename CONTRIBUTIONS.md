# Contributions

Registre fork-only conservé sur `custom`. Git porte le détail technique; ce fichier porte l'état de livraison et l'accord humain. Une ligne ne passe à `Approved` qu'après un test explicite de Nicolas sur l'image indiquée.

États : `Development` → `Validated` → `On custom` → `Deployed` → `Tested` → `Approved` → `PR opened` → `Merged`. `Changes requested` revient à `Development`; `Blocked` doit nommer la cause.

| ID | Feature | Branche | Commit | Image Unraid | Validation Nicolas | PR | État / cause |
|---|---|---|---|---|---|---|---|
| PERSON-001 | Enriched person credits and tracked works | `feat/home-all-media-in-progress` | `a65e2cbc` | — | Pending | — | On custom — sections configurables, tests personne et Ruff validés |
| DETAIL-002 | Enriched series and seasons | `feat/home-all-media-in-progress` | `a65e2cbc` | — | Pending | — | On custom — progression, spoilers, épisodes sautés, tests builders et Ruff validés |
| DETAIL-001 | Weighted public rating breakdown | `feat/detail-rating-aggregate` | `c479bfb2` | — | Pending | — | On custom — calcul, affichage, options, Ruff et templates validés |
| UI-001 | Appearance and detail layouts | `feat/user-appearance` | `5e75601d` | — | Pending | — | On custom — logo agrandi et réglages déplacés dans Appearance; 32 tests fusionnés et Ruff verts |
| HOME-008 | Configurable Home history row | `feat/home-history-row` | — | — | Pending | — | Validated — chargement progressif par lots de 14, 49 tests Home, migration `users` et Ruff validés |
| HISTORY-001 | Consecutive episode grouping | `feat/history-consecutive` | — | — | Pending | — | Validated — regroupement par série et saison, 28 tests History et Ruff validés |
| HOME-006 | Cross-media `In progress` row | `feat/home-all-media-ready` | `971877ff` | `sha-c112032af379cc542a7392658609d9ee3f191fb6` | Pending | — | Deployed — 82 tests ciblés, migration de fusion et Ruff validés |
| SERIES-001 | Series, seasons, credits and person details | `feat/home-all-media-in-progress` | `c112032a` | `sha-c112032af379cc542a7392658609d9ee3f191fb6` | Pending | — | Deployed — 82 tests ciblés, migrations, contrôle Django et Ruff validés |
| HOME-005 | Collapsible Home rows | `feat/home-collapsible-rows` | `c1aebfb9` | `sha-a9e52961` | Works | — | Tested |
| HOME-004 | `Up Next` row | `feat/home-up-next` | `2685526b` | `sha-a9e52961` | Pending | — | Validated — `SxxExx` conservé pour l’épisode connu; 45 tests Home validés |
| HOME-003 | Stale Home row | `feat/home-stale-row` | `79267e47` | `sha-a9e52961` | Pending | — | Deployed |
| HOME-002 | Resume next-episode navigation | `feat/home-resume-navigation` | `ab710d19` | `sha-a9e52961` | Pending | — | Deployed |
| HOME-001 | Pinned Home titles | `feat/home-pins` | `6e5a1d7e` | `sha-a9e52961` | Pending | — | Deployed |

## Règles de mise à jour

- Le coordinateur met à jour la ligne au début et à chaque changement d'état.
- Le commit est le commit propre de la branche; l'image est le tag immuable réellement déployé.
- `Tested` décrit le verdict de Nicolas, jamais seulement les tests automatisés.
- `Approved` autorise uniquement la PR indiquée; aucun accord global ou implicite.
- Après merge upstream, enregistrer le lien de PR puis retirer les détails devenus inutiles du `TODO.md`.
