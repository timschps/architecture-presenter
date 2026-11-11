# Presenter standard

## Audience orientation

Keep the entire responsibility map visible from the first reveal, with a fixed
camera and stable screen coordinates. Reveal components and connectors in place,
highlighting the addition rather than flying the camera. Manual inspection may
zoom; the next/previous reveal returns to overview. Keep the ribbon height stable
at landscape/projector sizes. Never let a longer caption rescale the diagram.

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

Microsoft Fluent is the neutral exploration default. Stage mode has a separate
dark deck-inspired skin: Segoe UI, generous boundaries, inset dark headers,
restrained responsibility accents and a bottom principle/value/trade-off ribbon.
Included stage colors are extracted tokens, not distributed presentation assets.
Use `var(--cp-*)` in component CSS; literals belong in theme definitions only.

A supplied current deck takes precedence for project-local styling after actual
inspection. Never claim exact visual alignment from an inaccessible URL.
Keep controls and calibration out of the audience diagram, with optional evidence.
Do not use a dashboard card grid in place of a directional architecture diagram.

## Operation and verification

No server, CDN, remote fonts or file-URL fetches. Inline data, diagrams and styles.
Escape embedded text, including script terminators. Links open only on demand.
No automatic telemetry, paid calls, cloud mutation, publishing or deployment.

Next: Right/PageDown/Space. Previous: Left/PageUp. Ignore held-key repeats and
editable controls. M: journeys, C: context, F: fullscreen, B: blackout,
0: overview, +/-: zoom. Provide calibration and explicit start/end notices.

Verify every journey at projector sizes with identical screen coordinates and
scale across reveals, plus responsive overflow, both Fluent themes, focus and
offline operation. Hardware rehearsal is separate from simulated key checks.
