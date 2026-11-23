# Official service icons

Icons are optional assets, separate from themes, geometry and implementation
states. No approval means no icon download or automatic update check.
Providers use Microsoft's official Azure, Microsoft 365 and Power Platform
pack pages, GitHub's brand-logo pack, and GitHub's Octicons UI-symbol repository.
They do not scrape image search results.
Coverage varies: some packs contain architecture symbols rather than current
product logos. Never substitute a different product or invent a missing logo.

## Consent before acquisition

Inspect the current provider terms and download source:

```powershell
python architecture\icons.py --project-root . inspect azure
```

Show the user the returned `source`, `download`, `terms` and `termsHash`.
Explain the intended architectural-diagram use and where the cache will live.
An agent must ask for approval, or use an explicitly configured approval matching
that exact terms hash. Tool access alone is not permission to accept terms.

After consent, copy the exact displayed hash into this command:

```powershell
python architecture\icons.py --project-root . approve azure --terms-hash "<termsHash>" --scope user --updates auto
```

This downloads/validates or reuses a fresh centrally cached pack and records consent for that
provider, scope and terms. It does not authorize unknown providers or future
changed terms. Microsoft permits architecture diagrams, training and
documentation; other rights are reserved. Preserve appearance/proportions and
nearby product labels. Do not recolor icons to match a theme or use them as
the plugin's own branding. GitHub logos have their own restrictive brand rules:
use permitted linking/integration contexts, not an implied endorsement,
your product's branding or an assumed blanket diagram license.

Available providers:

```powershell
python architecture\icons.py providers
```

## Device cache and scoped approvals

One device-local cache per operating-system user is shared across projects,
repository scopes and theme-library profiles. It is outside OneDrive and
the installed plugin, so changing themes or updating the plugin does not
relocate or discard packs.

| Platform | Cache |
| --- | --- |
| Windows | `%LOCALAPPDATA%\architecture-presenter\icons\cache` |
| macOS | `~/Library/Caches/architecture-presenter/icons/cache` |
| Linux | `$XDG_CACHE_HOME/architecture-presenter/icons/cache`, falling back to `~/.cache/architecture-presenter/icons/cache` |

Only selected SVGs are copied into presenters, not whole packs. A shared cache
does not grant consent: each requesting project must still have an applicable
provider/terms-hash approval. `--scope user` approves reuse across that user's
projects; `--scope project` retains project-only consent. The CLI's scope default
remains project for compatibility.

```powershell
python architecture\icons.py --project-root . storage
```

Approval precedence is project > repository > user > machine. Each provider is
a whole policy document, not a partial merge:

- Project: `<presenter>\icons\approvals\<provider>.json`.
- Repository: `.architecture-presenter\icons\approvals\<provider>.json`.
- User: `icons\approvals\<provider>.json` beneath the device-local configuration
  root (`%APPDATA%\architecture-presenter` on Windows), not the selected synced
  theme library.
- Machine: `icons\approvals\<provider>.json` beneath the machine configuration root.
- All scopes use the same per-user device cache. Machine policies do not create
  an all-users writable cache.

Theme-library profiles remain unchanged. Legacy user approvals in the selected
theme library are read after the local user approval and before machine scope.
`--user-library` selects that legacy lookup/migration profile, never the new
cache destination. No library is moved or merged. Machine approval writes need
ordinary filesystem permissions; the tool does not elevate privileges.

### Existing v1.4 caches

Approved old project/repository/profile caches can still supply assets offline
when no matching central version exists. To avoid a one-time central download,
copy a verified legacy pack deliberately:

```powershell
python architecture\icons.py --project-root . migrate azure
python architecture\icons.py --project-root . --user-library work migrate azure
```

Migration validates every copied SVG and hash, keeps original files intact,
and never copies an approval into a broader scope. It does not fetch the network.
Existing presenter locks need no migration. Cache versions are retained by
terms hash so approval under new terms cannot overwrite an older scope's
permitted version.

To preconfigure consent, first read the current terms and use their actual hash:

```json
{
  "schemaVersion": 1,
  "provider": "azure",
  "termsHash": "<exact SHA-256 from inspect>",
  "updates": "auto"
}
```

`auto` checks/downloads approved updates; `notify` checks metadata/HTTP validators
without downloading an update; `off` disables automatic checks for that policy.
Notify mode reports manual review when validators cannot establish that a pack
is unchanged. An explicit `fetch` still requires matching approved terms.

Remove one scope's approval with `revoke azure --scope user`. Use `--legacy`
to target an old library approval, for example global `--user-library work`
with `revoke azure --scope user --legacy`. Lower scopes or legacy user policies
may still approve it; inspect them too. A higher-priority policy with
`updates: "off"` disables inherited automatic monitoring without changing locks.

Do not commit whole caches, consent files or private library paths. Selected
snapshot assets and their provenance are intended for sharing as diagrams
under the applicable provider terms. Add appropriate ignore rules in consuming
projects deliberately; initialization does not edit them automatically.

## Authoring and choosing variants

Set an explicit service identifier on a component, for example:

