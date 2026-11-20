# Contributing

Small, focused contributions are welcome. Open an issue before changing the
content contract, design scopes, presenter behavior or dependency stack.
Treat everyone respectfully; harassment and disclosure of private information
are not acceptable.

## Pull request workflow

1. Fork the repository and create a topic branch from current `main`.
2. Keep the change scoped to one problem. Explain the behavior and trade-offs.
3. Add focused regression tests for changed behavior and update affected docs.
4. Run the checks below, then open a PR using the template.
5. Address review feedback and resolve conversations after addressing the issue.

Do not push directly to `main`. The `verify` GitHub Actions check must pass
against an up-to-date base, and review conversations must be resolved.
Contributions require maintainer approval; new commits dismiss stale approvals.
`CODEOWNERS` routes review to @timschps. Only maintainers merge accepted PRs,
using squash merge; topic branches are deleted afterward.

Maintainer-authored changes also use PRs and passing CI. GitHub prohibits
self-approval, so repository admins have a PR-only bypass of the **review
requirement only**. Use it for maintainer-authored PRs and explain any other
review exception in the PR. It cannot bypass the separate CI, PR, conversation,
linear-history, deletion or force-push rules. Admins can change repository
settings, so this is not a safeguard against an admin disabling the policy.

The desired rules are versioned in [.github/rulesets](.github/rulesets).
Those files do not activate rules automatically. Maintainers must apply any
approved policy changes to GitHub's repository rulesets and verify the effective
rules on `main`; editing a JSON file alone does not change enforcement.

## Local checks

Use Python 3.10+ and Node.js 22. From the repository root:

```powershell
python -m unittest discover -s tests -v
npm ci --ignore-scripts
npm test
git diff --check
```

Browser checks use Edge on Windows. Elsewhere, install Playwright Chromium with
`npx playwright install --with-deps chromium` before `npm test`.
Use the existing tests and dependencies; do not add a formatter or test runner
just for a small change. Documentation-only PRs still run the required CI check.

For renderer, theme or layout changes, inspect screenshots in light/dark mode
at 1280x720, 1920x1080 and 3840x2160, plus a narrow viewport. Check every affected
journey/reveal for clipping, readable connectors and stable map coordinates.
Simulated clicker keys are not a hardware rehearsal.

## Preserve the plugin contract

- Keep the offline, declarative engine. No CDNs, remote fonts, telemetry,
  executable theme plugins or unrequested cloud operations.
- Keep Fluent as the default; personal/event themes belong in local libraries.
- Keep the map fixed across reveals. Zoom is user-driven; respect reduced motion.
- Cite real source evidence for architecture claims. Rationale is optional.
  Conceptual journeys stay ILLUSTRATIVE, not deployment or productivity claims.
- Preserve existing generated presenters, copied engines and design locks.
  Do not silently edit installed plugins or user/machine libraries.
- Use synthetic fixtures. Never commit private designs, decks, session data,
  credentials, tenant details or generated personal previews.
- Record provenance and redistribution permissions for third-party code/assets.
- Dependency changes must explain their need and update the lockfile. Workflow
  actions use full commit pins; keep their version comments current.

See [the data contract](skills/architecture-presenter/references/DATA_CONTRACT.md),
[design system](skills/architecture-presenter/references/DESIGN_SYSTEM.md) and
[presenter standard](skills/architecture-presenter/references/PRESENTER_STANDARD.md).
Maintainers handle plugin version changes and releases deliberately.

## Reporting

Use the issue templates for reproducible bugs and scoped feature requests.
Sanitize examples and screenshots. Report suspected vulnerabilities privately
using [SECURITY.md](SECURITY.md), not in a public issue or PR.
