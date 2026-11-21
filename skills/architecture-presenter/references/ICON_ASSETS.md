# Official service icons

Icons are optional assets, separate from themes, geometry and implementation
states. No approval means no icon download or automatic update check.
The provider catalogue currently uses Microsoft's official Azure, Microsoft 365
and Power Platform SVG pack pages. It does not scrape image search results.
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
python architecture\icons.py --project-root . approve azure --terms-hash "<termsHash>" --scope project --updates auto
```

This downloads and validates the current pack and records consent for that
provider, scope and terms. It does not authorize unknown providers or future
changed terms. Microsoft permits architecture diagrams, training and
documentation; other rights are reserved. Preserve appearance/proportions and
nearby product labels. Do not recolor icons to match a theme or use them as
the plugin's own branding.

Available providers:

```powershell
python architecture\icons.py providers
```

## Scoped approvals and cache

Approval precedence is project > repository > user > machine. Each provider is
a whole policy document, not a partial merge. Paths use the existing design
library roots:

- Project: `<presenter>\icons\approvals\<provider>.json`.
- Repository: `.architecture-presenter\icons\approvals\<provider>.json`.
- User/machine: `icons\approvals\<provider>.json` beneath that library root.
- Cache: sibling `icons\cache\<provider>` beneath the approving scope.

User scope supports named libraries with global `--user-library work` or
`--user-library local`. Account registration remains explicit; no library is
moved or merged. Machine writes require ordinary filesystem permissions; the
tool does not elevate privileges.
Existing presenters default to the user-library profile recorded in their
design lock, not a subsequently changed device default. Explicit CLI profile
selection can override that routing.

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

Remove one scope's approval with `revoke azure --scope user`. A lower scope may
still approve it; inspect those policies too. A higher-priority policy with
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

## Monitoring newer releases

`init.py` and `build.py` check approved active provider policies at most once per
24 hours, counting failed attempts too. There is no background daemon, scheduled
task, browser networking or telemetry. Checks follow the official pack link and
HTTP validators; content hashes identify versions even when the URL is reused.

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

HTML/SVG embed images and provenance. Icons retain original colors, scale
proportionally and share node reveal visibility, without changing node/map
coordinates. Titles have less space; keep them short and verify every reveal.
The inspector links to the official source and shows pack/terms hashes.
Excalidraw remains geometry/text-only; image export is not implemented yet.

Downloads validate official HTTPS redirects, response/archive limits, paths,
symlinks and SVG content. Active content, external resources and unsupported
SVGs are rejected. Hashes record content/provenance, not a digital signature
from Microsoft; inspect trusted sources and do not treat edited locks as proof.