```json
{
  "id": "functions",
  "name": "Azure Functions",
  "lines": ["Handles the request"],
  "state": "TARGET",
  "service": "azure:functions",
  "phase": 1,
  "x": 100,
  "y": 160,
  "width": 330,
  "evidence": []
}
```

Replace illustrative coordinates/state/evidence with the actual story.
Common Azure aliases include `functions`, `api-management`, `key-vault`,
`storage-account`, `aks` and `app-service`. Other IDs use normalized official
filenames. List actual available IDs and paths:

```powershell
python architecture\icons.py --project-root . list azure
python architecture\icons.py --project-root . list power-platform
```

Examples include `power-platform:dataverse` and
`power-platform:copilot-studio`. The node still needs its real product name and
truth-state label. An icon never proves implementation or deployment.

Missing/unapproved icons fall back to text with an actionable warning.
Ambiguous variants also fall back: the generator does not guess a color/style.
Ask the user which catalogue entry to use and add `icon-selections.json`
adjacent to `story.json`, mapping service IDs to exact listed archive filenames.
Selection changes require `--refresh-icons`.

### GitHub logos versus feature symbols

`github` uses [GitHub's brand guidelines](https://brand.github.com/foundations/logo)
and the linked logo ZIP. Original black/white and clear-space variants require
explicit choice when ambiguous. Follow the brand and co-branding restrictions;
do not recolor logos. Some Copilot icon files are still in the pack even though
the current guidelines deprecate standalone Copilot branding. Do not infer
permitted use from a filename.

`octicons` uses [GitHub's official UI-symbol repository](https://github.com/primer/octicons).
Common IDs use the library's 16-unit variants:

| Service ID | Meaning |
| --- | --- |
| `octicons:repo` | Repository |
| `octicons:issues` | Open issue |
| `octicons:pull-request` | Pull request |
| `octicons:actions` | Workflow glyph for an Actions workflow, not a distinct Actions logo |
| `octicons:codespaces` | Codespaces UI symbol |
| `octicons:copilot` | Copilot UI symbol, not a standalone brand logo |

Other variants are listed by exact normalized filename, such as `repo-24`.
Octicons tracks immutable official repository revisions and the license at
that same revision; unrelated source changes may produce a new archive hash.
Only its `icons` directory is acquired as SVG assets. Its MIT copyright/license
notice is retained in locks and HTML/SVG provenance. Keep those notices when
sharing or extracting assets.

Licensed UI glyphs follow the theme foreground for contrast; brand logos keep
their original colors. This distinction does not change node positions,
implementation states or the glyph's source-file hash.

## Monitoring newer releases

`init.py` and `build.py` check approved active provider policies at most once per
24 hours per device user/provider, shared across projects and profiles and
counting failed attempts too. There is no background daemon, scheduled
task, browser networking or telemetry. Checks follow the official pack link and
HTTP validators; content hashes identify versions even when the URL is reused.
Metadata discovery is shared even across different scoped approvals. A notify
check can be followed by an approved auto download using that same discovery,
without fetching the source page again.

With `auto`, unchanged terms allow proactive caching. Changed terms/guidelines
stop the new download and require renewed consent. Failed, unsafe or unavailable
updates preserve the last successful pack and all presenter snapshots.
Updates are staged under an exclusive provider lock. A stale `update.lock`
needs manual investigation; remove it only after confirming its process stopped.

```powershell
python architecture\icons.py --project-root . check azure
python architecture\icons.py --project-root . check azure --force
python architecture\icons.py --project-root . fetch azure
```

`--force` bypasses the daily interval; explicit fetch re-downloads the approved
pack without cached HTTP validators and can repair corrupted cache bytes.
It never accepts changed terms or repairs altered project snapshot files.

## Portable, pinned output

Builds copy only selected passive SVGs into `icon-assets` and record an
`icons.lock.json` with hashes, source URLs, terms and pack identity.
Existing locks remain pinned even after newer packs enter the cache.
Adding/removing services or changing explicit variant choices requires refresh:

```powershell
python architecture\build.py --input architecture\story.json --project-root . --output architecture --refresh-icons
```

For a strictly offline run, add `--offline-icons` to `init.py` or `build.py`.
Locked rebuilding needs no original cache/library, consent registry or network.
It rejects missing/changed snapshot bytes. Restore an altered snapshot file
rather than treating refresh as permission to overwrite user changes.

HTML/SVG embed images/UI glyphs and provenance. Brand icons retain original colors, scale
proportionally and share node reveal visibility, without changing node/map
coordinates. Titles have less space; keep them short and verify every reveal.
The inspector links to the official source and shows pack/terms hashes.
Excalidraw remains geometry/text-only; image export is not implemented yet.

Downloads validate official HTTPS redirects, response/archive limits, paths,
symlinks and SVG content. Active content, external resources and unsupported
SVGs are rejected. Inline UI glyphs additionally reject styles, IDs, resource
references and behavioral attributes so they cannot affect the parent diagram.
Hashes record content/provenance, not a publisher's digital signature;
inspect trusted sources and do not treat edited locks as proof.
