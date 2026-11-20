---
name: architecture-presenter
description: >
  Build evidence-backed offline architecture presenters with fixed-overview reveals,
  concrete components and handoffs, optional NFR principles, and source/target state labels.
  Use this skill whenever the user asks for an architecture build-up, architecture
  presenter, interactive architecture walkthrough, project architecture visualization,
  or standard presenter experience across projects, even without naming the skill.
  Also use for independent delivery and engineering-learning journeys in that presenter.
  Use its optional conceptual branching example to explain agent steering and foundations.
  Not for generic dashboards, application UI redesigns or editing PowerPoint decks.
---

# Architecture Presenter

Build a tangible explanation of the current project, not a generic service diagram.
This plugin owns the presenter implementation. A generic HTML skill may supply
broader visual guidance, but must not generate a competing presenter engine.

## Prerequisites

- Read access to the project and any supplied evidence. No MCP or auth required.
- Python 3.10+ for generation, Node.js and Playwright for browser checks.
- Edge on Windows or an installed Playwright Chromium browser.
- For a supplied PowerPoint, invoke the PPTX skill first. Treat it as read-only.
  If unavailable, explain the access limit and use Fluent provisionally.

## Workflow

1. Establish audience and source boundaries. Inspect current source, infrastructure,
   workflows, ADRs and relevant prior decisions. Distinguish source implementation,
   recorded deployment, active execution and uncommissioned target states.
   Never infer that a template, test or resource deployment proves a live data path.
2. Plan 2-3 concrete stories as needed: architecture, delivery and engineering
   learnings. Do not force all projects into the five-plane agent-platform map.
   Use the actual project's responsibility boundaries, components and handoffs.
   Each story must be understandable without advancing through another.
3. Bootstrap only into a new project-local folder:
   `python <skill-root>\scripts\init.py --project-root <project> --name "<title>"`.
   The command refuses an existing output folder. For an existing presenter,
   read and update its sources without overwriting user work.
   For an explicitly requested agent-steering illustration, add
   `--example branching --folder agent-journey`. This produces five independent
   conceptual scenarios, not a default addition to every architecture story.
   Keep `kind: "conceptual"` and ILLUSTRATIVE node labels. Do not invent
   deployment state, historical execution, measured productivity or outcome
   probabilities. It is a narrative type, not a theme or a second engine.
4. Replace synthetic `story.json` with project-specific content using
   [Data contract](references/DATA_CONTRACT.md). Use short concrete stage labels,
   source files per component, exact artifact/identity handoffs, and deliberate
   reveal order. All boundaries start at reveal 1; endpoints precede their flows.
   Principles and ADRs are optional inputs, not prerequisites. Use documented
   decisions/principles when available and cite their evidence. Source/config/
   tests establish what exists, not why it was chosen. Never invent motivation
   or approved organizational principles to fill the presenter.
   Add principle commentary only when useful, with requirement, quality
   attributes, decision, trade-off, verification and evidence limit. Set
   `basis` to documented, observed, inferred or proposed as appropriate;
   explicitly label inferred explanations and suggested lenses. Omit absent
   principles/decisions or use empty collections. With no commentary, the
   renderer shows architecture and evidence without a forced ribbon.
   Keep historical insights empty unless supported by evidence.
   For conceptual stories, retain the hypothetical framing and distinguish
   guiding instructions, enforced permissions, verification and human
   decisions. Use validated `emphasis` and `trace` fields for manual reveals
   and the illustrative cursor; never infer actual session telemetry.
