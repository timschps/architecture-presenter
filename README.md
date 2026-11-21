# Architecture Presenter

A portable Copilot CLI plugin for evidence-backed architecture build-ups.
It carries the presenter engine, not any project's architecture or cloud access.

```powershell
copilot plugin install timschps/architecture-presenter
```

To update an existing installation from this repository:

```powershell
copilot plugin update architecture-presenter
copilot plugin list
```

Updating the plugin preserves local theme libraries and existing project
snapshots. Use the updated skill in a new session when creating a new presenter.

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
- Optional decision/principle context distinguishes documented rationale,
  observations, inferences, and suggestions, without inventing missing ADRs.
- Implemented, foundation, external and target states remain explicit.
- Microsoft Fluent by default, with independent theme, layout and appearance choices.
- Viewport-scaled stage typography with stable caption and ribbon space.
- Manual-only zoom, contextual evidence, clicker controls, blackout and fullscreen.
- Offline HTML plus SVG and editable Excalidraw companions.

No ADRs or declared principles are required. Omit absent rationale and show
the architecture with source evidence alone. Commentary-free journeys have
no ribbon; mixed journeys keep the map stable while commentary appears or
disappears. See the [content contract](skills/architecture-presenter/references/DATA_CONTRACT.md#principles-and-learnings)
for basis labels and optional fields.

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

### Optional agent-steering illustration

Explain the branching metaphor as five independent conceptual journeys:
possible outcomes, backtracking, patching forward, live steering, and
foundations before execution.

Ask the agent:

> Create the optional conceptual agent-steering branching example in agent-journey, using the architecture-presenter plugin.

```powershell
python <installed-skill>\scripts\init.py --project-root . --folder agent-journey --example branching
python agent-journey\build.py --input agent-journey\story.json --project-root . --output agent-journey
```

Open `agent-journey\presenter.html`. Next/Previous moves an illustrative dot
along the chosen path, including backtracking, while the map stays fixed.
Reduced motion shows each step immediately. The example uses your selected
theme and the same controls, inspector and offline engine, without video
dependencies or bundled event branding.

This is an optional narrative type, **not a recorded session or productivity
benchmark**. Default initialization still creates the architecture starter.
See [conceptual journeys](skills/architecture-presenter/references/DATA_CONTRACT.md#optional-conceptual-journeys)
for authoring fields and truth boundaries.

### Local designs and portable snapshots

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

## Optional official service icons

Declare an explicit component `service`, such as `azure:functions` or
`power-platform:dataverse`. The plugin uses official Azure, Microsoft 365 and
Power Platform packs, never image search. Coverage varies; missing/ambiguous
matches retain text labels until explicitly resolved.

Icon acquisition requires provider-specific consent:

```powershell
python architecture\icons.py --project-root . inspect azure
# Read the source and terms, then approve their exact displayed hash:
python architecture\icons.py --project-root . approve azure --terms-hash "<termsHash>" --scope user --updates auto
python architecture\build.py --input architecture\story.json --project-root . --output architecture --refresh-icons
```

Approved `auto` policies check during initialization/building, at most once per
24 hours, and proactively cache newer packs under unchanged terms. Changed
terms require renewed approval. No scheduler or background daemon is installed.
Add `--offline-icons` for a strictly offline tool run.

Selected images, sources/terms and content hashes are pinned in
`icons.lock.json` and `icon-assets`. Cache updates do not rewrite existing
presenters; `--refresh-icons` is intentional. HTML/SVG remain offline and
preserve original icon colors and fixed map coordinates. Excalidraw currently
exports geometry/text without images.

See [Icon assets](skills/architecture-presenter/references/ICON_ASSETS.md)
for consent, scoped/named libraries, variants, safe downloads and update controls.
Upgrading an engine snapshot also requires the new `icons.py` helper.

## Validation

```powershell
python -m unittest discover -s tests -v
npm ci --ignore-scripts
npm test
```

Browser tests need Microsoft Edge on Windows, or Playwright Chromium installed
with `npx playwright install chromium` elsewhere. They open generated files
offline and verify stable screen coordinates, stage text and overflow at 720p,
1080p and 4K, reveals, manual zoom, escaping, source links, navigation, blackout
and narrow viewports. Conceptual checks cover authored path prefixes,
backtracking, rapid-navigation cancellation and reduced motion.
To verify a generated presenter with the same checks:

```powershell
npm test -- agent-journey\presenter.html
```

Check actual viewing distance and display readability in
the room; simulated keys do not replace actual clicker rehearsal.

Optional consent-gated icon acquisition contacts official Microsoft sources;
generated presenters never fetch icons at runtime.
This plugin has no hooks, agents, MCP servers, telemetry or automatic deployment.
It is an independent reusable implementation, not a Microsoft-endorsed product.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR.
`main` requires an up-to-date PR, passing `verify` CI and resolved conversations.
Contributions require maintainer approval; admins may bypass only the review
layer for their own PRs, not CI. Squash merges keep history linear, and force
pushes/deletion of `main` are blocked.

Use the issue and PR templates and synthetic examples. Report vulnerabilities
privately through [SECURITY.md](SECURITY.md), never in public issues.

The engine was generalized from the owner's architecture-presenter work in
Superagents, which in turn used the owner's AIDC presenter foundation. Only
reusable controls/rendering and extracted theme tokens were copied; source
projects and supplied presentation files are not moved or changed.
