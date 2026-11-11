---
name: architecture-presenter
description: >
  Build evidence-backed offline architecture presenters with fixed-overview reveals,
  concrete components and handoffs, NFR principles, and source/target state labels.
  Use this skill whenever the user asks for an architecture build-up, architecture
  presenter, interactive architecture walkthrough, project architecture visualization,
  or standard presenter experience across projects, even without naming the skill.
  Also use for independent delivery and engineering-learning journeys in that presenter.
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
  If unavailable, explain the access limit and use the included theme provisionally.

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
4. Replace synthetic `story.json` with project-specific content using
   [Data contract](references/DATA_CONTRACT.md). Use short concrete stage labels,
   source files per component, exact artifact/identity handoffs, and deliberate
   reveal order. All boundaries start at reveal 1; endpoints precede their flows.
   Add principles with requirement, quality attributes, decision, value,
   trade-off, verification and evidence limit. Do not invent historical lessons.
5. Apply [Presenter standard](references/PRESENTER_STANDARD.md). Preserve the
   fixed full-map camera: no initial auto-zoom and no progressive zoom-out.
   Reserve stable caption/ribbon space so text wrapping cannot rescale the map.
   Show text state labels, never color alone. Zoom is explicit only.
6. Generate with the copied engine:
   `python architecture\build.py --input architecture\story.json --project-root <project> --output architecture`.
   Generation rejects missing local evidence and invalid reveal/flow bindings.
   It does not run code, publish, merge, deploy, grant access or contact a service.
7. Verify every reveal offline at 1920x1080 and 1280x720, then a narrow viewport,
   plus Fluent light/dark. Use the plugin's `tests\verify.cjs` with the generated
   HTML path, or adapt its checks without weakening fixed-position assertions.
   Check label bounds, hidden-item focus, source links, manual inspection/zoom,
   navigation, invalid query params, blackout and calibration. Inspect screenshots
   for clipping, connectors through words and insufficient contrast. Fix and rerun.
8. Deliver the HTML path and concise changes. Preserve source, generator, theme,
   SVG and Excalidraw companions in the project. Follow its issue/PR convention.
   No merge/deploy or PowerPoint mutation unless separately requested.

## Output

`architecture\presenter.html` is the offline stage entry.
`architecture\architecture-evolution.html` is exploration.
`story.json`, `build.py`, the template and theme are the regeneration sources.
SVG and Excalidraw exports accompany each independent journey.

## Error handling

| Condition | Required response |
|-----------|-------------------|
| Output directory exists | Inspect and edit intentionally; never force overwrite. |
| Missing or inaccessible evidence | State the gap and stop generation until references are corrected. |
| Live state unknown | Label source/target or recorded foundation, not verified live. |
| Supplied deck inaccessible | Mark styling provisional; do not claim inspected alignment. |
| Missing browser dependency | Restore the existing manifest or use an available installation; do not claim browser verification. |
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
