"""Declarative, offline design resolution shared by generation and design tooling."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from user_libraries import select_root

VERSION = 1
ENGINE = "design-v1"
ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
COLOR = re.compile(r"#[a-fA-F0-9]{6}(?:[a-fA-F0-9]{2})?")
SCOPES = ("builtin", "machine", "user", "repo", "project")
PRESETS = ("explore", "stage", "stage-ribbon")
FONTS = {
    "segoe": '"Segoe UI", Aptos, Calibri, sans-serif',
    "system": 'system-ui, sans-serif',
    "arial": 'Arial, Helvetica, sans-serif',
}
COLORS = set("""bg bg-elevated surface surface-soft border border-strong text
text-muted text-soft accent accent-hover accent-text accent-soft accent-fg success
danger warning link overlay panel panel-strong sheen highlight blackout plane-control
plane-build plane-hosting plane-access plane-lifecycle ribbon-start ribbon-mid
ribbon-end ribbon-shade divider""".split())
DEFAULTS = {
    "theme": "builtin:fluent", "stageTheme": None,
    "exploreLayout": "builtin:explore", "stageLayout": "builtin:stage-ribbon",
    "appearance": "system",
}
OPTION_DEFAULTS = {
    "titleAlign": "left", "captionHeight": 108, "explanationHeight": 110,
    "sidebarWidth": 360, "groupHeaders": False, "trackGroupTitles": False,
}


def assets_root():
    root = Path(__file__).resolve().parent
    return root if (root / "presenter-template.html").exists() else root.parent / "assets"


def read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"{path}: cannot read JSON: {error}") from error


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def document(value, allowed, required, context):
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise ValueError(f"{context}: expected keys {', '.join(required)}; unknown keys are not allowed.")
    if type(value.get("schemaVersion")) is not int or value["schemaVersion"] != VERSION:
        raise ValueError(f"{context}: unsupported schemaVersion; expected {VERSION}.")


def identity(value, context):
    if not isinstance(value.get("id"), str) or not ID.fullmatch(value["id"]):
        raise ValueError(f"{context}: invalid design ID.")
    if not isinstance(value.get("label"), str) or not 1 <= len(value["label"]) <= 80:
        raise ValueError(f"{context}: label must contain 1-80 characters.")


def validate_theme(value, base=None):
    required = ("schemaVersion", "id", "label", "defaultAppearance", "appearances")
    document(value, (*required, "base", "font"), required, "Theme")
    identity(value, "Theme")
    if "base" in value and value["base"] != "fluent":
        raise ValueError("Theme: only the bundled fluent base is supported.")
    if not isinstance(value.get("font", "segoe"), str) or value.get("font", "segoe") not in FONTS:
        raise ValueError("Theme: choose a documented system font.")
    variants = value["appearances"]
    if not isinstance(variants, dict) or not variants or set(variants) - {"light", "dark"}:
        raise ValueError("Theme: appearances must contain light and/or dark.")
    if not isinstance(value["defaultAppearance"], str) or value["defaultAppearance"] not in variants:
        raise ValueError("Theme: defaultAppearance must be supported.")
    result = deepcopy(value)
    result["font"] = value.get("font", base.get("font", "segoe") if base else "segoe")
    for mode, tokens in variants.items():
        if not isinstance(tokens, dict) or set(tokens) - COLORS:
            raise ValueError("Theme: unknown semantic color tokens.")
        if any(not isinstance(v, str) or not COLOR.fullmatch(v) for v in tokens.values()):
            raise ValueError("Theme: colors must be #RRGGBB or #RRGGBBAA, not CSS or resources.")
        resolved = dict(base["appearances"][mode]) if value.get("base") and base else {}
        resolved.update(tokens)
        if set(resolved) != COLORS:
            raise ValueError("Theme: missing tokens; specify base: fluent or a complete palette.")
        result["appearances"][mode] = resolved
    return result


def validate_layout(value):
    required = ("schemaVersion", "id", "label", "preset", "options")
    document(value, required, required, "Layout")
    identity(value, "Layout")
    if value["preset"] not in PRESETS:
        raise ValueError("Layout: unknown base preset.")
    options = value["options"]
    if not isinstance(options, dict) or set(options) - OPTION_DEFAULTS.keys():
        raise ValueError("Layout: unknown options.")
    for key, option in options.items():
        if key == "titleAlign":
            valid = option in ("left", "center")
        elif key in ("groupHeaders", "trackGroupTitles"):
            valid = type(option) is bool
        else:
            low, high = {"captionHeight": (96, 140), "explanationHeight": (110, 150),
                         "sidebarWidth": (280, 440)}[key]
            valid = type(option) is int and low <= option <= high
        if not valid:
            raise ValueError(f"Layout: invalid bounded option {key}.")
    result = deepcopy(value)
    result["options"] = {**OPTION_DEFAULTS, **options}
    if "titleAlign" not in options and value["preset"] == "stage-ribbon":
        result["options"]["titleAlign"] = "center"
    return result


def validate_settings(value):
    document(value, ("schemaVersion", *DEFAULTS, "userLibrary"), ("schemaVersion",), "Settings")
    for key, val in value.items():
        if key == "schemaVersion":
            continue
        if key == "appearance":
            if val not in ("system", "light", "dark"):
                raise ValueError("Settings: appearance must be system, light, or dark.")
        elif key == "userLibrary":
            if not isinstance(val, str) or not ID.fullmatch(val):
                raise ValueError("Settings: userLibrary must be a named local library profile.")
        elif val is None and key == "stageTheme":
            continue
        elif not isinstance(val, str) or not val:
            raise ValueError(f"Settings: {key} must be a nonempty design selector.")
    return value


def platform_roots(platform=None, env=None, home=None):
    platform, env, home = platform or sys.platform, os.environ if env is None else env, Path.home() if home is None else Path(home)
    if env.get("ARCHITECTURE_PRESENTER_CONFIG_ROOT"):
        root = Path(env["ARCHITECTURE_PRESENTER_CONFIG_ROOT"])
        if not root.is_absolute():
            raise ValueError("ARCHITECTURE_PRESENTER_CONFIG_ROOT must be absolute.")
        return {"user": root / "user", "machine": root / "machine"}
    if platform == "win32":
        return {
            "user": Path(env.get("APPDATA", home / "AppData" / "Roaming")) / "architecture-presenter",
            "machine": Path(env.get("PROGRAMDATA", r"C:\ProgramData")) / "architecture-presenter",
        }
    if platform == "darwin":
        return {"user": home / "Library" / "Application Support" / "architecture-presenter",
                "machine": Path("/Library/Application Support/architecture-presenter")}
    xdg = Path(env.get("XDG_CONFIG_HOME", home / ".config"))
    if not xdg.is_absolute():
        xdg = home / ".config"
    return {"user": xdg / "architecture-presenter", "machine": Path("/etc/architecture-presenter")}


class Library:
    def __init__(self, project_root, presenter_dir, roots=None):
        self.project = Path(project_root).resolve()
        self.presenter = Path(presenter_dir).resolve()
        self.roots = {
            **(platform_roots() if roots is None else roots), "builtin": assets_root(),
            "repo": self.project / ".architecture-presenter", "project": self.presenter,
        }
        self.base = validate_theme(read_json(self.roots["builtin"] / "themes" / "fluent.json"))
        self.sources = {}
        self.local_user_root = self.roots.get("user")
        self.user_profile = None

    def configure_user(self, overrides=None):
        # Profile routing cannot come from a synced or machine-wide config.
        profile = None
        for scope in ("repo", "project"):
            path = self.roots[scope] / ("presenter.json" if scope == "project" else "config.json")
            if path.exists():
                profile = validate_settings(read_json(path)).get("userLibrary", profile)
        if (overrides or {}).get("userLibrary") is not None:
            profile = overrides["userLibrary"]
            validate_settings({"schemaVersion": VERSION, "userLibrary": profile})
        if self.local_user_root is not None:
            self.user_profile, root = select_root(self.local_user_root, profile)
            self.roots["user"] = root
        elif profile is not None and profile != "local":
            raise ValueError("Named user libraries require a device-local user configuration root.")

    def settings(self, overrides=None):
        self.configure_user(overrides)
        result, origins = dict(DEFAULTS), {key: self.roots["builtin"] for key in DEFAULTS}
        for scope in SCOPES[1:]:
            if scope not in self.roots:
                continue
            root = self.roots[scope]
            path = root / ("presenter.json" if scope == "project" else "config.json")
            if path.exists():
                for key, val in validate_settings(read_json(path)).items():
                    if key == "userLibrary":
                        if scope in ("machine", "user"):
                            raise ValueError("userLibrary may only be set in project/repository settings or the CLI.")
                    elif key != "schemaVersion":
                        result[key], origins[key] = val, root
        for key, val in (overrides or {}).items():
            if val is not None and key != "userLibrary":
                result[key], origins[key] = val, Path.cwd()
        validate_settings({"schemaVersion": VERSION, **result})
        return result, origins

    def resolve(self, kind, selector, origin=None):
        if kind not in ("themes", "layouts"):
            raise ValueError("Choose themes or layouts.")
        scope, name = None, selector
        if ":" in selector and selector.split(":", 1)[0] in SCOPES:
            scope, name = selector.split(":", 1)
        if scope is not None or ID.fullmatch(name):
            if not ID.fullmatch(name):
                raise ValueError("Invalid design selector ID.")
            scopes = (scope,) if scope else reversed(SCOPES)
            candidates = [(s, self.roots[s] / kind / f"{name}.json") for s in scopes if s in self.roots]
            found = next(((s, p) for s, p in candidates if p.exists()), None)
            if not found:
                raise ValueError(f"Missing selected {kind}: {selector}. Use designs.py list to inspect scopes.")
            source_scope, path = found
            if not path.resolve().is_relative_to(self.roots[source_scope].resolve()):
                raise ValueError("Design symlink escapes its scope.")
        else:
            raw = Path(selector)
            if ".." in raw.parts:
                raise ValueError("Design imports cannot traverse '..'; use an explicit absolute path.")
            path = raw if raw.is_absolute() else (origin or self.presenter) / raw
            source_scope = "import"
        value = read_json(path)
        result = validate_theme(value, self.base) if kind == "themes" else validate_layout(value)
        if source_scope != "import" and result["id"] != name:
            raise ValueError(f"{path}: filename and design ID must match.")
        self.sources[(kind, result["id"])] = (source_scope, path, digest(value))
        return result

    def catalog(self, kind):
        rows = []
        for scope in reversed(SCOPES):
            if scope not in self.roots:
                continue
            for path in sorted((self.roots[scope] / kind).glob("*.json")):
                rows.append({"selector": f"{scope}:{path.stem}", "path": str(path),
                             "shadowed": any(r["id"] == path.stem for r in rows), "id": path.stem})
        return rows

    def validate_all(self):
        self.settings()
        return [self.resolve(kind, row["selector"]) for kind in ("themes", "layouts") for row in self.catalog(kind)]


def _project_inputs(library):
    inputs = {}
    settings = library.presenter / "presenter.json"
    if settings.exists():
        inputs["presenter.json"] = digest(read_json(settings))
    for (kind, _), (scope, path, hash_) in library.sources.items():
        if scope == "project":
            inputs[path.relative_to(library.presenter).as_posix()] = hash_
        elif scope == "import" and path.resolve().is_relative_to(library.presenter):
            inputs[path.resolve().relative_to(library.presenter).as_posix()] = hash_
    return inputs


def validate_lock(lock, base):
    required = ("schemaVersion", "engine", "settings", "themes", "layouts", "sources", "inputs", "hash")
    document(lock, (*required, "userLibrary"), required, "Design lock")
    if "userLibrary" in lock and (not isinstance(lock["userLibrary"], str) or not ID.fullmatch(lock["userLibrary"])):
        raise ValueError("Invalid user library profile in design lock.")
    if lock["engine"] != ENGINE or lock["hash"] != digest({k: v for k, v in lock.items() if k != "hash"}):
        raise ValueError("Invalid or incompatible design lock; use --refresh-design.")
    if not isinstance(lock["settings"], dict) or set(lock["settings"]) != set(DEFAULTS):
        raise ValueError("Design lock settings are incomplete.")
    validate_settings({"schemaVersion": VERSION, **lock["settings"]})
    for kind in ("themes", "layouts"):
        if not isinstance(lock[kind], dict):
            raise ValueError("Invalid design lock definitions.")
        for id_, value in lock[kind].items():
            validated = validate_theme(value, base) if kind == "themes" else validate_layout(value)
            if id_ != validated["id"] or value != validated:
                raise ValueError("Invalid design lock ID.")
    for field, kind in (("theme", "themes"), ("stageTheme", "themes"),
                        ("exploreLayout", "layouts"), ("stageLayout", "layouts")):
        id_ = lock["settings"].get(field)
        if id_ is not None and id_ not in lock[kind]:
            raise ValueError("Design lock references a missing definition.")
    for field, preset in (("exploreLayout", "explore"), ("stageLayout", None)):
        layout = lock["layouts"][lock["settings"][field]]
        if (preset and layout["preset"] != preset) or (not preset and layout["preset"] == "explore"):
            raise ValueError("Choose an explore preset for exploreLayout and a stage preset for stageLayout.")
    if not isinstance(lock["inputs"], dict):
        raise ValueError("Invalid design lock inputs.")
    return lock


def resolve_design(project_root, presenter_dir, overrides=None, refresh=False, roots=None, persist=True):
    library = Library(project_root, presenter_dir, roots)
    lock_path = library.presenter / "design.lock.json"
    if lock_path.exists() and not refresh and not any(v is not None for v in (overrides or {}).values()):
        lock = validate_lock(read_json(lock_path), library.base)
        current_settings = library.presenter / "presenter.json"
        if current_settings.exists() != ("presenter.json" in lock["inputs"]):
            raise ValueError("Project design settings changed; use --refresh-design.")
        for relative, hash_ in lock["inputs"].items():
            path = library.presenter / relative
            if not path.resolve().is_relative_to(library.presenter) or not path.is_file() or digest(read_json(path)) != hash_:
                raise ValueError("Project design inputs changed; use --refresh-design.")
        return lock
    settings, origins = library.settings(overrides)
    themes, layouts = {}, {}
    # Include built-ins; an explicitly selected same-ID design may replace one.
    for kind, output in (("themes", themes), ("layouts", layouts)):
        for row in library.catalog(kind):
            if row["selector"].startswith("builtin:"):
                value = library.resolve(kind, row["selector"])
                output[value["id"]] = value
    selections = {}
    for key, output, kind in (("theme", themes, "themes"), ("stageTheme", themes, "themes"),
                              ("exploreLayout", layouts, "layouts"), ("stageLayout", layouts, "layouts")):
        if settings[key] is not None:
            value = library.resolve(kind, settings[key], origins[key])
            identity_key = (kind, value["id"])
            if identity_key in selections and selections[identity_key] != digest(value):
                raise ValueError("Selected definitions share an ID but differ. Give the local design a unique ID.")
            selections[identity_key] = digest(value)
            # A selected same-ID design replaces that ID as a whole in the snapshot.
            output[value["id"]] = value
            settings[key] = value["id"]
    lock = {
        "schemaVersion": VERSION, "engine": ENGINE, "settings": settings,
        "themes": themes, "layouts": layouts,
        "sources": {f"{kind}/{id_}": {"scope": scope, "hash": hash_}
                    for (kind, id_), (scope, _, hash_) in library.sources.items()},
        "inputs": _project_inputs(library),
    }
    if library.user_profile is not None:
        lock["userLibrary"] = library.user_profile
    lock["hash"] = digest(lock)
    validate_lock(lock, library.base)
    if persist:
        write_json(lock_path, lock)
    return lock


def theme_variables(theme, appearance):
    mode = appearance if appearance in theme["appearances"] else theme["defaultAppearance"]
    tokens = theme["appearances"][mode]
    return (f"color-scheme:{mode};--cp-font:{FONTS[theme['font']]};"
            "--cp-shadow:0 2px 8px #00000030;"
            + "".join(f"--cp-{key}:{val};" for key, val in sorted(tokens.items())))


def design_css(lock):
    parts = []
    for id_, theme in lock["themes"].items():
        for mode in theme["appearances"]:
            parts.append(f'html[data-design-theme="{id_}"][data-appearance="{mode}"]'
                         + "{" + theme_variables(theme, mode) + "}")
    for id_, layout in lock["layouts"].items():
        options = layout["options"]
        parts.append(f'html[data-layout="{id_}"]' + "{"
                     + f"--cp-caption-height:{options['captionHeight']}px;"
                     + f"--cp-explanation-height:{options['explanationHeight']}px;"
                     + f"--cp-sidebar-width:{options['sidebarWidth']}px;"
                     + f"--cp-title-align:{options['titleAlign']};" + "}")
    return "\n".join(parts)


def add_design_arguments(parser):
    parser.add_argument("--user-library", help="Named user library profile, or local for device-local storage")
    parser.add_argument("--theme", help="Theme ID, scope:ID, or JSON import path")
    parser.add_argument("--stage-theme", help="Optional explicit stage-only theme")
    parser.add_argument("--explore-layout", help="Explore layout ID, scope:ID, or JSON path")
    parser.add_argument("--stage-layout", help="Stage layout ID, scope:ID, or JSON path")
    parser.add_argument("--appearance", choices=("system", "light", "dark"))
    parser.add_argument("--refresh-design", action="store_true", help="Re-resolve libraries and replace design lock")


def argument_overrides(args):
    overrides = {key: getattr(args, flag, None) for key, flag in (
        ("theme", "theme"), ("stageTheme", "stage_theme"), ("exploreLayout", "explore_layout"),
        ("stageLayout", "stage_layout"), ("appearance", "appearance"), ("userLibrary", "user_library"))}
    for key, value in overrides.items():
        if value is not None and key not in ("appearance", "userLibrary") and ("/" in value or "\\" in value or value.endswith(".json")):
            if ".." in Path(value).parts:
                raise ValueError("Design imports cannot traverse '..'; use an explicit absolute path.")
            overrides[key] = str(Path(value).resolve())
    return overrides
