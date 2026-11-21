# Data contract

`story.json` is a JSON object with `project`, `views`, optional `principles`,
and optional `insights`. Omitted principles mean `{}`; omitted insights mean
`{"items": []}`. ADRs and pre-existing architecture principles are not prerequisites.
The bootstrap generates a complete editable example. Coordinates are native
1490x700 SVG units; nodes are 76 units high. No implicit coordinate scaling.

## Project and journeys

`project`: `name`, optional `themeNote` describing actual styling provenance.
Design selection belongs in `presenter.json` and `design.lock.json`, not story
geometry. See [Design system](DESIGN_SYSTEM.md).
`views`: nonempty map keyed by lowercase HTML-safe IDs (for example
`architecture`, `principles`, `delivery`, `learn`). Each has:

- `title`, `label` (tab/menu title), `description`, `scope`, `snapshot`,
  `stepLabel`, `repository` (owner/name), `revision` (source commit).
  Optional `kind`: `architecture` (default) or `conceptual`. Conceptual
  journeys may omit repository/revision together; commit or issue links still
  require both.
- `phases`: consecutive `n` starting at 1, `title`, `dates`, `summary`,
  `commits` array, `evidence` array.
  Optional `decisions` array, `principles` array, `value`, `tradeoff`, `basis`,
  `issues`, `status`, `references`. Omit or use empty arrays for absent decisions
  and principle references. Explicit references must name existing principles.
- `groups`, `components`, `flows` as below.

The first journey is the default. Do not create journeys with empty content.

## Diagram elements

All elements have unique HTML-safe `id`, reveal `phase`, optional `state` and
optional `plane` (`control`, `build`, `hosting`, `access`, `lifecycle`).
Planes only select color roles, not architectural truth. Any project can use its
own boundaries and titles. Every group has phase 1 for full-map orientation.

Group: `title`, `detail`, `x`, `y`, `width`, `height`, optional `kind`.

Component: `name`, `lines` array (up to 2 short exploration details),
`x`, `y`, `width`, `evidence` array. State is APP, SOURCE, FOUNDATION, EXTERNAL or
TARGET. The name must fit two stage lines. Match the repository to these labels,
never mark a live resource from source alone.
Optional component `service` is an explicit `azure:<id>`, `microsoft365:<id>` or
`power-platform:<id>`. It selects an approved cached icon without changing
the component's implementation state. See [Icon assets](ICON_ASSETS.md) for
consent, actual catalogue IDs, ambiguous variants and portable icon locks.

Flow: `from`, `to` component IDs, `path` using positive integer M/H/V commands,
`label`, label `x`/`y`, `detail`, optional `until`. Flows cannot precede endpoints.
TARGET handoffs must have `state: "TARGET"` for dashed styling.

## Optional conceptual journeys

Use `kind: "conceptual"` for an explanatory model, not for a deployment,
historical session replay, probability estimate or measured productivity claim.
Architecture journeys remain the default and keep their evidence/state checks.
Do not use conceptual mode to bypass truth labels for real components.

Conceptual nodes require `state: "ILLUSTRATIVE"`. Implementation states such
as APP or TARGET are rejected in this mode; ILLUSTRATIVE is rejected in
architecture mode. Conceptual groups/flows may omit state or use ILLUSTRATIVE.
The footer always identifies the journey as a conceptual illustration.

Conceptual-only fields:

- Flow `alternative`: optional boolean. `true` draws a faint dashed
  hypothetical path, not another execution.
- Phase `emphasis`: optional array of active element IDs to highlight,
  independently of when those elements were introduced.
- Phase `trace`: optional `{"flow": "run-path", "progress": 0.5}`. The flow
  must be active and not an alternative; progress is a number from 0 to 1.
  The dot follows that route and reveals its solid prefix. Lower progress
  can illustrate backtracking. Moving between routes starts at the new
  route's beginning, never a straight-line shortcut across the map.

