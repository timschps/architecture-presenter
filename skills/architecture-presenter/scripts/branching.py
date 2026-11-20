"""Optional conceptual example: steering an agent toward an accepted outcome."""

from copy import deepcopy


def create_branching_story(name="Agent branching"):
    outcomes = [
        ("different", "Different interpretation", "Plausible, but not intended", 70),
        ("complexity", "Unnecessary complexity", "Extra code or dependencies", 180),
        ("intended", "Intended result", "Possible, not guaranteed", 290),
        ("unverified", "Unverified result", "Looks right, not yet proven", 400),
        ("action", "Unintended action", "Outside the agreed scope", 510),
    ]

    def node(id_, title, detail, x, y, width, phase=1):
        return dict(id=id_, name=title, lines=[detail], evidence=[],
                    state="ILLUSTRATIVE", x=x, y=y, width=width, phase=phase)

    nodes = [node("request", "Build the app", "Same illustrative request", 40, 300, 260)]
    nodes += [node(id_, title, detail, 1100, y, 350) for id_, title, detail, y in outcomes]
    routes = {
        "different": "M300 338 H480 V108 H1100",
        "complexity": "M300 338 H580 V218 H1100",
        "intended": "M300 338 H700 V328 H1100",
        "unverified": "M300 338 H580 V438 H1100",
        "action": "M300 338 H480 V548 H1100",
    }
    alternatives = [
        dict(id=f"possible-{id_}", **{"from": "request", "to": id_}, phase=1,
             path=routes[id_], label="", detail=f"Hypothetical outcome: {title}.",
             alternative=True)
        for id_, title, _, _ in outcomes
    ]

    def run(id_, outcome, phase=2, until=None):
        flow = dict(id=id_, **{"from": "request", "to": outcome}, phase=phase,
                    path=routes[outcome], label="", detail="One illustrative path, not recorded execution.")
        if until is not None:
            flow["until"] = until
        return flow

    def beat(title, value, tradeoff, emphasis, flow=None, progress=1):
        result = dict(title=title, value=value, tradeoff=tradeoff, emphasis=emphasis,
                      basis="proposed", dates="Conceptual example", commits=[], evidence=[],
                      summary=value)
        if flow:
            result["trace"] = dict(flow=flow, progress=progress)
        return result

    def journey(label, steps, flows, checkpoints=()):
        phases = [dict(n=i, **step) for i, step in enumerate(steps, 1)]
        return dict(
            kind="conceptual", title=name, label=label, stepLabel="Step",
            description="A conceptual branching timeline, not a recorded session or productivity benchmark.",
            scope="Hypothetical alternatives are not simultaneous executions or equally likely outcomes. "
                  "Instructions guide; permissions block; checks verify; humans handle exceptions.",
            snapshot="Illustrative example", phases=phases, groups=[],
            components=deepcopy(nodes) + list(checkpoints), flows=deepcopy(alternatives) + flows,
        )

    views = {}
    views["outcomes"] = journey("Outcomes", [
        beat("One request, many outcomes", "Unclear intent leaves room for several plausible interpretations.",
             "The examples overlap, are not exhaustive, and have no assigned likelihoods.", ["request"]),
        beat("One illustrative run", "The dot follows one path, not every hypothetical alternative.",
             "Generating a plausible result does not establish alignment with intent.", ["run-wrong"], "run-wrong", .4),
        beat("A plausible wrong turn", "A useful-looking result can still miss the intended requirement.",
             "Completed output is not acceptance evidence.", ["different", "run-wrong"], "run-wrong"),
        beat("Review against the request", "Compare behavior, scope and evidence with the original intent.",
             "Acceptance needs more than a successful-looking build.", ["review", "intended"], "run-wrong"),
        beat("An illustration, not a benchmark", "An intended result remains possible, not guaranteed.",
             "No probabilities or measured time savings are claimed.", ["intended", "different"], "run-wrong"),
    ], [run("run-wrong", "different")],
        [node("review", "Acceptance review", "Compare result with intent", 620, 615, 340, 4)])

    views["backtrack"] = journey("Backtrack", [
        beat("Agree on the intended outcome", "State the scope and acceptance criteria before reviewing progress.",
             "The same request still has several plausible interpretations.", ["request", "intended"]),
        beat("Work takes an unwanted branch", "An unwanted interpretation accumulates implementation work.",
             "Early visible progress can hide a mismatch.", ["run-wrong"], "run-wrong", .65),
        beat("Late review finds the mismatch", "Review catches the wrong direction after work has accumulated.",
             "Unwanted code and dependencies now need removal.", ["different", "review"], "run-wrong"),
        beat("Backtrack to the fork", "Remove unwanted work and return toward the decision point.",
             "Undoing work is work too.", ["run-wrong", "review"], "run-wrong", .17),
        beat("Rebuild toward the intended result", "Implement the accepted direction after removing the wrong turn.",
             "Review still needs evidence that the rebuilt result meets the request.", ["intended", "run-intended"], "run-intended"),
    ], [run("run-wrong", "different", until=4), run("run-intended", "intended", phase=5)],
        [node("review", "Late review", "Undo and rebuild", 620, 615, 340, 3)])

    patch = dict(id="patch", **{"from": "different", "to": "intended"}, phase=4,
                 path="M1275 146 H1470 V328 H1450", label="", detail="Illustrative corrective work, not measured effort.")
    views["patch-forward"] = journey("Patch forward", [
        beat("Agree on the intended outcome", "Start with the same request and plausible alternatives.",
             "The illustrative comparison assigns no costs or probabilities.", ["request", "intended"]),
        beat("Work takes the wrong turn", "An unintended implementation becomes established.",
             "Progress is not necessarily progress toward the accepted result.", ["run-wrong"], "run-wrong", .65),
        beat("Review catches the mismatch", "The result needs correction after the wrong turn.",
             "Correction does not always mean undoing the original work.", ["different", "review"], "run-wrong"),
        beat("Add a corrective layer", "Patch forward on top of the existing implementation.",
             "Compensating work may leave the original assumptions or dependency in place.", ["patch", "review"], "patch", .45),
        beat("The result can retain residue", "The immediate request may be met while avoidable complexity remains.",
             "Residue is a risk, not a claim about every corrective change.", ["intended", "residue", "patch"], "patch"),
    ], [run("run-wrong", "different"), patch], [
        node("review", "Corrective layer", "Added after the wrong turn", 460, 615, 290, 3),
        node("residue", "Residue can remain", "Review code and assumptions", 790, 615, 300, 5),
    ])

    views["live-steering"] = journey("Live steering", [
        beat("Start with the same request", "Make the intended result explicit while alternatives remain possible.",
             "A clearer request reduces ambiguity, not all uncertainty.", ["request", "intended"]),
        beat("Notice a fork early", "Inspect plans, actions and diffs; clarify an unwanted interpretation.",
             "Visible activity is not a complete view of internal reasoning.", ["nudge", "run-wrong"], "run-wrong", .2),
        beat("Nudge toward the intended result", "Small corrections can prevent an unwanted branch from growing.",
             "Someone still needs to recognize the consequential choice.", ["nudge", "run-intended"], "run-intended", .4),
        beat("Attention becomes the bottleneck", "Independent tasks may still compete for the same human's attention.",
             "Starting more sessions does not automatically improve useful throughput.", ["attention", "run-intended"], "run-intended", .75),
        beat("Less rework, continued supervision", "Early steering can reduce avoidable rework.",
             "Continuous attention still limits practical concurrency.", ["intended", "attention"], "run-intended"),
    ], [run("run-wrong", "different", until=2), run("run-intended", "intended", phase=3)], [
        node("nudge", "Clarify the intent", "A human nudge at the fork", 420, 615, 280, 2),
        node("attention", "Attention is limited", "Other work needs review too", 740, 615, 330, 4),
    ])

    valid = dict(id="valid-alternative", **{"from": "request", "to": "intended"}, phase=1,
                 path="M300 338 H600 V600 H1050 V328 H1100", label="Valid design alternative",
                 x=810, y=600, detail="Different designs may satisfy the same accepted requirements.", alternative=True)
    views["foundations"] = journey("Foundations", [
        beat("Establish the foundations first", "Scope and contracts guide consequential implementation choices.",
             "Instructions communicate intent; they are not permission boundaries.", ["scope", "request"]),
        beat("Permissions block an action", "A scoped permission can block a prohibited action before execution.",
             "The dot shows an attempted path, not a completed prohibited action.", ["permissions", "attempt"], "attempt", .8),
        beat("Checks reject an invalid result", "A check can detect a result that fails acceptance criteria.",
             "A failed check requires revision, not blind continuation.", ["checks", "run-invalid"], "run-invalid"),
        beat("Pause for a human decision", "Escalate an unresolved boundary or approval decision.",
             "Automation does not remove human accountability.", ["approval", "run-intended"], "run-intended", .8),
        beat("Selective supervision, not blind trust", "Leave valid alternatives open while reviewing exceptions.",
             "Foundations support bounded work; they do not guarantee correctness or speed.", ["intended", "approval"], "run-intended"),
    ], [
        run("attempt", "action", until=2), run("run-invalid", "unverified", phase=3, until=3),
        run("run-intended", "intended", phase=4), valid,
    ], [
        node("scope", "Scope + contracts", "Guide the intended work", 320, 615, 250),
        node("permissions", "Permission boundary", "Block a prohibited action", 590, 615, 250, 2),
        node("checks", "Result checks", "Reject an invalid result", 860, 615, 250, 3),
        node("approval", "Human approval", "Pause, review, decide", 1130, 615, 320, 4),
    ])
    return dict(project=dict(name=name), views=views)
