# Architecture Presenter

A portable Copilot CLI plugin for evidence-backed architecture build-ups.
It carries the presenter engine, not any project's architecture or cloud access.

```powershell
copilot plugin install timschps/architecture-presenter
```

In a new session, ask:

> Create an architecture presenter for this project using the fixed-overview standard.

Or:

> Build independent architecture, delivery and engineering-learnings journeys, with NFR principles and source evidence.

The skill inspects the current project, replaces starter content with verified
components and handoffs, and generates a standalone `architecture\presenter.html`.
No server, CDN, runtime MCP, cloud credentials or PowerPoint installation is
required to generate or present it.

## Standard

- Fixed camera and stable component positions through reveals.
- Responsibility boundaries visible from the first reveal.
- Concrete components and typed artifact/data/identity handoffs.
- Principle, value, trade-off and evidence limits accompany each reveal.
- Implemented, foundation, external and target states remain explicit.
- Microsoft Fluent by default, with independent theme, layout and appearance choices.
- Manual-only zoom, contextual evidence, clicker controls, blackout and fullscreen.
- Offline HTML plus SVG and editable Excalidraw companions.

Choose Explore, Stage, or Stage Ribbon independently of branding. Define local
JSON themes and preset-based layouts at project, repository, user, or machine
scope, without forking the engine. Personal/event branding is not bundled.
See the [design system guide](skills/architecture-presenter/references/DESIGN_SYSTEM.md)
for precedence, authoring, validation, and migration.

## Project-local generation

The skill's bootstrap copies the reusable engine and starter into a project.
Existing output directories are refused, never overwritten.

```powershell
python <installed-skill>\scripts\init.py --project-root . --name "Project architecture"
python architecture\build.py --input architecture\story.json --project-root . --output architecture
```

For a reusable local theme:

```powershell
python architecture\designs.py --project-root . new themes company --scope user
# Edit the reported JSON path, then:
python architecture\designs.py --project-root . select --theme user:company
python architecture\build.py --input architecture\story.json --project-root . --output architecture
```

The Design dialog selects embedded themes, appearance, and layouts. Present
does not force event branding. `design.lock.json` snapshots selected definitions
so recipients can rebuild offline without your local libraries. Only selected
local designs are shared; a library's unselected themes are not copied.

User libraries can also live in OneDrive or another synced folder. Named
profiles map portable names such as `work` and `personal` to device-local
paths. Account discovery never chooses or merges accounts automatically:

```powershell
python architecture\designs.py libraries discover
python architecture\designs.py libraries list
```

See [synced user libraries](skills/architecture-presenter/references/DESIGN_SYSTEM.md#synced-user-libraries-and-multiple-onedrive-accounts)
for registration, explicit default selection, repository overrides, and
copying existing designs without moving the originals.

The engine accepts JSON, not executable project plugins. The starter explicitly
uses synthetic target components and is not an architecture assessment.
Replace it with project evidence before delivery. Read the skill's
[data contract](skills/architecture-presenter/references/DATA_CONTRACT.md).

Updates to the installed plugin do not silently rewrite project-local snapshots.
Review engine/design changes before copying them into an existing project.
New snapshots include `design_config.py`, `designs.py`, `user_libraries.py`, `layouts.css`, `themes`,
`layouts`, `presenter.json`, and `design.lock.json`; copying only `build.py`
is not an engine upgrade. Changes to selected project design sources require
`--refresh-design`. Old generated pages remain unchanged.

## Validation

```powershell
python -m unittest discover -s tests -v
npm ci
npm test
```

Browser tests need Microsoft Edge on Windows, or Playwright Chromium installed
with `npx playwright install chromium` elsewhere. They open generated files
offline and verify stable screen coordinates, reveals, manual zoom, escaping,
source links, navigation, blackout and multiple viewports. Simulated keys do
not replace actual clicker rehearsal.

This plugin has no hooks, agents, MCP servers, telemetry or automatic deployment.
It is a private reusable implementation, not a Microsoft-endorsed product.

The engine was generalized from the owner's architecture-presenter work in
Superagents, which in turn used the owner's AIDC presenter foundation. Only
reusable controls/rendering and extracted theme tokens were copied; source
projects and supplied presentation files are not moved or changed.
