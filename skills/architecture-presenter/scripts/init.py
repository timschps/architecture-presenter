"""Copy a reviewed engine snapshot and synthetic starter into a new project folder."""

import argparse
import json
from pathlib import Path
import shutil
from starter import create_story


def initialize(project_root, folder="architecture", name="Project architecture"):
    project = Path(project_root).resolve(strict=True)
    target = project / folder
    if not target.resolve().is_relative_to(project) or target.resolve() == project:
        raise ValueError("Choose a new output directory inside the project.")
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite existing directory: {target}")
    source = Path(__file__).resolve().parent
    target.mkdir(parents=True)
    shutil.copy2(source / "build.py", target / "build.py")
    for file in ("presenter-template.html", "microsoft-theme.css"):
        shutil.copy2(source.parent / "assets" / file, target / file)
    (target / "story.json").write_text(json.dumps(create_story(name), indent=2) + "\n", encoding="utf-8")
    print(f"Created {target}. Replace synthetic starter content before delivery.")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--folder", default="architecture")
    parser.add_argument("--name", default="Project architecture")
    args = parser.parse_args()
    initialize(args.project_root, args.folder, args.name)