Navigation changes the illustrative dot, not the full-map camera.
Deep links start at the selected step. Normal motion interpolates within
the route; reduced motion shows the authored state immediately.
SVG exports show the final step and dot. Excalidraw exports retain editable
diagram geometry and dashed alternatives, not animation or playback state.

Create the optional five-scenario example explicitly:

```powershell
python <skill-root>\scripts\init.py --project-root . --folder agent-journey --example branching
python agent-journey\build.py --input agent-journey\story.json --project-root . --output agent-journey
```

It covers possible outcomes, backtracking, patching forward, live steering,
and foundations before execution. Each scenario is an independent journey.
Without `--example branching`, initialization still creates the original
architecture starter. The example needs no video tools, private presentation,
personal theme, ADRs or original author's session database. Its complete
story is copied as JSON for offline rebuilding.

Keep the distinction explicit: instructions guide, permissions can block
prohibited actions, checks reject unacceptable results, and humans handle
exceptions. Valid alternative designs remain possible. These mechanisms do
not guarantee correctness, remove review, or establish the shortest completion
time.

## Principles and learnings

`principles`: optional map of IDs to `name`, `attributes`, `requirement`,
`decision`, `tradeoff`, `verification`, `scope`, `evidence`, optional `basis`.
No phase is required to reference a principle. Keep a reusable analytical lens
distinct from an approved project principle.

`basis` on a principle or phase describes its commentary:

| Value | Meaning |
| --- | --- |
| `documented` | Recorded rationale, cite the decision/principle source in evidence |
| `observed` | What source/config/tests show, not evidence of original intent |
| `inferred` | An explicitly inferred explanation, not a recorded decision |
| `proposed` | A suggested lens or proposal, not an approved principle |

Omitted basis displays "Basis not recorded", preserving legacy stories without
claiming approval. A phase basis labels its ribbon context; otherwise that
context uses its first principle's basis. Inspector principle entries retain
their own basis and decision entries use the phase's basis.
Basis is author-supplied. The generator validates its value and local evidence
paths, not whether a cited source actually records a decision or its motivation.
Verify that distinction before choosing `documented`.

With no referenced principle, explicit `decisions`, `value`, or `tradeoff` can
provide standalone decision context. Omit all of them for an architecture-only
reveal. `summary` and component evidence remain available without inventing
requirements, trade-offs, ADRs, or organizational principles.

For example, an architecture-only phase can be:

```json
{
  "n": 1,
  "title": "Request entry point",
  "dates": "Source snapshot",
  "summary": "The handler accepts a request and passes it to the worker.",
  "commits": [],
  "evidence": ["src/handler.py", "src/worker.py"]
}
```

Replace these example paths with actual project evidence. If useful, add
`"decisions": ["Separating acceptance from execution may simplify retries."]`
and `"basis": "inferred"` as an explicitly analytical explanation, not a claim
that a historical decision was recorded.

A journey without commentary has no ribbon or reserved ribbon space, with the
implementation-state key in the footer. Mixed journeys reserve stable space
across reveals; empty reveals have an invisible, inert commentary slot, not
fabricated text. Journey or explicit layout changes may resize the map, but
advancing reveals must not.

`insights`: `items` array, empty unless historical evidence exists.
Optional entries use `id`, `title`, `lesson`, `voiceover`, `targets` keyed by
journey, optional `availableFrom`, and `sources` as supported by the template.
Suggested narration must not be presented as a quotation or measured outcome.
If no historical evidence is available, omit insights rather than synthesizing
lessons. Reading source alone does not establish historical motivation.

## Evidence and safety

Evidence uses repository-relative file/directory paths resolved inside
`--project-root`. Generation rejects missing paths and traversal outside it.
Links use the supplied repository and revision; inspect these before publishing.
Avoid secrets, local operator identity, tenant IDs, runtime auth links and
private-session transcripts. Do not commit supplied decks or reference images.

The generator is declarative. It reads JSON and local evidence paths, then writes
only under the requested output folder. It never imports project Python code.
