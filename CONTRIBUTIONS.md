# Contributions

Registre fork-only conservé sur `custom`. Git porte le détail technique; ce fichier porte l'état de livraison et l'accord humain. Une ligne ne passe à `Approved` qu'après un test explicite de Nicolas sur l'image indiquée.

États : `Development` → `Validated` → `On custom` → `Deployed` → `Tested` → `Approved` → `PR opened` → `Merged`. `Changes requested` revient à `Development`; `Blocked` doit nommer la cause.

| ID | Feature | Branche | Commit | Image Unraid | Validation Nicolas | PR | État / cause |
|---|---|---|---|---|---|---|---|
| UI-001 | Appearance and detail layouts | `feat/user-appearance` | `7831a40e` | `sha-17668a57` | Pending | — | Deployed — palette et éditeur corrigés; Glass Cinema ajouté; préflight vert |
| HOME-006 | Cross-media `In progress` row | `feat/home-all-media-in-progress` | — | — | Pending | — | Validated — 47 tests Home, migration `users` et Ruff validés |
| HOME-005 | Collapsible Home rows | `feat/home-collapsible-rows` | `c1aebfb9` | `sha-a9e52961` | Works | — | Tested |
| HOME-004 | `Up Next` row | `feat/home-up-next` | `2685526b` | `sha-a9e52961` | Changes requested — conserver `SxxExx` | — | Changes requested |
| HOME-003 | Stale Home row | `feat/home-stale-row` | `79267e47` | `sha-a9e52961` | Pending | — | Deployed |
| HOME-002 | Resume next-episode navigation | `feat/home-resume-navigation` | `ab710d19` | `sha-a9e52961` | Pending | — | Deployed |
| HOME-001 | Pinned Home titles | `feat/home-pins` | `6e5a1d7e` | `sha-a9e52961` | Pending | — | Deployed |

## Règles de mise à jour

- Le coordinateur met à jour la ligne au début et à chaque changement d'état.
- Le commit est le commit propre de la branche; l'image est le tag immuable réellement déployé.
- `Tested` décrit le verdict de Nicolas, jamais seulement les tests automatisés.
- `Approved` autorise uniquement la PR indiquée; aucun accord global ou implicite.
- Après merge upstream, enregistrer le lien de PR puis retirer les détails devenus inutiles du `TODO.md`.
