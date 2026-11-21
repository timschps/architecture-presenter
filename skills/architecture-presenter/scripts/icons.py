"""Consent-gated official icon packs, local updates, and portable offline snapshots."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import tempfile
import time
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import xml.etree.ElementTree as ET
import zipfile

from design_config import Library, digest, read_json

PROVIDERS = {
    "azure": {
        "source": "https://learn.microsoft.com/en-us/azure/architecture/icons/",
        "hosts": ("arch-center.azureedge.net", "download.microsoft.com"),
    },
    "microsoft365": {
        "source": "https://learn.microsoft.com/en-us/microsoft-365/solutions/architecture-icons-templates",
        "hosts": ("go.microsoft.com", "download.microsoft.com"),
    },
    "power-platform": {
        "source": "https://learn.microsoft.com/en-us/power-platform/guidance/icons",
        "hosts": ("download.microsoft.com",),
    },
}
ALIASES = {
    "azure": {
        "api-management": ("api-management-services",),
        "key-vault": ("key-vaults",),
        "storage-account": ("storage-accounts",),
        "functions": ("function-apps",),
        "aks": ("kubernetes-services",),
        "app-service": ("app-services",),
        "sql-database": ("sql-database", "sql-databases"),
        "cosmos-db": ("azure-cosmos-db",),
    },
    "microsoft365": {"teams": ("microsoft-teams", "teams"), "sharepoint": ("sharepoint",)},
    "power-platform": {"copilot-studio": ("copilot-studio", "microsoft-copilot-studio")},
}
SERVICE = re.compile(r"(azure|microsoft365|power-platform):[a-z][a-z0-9-]{0,100}")
SHA = re.compile(r"[a-f0-9]{64}")
MAX_PACK = 64 * 1024 * 1024
MAX_SVG = 2 * 1024 * 1024
INTERVAL = 24 * 60 * 60


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        file.write(json.dumps(value, indent=2) + "\n")
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def contained(root, path):
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Icon path escapes its library or snapshot.")
    return path


def validate_url(url, hosts):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in hosts or parsed.port not in (None, 443)
            or parsed.username is not None or parsed.password is not None):
        raise ValueError("Icon downloads require an approved official HTTPS host.")
    return url


def fetch(url, hosts, limit, headers=None, method="GET"):
    class Redirects(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, message, response_headers, target):
            validate_url(target, hosts)
            return super().redirect_request(request, fp, code, message, response_headers, target)

    validate_url(url, hosts)
    request = Request(url, headers={"User-Agent": "ArchitecturePresenter/1", **(headers or {})}, method=method)
    begun = time.monotonic()
    try:
        with build_opener(Redirects()).open(request, timeout=20) as response:
            validate_url(response.url, hosts)
            chunks, size = [], 0
            while chunk := response.read(64 * 1024):
                size += len(chunk)
                if size > limit or time.monotonic() - begun > 60:
                    raise ValueError("Official icon response exceeds the size limit.")
                chunks.append(chunk)
            return b"".join(chunks), {k.lower(): v for k, v in response.headers.items()}
    except HTTPError as error:
        if error.code == 304:
            return None, {}
        raise


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections, self.links = [], []
        self.heading, self.link, self.skip = None, None, 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        if tag in ("h1", "h2", "h3"):
            self.heading = []
        if tag == "a":
            self.link = [attrs.get("href", ""), []]

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.skip = max(0, self.skip - 1)
        if tag in ("h1", "h2", "h3") and self.heading is not None:
            self.sections.append([" ".join(self.heading).strip(), []])
            self.heading = None
        if tag == "a" and self.link is not None:
            self.links.append((self.link[0], " ".join(self.link[1])))
            self.link = None

    def handle_data(self, text):
        if self.skip:
            return
        if self.heading is not None:
            self.heading.append(text)
        elif self.sections:
            self.sections[-1][1].append(text)
        if self.link is not None:
            self.link[1].append(text)


def metadata(provider):
    definition = PROVIDERS[provider]
    data, _ = fetch(definition["source"], ("learn.microsoft.com",), 3 * 1024 * 1024)
    page = Page()
    page.feed(data.decode("utf-8-sig"))
    sections = []
    has_terms = False
    for heading, body in page.sections:
        key = heading.lower().replace("\u2019", "'")
        if "terms" in key or key in ("do", "don't", "do's", "don'ts"):
            has_terms |= "terms" in key
            text = " ".join(body)
            for _, label in page.links:
                if re.match(r"download\s+(svg\s+icons|visio\s+templates)", label, re.I):
                    text = text.replace(label, "")
            text = re.sub(r"I agree to the above terms\.?", "", text, flags=re.I)
            sections.append(re.sub(r"\s+", " ", heading + " " + text).strip())
    if not has_terms or not sections:
        raise ValueError("Cannot identify official icon terms; no automatic approval or download.")
    links = [urljoin(definition["source"], href) for href, label in page.links
             if re.search(r"download\s+svg\s+icons", label, re.I)]
    if len(set(links)) != 1:
        raise ValueError("Cannot identify one official SVG pack download; manual review required.")
    url = validate_url(links[0], definition["hosts"])
    terms = "\n".join(sections)
    return {"provider": provider, "source": definition["source"], "download": url,
            "terms": terms, "termsHash": hashlib.sha256(terms.encode()).hexdigest()}


def safe_svg(data):
    if len(data) > MAX_SVG:
        raise ValueError("SVG exceeds the size limit.")
    text = data.decode("utf-8-sig")
    if re.search(r"<!\s*(DOCTYPE|ENTITY)|<\?(?!xml\s)", text, re.I):
        raise ValueError("SVG entities or processing instructions are not allowed.")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        raise ValueError("Malformed SVG.") from error
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise ValueError("Expected an SVG root.")
    forbidden = {"script", "foreignobject", "image", "a", "animate", "animatemotion",
                 "animatetransform", "set", "discard", "iframe", "audio", "video"}
    elements = list(root.iter())
    if len(elements) > 10000:
        raise ValueError("SVG exceeds the element limit.")
    for element in elements:
        name = element.tag.rsplit("}", 1)[-1].lower()
        if name in forbidden:
            raise ValueError("Active or nested external SVG content is not allowed.")
        for attribute, value in element.attrib.items():
            attribute = attribute.rsplit("}", 1)[-1].lower()
            if attribute.startswith("on") or attribute == "base":
                raise ValueError("SVG event handlers and base URLs are not allowed.")
            if attribute in ("href", "src") and not value.startswith("#"):
                raise ValueError("SVG external resources are not allowed.")
            if attribute == "style" or re.search(r"url\s*\(", value, re.I) or "\\" in value:
                safe_css(value)
        if name == "style":
            safe_css("".join(element.itertext()))
    return data


def safe_css(value):
    if "\\" in value or "@" in value or re.search(r"expression\s*\(", value, re.I):
        raise ValueError("SVG CSS imports, escapes or active content are not allowed.")
    for target in re.findall(r"url\s*\((.*?)\)", value, re.I):
        if not re.fullmatch(r"""['"]?#[a-zA-Z0-9_.:-]+['"]?""", target.strip()):
            raise ValueError("SVG CSS external resources are not allowed.")


