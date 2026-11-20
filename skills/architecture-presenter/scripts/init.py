"""Copy a reviewed engine snapshot and synthetic starter into a new project folder."""

import argparse
import json
from pathlib import Path
import shutil
from starter import create_story
from branching import create_branching_story
from design_config import (
    add_design_arguments, argument_overrides, resolve_design, write_json,
)


def initialize(project_root, folder="architecture", name=None, overrides=None, roots=None, example="architecture"):
    if example not in ("architecture", "branching"):
        raise ValueError("Example must be architecture or branching.")
    name = name or ("Agent branching" if example == "branching" else "Project architecture")
    project = Path(project_root).resolve(strict=True)
    target = project / folder
    if not target.resolve().is_relative_to(project) or target.resolve() == project:
        raise ValueError("Choose a new output directory inside the project.")
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing directory: {target}")
    source = Path(__file__).resolve().parent
    lock = resolve_design(project, target, overrides, roots=roots, persist=False)
    target.mkdir(parents=True)
    for file in ("build.py", "design_config.py", "designs.py", "user_libraries.py"):
        shutil.copy2(source / file, target / file)
    for file in ("presenter-template.html", "layouts.css"):
        shutil.copy2(source.parent / "assets" / file, target / file)
    for folder_name in ("themes", "layouts"):
        shutil.copytree(source.parent / "assets" / folder_name, target / folder_name)
    settings = {"schemaVersion": 1, **{k: v for k, v in (overrides or {}).items() if v is not None}}
    # The lock carries resolved selections; refresh uses these explicit project settings.
    write_json(target / "presenter.json", settings)
    from design_config import digest
    lock["inputs"]["presenter.json"] = digest(settings)
    lock["hash"] = digest({k: v for k, v in lock.items() if k != "hash"})
    write_json(target / "design.lock.json", lock)
    story = create_branching_story(name) if example == "branching" else create_story(name)
    (target / "story.json").write_text(json.dumps(story, indent=2) + "\n", encoding="utf-8")
    note = "Conceptual example, not a recorded session." if example == "branching" else "Replace synthetic starter content before delivery."
    print(f"Created {target}. {note}")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--folder", default="architecture")
    parser.add_argument("--name")
    parser.add_argument("--example", choices=("architecture", "branching"), default="architecture")
    add_design_arguments(parser)
    args = parser.parse_args()
    try:
        initialize(args.project_root, args.folder, args.name, argument_overrides(args), example=args.example)
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