5. Follow the [Design system](references/DESIGN_SYSTEM.md) for styling. Keep
   theme, layout and light/dark appearance separate. Default to Fluent with
   Explore and Stage Ribbon; never infer or force a personal/event theme.
   Inspect available designs with `python <skill-root>\scripts\designs.py
   --project-root <project> list`. Use explicit selection for local themes.
   Designs may live at presenter, repository, user or machine scope. Use
   declarative JSON tokens and preset-based layouts, not custom engine/CSS forks.
   Preserve `presenter.json` and `design.lock.json` for offline portability.
   Selected local styling is embedded and shared in the generated output.
   For synced user libraries, run `designs.py libraries discover` to list
   configured roots without inspecting synced content. Never choose the first
   OneDrive environment variable automatically. Ask which profile to register
   or make default; retain device-local paths in `libraries.json`, not shared
   repository settings. Use portable `userLibrary` profile names for explicit
   repo/project overrides. Do not merge libraries or move existing designs.
   Locked rebuilds do not require the original library/profile to be available.
   Apply [Presenter standard](references/PRESENTER_STANDARD.md). Preserve the
   fixed full-map camera: no initial auto-zoom and no progressive zoom-out.
   Reserve stable caption/ribbon space so text wrapping cannot rescale the map.
   Show text state labels, never color alone. Zoom is explicit only.
6. Generate with the copied engine (substitute the chosen folder when different):
   `python architecture\build.py --input architecture\story.json --project-root <project> --output architecture`.
   Generation rejects missing local evidence and invalid reveal/flow bindings.
   It does not run code, publish, merge, deploy, grant access or contact a service.
7. Verify every reveal offline at 1920x1080 and 1280x720, then a narrow viewport,
   plus supported theme appearances and layouts. Use the plugin's `tests\verify.cjs` with the generated
   HTML path, or adapt its checks without weakening fixed-position assertions.
   Check label bounds, hidden-item focus, source links, manual inspection/zoom,
   navigation, invalid query params, blackout and calibration. Inspect screenshots
   for clipping, connectors through words and insufficient contrast. Fix and rerun.
8. Deliver the HTML path and concise changes. Preserve source, generator, theme,
   design lock, tools, layouts, SVG and Excalidraw companions in the project.
   Follow its issue/PR convention.
   No merge/deploy or PowerPoint mutation unless separately requested.

## Output

`architecture\presenter.html` is the offline stage entry.
`architecture\architecture-evolution.html` is exploration.
`story.json`, `build.py`, `design_config.py`, `designs.py`, `user_libraries.py`, the template,
`layouts.css`, built-in JSON designs, `presenter.json` and `design.lock.json`
are the regeneration sources. A normal rebuild uses the lock. Explicit design
overrides or `--refresh-design` re-resolve libraries; do not silently refresh.
SVG and Excalidraw exports accompany each independent journey.

## Error handling

| Condition | Required response |
|-----------|-------------------|
| Output directory exists | Inspect and edit intentionally; never force overwrite. |
| Missing or inaccessible evidence | State the gap and stop generation until references are corrected. |
| Live state unknown | Label source/target or recorded foundation, not verified live. |
| Supplied deck inaccessible | Mark styling provisional; do not claim inspected alignment. |
| Missing browser dependency | Restore the existing manifest or use an available installation; do not claim browser verification. |
| Invalid/missing selected design | Report the configuration error; do not silently replace an explicit build choice. |
| Stale project design lock | Explain the changed input and request an intentional `--refresh-design` rebuild. |
| Unknown/unavailable user library | Report the profile/path and restore availability or explicitly choose `--user-library local`; never silently use another account. |
| Fullscreen denied | Keep windowed mode and show the engine's visible error. |
| New project differs from starter | Replace the map, never relabel the example as verified architecture. |

## Post-Run Reflection

Check against [Presenter standard](references/PRESENTER_STANDARD.md).
Record project-specific decisions in that project. Improve this canonical plugin
only for reusable, verified behavior, with regression cases and reviewed changes.
Do not silently edit cached installed copies or global theme files.

## References

| Reference | Load when |
|-----------|-----------|
| [Data contract](references/DATA_CONTRACT.md) | Authoring or validating content |
| [Presenter standard](references/PRESENTER_STANDARD.md) | Every presenter build or update |
| [Design system](references/DESIGN_SYSTEM.md) | Selecting, authoring, or migrating themes/layouts |
