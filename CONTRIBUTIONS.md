# Contributions

Registre fork-only conservé sur `custom`. Git porte le détail technique; ce fichier porte l'état de livraison et l'accord humain. Une ligne ne passe à `Approved` qu'après un test explicite de Nicolas sur l'image indiquée.

États : `Development` → `Validated` → `On custom` → `Deployed` → `Tested` → `Approved` → `PR opened` → `Merged`. `Changes requested` revient à `Development`; `Blocked` doit nommer la cause.

| ID | Feature | Branche | Commit | Image Unraid | Validation Nicolas | PR | État / cause |
|---|---|---|---|---|---|---|---|
| DETAIL-001 | Weighted public rating breakdown | `feat/detail-rating-aggregate` | `c479bfb2` | `sha-39037960b0c72543ac9a62d93531f9e206aaccba` | Pending | — | Deployed — calcul, affichage, options et préflight vert |
| PWA-001 | Installable app experience | `feat/pwa-install` | `0a810b38` | `sha-2f3741c8d86dc66a0edfe8b08597d5ecb418eddf` | Pending | — | Deployed — installation Chromium, guide iOS, mode standalone et paysage; 14 tests combinés et préflight verts |
| UI-002 | Direct horizontal carousel gestures | `feat/horizontal-swipe` | `5a5b85fe` | `sha-c7b650655dc08564586be05467d0615be16f4881` | Pending | — | Deployed — Home, casting, recommandations, aperçus, statistiques et titres suivis; 224 tests ciblés et préflight verts |
| UI-001 | Appearance and detail layouts | `feat/user-appearance` | `f153d7a4` | `sha-ba463cddbc36489cdd809ba70902e4a65bbe0a28` | Pending | — | Deployed — logo centré à 0 px d'écart, typographie réglable; 41 tests combinés, Ruff et préflight verts |
| HOME-008 | Configurable Home history row | `feat/home-history-row` | — | — | Pending | — | Validated — chargement progressif par lots de 14, 49 tests Home, migration `users` et Ruff validés |
| HISTORY-001 | Consecutive episode grouping | `feat/history-consecutive` | — | — | Pending | — | Validated — regroupement par série et saison, 28 tests History et Ruff validés |
| HOME-006 | Cross-media `In progress` row | `feat/home-all-media-ready` | `971877ff` | `sha-39037960b0c72543ac9a62d93531f9e206aaccba` | Pending | — | Deployed — 82 tests ciblés, migration de fusion, Ruff et préflight vert |
| SERIES-001 | Series, seasons, credits and person details | `feat/home-all-media-in-progress` | `c112032a` | `sha-39037960b0c72543ac9a62d93531f9e206aaccba` | Pending | — | Deployed — 82 tests ciblés, migrations, Ruff et préflight vert |
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
