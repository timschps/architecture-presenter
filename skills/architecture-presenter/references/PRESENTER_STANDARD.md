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

## Visuals

Microsoft Fluent is the default theme in exploration and presentation.
Explore, Stage and Stage Ribbon are independent layout presets. Appearance is
system, light or dark, constrained by the selected theme's supported variants.
Use semantic `var(--cp-*)` colors and system-font choices in component CSS;
palette literals belong in validated JSON theme definitions.
Personal/event themes belong in local libraries, never hard-coded engine branches.
See [Design system](DESIGN_SYSTEM.md) for resolution and portable snapshots.

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
