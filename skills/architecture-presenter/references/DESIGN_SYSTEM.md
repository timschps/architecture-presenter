# Themes, layouts, and local libraries

The engine owns evidence, diagrams, reveals, controls, and offline behavior.
Designs are versioned JSON, not executable plugins. They cannot change story
coordinates, truth states, or source evidence.

- **Theme:** semantic colors and a system-font choice.
- **Layout:** the position and reserved space of presenter chrome.
- **Appearance:** system, light, or dark, independent of layout.

## Built-ins

| Layout | Arrangement |
| --- | --- |
| `explore` | Exploration toolbar, diagram, explanation, optional detail sidebar |
| `stage` | Large diagram with explanation above |
| `stage-ribbon` | Large diagram with explanation below |

Fluent is the default theme, supporting light and dark. Exploration starts
with Explore; presentation starts with Stage Ribbon. Present changes layout,
not branding, unless an explicit `stageTheme` is configured.

## Quick start

After initialization, run the copied tools from the consuming project:

```powershell
python architecture\designs.py --project-root . list
python architecture\designs.py --project-root . new themes company
python architecture\designs.py --project-root . new layouts workshop --preset stage-ribbon
```

Edit `architecture\themes\company.json` and
`architecture\layouts\workshop.json`, then validate and select:

```powershell
python architecture\designs.py --project-root . validate
python architecture\designs.py --project-root . select --theme project:company --stage-layout project:workshop
python architecture\build.py --input architecture\story.json --project-root . --output architecture
```

Selection updates `presenter.json` and `design.lock.json`. It does not rebuild
HTML. `inspect` reports the lock's effective settings, source scopes and hashes,
and locally available paths/shadowed definitions:

```powershell
python architecture\designs.py --project-root . inspect
python architecture\designs.py --project-root . validate --kind themes --file architecture\themes\company.json
```

For a nonstandard output directory, pass `--presenter-dir` before the subcommand.
`--project-root` remains the consuming repository's evidence/configuration root.

## Synced user libraries and multiple OneDrive accounts

The user library may live in OneDrive or another local synced folder.
Only themes, preset-based layouts, and library preferences belong there.
Installed plugin caches, credentials, machine configuration, and device-local
path mappings do not.

The device-local registry is `libraries.json` in the platform's original user
configuration directory, for example
`%APPDATA%\architecture-presenter\libraries.json` on Windows. The reserved
profile `local` always means that original directory.

```json
{
  "schemaVersion": 1,
  "default": "work",
  "profiles": {
    "work": "C:\\Users\\example\\OneDrive - Organization\\Architecture Presenter",
    "personal": "C:\\Users\\example\\OneDrive\\Architecture Presenter"
  }
}
```

This registry stays on the device. Configure the same profile names with that
device's own paths on another computer. Shared repository settings contain
profile names, never these absolute mappings. See the
[registry schema](schemas/libraries.schema.json).

### Discover and register explicitly

```powershell
python architecture\designs.py libraries discover
python architecture\designs.py libraries list
```

On Windows, discovery reads all OneDrive account roots from the current user's
account configuration, then adds nonduplicate environment-variable roots.
This handles multiple work accounts that `OneDriveCommercial` alone misses.
It does not read email addresses, tenant IDs, or synced files. Other platforms
can register paths manually; available OneDrive environment roots are also
listed when present.

Discovery only lists candidates. It never registers, picks a default, copies
files, or merges libraries. Local folder access does not prove that OneDrive
is running or that synchronization has completed.

Choose a root from the list and register a library beneath it:

```powershell
python architecture\designs.py libraries add work --path "<chosen-account-root>\Architecture Presenter" --create
python architecture\designs.py libraries add personal --path "<another-account-root>\Architecture Presenter" --create
python architecture\designs.py libraries use work
```