def slug(filename):
    value = PurePosixPath(filename).stem
    value = re.sub(r"^\d+-icon-service-", "", value, flags=re.I)
    value = re.sub(r"_scalable$", "", value, flags=re.I)
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1-\2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", value).lower()
    return re.sub(r"[^a-z0-9]+", "-", value).strip("-")


def unpack(data, destination):
    items, rejected = [], []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        if len(entries) > 10000 or sum(item.file_size for item in entries) > 256 * 1024 * 1024:
            raise ValueError("Icon archive exceeds extraction limits.")
        for item in entries:
            path = PurePosixPath(item.filename)
            if (path.is_absolute() or ".." in path.parts or "\\" in item.filename or ":" in item.filename
                    or stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1):
                raise ValueError("Unsafe icon archive path, symlink or encrypted entry.")
            if item.is_dir() or path.suffix.lower() != ".svg" or "__MACOSX" in path.parts:
                continue
            if item.file_size > MAX_SVG:
                rejected.append(item.filename)
                continue
            try:
                svg = safe_svg(archive.read(item))
            except (RuntimeError, NotImplementedError) as error:
                raise ValueError("Unsupported icon archive compression.") from error
            except (ValueError, ET.ParseError, UnicodeError):
                rejected.append(item.filename)
                continue
            hash_ = hashlib.sha256(svg).hexdigest()
            (destination / f"{hash_}.svg").write_bytes(svg)
            items.append({"name": item.filename, "id": slug(item.filename), "sha256": hash_})
    if not items:
        raise ValueError("Pack contains no supported passive SVG icons.")
    return items, rejected


