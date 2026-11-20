"""List, inspect, scaffold, validate, and select local presenter designs."""

import argparse
from pathlib import Path

from design_config import (
    Library, VERSION, ID, SCOPES, add_design_arguments, argument_overrides,
    read_json, resolve_design, validate_layout, validate_theme, write_json,
    platform_roots,
)
from user_libraries import (
    discover_onedrive, read_registry, register, registry_path, select_root, set_default,
)


def copy_design(library, kind, id_, source, target):
    if kind not in ("themes", "layouts") or not ID.fullmatch(id_):
        raise ValueError("Choose themes/layouts and a valid design ID.")
    _, source_root = select_root(library.local_user_root, source)
    _, target_root = select_root(library.local_user_root, target)
    original, destination = source_root / kind / f"{id_}.json", target_root / kind / f"{id_}.json"
    if (not original.resolve().is_relative_to(source_root.resolve())
            or not destination.resolve().is_relative_to(target_root.resolve())):
        raise ValueError("Design copy cannot escape a library root.")
    value = read_json(original)
    (validate_theme(value, library.base) if kind == "themes" else validate_layout(value))
    if value["id"] != id_:
        raise ValueError("Filename and design ID must match.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as file:
        file.write(original.read_bytes())
    return destination


def library_command(args):
    import json
    root = platform_roots()["user"]
    if args.library_command == "discover":
        print(json.dumps(discover_onedrive(), indent=2))
        print("Discovery does not register or select accounts. Availability is local folder access, not sync health.")
    elif args.library_command == "list":
        registry = read_registry(root)
        print(f"Registry: {registry_path(root)}")
        for name, path in {"local": str(root), **registry["profiles"]}.items():
            print(f"{name}: {path} [{'available' if Path(path).is_dir() else 'unavailable'}]"
                  f"{' [default]' if registry['default'] == name else ''}")
    elif args.library_command == "add":
        print(register(root, args.name, args.path, args.create))
        print("Registered only. No default, themes, or synced files were changed.")
    elif args.library_command == "use":
        set_default(root, args.name)
        print(f"Default user library: {args.name}. Existing project locks are unchanged.")
    else:
        presenter = args.presenter_dir or args.project_root / "architecture"
        library = Library(args.project_root, presenter)
        print(copy_design(library, args.kind, args.id, args.source, args.target))
        print("Copied one design. The original and theme defaults are unchanged.")


def scaffold(library, kind, id_, scope="project", preset="stage-ribbon"):
    if not ID.fullmatch(id_) or scope not in SCOPES[1:] or scope not in library.roots:
        raise ValueError("Choose a valid ID and a writable scope, not builtin.")
    root = library.roots[scope].resolve()
    path = root / kind / f"{id_}.json"
    if not path.resolve().is_relative_to(root):
        raise ValueError("Scaffold destination escapes its scope.")
    if path.exists():
        raise FileExistsError(f"Refusing to overwrite {path}")
    if kind == "themes":
        value = {"schemaVersion": VERSION, "id": id_, "label": id_.replace("-", " ").title(),
                 "base": "fluent", "defaultAppearance": "light",
                 "appearances": {"light": {"accent": "#0078d4"}, "dark": {"accent": "#75b6e7"}}}
        validate_theme(value, library.base)
    elif kind == "layouts":
        value = {"schemaVersion": VERSION, "id": id_, "label": id_.replace("-", " ").title(),
                 "preset": preset, "options": {}}
        validate_layout(value)
    else:
        raise ValueError("Choose themes or layouts.")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation also protects against another process creating the same file.
    with path.open("x", encoding="utf-8") as file:
        import json
        file.write(json.dumps(value, indent=2) + "\n")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--presenter-dir", type=Path, help="Defaults to <project-root>\\architecture")
    parser.add_argument("--user-library", dest="library_profile", help="User library for list/new/validate")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    sub.add_parser("inspect")
    create = sub.add_parser("new")
    create.add_argument("kind", choices=("themes", "layouts"))
    create.add_argument("id")
    create.add_argument("--scope", choices=SCOPES[1:], default="project")
    create.add_argument("--preset", choices=("explore", "stage", "stage-ribbon"), default="stage-ribbon")
    validate = sub.add_parser("validate")
    validate.add_argument("--kind", choices=("themes", "layouts"))
    validate.add_argument("--file", type=Path)
    select = sub.add_parser("select")
    add_design_arguments(select)
    libraries = sub.add_parser("libraries", help="Manage device-local pointers to synced user libraries")
    library_sub = libraries.add_subparsers(dest="library_command", required=True)
    library_sub.add_parser("discover", help="List OneDrive roots without reading their content")
    library_sub.add_parser("list")
    add = library_sub.add_parser("add")
    add.add_argument("name")
    add.add_argument("--path", type=Path, required=True)
    add.add_argument("--create", action="store_true", help="Create only the final folder under an available parent")
    use = library_sub.add_parser("use")
    use.add_argument("name", help="Registered profile, or local")
    copy = library_sub.add_parser("copy")
    copy.add_argument("kind", choices=("themes", "layouts"))
    copy.add_argument("id")
    copy.add_argument("--from", dest="source", required=True)
    copy.add_argument("--to", dest="target", required=True)
    args = parser.parse_args()
    if args.command == "libraries":
        library_command(args)
        return
    presenter = args.presenter_dir or args.project_root / "architecture"
    library = Library(args.project_root, presenter)
    profile_override = {"userLibrary": args.library_profile} if args.library_profile is not None else {}
    if args.command == "new":
        library.settings(profile_override)
        print(scaffold(library, args.kind, args.id, args.scope, args.preset))
    elif args.command == "validate":
        if bool(args.kind) != bool(args.file):
            parser.error("--kind and --file must be used together")
        if args.file:
            value = read_json(args.file)
            (validate_theme(value, library.base) if args.kind == "themes" else validate_layout(value))
        else:
            library.settings(profile_override)
            for kind in ("themes", "layouts"):
                for row in library.catalog(kind):
                    library.resolve(kind, row["selector"])
        print("Design validation passed.")
    elif args.command == "list":
        library.settings(profile_override)
        for kind in ("themes", "layouts"):
            for row in library.catalog(kind):
                value = library.resolve(kind, row["selector"])
                support = ", ".join(value["appearances"]) if kind == "themes" else value["preset"]
                print(f"{kind}: {row['selector']} ({support})"
                      f"{' [shadowed]' if row['shadowed'] else ''} {row['path']}")
    elif args.command == "inspect":
        import json
        effective = resolve_design(args.project_root, presenter, profile_override, persist=False)
        print(json.dumps({"settings": effective["settings"], "sources": effective["sources"],
                          "userLibrary": effective.get("userLibrary", "local"),
                          "locked": (presenter / "design.lock.json").exists()}, indent=2))
        if not (presenter / "design.lock.json").exists() or profile_override:
            library.settings(profile_override)
        else:
            print("Locked design shown. Live user-library discovery is skipped; use list for current libraries.")
            library.roots.pop("user", None)
        for kind in ("themes", "layouts"):
            for row in library.catalog(kind):
                print(f"{row['selector']}: {row['path']}{' [shadowed]' if row['shadowed'] else ''}")
    else:
        config_path = presenter / "presenter.json"
        config = read_json(config_path) if config_path.exists() else {"schemaVersion": VERSION}
        from design_config import validate_settings
        validate_settings(config)
        overrides = {**profile_override, **{k: v for k, v in argument_overrides(args).items() if v is not None}}
        config.update(overrides)
        # Validate before changing either settings or lock.
        resolve_design(args.project_root, presenter, overrides, refresh=True, persist=False)
        write_json(config_path, config)
        lock = resolve_design(args.project_root, presenter, refresh=True)
        print(f"Selected {lock['settings']}. Rebuild the presenter to apply.")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileExistsError, OSError) as error:
        raise SystemExit(str(error))