Replace the placeholder paths with actual absolute filesystem paths.
Registration refuses existing profile names and duplicate folder mappings.
Without `--create`, the library directory must already exist. With `--create`,
only the final folder is created and its parent must exist, preventing accidental
recreation of a missing sync root. Registration alone does not change the default.

`libraries use work` explicitly sets the device default for future resolution.
Existing design locks remain unchanged. `libraries use local` returns the
default to device-local storage without deleting any mappings or designs.

### Select a profile without mixing accounts

Profile routing has separate precedence from design settings:

1. Explicit `--user-library <name>`.
2. `userLibrary` in the presenter's `presenter.json`.
3. `userLibrary` in the repository's `.architecture-presenter\config.json`.
4. The device registry's selected default, initially `local`.

Profiles replace only the **user scope**. Machine, repository, project, and
built-in scopes keep their existing precedence. Libraries are not merged:
selecting `work` does not search the personal library or the old local library
for a missing theme. `user:<id>` always refers to the selected user library.
Synced user or machine configuration cannot redirect the selected profile.

For persisted presenter selection:

```powershell
python architecture\designs.py --project-root . select --user-library work --theme user:company
```

For repository routing:

```json
{
  "schemaVersion": 1,
  "userLibrary": "work",
  "theme": "user:company"
}
```

For a one-off build or initialization, use `--user-library work` with `build.py`
or `init.py`. To list, validate, or scaffold within a different user library,
put the flag **before** the `designs.py` subcommand:

```powershell
python architecture\designs.py --user-library personal list
python architecture\designs.py --user-library work new themes company --scope user
python architecture\designs.py --user-library local validate
```

Only portable profile names and selected definitions go into the design lock,
not absolute paths or the registry. A locked rebuild and locked `inspect` work
even if the profile is unavailable or unregistered on the current device.
Explicit refresh or design overrides require the configured library to be
available. Use `list` to inspect live libraries; locked `inspect` intentionally
skips live user-library discovery.

Unknown profiles and unavailable configured folders are errors. There is no
silent fallback to another account. To deliberately use local storage for a
fresh resolution, pass `--user-library local`. For offline use, mark the chosen
OneDrive library **Always keep on this device** using OneDrive's own controls.
Cloud-only files or incomplete synchronization can still cause read errors;
this plugin cannot certify or manage sync health.

### Copy existing designs, never move them

```powershell
python architecture\designs.py libraries copy themes company --from local --to work
python architecture\designs.py libraries copy layouts workshop --from local --to work
```

Copying validates one named JSON definition, preserves the original, refuses
destination overwrites, and does not change theme/layout defaults. There is no
automatic whole-library migration. Treat a copy into OneDrive as a deliberate
sharing/synchronization choice; do not copy private work material into a personal
account without appropriate authorization.

## Configuration scopes

Highest precedence first:

1. Explicit generation CLI flags.
2. Presenter/project settings: `<presenter-folder>\presenter.json`.
3. Repository settings: `<project-root>\.architecture-presenter\config.json`.
4. User settings.
5. Machine-wide settings.
6. Package defaults.

| Platform | User library | Machine library |
| --- | --- | --- |
| Windows | `%APPDATA%\architecture-presenter` | `%PROGRAMDATA%\architecture-presenter` |
| Linux | `$XDG_CONFIG_HOME/architecture-presenter`, or `~/.config/architecture-presenter` | `/etc/architecture-presenter` |
| macOS | `~/Library/Application Support/architecture-presenter` | `/Library/Application Support/architecture-presenter` |

These user paths are the device-local default and registry location. A selected
named profile replaces the active user-library path only.

Each library has optional `config.json`, `themes`, and `layouts`. The presenter
folder uses `presenter.json` instead of `config.json`, with sibling `themes` and
`layouts`. No arbitrary ancestor-folder search is performed.

Settings merge by field. Same-ID definitions resolve as complete documents
from project, repo, user, machine, then builtin scope. A selected theme can
explicitly inherit the bundled Fluent palette; it does not inherit from a
same-name definition in another scope.