@contextmanager
def writing(cache):
    cache.mkdir(parents=True, exist_ok=True)
    path = cache / "update.lock"
    with path.open("x") as file:
        file.write("An icon operation is in progress. Remove only after confirming it stopped.\n")
    try:
        yield
    finally:
        path.unlink(missing_ok=True)


def cache_pack(cache, meta, previous=None, force=False):
    headers = {}
    if previous and previous["download"] == meta["download"] and not force:
        for field, header in (("etag", "If-None-Match"), ("modified", "If-Modified-Since")):
            if previous.get(field):
                headers[header] = previous[field]
    data, response = fetch(meta["download"], PROVIDERS[meta["provider"]]["hosts"], MAX_PACK, headers)
    if data is None:
        if previous is None:
            raise ValueError("Received not-modified without a cached pack.")
        return previous
    hash_ = hashlib.sha256(data).hexdigest()
    destination = contained(cache, cache / hash_)
    with tempfile.TemporaryDirectory(dir=cache) as temporary:
        staging = Path(temporary)
        items, rejected = unpack(data, staging)
        destination.mkdir(exist_ok=True)
        for file in staging.iterdir():
            target = contained(cache, destination / file.name)
            # Re-fetching repairs missing/corrupt cache bytes, never project snapshots.
            temporary_file = contained(cache, destination / (file.name + ".tmp"))
            shutil.copy2(file, temporary_file)
            temporary_file.replace(target)
    result = {**meta, "packHash": hash_, "items": items, "rejected": rejected,
              "etag": response.get("etag"), "modified": response.get("last-modified"),
              "downloadedAt": datetime.now(timezone.utc).isoformat()}
    atomic_json(cache / "current.json", result)
    return result


def approval(path, provider):
    value = read_json(path)
    if (not isinstance(value, dict) or set(value) != {"schemaVersion", "provider", "termsHash", "updates"}
            or type(value["schemaVersion"]) is not int or value["schemaVersion"] != 1
            or value["provider"] != provider or not isinstance(value["termsHash"], str)
            or not SHA.fullmatch(value["termsHash"]) or value["updates"] not in ("auto", "notify", "off")):
        raise ValueError(f"{path}: invalid provider approval.")
    return value


def cached_manifest(path, provider):
    value = read_json(path)
    strings = ("source", "download", "terms", "termsHash", "packHash", "downloadedAt")
    if (not isinstance(value, dict) or value.get("provider") != provider
            or any(not isinstance(value.get(key), str) for key in strings)
            or any(not SHA.fullmatch(value[key]) for key in ("termsHash", "packHash"))
            or value["source"] != PROVIDERS[provider]["source"]
            or hashlib.sha256(value["terms"].encode()).hexdigest() != value["termsHash"]
            or not isinstance(value.get("items"), list) or not 0 < len(value["items"]) <= 10000
            or any(value.get(key) is not None and not isinstance(value[key], str)
                   for key in ("etag", "modified"))):
        raise ValueError("Invalid icon cache manifest; explicitly fetch a clean pack.")
    validate_url(value["download"], PROVIDERS[provider]["hosts"])
    for item in value["items"]:
        if (not isinstance(item, dict) or set(item) != {"name", "id", "sha256"}
                or any(not isinstance(item[key], str) for key in item)
                or not SHA.fullmatch(item["sha256"])):
            raise ValueError("Invalid icon cache catalogue; explicitly fetch a clean pack.")
    return value


