# Data contract

`story.json` is a JSON object with `project`, `views`, `principles`, `insights`.
The bootstrap generates a complete editable example. Coordinates are native
1490x700 SVG units; nodes are 76 units high. No implicit coordinate scaling.

## Project and journeys

`project`: `name`, `themeNote` describing actual styling provenance.
`views`: nonempty map keyed by lowercase HTML-safe IDs (for example
`architecture`, `principles`, `delivery`, `learn`). Each has:

- `title`, `label` (tab/menu title), `description`, `scope`, `snapshot`,
  `stepLabel`, `repository` (owner/name), `revision` (source commit).
- `phases`: consecutive `n` starting at 1, `title`, `dates`, `summary`,
  `decisions` array, `principles` array, `commits` array, `evidence` array.
  Optional `value`, `tradeoff`, `issues`, `status`, `references`.
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

Flow: `from`, `to` component IDs, `path` using positive integer M/H/V commands,
`label`, label `x`/`y`, `detail`, optional `until`. Flows cannot precede endpoints.
TARGET handoffs must have `state: "TARGET"` for dashed styling.

## Principles and learnings

`principles`: map of IDs to `name`, `attributes`, `requirement`, `decision`,
`tradeoff`, `verification`, `scope`, `evidence`. Every phase references at least
one existing principle. Keep a reusable lens distinct from a project claim.

`insights`: `items` array, empty unless historical evidence exists.
Optional entries use `id`, `title`, `lesson`, `voiceover`, `targets` keyed by
journey, optional `availableFrom`, and `sources` as supported by the template.
Suggested narration must not be presented as a quotation or measured outcome.

## Evidence and safety

Evidence uses repository-relative file/directory paths resolved inside
`--project-root`. Generation rejects missing paths and traversal outside it.
Links use the supplied repository and revision; inspect these before publishing.
Avoid secrets, local operator identity, tenant IDs, runtime auth links and
private-session transcripts. Do not commit supplied decks or reference images.

The generator is declarative. It reads JSON and local evidence paths, then writes
only under the requested output folder. It never imports project Python code.