Use unqualified IDs for scope-based lookup, or `project:company`,
`repo:company`, `user:company`, `machine:company`, `builtin:fluent` to select
an exact scope. A definition's filename must match its ID. If two selected
definitions have the same ID but different contents, give them unique IDs.
Built-ins remain available unless a selected same-ID definition replaces that
ID in the snapshot.

JSON file imports are also accepted, including absolute paths. Relative paths
in configuration resolve from the declaring file's directory; CLI imports
resolve from the current working directory. Imports containing `..` are
rejected; use an absolute path instead. Library symlinks may not escape their
scope.

Create a reusable user design explicitly:

```powershell
python architecture\designs.py --project-root . new themes company --scope user
python architecture\designs.py --project-root . select --theme user:company
```

Scaffolding refuses overwrites. Machine scope requires an explicit
`--scope machine` and OS write permissions. Merely reading or selecting a
design never changes user/machine settings.

Example `presenter.json` or library `config.json`:

```json
{
  "schemaVersion": 1,
  "theme": "builtin:fluent",
  "exploreLayout": "builtin:explore",
  "stageLayout": "builtin:stage-ribbon",
  "appearance": "system"
}
```

Optional `stageTheme` selects a different theme upon entering presentation;
omit it or set it to `null` to keep the current theme. All other theme choices
are independent of layout. The library definitions themselves are not defaults:
creating a theme never selects it.

## Theme contract

```json
{
  "schemaVersion": 1,
  "id": "company",
  "label": "Company",
  "base": "fluent",
  "font": "system",
  "defaultAppearance": "light",
  "appearances": {
    "light": {
      "accent": "#005a70",
      "accent-text": "#005a70",
      "accent-soft": "#e5f4f7",
      "link": "#005a70"
    },
    "dark": {
      "accent": "#90d8e8",
      "accent-text": "#90d8e8",
      "link": "#90d8e8"
    }
  }
}
```

Supported colors are `#RRGGBB` and `#RRGGBBAA`. Fonts are `segoe`, `system`,
or `arial`. No CSS expressions, arbitrary font stacks, URLs, imports, images,
JavaScript, HTML, or external fonts are accepted.

The [theme schema](schemas/theme.schema.json) enumerates all tokens:
backgrounds, surfaces, borders, text, accent states, status colors, links,
overlay/panels, five optional responsibility accents, and ribbon colors.
Set the `plane-*` tokens separately to recolor responsibility roles. An accent
override does not implicitly recolor other semantic tokens.

With `base: fluent`, missing tokens inherit from the bundled appearance.
Without `base`, each appearance must define the complete token set. Inheritance
from another local theme is not supported. The `appearances` map declares only
the appearances the theme supports. A dark-only theme can define only `dark`.
Unsupported requested appearances resolve to `defaultAppearance`; the Design
dialog shows the effective result and disables unsupported direct selections.

All definitions require schema version 1, an ID matching
`[a-z][a-z0-9-]{0,63}`, and a label of 1-80 characters. Unknown keys fail
validation. Schema files aid editors; Python enforces the full contract,
including completeness and supported default appearance.

## Layout contract

```json
{
  "schemaVersion": 1,
  "id": "workshop",
  "label": "Workshop",
  "preset": "stage-ribbon",
  "options": {
    "titleAlign": "center",
    "captionHeight": 120,
    "explanationHeight": 120,
    "sidebarWidth": 360,
    "groupHeaders": true,
    "trackGroupTitles": true
  }
}
```

See the [layout schema](schemas/layout.schema.json). `preset` must be Explore,
Stage, or Stage Ribbon's ID. Options:

| Key | Allowed values | Default |
| --- | --- | --- |
| `titleAlign` | `left`, `center` | Center for Stage Ribbon, left otherwise |
| `captionHeight` | Integer 96-140 pixels | 108, built-in Explore uses 140 |
| `explanationHeight` | Integer 110-150 pixels | 110 |
| `sidebarWidth` | Integer 280-440 pixels | 360 |
| `groupHeaders` | Boolean | false, built-in Stage Ribbon uses true |
| `trackGroupTitles` | Boolean, keep group titles over visible group area on manual zoom | false, built-in Stage Ribbon uses true |

