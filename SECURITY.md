# Security policy

## Supported version

Security fixes target the latest published plugin version on `main`.
Existing project-local engine snapshots are not updated automatically; review
and intentionally migrate affected snapshots after a fix.

## Private reporting

Use GitHub's [Report a vulnerability](https://github.com/timschps/architecture-presenter/security/advisories/new)
to send a private report to the maintainer. Do not disclose an exploit, secret,
private source or personal data in a public issue or PR.

Include the affected version, impact, minimal synthetic reproduction and any
suggested mitigation. Never include real credentials or private session data.
The maintainer will assess the report and coordinate a fix/disclosure; no
response-time or bounty commitment is made.

## Boundaries

The plugin generates offline HTML/SVG and editable diagrams from local JSON.
It validates local evidence paths and design inputs; it does not execute project
code, prove that evidence supports a claim, or verify live cloud state.
Only use trusted engine snapshots. Inspect selected designs before sharing:
selected local styling is embedded in generated deliverables.
