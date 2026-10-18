# Upstream sync — 2026-10-17 / local integration 2026-10-18

## State

Local integration into `custom` requested by Nicolas on 2026-10-18. The tested merge preserves both histories and the fork customizations. This supersedes the earlier preparation-only/no-commit scope. No push, PR or deployment is authorized or performed. The remaining gates below apply before deployment/release; full-suite success is not claimed.

- Worktree: `.worktrees/fix-upstream-sync-2026-10-17`.
- Branch: `fix/upstream-sync-2026-10-17`, based on upstream `e56a5f669` (2026-10-16), with the resolved merge of previous `custom` `cca4cf8c3`. The integration commit is recorded in `CONTRIBUTIONS.md`.
- Previous captured upstream: `d53ff64d3` (2026-10-07). The new target contains 273 additional commits and changes 385 files. These are Git counts, not feature counts.
- Initial working directory remains on `feat/home-all-media-in-progress` `947772ca5`; only the new tracking entry in its already-modified canonical `TODO.md` was added. Its previous changes and untracked directories were preserved.

## Contributions already upstream

Verified through GitHub PR state and upstream history on 2026-10-17, refreshed on 2026-10-18 (unchanged). The remote `latest` still points to `e56a5f669`.

| Contribution | State | Handling |
| --- | --- | --- |
| [#1134 horizontal drag](https://github.com/dannyvfilms/Floppy/pull/1134) | Merged 2026-09-09 | Keep upstream implementation |
| [#1144 episode picker](https://github.com/dannyvfilms/Floppy/pull/1144) | Merged 2026-09-10 | Keep upstream implementation |
| [#1145 appearance foundation](https://github.com/dannyvfilms/Floppy/pull/1145) | Merged 2026-09-10 | Keep upstream schema/runtime outcome |
| [#1155 themes/detail layouts](https://github.com/dannyvfilms/Floppy/pull/1155) | Merged 2026-09-16 | Keep upstream implementation plus private extensions |
| [#1268 Home menus/poster actions](https://github.com/dannyvfilms/Floppy/pull/1268) | Merged 2026-09-23 | Keep upstream implementation |
| [#1245 cross-media rows](https://github.com/dannyvfilms/Floppy/pull/1245), replaced by [#1430](https://github.com/dannyvfilms/Floppy/pull/1430) | Original closed; replacement merged 2026-10-05 | Keep upstream implementation plus private row types/options |
| [#1234 instance branding](https://github.com/dannyvfilms/Floppy/pull/1234) | Open | Preserve private and published branding |

These merged contributions were already in the previous captured upstream. Historical fork commits must not be counted as independent missing features or blindly replayed over their current upstream equivalents.

## Notable upstream additions since October 7

- Manual check-in across media families, Now Playing controls, and revised tracking/Notes actions.
- Game logo/backdrop providers and galleries, with cached artwork rendered in the initial response.
- Music Recently Played modes (album, artist, track or combined), private track notes, and improved Home ordering.
- Opt-in TMDb rating delivery, PSN playtime snapshots, Playnite import and Stremio playback/library improvements.
- Optional list ranks, provider-ID API endpoints, mobile/foldable layouts, metadata-language preservation and import/history corrections.

## Integration decisions

The merge had 18 conflicted files and 62 overlapping files. Conflicts were resolved by combining upstream behavior with private extensions, rather than choosing one entire side.

Preserved: configurable Home rows/pins/episode navigation, caught-up-series filtering, Activity Journal and expandable cached episode members, History theme/readability/sidebar visibility, availability and public reviews, enriched credits, signed-out branding/theme publication, PWA and isolated interactive workers.

Integration regressions reproduced before their fixes:

1. Music mode disappeared from the Home settings round-trip when retaining the private serializer. One serializer now preserves both music mode and private row options.
2. Enabling Video caused Home settings saves to fail because the supported-filter registry lacked that existing media family. The registry now accepts its common library filters.
3. Private History timeline images still depended on a JavaScript `data-src` swap. Both timeline templates now use the native image-loading contract.

Consumers were updated for the upstream Home function signature and native portrait `src` attribute without removing the associated behavioral/position assertions. Detail action wrappers were made structurally valid without changing their conditional layout. Tailwind output was regenerated and proved stable.

## Native migrations

All previously deployed fork migrations were preserved unchanged. New upstream migration files were removed from the candidate tree; Django generated the final schema changes against the actual fork leaves:

- `app.0183_gameartwork`
- `app.0184_reconcile_tags_and_deletion_markers`
- `integrations.0039_playtimesnapshot_ratingsyncedit_tmdbaccount_and_more`
- `lists.0016_customlistitem_rank`
- `users.0153_alter_user_onboarding_step`

The data repair retains every distinct item/tag relationship and owner boundary, and deletes only deletion markers contradicted by the same owner's tracked identity. Operations use the schema editor's database alias. Tag canonicalization/merging and stale-marker cleanup have no automatic inverse; restoring their exact prior data requires the pre-upgrade backup.

Rating migration guards recognize partial unique indexes as well as table constraints. Rollback removes rating-only intents before restoring watched-only uniqueness. Existing watched intents and local scores survive the real SQLite upgrade/rollback test.

## Verification

All application runs used synthetic data, explicit test settings and a local Python bootstrap that prevents python-decouple from loading any `.env`. No production database or provider account was accessed. The venv uses the locked dependencies and Django 5.2.17; uv 0.12.3 was invoked in isolation without changing the global uv installation.

| Check | Result |
| --- | --- |
| Final Home/History/Appearance/details/reviews/availability/check-in/rating/performance regression run | 926 tests executed, OK, 2 skipped; UTF-8 mode and fast model-built DB. Explicit labels exclude the separately failing upstream ExpiryTests class; no test or assertion was changed to obtain this result. |
| Real migration graph, tag/marker repairs, rating upgrade/rollback | 8 tests passed |
| Existing-fork preferences/branding/history/tag links across real upgrade, plus graph/rating regression | 3 tests passed (two overlap the preceding group) |
| Fresh synthetic SQLite migrate | Passed |
| Django check and makemigrations --check --dry-run | Passed, no model/schema drift |
| Migration hygiene --base-ref custom --strict | Passed for all new migration work |
| Ruff, touched template lint, domain vocabulary | Passed |
| Tailwind rebuild | Passed and stable |
| OpenAPI generation with validation and fail-on-warn | Passed; generated contract matches tracked content after line-ending normalization |
| Fiches/people/credits/availability/reviews/artwork/live playback | 414 tests executed; the old portrait assertion was adapted, but variable artwork-expiry failures remain; 2 tests skipped |
| Complete fast suite | Not validated: Windows-only failures and subsequent lack of progress; interrupted, log retained |

Browser checks used the real application on loopback with a synthetic account: Home and History loaded, mobile History filters opened, the music mode appeared, and Home saved successfully with Video enabled after the fix. Save appearance persisted Nord and the text branding; after logout the public login showed NicoFlix and the published palette. At 390 px, the document width remained 390 px and the logo text fit its measured width. No browser console errors were observed. This does not replace broad cross-device or provider testing.

## Remaining gates before deployment/release

1. Run the full suite in Linux with PostgreSQL upgrade/rollback replay. Neither a local PostgreSQL runtime nor a Linux test environment was available for this preparation. The Windows run encounters POSIX-only `os.geteuid` and historical naive-date conversion errors in import scheduling; it was not declared green.
2. Investigate upstream artwork-expiry clock ordering before release. Different existing expiry tests fail between runs. A local probe shows `time.time()` and `datetime.now(UTC).timestamp()` share coarse Windows ticks with different sub-microsecond precision. Production compares the former credential-change timestamp with the latter persisted timestamp. Changing that shared invalidation protocol also affects per-user credential isolation and concurrent refreshes, so it was left explicit rather than replaced speculatively during this merge.
3. The strict migration gate against upstream/latest reports 54 raw-operation violations in older, already-deployed fork migrations. The strict gate against the deployed custom baseline passes for the new files. Rewriting deployed migration history to silence the broader gate would be unsafe; reconcile that historical gate separately.
4. No real instance data drift audit, provider/account smoke, container build or server acceptance was performed. Local integration was explicitly requested on 2026-10-18; deployment remains unauthorized. The upstream artwork implementation and its expiry tests have an empty diff against `upstream/latest`, so their Windows failures were not treated as merge regressions or silently fixed in this synchronization.

Logs remain in ignored `.codex/qa/`: `focused-final.log`, `details-final.log`, `migrations.log`, `upgrade-preservation.log`, `browser-migrate.log`, `artwork-expiry.log`, `fast-suite.log`, `integration-final.log`. Final Ruff, Django check, no-drift migration check and strict hygiene against the deployed custom baseline were rerun successfully on 2026-10-18.


## Bilan des PR — 2026-10-18

Comparaison du contenu final avec `upstream/latest` `e56a5f669`, et non décompte des anciens commits du fork. « Utile » signifie une capacité encore absente, pas une PR prête à publier : chaque tranche doit être reconstruite sur upstream actuel, testée et approuvée par Nicolas.

| Contribution | Décision | Motif / prochaine tranche utile |
| --- | --- | --- |
| UI-002 — carrousels | Aucune nouvelle PR | #1134 fusionnée. Conserver le composant upstream. |
| UI-001A — sélecteur d’épisode | Aucune nouvelle PR | #1144 fusionnée. |
| UI-001B — fondation Appearance | Aucune nouvelle PR | #1145 fusionnée. Ne pas reproposer les anciennes migrations du fork. |
| UI-001C — thèmes et layouts | Aucune nouvelle PR globale | #1155 fusionnée. Proposer seulement un complément précis encore absent. |
| UI-003 — menus Home / affiches | Aucune répétition de l’ancien correctif | #1268 fusionnée. Un éventuel nouveau bug d’affiche présente dans deux rangées est une régression distincte à reproduire sur upstream courant. |
| HOME-006 — All media / In progress | Ne pas rouvrir #1245 | Reprise dans #1430 fusionnée. Le fork garde des compléments (défaut `not_caught_up`, sélection des familles et navigation) : isoler uniquement un écart réellement reproduit avec l’implémentation actuelle. |
| UI-001D — branding | Actualiser la PR existante #1234 | Toujours ouverte. Pas de deuxième PR branding. Les compléments récents sauvegarde/publication du thème doivent être rapprochés de son contenu avant mise à jour. |
| DETAIL-001 — moyenne publique pondérée | Encore utile | `_build_aggregate_rating_context` et le détail des poids restent propres au fork. La nouvelle synchronisation de notes personnelles TMDb couvre un autre besoin. |
| DETAIL-002 — avis publics | Encore utile | Fournisseurs TMDb/BetaSeries/Hardcover, masquage des spoilers et routes/templates dédiés absents upstream. Une branche propre existe déjà : la réactualiser, pas repartir du diff complet custom. |
| DETAIL-003 — disponibilités privées | Encore utile | Présence Plex/Radarr/Sonarr et préférences correspondantes restent propres au fork ; distinguer des fournisseurs de streaming publics déjà upstream. |
| SERIES-001 — fiches/crédits/personnes | Encore utile, à découper | Âge à la sortie, œuvres connues issues de l’historique local, enrichissement saisons/épisodes et tendance des notes demeurent des ajouts. Ne pas reproposer les crédits ou portraits de base déjà upstream. |
| HISTORY-001 — épisodes consécutifs | Encore utile | Regroupement visuel conservé dans le fork, absent du rendu upstream équivalent. |
| HISTORY-002 — groupes en cache dépliables | Encore utile, dépend du regroupement | Le fork conserve les membres sérialisés, le compteur et le détail dépliable ; proposer après/avec la tranche de regroupement nécessaire. |
| HOME-008 — rangée History | Encore utile | Type de rangée et lecteur dédié absents des choix upstream. |
| HOME-009 — Companion Home | Encore utile, pas en une PR globale | Activity Journal, Shelves Resume/Stale/Unstarted/Finished et compléments History restent privés. Réutiliser les tranches ci-dessous, sans dupliquer HOME-003/004/008 et HISTORY-001/002. |
| HOME-001 — épingles de titres | Encore utile | `HomePinnedItem` et action d’épingle absents upstream. Les favoris de fournisseurs upstream ne sont pas des épingles Home. |
| HOME-002 — ouvrir l’épisode à reprendre | Encore utile | Option persistante `open_last_episode` par rangée et métadonnées de navigation restent propres au fork. |
| HOME-003 — Stale | Encore utile | Seuil configurable et sélection d’un épisode régulier diffusé non vu restent des ajouts. |
| HOME-004 — Up Next | Encore utile | Type de rangée dédié et identité `SxxExx` restent absents des choix upstream. |
| HOME-005 — rangées repliables | Seulement le branchement Home restant | Le composant `_scrollable_row.html` upstream sait déjà se replier ; le fork lui fournit une `collapse_key` par rangée Home. Ancienne réimplémentation inutile, petite activation ciblée possible. |
| PERF-001 — performances | Ancienne PR globale devenue inadaptée | La recherche `app/search_views.py` est identique upstream et Home utilise déjà l’exécuteur paginé et un ordre compact. Le fork conserve un cache d’ordre alternatif, des comptages et des cas particuliers : mesurer leur gain sur upstream actuel avant toute PR, ne pas republier l’ancienne pagination/recherche. |
| PWA-001 — installation | Pas prête | Installation signalée non fonctionnelle ; corriger et valider une installation réelle avant toute PR. |

Aucune PR créée, rouverte ou modifiée par ce bilan. Les scripts privés de publication, migrations de réconciliation du fork et réglages d’exploitation restent hors des futures PR de fonctionnalités.
