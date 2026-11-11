"""Synthetic example only. Replace it with evidence from the current project."""

from copy import deepcopy
from datetime import date


def create_story(name):
    lenses = [
        ("P1", "Separate responsibilities", "Keep acceptance separate from execution.", "Explicit review adds a handoff."),
        ("P2", "Apply least privilege", "Give each component only scoped authority.", "Identity and access reviews add effort."),
        ("P3", "Assume failure", "Make failure and uncertain outcomes observable.", "A safe stop can interrupt progress."),
        ("P4", "Design for change", "Review evidence before promoting a new version.", "Versioned contracts require maintenance."),
        ("P5", "Keep it proportional", "Reuse foundations that match the workload.", "Shared resources still need boundaries."),
    ]
    principles = {
        id: dict(name=title, attributes="Replace with project quality attributes",
                 requirement="Replace with a verified project requirement.",
                 decision=decision, tradeoff=tradeoff,
                 verification="Replace with the actual test or evidence.",
                 scope="Synthetic example only. No operational claims.", evidence=[])
        for id, title, decision, tradeoff in lenses
    }
    positions = [
        ("intent", "User experience", "control", 20, 15, 1450, 170, 55, 85, 1),
        ("implementation", "Implementation + delivery", "build", 20, 215, 550, 210, 55, 300, 2),
        ("runtime", "Application runtime", "hosting", 650, 215, 820, 210, 710, 300, 3),
        ("operations", "Operations + evolution", "lifecycle", 20, 465, 550, 210, 55, 550, 5),
        ("dependencies", "Approved dependencies", "access", 650, 465, 820, 210, 710, 550, 4),
    ]
    groups, nodes = [], []
    for id, title, plane, x, y, w, h, nx, ny, phase in positions:
        groups.append(dict(id=f"{id}-boundary", title=title, detail="Synthetic boundary, replace from project evidence",
                           plane=plane, x=x, y=y, width=w, height=h, phase=1))
        nodes.append(dict(id=id, name=f"Example {id}", lines=["SYNTHETIC TARGET", "Replace with a concrete component"],
                          plane=plane, x=nx, y=ny, width=380, phase=phase, state="TARGET", evidence=[]))
    flows = [
        dict(id="intent-build", **{"from": "intent", "to": "implementation"}, phase=2,
             path="M245 161 V195 H245 V300", label="Reviewed artifact", x=360, y=195,
             detail="Synthetic handoff. Replace with exact contract and approval.", state="TARGET", plane="control"),
        dict(id="build-runtime", **{"from": "implementation", "to": "runtime"}, phase=3,
             path="M435 338 H710", label="Version + evidence", x=572, y=325,
             detail="Synthetic release target, not a deployed workload.", state="TARGET", plane="build"),
        dict(id="runtime-dependencies", **{"from": "runtime", "to": "dependencies"}, phase=4,
             path="M900 376 V550", label="Scoped call", x=950, y=455,
             detail="Synthetic dependency authorization target.", state="TARGET", plane="hosting"),
        dict(id="observe", **{"from": "dependencies", "to": "operations"}, phase=5,
             path="M710 588 H435", label="Evidence", x=572, y=575,
             detail="Synthetic operational feedback target.", state="TARGET", plane="lifecycle"),
    ]
    phases = [
        dict(n=i, title=title, dates="Synthetic example", summary="Replace with project-specific causal explanation.",
             decisions=[decision], principles=[id], commits=[], evidence=[],
             value=decision, tradeoff=tradeoff)
        for i, (id, title, decision, tradeoff) in enumerate(lenses, 1)
    ]
    architecture = dict(title=name, label="Architecture build-up",
                        description="Synthetic starter. Not a verified project architecture.",
                        scope="All content is illustrative TARGET material until replaced with project evidence.",
                        repository="example/project", revision="main", snapshot=date.today().isoformat(),
                        stepLabel="Reveal", phases=phases, groups=groups, components=nodes, flows=flows)
    principles_view = deepcopy(architecture)
    principles_view.update(label="Principles to decisions", stepLabel="Principle")
    return dict(project=dict(name=name, themeNote="Included deck-inspired tokens; no project-specific deck alignment claimed."),
                views=dict(architecture=architecture, principles=principles_view),
                principles=principles, insights=dict(items=[]))
