"""Copy a reviewed engine snapshot and synthetic starter into a new project folder."""

import argparse
import json
from pathlib import Path
import shutil
from starter import create_story
from design_config import (
    add_design_arguments, argument_overrides, resolve_design, write_json,
)


def initialize(project_root, folder="architecture", name="Project architecture", overrides=None, roots=None):
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
    (target / "story.json").write_text(json.dumps(create_story(name), indent=2) + "\n", encoding="utf-8")
    print(f"Created {target}. Replace synthetic starter content before delivery.")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--folder", default="architecture")
    parser.add_argument("--name", default="Project architecture")
    add_design_arguments(parser)
    args = parser.parse_args()
    try:
        initialize(args.project_root, args.folder, args.name, argument_overrides(args))
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