Explore selections require an Explore preset. Stage selections require a
Stage or Stage Ribbon preset. Layouts do not change the fixed SVG viewBox,
node positions, reveal order, or implementation-state labels. Caption and
explanation height are reserved on landscape viewports; long text scrolls
within that space instead of shrinking the map. Narrow viewports use responsive
rules. New content/designs still require screenshot and contrast verification.

## Locks, sharing, and rebuilding

Initialization copies the engine, design tools, generic template/layout CSS,
and built-in JSON definitions into a new project folder. It snapshots selected
local designs into `design.lock.json`, alongside the effective settings,
definition hashes, source scopes, and engine contract version. The lock and
generated HTML do not contain personal absolute source paths.

Ordinary builds use the lock and do not read the profile registry or user/machine
configuration. Another
person can rebuild with no copy of your local theme library. The lock contains
all built-ins plus only selected local designs, not your whole private library.
Selected designs are included in output and are not private from recipients.

Changes to `presenter.json`, or a selected definition inside the presenter
folder, require explicit refresh:

```powershell
python architecture\build.py --input architecture\story.json --project-root . --output architecture --refresh-design
```

An explicit design flag also re-resolves and replaces the lock:

```powershell
python architecture\build.py --input architecture\story.json --project-root . --output architecture --theme user:company --stage-layout stage
```

Build flags change the lock, not `presenter.json`. Use `designs.py select` for
persisted selections that should also survive a later ambient-library refresh.
Refreshing re-reads configuration and requires its referenced source designs
to exist. Normal locked rebuilding does not. Repository/user/machine library
changes do not silently change existing locked presenters.

Commit the copied engine, `presenter.json`, lock, story, and any project-local
design sources needed for future refreshes. Use scope selectors instead of
personal absolute paths in shared settings. If a repository-only library should
stay private, add `.architecture-presenter` to `.git\info\exclude` yourself;
the plugin never edits a consuming project's ignore policy.

HTML is fully offline and embeds theme/layout choices. Runtime Design controls
cannot discover additional filesystem libraries. URL keys are `theme`,
`appearance`, `layout`, `exploreLayout`, and `stageLayout`; changing a journey
or layout does not reset the theme. Unknown URL choices use embedded defaults
and show a notice. Unknown explicit build selections are errors instead.

Legacy `present`, `brand=<theme-id>` and `scoutTheme=light|dark` links remain
accepted. Legacy branding only selects an already-embedded theme. It never
imports a local library. A missing former personal theme produces a notice and
the embedded default. Existing HTML and project engine snapshots are never
rewritten by a plugin upgrade.

SVG exports embed the selected primary theme's concrete palette. `system`
exports use that theme's default appearance for deterministic output.
Excalidraw exports remain editable and theme-neutral, without presentation
chrome.

## Migration and validation

Owner-specific designs belong in local libraries, not built-in palettes. An
existing personal theme can be exported into the user library and selected
explicitly with `--theme user:<id>`. The generic Stage Ribbon preset replaces
the old branding-dependent ribbon arrangement. Use its group-header options
if desired. This is not an automatic migration of other users' installations.

Run Python and browser checks after engine changes. For custom designs:
validate JSON, generate, inspect every reveal at projector sizes and a narrow
viewport, and check light/dark contrast, label bounds, focus, manual zoom and
offline behavior. Successful syntax validation does not certify contrast or
that a particular story fits the available space.

For isolated CI or tests, set `ARCHITECTURE_PRESENTER_CONFIG_ROOT` to an
absolute temporary directory. User and machine discovery then use its `user`
and `machine` children instead of the host's libraries. Python callers can
also inject roots directly.
