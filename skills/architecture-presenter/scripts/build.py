"""Rebuild the offline architecture and delivery presenter experience."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from html import escape
import json
import math
from pathlib import Path
import re
import textwrap
from typing import Any
from design_config import (
    add_design_arguments, argument_overrides, design_css, resolve_design, theme_variables,
)


ROOT = Path(__file__).resolve().parent
HEIGHT = 76
SVG_STYLE = """
svg { font-family: var(--cp-font); }
.group-box { fill: none; stroke: var(--cp-border); stroke-width: 1.5; }
.boundary .group-box { stroke: var(--cp-accent); stroke-dasharray: 8 6; }
.group-title { fill: var(--cp-text); font-size: 17px; font-weight: 600; }
.group[data-plane] .group-title { text-anchor: middle; }
.group-detail { fill: var(--cp-text-muted); font-size: 12px; }
.group-header { display: none; }
[data-plane="control"] { --cp-plane: var(--cp-plane-control); }
[data-plane="build"] { --cp-plane: var(--cp-plane-build); }
[data-plane="hosting"] { --cp-plane: var(--cp-plane-hosting); }
[data-plane="access"] { --cp-plane: var(--cp-plane-access); }
[data-plane="lifecycle"] { --cp-plane: var(--cp-plane-lifecycle); }
.group[data-plane] .group-box { stroke: var(--cp-plane); stroke-width: 2; }
[data-group-headers="true"] .group[data-plane] .group-header { display: block; fill: var(--cp-surface); }
.node[data-plane].new .node-box { stroke: var(--cp-plane); stroke-width: 3; }
.edge[data-plane] path:not(.edge-hit) { stroke: var(--cp-plane); stroke-width: 2; }
.node-box { fill: var(--cp-surface); stroke: var(--cp-border-strong); }
.node-title { fill: var(--cp-text); font-size: 16px; font-weight: 600; }
.node-detail { fill: var(--cp-text-muted); font-size: 12px; }
.node-state { fill: var(--cp-accent-text, var(--cp-accent)); font-size: 10px; font-weight: 600; letter-spacing: .06em; }
.node[data-state="TARGET"] .node-box, .edge[data-state="TARGET"] path:not(.edge-hit) { stroke-dasharray: 6 4; }
.stage-label { display: none; }
.edge path { fill: none; stroke: var(--cp-text-muted); stroke-width: 1.5; }
.edge text { fill: var(--cp-text-muted); font-size: 11px; text-anchor: middle; }
.future { opacity: .06; }
.future text { visibility: hidden; }
.gone { display: none; }
.new .node-box { stroke: var(--cp-accent); stroke-width: 2.5; }
.new .node-title, .new.group .group-title { fill: var(--cp-accent-text, var(--cp-accent)); }
.new.edge path { stroke: var(--cp-accent); stroke-width: 2.5; }
.node.current .node-box { fill: var(--cp-accent-soft); }
[data-inspect] { cursor: pointer; }
[data-inspect]:focus { outline: none; }
[data-inspect]:focus .node-box, .selected .node-box { stroke: var(--cp-accent); stroke-width: 3; }
.selected .node-box { fill: var(--cp-accent-soft); }
.selected.edge path:not(.edge-hit), .edge:focus path:not(.edge-hit) { stroke: var(--cp-accent); stroke-width: 3; }
.selected.group .group-box, .group:focus .group-box { stroke: var(--cp-accent); stroke-width: 3; }
.edge path.edge-hit { stroke-width: 18; stroke-opacity: 0; pointer-events: stroke; }
.edge[data-alternative="true"]:not(.future):not(.gone) { opacity: .4; }
.edge[data-alternative="true"]:is(:focus, .selected) { opacity: 1; }
.edge[data-alternative="true"] path:not(.edge-hit) { stroke-dasharray: 7 6; }
.trace-cursor { fill: var(--cp-accent); stroke: var(--cp-accent-fg); stroke-width: 3; pointer-events: none; }
.future, .future path.edge-hit { pointer-events: none; }
[data-phase] { transition: opacity .35s ease; }
@media (prefers-reduced-motion: reduce) { [data-phase] { transition: none; } }
"""


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    lines: list[str]
    x: int
    y: int
    width: int
    phase: int
    state: str = ""
    evidence: list[str] = field(default_factory=list)
    plane: str = ""


def evidence_exists(path: str, project_root: Path) -> bool:
    target = (project_root / path).resolve()
    return target.is_relative_to(project_root) and target.exists()


def validate_basis(item: dict[str, Any], context: str) -> None:
    if "basis" in item and item["basis"] not in ("documented", "observed", "inferred", "proposed"):
        raise ValueError(f"{context}: basis must be documented, observed, inferred, or proposed.")


def validate_data(data: dict[str, Any], project_root: Path) -> dict[str, Any]:
    conceptual = data.get("kind", "architecture") == "conceptual"
    if data.get("kind", "architecture") not in ("architecture", "conceptual"):
        raise ValueError("Journey kind must be architecture or conceptual.")
    count = len(data["phases"])
    if not count or [p["n"] for p in data["phases"]] != list(range(1, count + 1)):
        raise ValueError("Phase numbers must be consecutive, starting at 1.")
    for phase in data["phases"]:
        validate_basis(phase, f"Phase {phase['n']}")
        for key in ("principles", "decisions"):
            values = phase.get(key, [])
            if not isinstance(values, list) or any(not isinstance(value, str) for value in values):
                raise ValueError(f"Phase {phase['n']}: {key} must be an array of strings when provided.")
        for path in phase["evidence"]:
            if not evidence_exists(path, project_root):
                raise ValueError(f"Phase {phase['n']}: missing repository evidence {path}.")
    components = {item["id"]: item for item in data["components"]}
    if any(not item.get("state") for item in data["components"]):
        if conceptual:
            raise ValueError("Every conceptual node needs state ILLUSTRATIVE.")
        raise ValueError("Every component needs an explicit implementation state.")
    elements = data["groups"] + data["components"] + data["flows"]
    ids = [item["id"] for item in elements]
    if len(set(ids)) != len(ids):
        raise ValueError("Every group, component and flow must have a unique ID.")
    for item in elements:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", item["id"]):
            raise ValueError(f"Invalid element ID: {item['id']}.")
        if not 1 <= item["phase"] <= count:
            raise ValueError(f"{item['id']}: phase is outside the timeline.")
        states = ("", "ILLUSTRATIVE") if conceptual else ("", "APP", "SOURCE", "FOUNDATION", "EXTERNAL", "TARGET")
        if item.get("state", "") not in states:
            if conceptual:
                raise ValueError(f"{item['id']}: conceptual elements use ILLUSTRATIVE, not implementation states.")
            raise ValueError(f"{item['id']}: unknown implementation state.")
        if "alternative" in item and (not conceptual or not isinstance(item["alternative"], bool) or item not in data["flows"]):
            raise ValueError(f"{item['id']}: alternative is a boolean for conceptual flows only.")
        for path in item.get("evidence", []):
            if not evidence_exists(path, project_root):
                raise ValueError(f"{item['id']}: missing repository evidence {path}.")
    for flow in data["flows"]:
        if not re.fullmatch(r"M\d+ \d+(?:\s*[HV]\d+)*", flow["path"]):
            raise ValueError(f"{flow['id']}: use positive integer M/H/V routes.")
        for endpoint in ("from", "to"):
            if flow[endpoint] not in components:
                raise ValueError(f"{flow['id']}: unknown endpoint {flow[endpoint]}.")
            if components[flow[endpoint]]["phase"] > flow["phase"]:
                raise ValueError(f"{flow['id']}: flow predates its endpoint.")
        if "until" in flow and not flow["phase"] <= flow["until"] <= count:
            raise ValueError(f"{flow['id']}: invalid end phase.")
    elements_by_id = {item["id"]: item for item in elements}
    flows_by_id = {item["id"]: item for item in data["flows"]}
    for phase in data["phases"]:
        if any(key in phase for key in ("emphasis", "trace")) and not conceptual:
            raise ValueError("Emphasis and trace are for conceptual journeys only.")
        emphasis = phase.get("emphasis", [])
        if not isinstance(emphasis, list) or any(not isinstance(id_, str) for id_ in emphasis):
            raise ValueError(f"Phase {phase['n']}: emphasis must be an array of element IDs.")
        for id_ in emphasis:
            item = elements_by_id.get(id_)
            if not item or not item["phase"] <= phase["n"] <= item.get("until", count):
                raise ValueError(f"Phase {phase['n']}: emphasis must reference active elements.")
        if "trace" in phase:
            trace = phase["trace"]
            if not isinstance(trace, dict) or set(trace) != {"flow", "progress"} or not isinstance(trace["flow"], str):
                raise ValueError(f"Phase {phase['n']}: trace needs a flow ID and progress.")
            flow = flows_by_id.get(trace["flow"])
            progress = trace["progress"]
            if not flow or flow.get("alternative") or not flow["phase"] <= phase["n"] <= flow.get("until", count):
                raise ValueError(f"Phase {phase['n']}: trace must reference an active illustrative flow, not an alternative.")
            if isinstance(progress, bool) or not isinstance(progress, (int, float)) or not 0 <= progress <= 1:
                raise ValueError(f"Phase {phase['n']}: trace progress must be between 0 and 1.")
    return data


def attributes(item: dict[str, Any]) -> str:
    result = f'id="{escape(item["id"], quote=True)}" data-phase="{item["phase"]}"'
    if "until" in item:
        result += f' data-until="{item["until"]}"'
    if item.get("state"):
        result += f' data-state="{escape(item["state"], quote=True)}"'
    if item.get("plane"):
        result += f' data-plane="{escape(item["plane"], quote=True)}"'
    if item.get("alternative"):
        result += ' data-alternative="true"'
    return result


def interactive(item: dict[str, Any], label: str) -> str:
    return (
        f'{attributes(item)} data-inspect="{escape(item["id"], quote=True)}" '
        f'role="button" tabindex="0" aria-label="Inspect {escape(label, quote=True)}"'
    )


def build_svg(data: dict[str, Any]) -> str:
    conceptual = data.get("kind") == "conceptual"
    final = data["phases"][-1]
    emphasis = final.get("emphasis", []) if conceptual else []
    # Static exports retain the last authored progress of each illustrative path.
    traces = {phase["trace"]["flow"]: phase["trace"]["progress"] for phase in data["phases"] if "trace" in phase}
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" id="diagram" '
        f'viewBox="0 0 1490 700" data-kind="{data.get("kind", "architecture")}" role="group" aria-labelledby="diagram-title diagram-desc">',
        f'<title id="diagram-title">{escape(data["title"])}</title>',
        f'<desc id="diagram-desc">{escape(data["description"])}</desc>',
        f"<style>{SVG_STYLE}</style>",
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M0 0 L10 5 L0 10 Z" fill="var(--cp-text-muted)"/></marker></defs>',
    ]
    for plane in ("control", "build", "hosting", "access", "lifecycle"):
        parts.append(
            f'<defs><marker id="arrow-{plane}" viewBox="0 0 10 10" refX="9" refY="5" '
            'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
            f'<path d="M0 0 L10 5 L0 10 Z" fill="var(--cp-plane-{plane}, var(--cp-text-muted))"/></marker></defs>'
        )
    for group in data["groups"]:
        parts.append(
            f'<g {interactive(group, group["title"])} class="group {group.get("kind", "")}">'
            f'<rect class="group-box" x="{group["x"]}" y="{group["y"]}" '
            f'width="{group["width"]}" height="{group["height"]}" rx="4"/>'
            f'<rect class="group-header" x="{group["x"] + 10}" y="{group["y"] + 8}" '
            f'width="{group["width"] - 20}" height="31" rx="10"/>'
            f'<text class="group-title" x="{group["x"] + (group["width"] / 2 if group.get("plane") else 16)}" '
            f'y="{group["y"] + 28}">{escape(group["title"])}</text>'
            f'<text class="group-detail" x="{group["x"] + 16}" '
            f'y="{group["y"] + 49}">{escape(group["detail"])}</text></g>'
        )
    for flow in data["flows"]:
        # A standalone SVG represents the final phase, not obsolete public flows.
        css = "edge gone" if flow.get("until", len(data["phases"])) < len(data["phases"]) else "edge"
        if flow["id"] in emphasis:
            css += " new current"
        if flow["id"] in traces:
            points = route_points(flow["path"])
            length = sum(math.dist(a, b) for a, b in zip(points, points[1:]))
            ending = f'stroke-dasharray="{length}" stroke-dashoffset="{length * (1 - traces[flow["id"]])}"'
        else:
            ending = f'marker-end="url(#arrow{("-" + flow["plane"]) if flow.get("plane") else ""})"'
        parts.append(
            f'<g {interactive(flow, flow.get("label", flow["id"]))} class="{css}">'
            f'<title>{escape(flow["detail"])}</title>'
            f'<path class="edge-hit" d="{escape(flow["path"], quote=True)}"/>'
            f'<path d="{escape(flow["path"], quote=True)}" {ending}/>'
        )
        if flow.get("label"):
            parts.append(
                f'<text x="{flow["x"]}" y="{flow["y"]}">'
                f'{escape(flow["label"])}</text>'
            )
        parts.append("</g>")
    for item in data["components"]:
        node = Node(**item)
        parts.append(
            f'<g {interactive(item, node.name + (" / " + node.state if node.state else ""))} class="node{" new current" if node.id in emphasis else ""}">'
            f'<rect class="node-box" x="{node.x}" y="{node.y}" '
            f'width="{node.width}" height="{HEIGHT}" rx="4"/>'
            f'<text class="node-title" x="{node.x + 14}" y="{node.y + (33 if node.state else 25)}">'
            f'{escape(node.name)}</text>'
        )
        for index, line in enumerate(node.lines):
            parts.append(
                f'<text class="node-detail" x="{node.x + 14}" '
                f'y="{node.y + (51 if node.state else 46) + index * 17}">{escape(line)}</text>'
            )
        if node.state:
            parts.append(
                f'<text class="node-state" x="{node.x + 14}" y="{node.y + 15}">'
                f'{escape(node.state)}</text>'
            )
        stage_lines = textwrap.wrap(node.name, width=max(16, (node.width - 28) // 12))
        if len(stage_lines) > 2:
            raise ValueError(f"{node.id}: stage title must fit two lines.")
        stage_y = node.y + (HEIGHT - (len(stage_lines) - 1) * 25) / 2 + (15 if node.state else 8)
        parts.append(f'<text class="node-title stage-label" x="{node.x + 14}" y="{stage_y}">')
        for index, line in enumerate(stage_lines):
            parts.append(f'<tspan x="{node.x + 14}" dy="{0 if index == 0 else 25}">{escape(line)}</tspan>')
        parts.append("</text>")
        parts.append("</g>")
    if conceptual:
        trace = final.get("trace")
        if trace:
            flow = next(flow for flow in data["flows"] if flow["id"] == trace["flow"])
            x, y = point_on_route(flow["path"], trace["progress"])
        else:
            x, y = 0, 0
        parts.append(
            f'<circle id="trace-cursor" class="trace-cursor" cx="{x}" cy="{y}" r="8" '
            f'aria-label="Illustrative progress, not recorded execution" role="img"{" hidden" if not trace else ""}/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def route_points(path: str) -> list[tuple[int, int]]:
    commands = re.findall(r"([MHV])([\d ]+)", path)
    x, y = map(int, commands[0][1].split())
    points = [(x, y)]
    for command, value in commands[1:]:
        x, y = (int(value), y) if command == "H" else (x, int(value))
        points.append((x, y))
    return points


def point_on_route(path: str, progress: float) -> tuple[float, float]:
    points = route_points(path)
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    remaining = sum(lengths) * progress
    for a, b, length in zip(points, points[1:], lengths):
        if length and remaining <= length:
            ratio = remaining / length
            return a[0] + (b[0] - a[0]) * ratio, a[1] + (b[1] - a[1]) * ratio
        remaining -= length
    return points[-1]


def build_excalidraw(data: dict[str, Any]) -> dict[str, Any]:
    elements = []
    for item in data["groups"] + data["components"]:
        is_group = "name" not in item
        text = (
            f'{item["title"]}\n{item["detail"]}'
            if is_group else "\n".join([
                f'{item["name"]} [{item["state"]}]' if item.get("state") else item["name"],
                *item["lines"],
            ])
        )
        elements.append({
            "id": item["id"], "type": "rectangle", "x": item["x"], "y": item["y"],
            "width": item["width"], "height": item.get("height", HEIGHT),
            "angle": 0, "strokeColor": "#919191",
            "backgroundColor": "transparent" if is_group else "#f5f5f5",
            "fillStyle": "solid", "strokeWidth": 1, "roughness": 0, "opacity": 100,
            "strokeStyle": "dashed" if item.get("state") == "TARGET" else "solid",
            "roundness": {"type": 3}, "groupIds": [item["id"] + "-group"],
        })
        elements.append({
            "id": item["id"] + "-text", "type": "text",
            "x": item["x"] + 14, "y": item["y"] + 8,
            "width": item["width"] - 28, "height": 12 * 2.5 * len(text.splitlines()),
            "text": text, "originalText": text, "fontSize": 12, "fontFamily": 2,
            "lineHeight": 1.25, "strokeColor": "#000000", "angle": 0,
            "textAlign": "left", "verticalAlign": "top",
            "groupIds": [item["id"] + "-group"],
        })
    for flow in data["flows"]:
        if flow.get("until", len(data["phases"])) < len(data["phases"]):
            continue
        # Paths use only horizontal and vertical segments.
        commands = re.findall(r"([MHV])([\d ]+)", flow["path"])
        x, y = map(int, commands[0][1].split())
        points = [[0, 0]]
        for command, value in commands[1:]:
            last_x, last_y = points[-1]
            points.append(
                [int(value) - x, last_y] if command == "H"
                else [last_x, int(value) - y]
            )
        elements.append({
            "id": flow["id"], "type": "arrow", "x": x, "y": y,
            "width": max(p[0] for p in points) - min(p[0] for p in points),
            "height": max(p[1] for p in points) - min(p[1] for p in points),
            "points": points, "strokeColor": "#5c5c5c", "strokeWidth": 1,
            "roughness": 0, "endArrowhead": "arrow",
            "strokeStyle": "dashed" if flow.get("state") == "TARGET" or flow.get("alternative") else "solid",
        })
    return {
        "type": "excalidraw", "version": 2, "source": "architecture-presenter",
        "elements": elements, "appState": {"viewBackgroundColor": "#ffffff"},
    }


def build(input_path: Path, output_dir: Path, project_root: Path, overrides=None, refresh=False, roots=None) -> None:
    project_root = project_root.resolve(strict=True)
    content = json.loads(input_path.read_text(encoding="utf-8"))
    principles = content.get("principles", {})
    if not isinstance(principles, dict):
        raise ValueError("Principles must be an object when provided.")
    for id_, principle in principles.items():
        if not isinstance(principle, dict):
            raise ValueError(f"Principle {id_}: expected an object.")
        validate_basis(principle, f"Principle {id_}")
        for path in principle["evidence"]:
            if not evidence_exists(path, project_root):
                raise ValueError(f"Missing principle evidence {path}.")
    views = content["views"]
    if not views:
        raise ValueError("At least one journey is required.")
    for name, data in views.items():
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name):
            raise ValueError(f"Invalid journey ID: {name}.")
        validate_data(data, project_root)
        conceptual = data.get("kind") == "conceptual"
        if (not conceptual or "repository" in data or "revision" in data) and not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", data.get("repository", "")):
            raise ValueError("Repository must be owner/name, not an arbitrary URL.")
        if (not conceptual or "repository" in data or "revision" in data) and not re.fullmatch(r"[A-Za-z0-9_.-]+", data.get("revision", "")):
            raise ValueError("Use a source commit or simple ref without URL delimiters.")
        if conceptual and not data.get("repository") and any(phase.get("commits") or phase.get("issues") for phase in data["phases"]):
            raise ValueError("Commit and issue references need repository and revision metadata.")
        for group in data["groups"]:
            if group["phase"] != 1:
                raise ValueError("All responsibility boundaries must be visible from reveal 1.")
        for phase in data["phases"]:
            if set(phase.get("principles", [])) - principles.keys():
                raise ValueError(f"Phase {phase['n']}: reference only known principles.")
    insights = content.get("insights", {"items": []})
    for insight in insights["items"]:
        for view, phase in insight.get("availableFrom", {}).items():
            if (
                view not in views
                or not isinstance(phase, int)
                or not 1 <= phase <= len(views[view]["phases"])
            ):
                raise ValueError(f"{insight['id']}: invalid learning start phase.")
        for view, targets in insight["targets"].items():
            if view not in views:
                raise ValueError(f"{insight['id']}: unknown journey {view}.")
            ids = {
                item["id"] for kind in ("components", "groups", "flows")
                for item in views[view][kind]
            }
            if set(targets) - ids:
                raise ValueError(f"{insight['id']}: unknown focus target.")
    assets = ROOT if (ROOT / "presenter-template.html").exists() else ROOT.parent / "assets"
    template = (assets / "presenter-template.html").read_text(encoding="utf-8")
    design = resolve_design(project_root, input_path.resolve().parent, overrides, refresh, roots)
    theme = design_css(design)
    layouts = (assets / "layouts.css").read_text(encoding="utf-8")
    diagrams = {name: build_svg(data) for name, data in views.items()}
    # Escape '<' so source text cannot terminate the embedded script element.
    embedded = json.dumps(views, ensure_ascii=True).replace("<", "\\u003c")
    embedded_diagrams = json.dumps(diagrams, ensure_ascii=True).replace("<", "\\u003c")
    embedded_insights = json.dumps(insights, ensure_ascii=True).replace("<", "\\u003c")
    replacements = {
        "__THEME__": theme,
        "__LAYOUTS__": layouts,
        "__DESIGN__": json.dumps({k: design[k] for k in ("settings", "themes", "layouts")}).replace("<", "\\u003c"),
        "__SVG__": next(iter(diagrams.values())),
        "__DATA__": embedded,
        "__DIAGRAMS__": embedded_diagrams,
        "__INSIGHTS__": embedded_insights,
        "__PRINCIPLES__": json.dumps(principles).replace("<", "\\u003c"),
        "__PROJECT__": escape(content["project"]["name"]),
        "__THEME_NOTE__": escape(content["project"].get("themeNote", "")),
        "__JOURNEYS__": json.dumps({key: value["label"] for key, value in views.items()}).replace("<", "\\u003c"),
        "__TABS__": "".join(
            f'<button class="tab" id="{key}-tab" role="tab" type="button" data-view="{key}" aria-controls="canvas">{escape(value["label"])}</button>'
            for key, value in views.items()),
        "__CHOICES__": "".join(
            f'<button type="button" data-journey="{key}"><strong>{escape(value["label"])}</strong><span>{len(value["phases"])} reveals: {escape(value["description"])}</span></button>'
            for key, value in views.items()),
    }
    page = re.sub(r"__[A-Z_]+__", lambda match: replacements[match[0]], template)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "architecture-evolution.html").write_text(page, encoding="utf-8")
    (output_dir / "presenter.html").write_text(
        page.replace('<html lang="en">', '<html lang="en" data-launch="presenter">', 1),
        encoding="utf-8",
    )
    for name, data in views.items():
        export_theme = design["themes"][design["settings"]["theme"]]
        appearance = design["settings"]["appearance"]
        static_svg = diagrams[name].replace(
            'id="diagram"', f'id="diagram" style=\'{theme_variables(export_theme, appearance)}\'', 1)
        (output_dir / f"{name}.svg").write_text(
            static_svg, encoding="utf-8"
        )
        (output_dir / f"{name}.excalidraw").write_text(
            json.dumps(build_excalidraw(data), indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    add_design_arguments(parser)
    args = parser.parse_args()
    try:
        build(args.input, args.output, args.project_root, argument_overrides(args), args.refresh_design)
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
