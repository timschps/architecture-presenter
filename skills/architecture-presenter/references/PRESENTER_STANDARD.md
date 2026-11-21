# Presenter standard

## Audience orientation

Keep the entire responsibility map visible from the first reveal, with a fixed
camera and stable screen coordinates. Reveal components and connectors in place,
highlighting the addition rather than flying the camera. Manual inspection may
zoom; the next/previous reveal returns to overview. Keep the ribbon height stable
at landscape/projector sizes. Never let a longer caption rescale the diagram.
Scale stage titles, ribbon text and status keys with viewport height. Keep
stage copy concise enough to fit the reserved spaces at every reveal; revise
the wording rather than shrinking text or hiding overflow.

## Tangibility and truth

Name concrete technologies, source modules, artifacts and identities. Explain
what crosses each boundary and who authorizes it. Distinguish:

- APP: implemented application, deployment claims qualified by dated evidence.
- SOURCE: implemented source contract/handler, not enabled end-to-end execution.
- FOUNDATION: recorded provisioned resources, not workload or data-plane proof.
- EXTERNAL: another builder/system's responsibility, not this project's service.
- TARGET: uncommissioned/proposed capability, dashed and explicitly labelled.

Do not claim measured SLOs, WAF certification, isolation, provenance, execution,
cost savings, or release approval from code or templates alone.
Principles are causal chains, not decorative labels:
requirement -> decision -> value -> trade-off -> verification -> evidence limit.
They are optional. A project without ADRs or declared principles can be shown
using source evidence alone. Label documented rationale, source observations,
inferences and proposed lenses distinctly. Never turn a source observation into
a claim about recorded intent, approval, or historical lessons.

Omit absent decision commentary. A commentary-free journey has no ribbon.
Mixed journeys keep a stable reserved slot, invisible and unfocusable on
reveals without commentary. Keep implementation-state labels and source
inspection available regardless of rationale coverage.

Conceptual journeys are explicitly optional, not evidence of real execution.
Use ILLUSTRATIVE node labels and a persistent conceptual notice, not APP,
FOUNDATION or TARGET deployment labels. Dashed alternatives represent
possibilities; one dot shows an illustrative path. Animation may move or
rewind the dot but must not zoom or rescale the map. Respect reduced motion.
Instructions guide, permissions can block, checks verify and humans decide;
do not imply guaranteed correctness or measured time savings.

## Visuals

Microsoft Fluent is the default theme in exploration and presentation.
Explore, Stage and Stage Ribbon are independent layout presets. Appearance is
system, light or dark, constrained by the selected theme's supported variants.
Use semantic `var(--cp-*)` colors and system-font choices in component CSS;
palette literals belong in validated JSON theme definitions.
Personal/event themes belong in local libraries, never hard-coded engine branches.
See [Design system](DESIGN_SYSTEM.md) for resolution and portable snapshots.
Optional [official icons](ICON_ASSETS.md) preserve provider colors and aspect
ratio, nearby service names and text state labels. Reserve icon/title space
without moving nodes between reveals. Download/update consent is separate
from theme selection; browser output stays offline and snapshots stay pinned.

A supplied current deck can inform an explicitly selected local theme after
actual inspection. Never claim exact alignment from an inaccessible URL.
Keep controls and calibration out of the audience diagram, with optional evidence.
Do not use a dashboard card grid in place of a directional architecture diagram.

## Operation and verification

No server, CDN, remote fonts or file-URL fetches. Inline data, diagrams and styles.
Escape embedded text, including script terminators. Links open only on demand.
No automatic telemetry, paid calls, cloud mutation, publishing or deployment.

Next: Right/PageDown/Space. Previous: Left/PageUp. Ignore held-key repeats and
editable controls. M: journeys, C: context, F: fullscreen, B: blackout,
0: overview, +/-: zoom. Provide calibration and explicit start/end notices.

Verify every journey at 1280x720, 1920x1080 and 3840x2160 with identical
screen coordinates and scale across reveals, readable stage typography and no
caption or ribbon overflow, plus narrow viewports, supported appearances, focus
and offline operation. Actual display size, viewing distance and clicker
hardware require a separate in-room rehearsal.