def locations(project, presenter, roots=None, profile=None):
    library = Library(project, presenter, roots)
    lock = Path(presenter) / "design.lock.json"
    if profile is None and lock.exists():
        profile = read_json(lock).get("userLibrary")
    library.configure_user({"userLibrary": profile} if profile is not None else {})
    return library.roots


def stores(project, presenter, roots=None, profile=None):
    result = {}
    paths = locations(project, presenter, roots, profile)
    for provider in PROVIDERS:
        for scope in ("project", "repo", "user", "machine"):
            if scope not in paths:
                continue
            root = paths[scope]
            path = contained(root, root / "icons" / "approvals" / f"{provider}.json")
            if path.is_file():
                result[provider] = (approval(path, provider),
                                    contained(root, root / "icons" / "cache" / provider))
                break
    return result


def check(provider, policy, cache, force=False, download=False, now=None):
    now = time.time() if now is None else now
    state_path = cache / "check.json"
    state = read_json(state_path) if state_path.exists() else {}
    if not isinstance(state, dict) or (state and not isinstance(state.get("attemptedAt"), (int, float))):
        raise ValueError("Invalid icon check state; inspect the local cache.")
    if policy["updates"] == "off" and not force:
        return {"provider": provider, "status": "off"}
    if state and not force and now - state.get("attemptedAt", 0) < INTERVAL:
        return {**state, "provider": provider, "checked": False}
    try:
        with writing(cache):
            result = {"provider": provider, "attemptedAt": now, "checked": True}
            # Count failed attempts too, avoiding repeated network calls when offline.
            atomic_json(state_path, {**result, "status": "checking"})
            try:
                meta = metadata(provider)
                current_path = cache / "current.json"
                try:
                    previous = cached_manifest(current_path, provider) if current_path.exists() else None
                except ValueError:
                    if not download:
                        raise
                    previous = None
                if meta["termsHash"] != policy["termsHash"]:
                    result.update(status="terms-changed", termsHash=meta["termsHash"])
                elif policy["updates"] == "auto" or download:
                    current = cache_pack(cache, meta, previous, force=force)
                    result.update(status="updated" if not previous or current["packHash"] != previous["packHash"]
                                  else "unchanged", packHash=current["packHash"])
                else:
                    _, response = fetch(meta["download"], PROVIDERS[provider]["hosts"], MAX_PACK, method="HEAD")
                    unchanged = previous and previous["download"] == meta["download"] and (
                        response["etag"] == previous.get("etag") if response.get("etag") else
                        response.get("last-modified") and response["last-modified"] == previous.get("modified"))
                    result.update(status="unchanged" if unchanged else "update-review-needed",
                                  download=meta["download"])
            except (OSError, ValueError, zipfile.BadZipFile) as error:
                result.update(status="unavailable", message=str(error))
            atomic_json(state_path, result)
            return result
    except FileExistsError:
        return {"provider": provider, "status": "busy"}


def monitor(project, presenter, roots=None, profile=None, offline=False):
    if offline:
        return []
    results = []
    try:
        for provider, (policy, cache) in stores(project, presenter, roots, profile).items():
            result = check(provider, policy, cache)
            results.append(result)
            if result.get("checked") and result["status"] not in ("off", "unchanged"):
                print(f"Icons {provider}: {result['status']}. Existing snapshots are unchanged.", file=sys.stderr)
    except (OSError, ValueError) as error:
        print(f"Icon monitoring unavailable: {error}. Locked output remains offline.", file=sys.stderr)
    return results


