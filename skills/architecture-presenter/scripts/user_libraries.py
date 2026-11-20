"""Device-local pointers to optional synced user design libraries."""

import json
import os
from pathlib import Path
import re
import sys
import tempfile

NAME = re.compile(r"[a-z][a-z0-9-]{0,63}")


def registry_path(local_root):
    return Path(local_root) / "libraries.json"


def validate_registry(value):
    if (not isinstance(value, dict) or set(value) != {"schemaVersion", "default", "profiles"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1
            or not isinstance(value["profiles"], dict)):
        raise ValueError("Invalid user library registry; expected schemaVersion 1, default, and profiles.")
    for name, path in value["profiles"].items():
        if not NAME.fullmatch(name) or name == "local":
            raise ValueError("Invalid library name; 'local' is reserved for device-local storage.")
        if not isinstance(path, str) or not path or not Path(path).is_absolute():
            raise ValueError(f"Library {name}: register an absolute local filesystem path.")
    default = value["default"]
    if not isinstance(default, str) or (default != "local" and default not in value["profiles"]):
        raise ValueError("Default user library is not registered.")
    return value


def read_registry(local_root):
    path = registry_path(local_root)
    if not path.exists():
        return {"schemaVersion": 1, "default": "local", "profiles": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read user library registry {path}: {error}") from error
    return validate_registry(value)


def write_registry(local_root, value):
    validate_registry(value)
    path = registry_path(local_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="libraries-", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            file.write(json.dumps(value, indent=2) + "\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def select_root(local_root, profile=None):
    # Explicit local selection remains usable even if an unrelated registry is broken.
    if profile == "local":
        return "local", Path(local_root)
    registry = read_registry(local_root)
    name = registry["default"] if profile is None else profile
    if name == "local":
        return name, Path(local_root)
    if name not in registry["profiles"]:
        raise ValueError(f"Unknown user library '{name}'. Register it with designs.py libraries add, "
                         "or select --user-library local.")
    root = Path(registry["profiles"][name])
    if not root.is_dir():
        raise ValueError(f"User library '{name}' is unavailable at {root}. Restore its local availability "
                         "or explicitly select --user-library local. No library fallback was applied.")
    return name, root


def register(local_root, name, path, create=False):
    if not NAME.fullmatch(name) or name == "local":
        raise ValueError("Choose a lowercase library name other than 'local'.")
    raw = Path(path)
    if not raw.is_absolute():
        raise ValueError("Register an absolute local filesystem path, not a URL or relative path.")
    root = raw.resolve()
    value = read_registry(local_root)
    if name in value["profiles"]:
        raise FileExistsError(f"Library '{name}' is already registered; no mapping was changed.")
    if root == Path(local_root).resolve() or any(Path(p).resolve() == root for p in value["profiles"].values()):
        raise ValueError("This folder is already mapped. Use its existing profile.")
    if not root.is_dir():
        if not create:
            raise ValueError("Library folder does not exist. Use --create only under an available parent folder.")
        if not root.parent.is_dir():
            raise ValueError("Library parent is unavailable; refusing to recreate a missing sync root.")
        root.mkdir()
    value["profiles"][name] = str(root)
    write_registry(local_root, value)
    return root


def set_default(local_root, name):
    select_root(local_root, name)
    value = read_registry(local_root)
    value["default"] = name
    write_registry(local_root, value)


def windows_accounts():
    if sys.platform != "win32":
        return []
    import winreg
    accounts = []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\OneDrive\Accounts") as key:
            index = 0
            while True:
                try:
                    name = winreg.EnumKey(key, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(key, name) as account:
                        folder = winreg.QueryValueEx(account, "UserFolder")[0]
                        if isinstance(folder, str) and folder:
                            accounts.append((name, folder))
                except OSError:
                    continue
    except OSError:
        pass
    return accounts


def discover_onedrive(accounts=None, env=None):
    """Read account roots only, never email, tenant IDs, or synced content."""
    env = os.environ if env is None else env
    candidates = list(windows_accounts() if accounts is None else accounts)
    candidates.extend((name, env[name]) for name in ("OneDrive", "OneDriveCommercial", "OneDriveConsumer")
                      if env.get(name))
    result, seen = [], set()
    for source, folder in candidates:
        path = Path(folder)
        if not path.is_absolute():
            continue
        key = os.path.normcase(str(path.resolve()))
        if key in seen:
            continue
        seen.add(key)
        result.append({"source": source, "root": str(path), "available": path.is_dir()})
    return result