def approve(project, presenter, provider, terms_hash, scope="project", updates="auto", roots=None, profile=None):
    if provider not in PROVIDERS or updates not in ("auto", "notify", "off"):
        raise ValueError("Choose an official provider and a supported update policy.")
    meta = metadata(provider)
    if meta["termsHash"] != terms_hash:
        raise ValueError("Terms changed or were not accepted. Inspect and approve the current terms hash.")
    paths = locations(project, presenter, roots, profile)
    if scope not in paths:
        raise ValueError("Selected approval scope is unavailable.")
    root = paths[scope]
    cache = contained(root, root / "icons" / "cache" / provider)
    with writing(cache):
        result = cache_pack(cache, meta)
        atomic_json(contained(root, root / "icons" / "approvals" / f"{provider}.json"),
                    {"schemaVersion": 1, "provider": provider, "termsHash": terms_hash, "updates": updates})
        atomic_json(cache / "check.json", {"provider": provider, "attemptedAt": time.time(),
                                         "status": "approved", "packHash": result["packHash"]})
    return result


def load_snapshot(presenter, lock, services, choices):
    if (not isinstance(lock, dict) or set(lock) != {"schemaVersion", "services", "choicesHash", "icons", "hash"}
            or type(lock["schemaVersion"]) is not int or lock["schemaVersion"] != 1
            or not isinstance(lock["icons"], dict) or lock["services"] != services
            or lock["choicesHash"] != digest(choices)
            or lock.get("hash") != digest({k: v for k, v in lock.items() if k != "hash"})):
        raise ValueError("Icon selections/lock changed; use --refresh-icons.")
    result = {}
    for service, item in lock["icons"].items():
        required = {"name", "id", "sha256", "source", "download", "terms", "termsHash", "packHash"}
        if (not isinstance(item, dict) or set(item) != required or service not in services
                or any(not isinstance(item[key], str) for key in required)
                or any(not SHA.fullmatch(item[key]) for key in ("sha256", "termsHash", "packHash"))):
            raise ValueError("Invalid locked icon identity.")
        provider = service.split(":", 1)[0]
        if (item["source"] != PROVIDERS[provider]["source"]
                or hashlib.sha256(item["terms"].encode()).hexdigest() != item["termsHash"]):
            raise ValueError("Invalid locked icon provenance.")
        validate_url(item["download"], PROVIDERS[provider]["hosts"])
        path = contained(presenter, presenter / "icon-assets" / f"{item['sha256']}.svg")
        data = safe_svg(path.read_bytes())
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("Locked icon bytes changed; restore them or use --refresh-icons.")
        result[service] = data
    return result


def resolve_icons(views, presenter, project, roots=None, profile=None, refresh=False):
    services = sorted({node["service"] for view in views.values() for node in view["components"]
                       if node.get("service")})
    lock_path = presenter / "icons.lock.json"
    choices_path = presenter / "icon-selections.json"
    choices = read_json(choices_path) if choices_path.exists() else {}
    if (not isinstance(choices, dict) or any(not isinstance(k, str) or not SERVICE.fullmatch(k)
            or not isinstance(v, str) or not v or len(v) > 512 for k, v in choices.items())):
        raise ValueError("icon-selections.json maps service IDs to exact catalogue filenames.")
    if lock_path.exists() and not refresh:
        return load_snapshot(presenter, read_json(lock_path), services, choices)
    if not services:
        if lock_path.exists():
            lock = {"schemaVersion": 1, "services": [], "choicesHash": digest(choices), "icons": {}}
            lock["hash"] = digest(lock)
            atomic_json(lock_path, lock)
        return {}
    available = stores(project, presenter, roots, profile)
    selected = {}
    for service in services:
        provider, id_ = service.split(":", 1)
        if provider not in available:
            print(f"Icons: {service} has no approved cache; retaining its text label.", file=sys.stderr)
            continue
        policy, cache = available[provider]
        current_path = cache / "current.json"
        if not current_path.exists():
            print(f"Icons: {service} is not cached; explicitly fetch the approved pack.", file=sys.stderr)
            continue
        current = cached_manifest(current_path, provider)
        if current["termsHash"] != policy["termsHash"]:
            raise ValueError("Cached icon terms differ from approval; inspect and approve explicitly.")
        names = {id_, *ALIASES.get(provider, {}).get(id_, ())}
        matches = [item for item in current["items"] if
                   (item["name"] == choices[service] if service in choices else slug(item["name"]) in names)]
        matches = {item["sha256"]: item for item in matches}
        if len(matches) != 1:
            print(f"Icons: {service} is missing or ambiguous; use icons.py list and icon-selections.json. "
                  "Retaining its text label.", file=sys.stderr)
            continue
        item = next(iter(matches.values()))
        path = contained(cache, cache / current["packHash"] / f"{item['sha256']}.svg")
        data = safe_svg(path.read_bytes())
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("Cached icon hash mismatch; fetch a clean pack.")
        destination = contained(presenter, presenter / "icon-assets" / f"{item['sha256']}.svg")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError("Refusing to overwrite a changed snapshot icon.")
        destination.write_bytes(data)
        selected[service] = {**item, **{key: current[key] for key in
                            ("source", "download", "terms", "termsHash", "packHash")}}
    lock = {"schemaVersion": 1, "services": services, "choicesHash": digest(choices), "icons": selected}
    lock["hash"] = digest(lock)
    atomic_json(lock_path, lock)
    return load_snapshot(presenter, lock, services, choices)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--presenter-dir", type=Path)
    parser.add_argument("--user-library")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("providers")
    inspect = sub.add_parser("inspect")
    inspect.add_argument("provider", choices=PROVIDERS)
    accept = sub.add_parser("approve")
    accept.add_argument("provider", choices=PROVIDERS)
    accept.add_argument("--terms-hash", required=True, help="Exact termsHash displayed by inspect")
    accept.add_argument("--scope", choices=("project", "repo", "user", "machine"), default="project")
    accept.add_argument("--updates", choices=("auto", "notify", "off"), default="auto")
    for command in ("check", "fetch", "list", "revoke"):
        child = sub.add_parser(command)
        child.add_argument("provider", choices=PROVIDERS)
        if command in ("check", "fetch"):
            child.add_argument("--force", action="store_true", help="Check even within the daily interval")
        if command == "revoke":
            child.add_argument("--scope", choices=("project", "repo", "user", "machine"), default="project")
    args = parser.parse_args()
    project = args.project_root.resolve(strict=True)
    presenter = (args.presenter_dir or project / "architecture").resolve()
    if not presenter.is_relative_to(project):
        parser.error("Presenter directory must be inside the project.")
    try:
        if args.command == "providers":
            print(json.dumps({key: value["source"] for key, value in PROVIDERS.items()}, indent=2))
        elif args.command == "inspect":
            print(json.dumps(metadata(args.provider), indent=2))
        elif args.command == "approve":
            result = approve(project, presenter, args.provider, args.terms_hash, args.scope,
                             args.updates, profile=args.user_library)
            print(f"Approved and cached {args.provider}: {result['packHash']}. "
                  f"{len(result['items'])} SVGs supported; {len(result['rejected'])} rejected.")
        elif args.command == "revoke":
            paths = locations(project, presenter, profile=args.user_library)
            path = contained(paths[args.scope], paths[args.scope] / "icons" / "approvals" / f"{args.provider}.json")
            path.unlink(missing_ok=True)
            print("Removed this scope's approval. Lower scopes may still approve the provider; inspect them too.")
        else:
            available = stores(project, presenter, profile=args.user_library)
            if args.provider not in available:
                raise ValueError("Provider has no approval; inspect its terms, then explicitly approve.")
            policy, cache = available[args.provider]
            if args.command == "list":
                print(json.dumps([{**item, "id": slug(item["name"]),
                                   "serviceId": args.provider + ":" + slug(item["name"])}
                                  for item in cached_manifest(cache / "current.json", args.provider)["items"]], indent=2))
            else:
                result = check(args.provider, policy, cache, args.force or args.command == "fetch",
                               args.command == "fetch")
                print(json.dumps(result, indent=2))
                if result["status"] in ("terms-changed", "unavailable", "busy"):
                    parser.exit(2, "No new pack loaded. Existing cache/snapshots were preserved.\n")
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    main()
