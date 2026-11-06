"""The release checker of the publishing pipeline (docs/publishing_pipeline.md).

Each sub-command is one step a workflow runs; section numbers (§n) are that
document's. Nothing here holds a credential: the GitHub token and the Google
access token come from the environment the workflow gives the step.

    build          §3    the candidate: deploy/ from the inclusion list
    verify         §4.2  the candidate re-judged as data, with main's code
    check-version  §4.3  the deployed version is the verified artifact, exactly
    decide         §4.4  the GitHub-only conditions of a promotion
    check-channel  §4.4  promote, step 3: the channel still holds the version
    promote        §4.4  promote, steps 4-6: the clone by version and its read-back
"""

from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import gzip
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

from . import contract as c
from . import envelope as e

ROOT = pathlib.Path(__file__).resolve().parents[2]
RELEASE = ROOT / "release"
SITE = "site"
PUBLISHER = ".github/workflows/publish.yml"
RECORD_ARTIFACT = "release-record"
MARGIN = dt.timedelta(days=1)


class Refused(Exception):
    """A release condition that does not hold. The message is the reason the
    job summary shows."""


class NothingToPromote(Refused):
    """`decide`'s conditions 1 and 2: not an error, the run ends green (§4.4)."""


# --- the declarations ------------------------------------------------------------


def _lines(path: pathlib.Path) -> list[str]:
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def inclusion(root: pathlib.Path = ROOT) -> list[str]:
    """`release/include.txt`: globs under `site/`, one per line."""
    globs = _lines(root / "release" / "include.txt")
    for g in globs:
        if not g.startswith(f"{SITE}/") or ".." in g.split("/"):
            raise Refused(f"include.txt: {g!r} is not a path under {SITE}/")
    return globs


def media_types(root: pathlib.Path = ROOT) -> dict[str, str]:
    """`release/media_types.txt`: `.ext  type` — the only extensions allowed."""
    out = {}
    for line in _lines(root / "release" / "media_types.txt"):
        ext, kind = line.split()
        out[ext] = kind
    return out


def protected(root: pathlib.Path = ROOT) -> list[str]:
    """`release/protected.txt`: paths or prefixes ending in `/` a previewable PR
    must not touch (§2)."""
    return _lines(root / "release" / "protected.txt")


def touches_protected(changed: list[str], rules: list[str]) -> list[str]:
    hits = []
    for path in changed:
        for rule in rules:
            if (rule.endswith("/") and path.startswith(rule)) or path == rule:
                hits.append(path)
                break
    return hits


def profiles(root: pathlib.Path = ROOT) -> list[e.DeclaredProfile]:
    """`release/profiles.json`: the one declaration of the profiles and their
    public passwords (N22, PLAN §3.2)."""
    data = json.loads((root / "release" / "profiles.json").read_text(encoding="utf-8"))
    return [e.DeclaredProfile(p["id"], p["label"], p["password"], tuple(p["reports"])) for p in data["profiles"]]


# --- artifacts, fetched and extracted safely (IMPL-1-01) --------------------------


def safe_extract(archive: bytes, out: pathlib.Path) -> list[str]:
    """Extracts a zip into `out`, which must not exist, refusing — before
    anything is written — any entry that is absolute, holds `..`, a backslash
    or a drive, repeats, or is anything but a regular file or directory. An
    artifact is the output of a job that may have run a PR's code: its names
    are data, and no name may reach outside `out`."""
    import io
    import stat
    import zipfile

    if out.exists():
        raise Refused(f"{out} exists: an artifact is extracted into a fresh directory")
    with zipfile.ZipFile(io.BytesIO(archive)) as zf:
        infos = zf.infolist()
        seen: set[str] = set()
        for info in infos:
            name = info.filename
            parts = name.rstrip("/").split("/")
            mode = info.external_attr >> 16
            if (not name or name.startswith("/") or "\\" in name or ":" in parts[0] or any(p in ("", ".", "..") for p in parts)):
                raise Refused(f"artifact entry {name!r} is not a plain relative path")
            kind = stat.S_IFMT(mode)
            if kind and kind not in (stat.S_IFREG, stat.S_IFDIR):
                raise Refused(f"artifact entry {name!r} is not a regular file or directory")
            key = name.rstrip("/")
            if key in seen:
                raise Refused(f"artifact entry {name!r} repeats")
            seen.add(key)
        out.mkdir(parents=True)
        root = out.resolve()
        written = []
        for info in infos:
            target = (out / info.filename).resolve()
            if root not in target.parents and target != root:
                raise Refused(f"artifact entry {info.filename!r} leaves the destination")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "xb") as dst:
                dst.write(src.read())
            written.append(info.filename)
        return written


def fetch_artifact(repo: str, run_id: int, name: str, out: pathlib.Path, token: str) -> list[str]:
    """The one artifact `name` of a run, downloaded through GitHub's API —
    never by an action that extracts it unchecked — and extracted safely."""
    artifacts = _paged(f"{GITHUB}/repos/{repo}/actions/runs/{run_id}/artifacts", token, "artifacts")
    matching = [a for a in artifacts if a["name"] == name and not a.get("expired")]
    if len(matching) != 1:
        raise Refused(f"run {run_id} holds {len(matching)} artifacts named {name!r}; exactly one is needed")
    return safe_extract(_download(matching[0]["archive_download_url"], token), out)


# --- §3: build -------------------------------------------------------------------


def included_files(root: pathlib.Path, globs: list[str]) -> list[str]:
    site = root / SITE
    found = []
    for path in sorted(site.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise Refused(f"{rel} is a symbolic link")
        if path.is_file() and any(fnmatch.fnmatchcase(rel, g) for g in globs):
            found.append(rel)
    return found


def build(root: pathlib.Path, out: pathlib.Path) -> list[str]:
    """Copies the included files of `site/` to `out/`, which must not exist:
    a fresh directory, never one with leftovers (PLAN §3.4)."""
    if out.exists():
        raise Refused(f"{out} exists: the deploy directory is built fresh")
    files = included_files(root, inclusion(root))
    for rel in files:
        dest = out / pathlib.PurePosixPath(rel).relative_to(SITE)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((root / rel).read_bytes())
    return files


# --- §4.2: verify -----------------------------------------------------------------


def listing(deploy: pathlib.Path) -> list[tuple[str, str]]:
    """(path, sha256) of every file, sorted; refuses anything but plain files."""
    out = []
    for path in sorted(deploy.rglob("*")):
        rel = path.relative_to(deploy).as_posix()
        if path.is_symlink():
            raise Refused(f"{rel} is a symbolic link")
        if path.is_file():
            out.append((rel, hashlib.sha256(path.read_bytes()).hexdigest()))
        elif not path.is_dir():
            raise Refused(f"{rel} is not a plain file")
    return out


def canonical_digest(files: list[tuple[str, str]]) -> str:
    text = "".join(f"{sha}  {rel}\n" for rel, sha in files)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


#: What clear report data and key material look like, by content (PLAN §3.4).
PARQUET_MAGIC = b"PAR1"
PAYLOAD_MAGIC = e.PAYLOAD_MAGIC
SOURCE_MAP = b"sourceMappingURL"


def _package(deploy: pathlib.Path) -> pathlib.Path:
    manifests = sorted(deploy.rglob("manifest.json"))
    if len(manifests) != 1:
        raise Refused(f"{len(manifests)} package manifests in the artifact; exactly one is expected")
    return manifests[0]


#: §5.1: what `read_live` returns when live has no package — the first release.
NO_LIVE = None


def verify(
    root: pathlib.Path,
    deploy: pathlib.Path,
    pr: int | None = None,
    head_sha: str | None = None,
    *,
    live,
    now: dt.datetime | None = None,
) -> dict:
    """The candidate re-judged as data (pipeline §4.2, package_gate §1): inclusion,
    media types, the declarations, the inventory and the entitlements, the package
    through the whole matrix, each report against the contract, the package
    live, and the inspection by content. `live()` returns live's package —
    (manifest bytes, envelopes by file name) — or `NO_LIVE`. Returns the body
    of `release.json`."""
    declared = profiles(root)
    declared_map = {p.id: set(p.reports) for p in declared}
    try:  # package_gate §2.2, step 1: before any candidate byte is read (GIMPL-1-01)
        contract, public = c.load(root)
        c.declarations_agree(contract, declared_map)
    except c.Refused as refusal:
        raise Refused(str(refusal)) from None
    globs = [g[len(SITE) + 1 :] for g in inclusion(root)]
    allowed = media_types(root)
    files = listing(deploy)
    for rel, _ in files:
        if not any(fnmatch.fnmatchcase(rel, g) for g in globs):
            raise Refused(f"{rel} is not under the inclusion list")
        if pathlib.PurePosixPath(rel).suffix not in allowed:
            raise Refused(f"{rel}: extension not in media_types.txt")
        if rel.endswith(".map"):
            raise Refused(f"{rel} is a source map")
        if rel.startswith("__/"):
            raise Refused(f"{rel} is under Hosting's reserved __/ URLs")
    manifest_path = _package(deploy)
    package_dir = manifest_path.parent
    manifest_raw = manifest_path.read_bytes()
    try:
        manifest = e.validate_manifest(manifest_raw)
    except e.Refused as refusal:
        raise Refused(f"package manifest refused: {refusal}") from None
    envelopes = {}
    for entry in manifest.reports.values():
        path = package_dir / entry.file
        if not path.is_file():
            raise Refused(f"{entry.file} is in the manifest and not in the artifact")
        envelopes[entry.file] = path.read_bytes()
    stray = {p.name for p in package_dir.glob("*.bice")} - set(envelopes)
    if stray:
        raise Refused(f"envelopes not in the manifest: {sorted(stray)}")
    manifest_map = {pid: set(p.reports) for pid, p in manifest.profiles.items()}
    try:
        c.inventory_exact(contract, set(manifest.reports))  # step 2
        c.entitlements_exact(manifest_map, declared_map)  # step 3
    except c.Refused as refusal:
        raise Refused(str(refusal)) from None
    passwords = {p.id: p.password for p in declared}
    try:
        e.check_package(manifest_raw, envelopes, passwords)
    except (e.Refused, ValueError) as refusal:
        raise Refused(f"package refused: {refusal}") from None
    values = []
    try:
        for report in sorted(manifest.reports):
            pid = sorted(manifest.entitled(report))[0]
            key = e.login(manifest, pid, passwords[pid])
            totals, parquet = e.open_report(manifest, envelopes[manifest.reports[report].file], report, key)
            values.append(c.check_payload(contract, contract.reports[report], totals, parquet))
    except c.Refused as refusal:
        raise Refused(str(refusal)) from None
    except Exception:  # never a value in the log (package_gate §7)
        raise Refused(f"{c.PARQUET_UNREADABLE}: a report could not be checked") from None
    checked_at = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    found = live()
    if found is NO_LIVE:
        live_record: object = "none"
    else:
        live_manifest_raw, live_files = found
        try:
            e.check_against_live(manifest_raw, envelopes, live_manifest_raw, live_files, passwords)
        except e.Refused as refusal:
            raise Refused(f"against live: {refusal}") from None
        live_manifest = e.validate_manifest(live_manifest_raw)
        live_record = sorted(f"package/{r.file}" for r in live_manifest.reports.values())
    deks = _deks(manifest, envelopes, passwords)
    envelope_paths = {(package_dir / name).relative_to(deploy).as_posix() for name in envelopes}
    manifest_rel = manifest_path.relative_to(deploy).as_posix()
    haystacks = {}
    for rel, _ in files:
        data = (deploy / rel).read_bytes()
        if rel not in envelope_paths:
            if PARQUET_MAGIC in data:
                raise Refused(f"{rel} holds a Parquet magic outside an envelope")
            if PAYLOAD_MAGIC in data:
                raise Refused(f"{rel} holds a clear payload outside an envelope")
            haystacks[rel] = c.manifest_labels(manifest) if rel == manifest_rel else data
        if SOURCE_MAP in data:
            raise Refused(f"{rel} references a source map")
        lowered = data.lower()
        for dek in deks:
            if dek in data or dek.hex().encode() in lowered:
                raise Refused(f"{rel} holds a data key in the clear")
    try:
        c.inspect(haystacks, values, public)
    except c.Refused as refusal:
        raise Refused(str(refusal)) from None
    return {
        "pr": pr,
        "head_sha": head_sha,
        "package_id": manifest.package_id.hex(),
        "files": [{"path": rel, "sha256": sha} for rel, sha in files],
        "digest": canonical_digest(files),
        "live": live_record,
        "checked_at": checked_at,
    }


def _public_get(url: str) -> tuple[int, bytes]:
    """A GET with no credential and no redirect followed (package_gate §5.1)."""
    request = urllib.request.Request(url, headers={"User-Agent": "bi-como-codigo-release", "Cache-Control": "no-cache"})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=60) as response:
            body = response.read()
            if response.headers.get("Content-Encoding", "identity") not in ("identity", ""):
                body = gzip.decompress(body) if response.headers.get("Content-Encoding") == "gzip" else b""
            return response.status, body
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (OSError, EOFError, ValueError):  # transport, TLS, a truncated gzip (GIMPL-1-03)
        return 0, b""


def read_live(site: str, get=_public_get):
    """§5.1: live's package from the site's public URL, or `NO_LIVE` on a 404
    of the manifest. Anything else but 200 is `live_unreadable`."""
    base = f"https://{site}.web.app/package/"
    status, body = get(base + "manifest.json")
    if status == 404:
        return NO_LIVE
    if status != 200:
        raise Refused(f"{e.LIVE_UNREADABLE}: live's manifest answered {status}")
    try:
        manifest = e.validate_manifest(body)
    except e.Refused:
        raise Refused(f"{e.LIVE_UNREADABLE}: live's manifest is not valid") from None
    files = {}
    for entry in manifest.reports.values():
        status, data = get(base + entry.file)
        if status != 200 or len(data) != entry.size or hashlib.sha256(data).hexdigest() != entry.sha256:
            raise Refused(f"{e.LIVE_UNREADABLE}: live's {entry.file} does not match its manifest")
        files[entry.file] = data
    return body, files


def _deks(manifest: e.Manifest, envelopes: dict[str, bytes], passwords: dict[str, str]) -> list[bytes]:
    from cryptography.hazmat.primitives.keywrap import aes_key_unwrap

    keys = {pid: e.login(manifest, pid, pw) for pid, pw in passwords.items()}
    out = []
    for report in manifest.reports.values():
        header, _ = e.parse_header(envelopes[report.file])
        pid = sorted(manifest.entitled(report.id))[0]
        slot = next(s for s in header.slots if s.profile_id == pid.encode("ascii"))
        out.append(aes_key_unwrap(keys[pid].kek, slot.wrapped_key))
    return out


# --- HTTP, for the two APIs ------------------------------------------------------------


def _http(url: str, token: str | None = None, accept: str = "application/json") -> tuple[int, dict, bytes]:
    request = urllib.request.Request(url, headers={"Accept": accept, "User-Agent": "bi-como-codigo-release"})
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _download(url: str, token: str) -> bytes:
    """An artifact's zip (IMPL-2-01): GitHub answers its API URL with a
    redirect to signed storage, which refuses a request that still carries
    GitHub's token. So the redirect is not followed with the token: its
    `Location` is fetched with no `Authorization` at all."""
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "bi-como-codigo-release",
                                                   "Authorization": f"Bearer {token}"})
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=60) as response:
            if response.status == 200:
                return response.read()
            raise Refused(f"{url} answered {response.status}")
    except urllib.error.HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308) or not error.headers.get("Location"):
            raise Refused(f"{url} answered {error.code}") from None
        location = error.headers["Location"]
    if urllib.parse.urlsplit(location).scheme != "https":
        raise Refused(f"{url} redirected to a non-https location")
    status, _, body = _http(location, accept="*/*")
    if status != 200:
        raise Refused(f"the artifact's storage answered {status}")
    return body


def _json(url: str, token: str | None) -> dict:
    status, _, body = _http(url, token)
    if status != 200:
        raise Refused(f"GET {url} answered {status}")
    return json.loads(body)


#: A collection longer than this is refused, never read as if complete.
PAGES_MAX = 50


def _paged(url: str, token: str, key: str | None = None) -> list[dict]:
    """Every item of a GitHub collection, 100 a page (IMPL-1-07)."""
    items: list[dict] = []
    sep = "&" if "?" in url else "?"
    for page in range(1, PAGES_MAX + 1):
        data = _json(f"{url}{sep}per_page=100&page={page}", token)
        batch = data[key] if key else data
        items.extend(batch)
        if len(batch) < 100:
            total = data.get("total_count") if key else None
            if isinstance(total, int) and total > len(items):
                # The filtered runs API stops at 1,000 results (IMPL-2-02).
                raise Refused(f"{url} lists {len(items)} of {total}: not read as complete")
            return items
    raise Refused(f"{url} has more than {PAGES_MAX} pages: not read as complete")


HOSTING = "https://firebasehosting.googleapis.com/v1beta1"


def channel(site: str, name: str, token: str) -> dict | None:
    status, _, body = _http(f"{HOSTING}/sites/{site}/channels/{name}", token)
    if status == 404:
        return None
    if status != 200:
        raise Refused(f"channel {name} of {site}: {status}")
    return json.loads(body)


def channel_version(data: dict | None) -> str | None:
    name = ((data or {}).get("release") or {}).get("version", {}).get("name")
    return name.rsplit("/", 1)[-1] if name else None


# --- §4.3, step 5: the version is the artifact ---------------------------------------


def version_files(site: str, version: str, token: str) -> dict[str, str]:
    files, page = {}, ""
    while True:
        url = f"{HOSTING}/sites/{site}/versions/{version}/files?pageSize=1000" + (f"&pageToken={page}" if page else "")
        data = _json(url, token)
        for f in data.get("files", []):
            if f.get("status") != "ACTIVE":
                raise Refused(f"{f.get('path')} is {f.get('status')}, not ACTIVE")
            files[f["path"].lstrip("/")] = f.get("hash", "")
        page = data.get("nextPageToken", "")
        if not page:
            return files


def served(base_url: str, rel: str) -> bytes:
    status, headers, body = _http(f"{base_url.rstrip('/')}/{urllib.parse.quote(rel)}", accept="*/*")
    if status != 200:
        raise Refused(f"{rel} served {status}")
    encoding = {k.lower(): v for k, v in headers.items()}.get("content-encoding", "identity").lower()
    if encoding == "gzip":
        return gzip.decompress(body)
    if encoding not in ("identity", ""):
        raise Refused(f"{rel} served with an encoding this check cannot read: {encoding}")
    return body


#: The files Hosting adds to every version under its reserved `/__/` URLs —
#: measured on the first real deploy (T1, 2026-11-06): they are Hosting's, not
#: the artifact's, and the artifact may hold nothing under `__/` (verify).
HOSTING_RESERVED = frozenset({"__/firebase/init.js", "__/firebase/init.json"})


def check_version(record: dict, site: str, version: str, base_url: str, token: str) -> None:
    """Exact or nothing (PIPE-1-06): the version's ACTIVE paths are the
    artifact's plus exactly Hosting's reserved ones, and every served body
    of the artifact's paths is the artifact's bytes."""
    expected = {f["path"]: f["sha256"] for f in record["files"]}
    listed = version_files(site, version, token)
    if set(listed) != set(expected) | HOSTING_RESERVED:
        raise Refused(f"version {version} holds {sorted(set(listed) ^ (set(expected) | HOSTING_RESERVED))} unlike the artifact")
    for rel, sha in expected.items():
        if hashlib.sha256(served(base_url, rel)).hexdigest() != sha:
            raise Refused(f"{rel} as served is not the verified artifact's bytes")


# --- §4.4: decide -------------------------------------------------------------------


GITHUB = "https://api.github.com"


# --- package_gate §5.2, §5.4: what `preview` checks, with the API only ------------------

#: §5.2, step 3: live's release must be at least this much older than verify's read.
LIVE_SETTLED = dt.timedelta(minutes=10)


def check_listing(deploy: pathlib.Path, record: dict) -> None:
    """§5.4: the artifact is, file for file, what `verify` listed — nothing parsed."""
    files = listing(deploy)
    if [{"path": rel, "sha256": sha} for rel, sha in files] != record["files"] or canonical_digest(files) != record["digest"]:
        raise Refused("the verified artifact changed")


def _when(text: str) -> dt.datetime:
    """An RFC 3339 time with its offset; a time without one is refused."""
    when = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise ValueError("a time without its offset")
    return when


def bind_live(site: str, record: dict, token: str) -> str:
    """§5.2: the live version `verify` compared with, read through Hosting's
    API, or `"none"` for no live release."""
    compared = record.get("live")
    checked_at = record.get("checked_at")
    if not (compared == "none" or isinstance(compared, list)) or not isinstance(checked_at, str):
        raise Refused("the verified record names no live comparison")
    changed = Refused("live changed during this run; re-run the candidate")
    try:
        data = channel(site, "live", token)
        version = channel_version(data)
        if version is None:
            if compared != "none":
                raise changed
            return "none"
        released = _when(data["release"]["releaseTime"])
        settled = released <= _when(checked_at) - LIVE_SETTLED
        held = sorted(p for p in version_files(site, version, token) if p.startswith("package/"))
    except Refused as refusal:
        if refusal is changed:
            raise
        raise Refused("live could not be read") from None
    except Exception:  # transport, shape, time (GIMPL-1-03): never a pass, never "changed"
        raise Refused("live could not be read") from None
    expected = [] if compared == "none" else sorted([*compared, "package/manifest.json"])
    if held != expected:
        raise changed
    if not settled:
        raise changed
    return version


def path_is_publisher(path: str) -> bool:
    """A run's `path`, bare or as GitHub documents it, `path@ref` (PIPE-2-01)."""
    file, _, ref = path.partition("@")
    return file == PUBLISHER and ref in ("", "main", "refs/heads/main")


@dataclass(frozen=True)
class Record:
    pr: int
    head_sha: str
    candidate_run: int
    version: str
    channel: str
    url: str
    expires: str
    digest: str
    artifact_id: int
    artifact_sha256: str
    live_version: str


def select_record(runs: list[dict], head_sha: str, artifacts_of, download) -> Record:
    """§4.4, condition 3. `runs` are the publisher's runs listed by its
    workflow ID; `artifacts_of(run)` lists a run's artifacts and `download(a)`
    returns one's JSON bytes — both GitHub's."""
    eligible = [
        r for r in runs
        if path_is_publisher(r.get("path", ""))
        and r.get("event") == "workflow_run"
        and r.get("head_branch") == "main"
        and r.get("conclusion") == "success"
    ]
    for run in sorted(eligible, key=lambda r: (r["run_started_at"], r["run_attempt"]), reverse=True):
        records = [a for a in artifacts_of(run) if a["name"] == RECORD_ARTIFACT and not a.get("expired")]
        if not records:
            continue
        if len(records) > 1:
            raise Refused(f"run {run['id']} holds {len(records)} release records: ambiguous")
        raw = download(records[0])
        body = json.loads(raw)
        if body.get("head_sha") != head_sha:
            continue
        live_version = body.get("live_version")
        if not isinstance(live_version, str) or not live_version or any(ch in live_version for ch in ":/@ "):
            raise Refused(f"the record of run {run['id']} names no live version (package_gate §5.2): a new preview is needed")
        return Record(
            int(body["pr"]), body["head_sha"], int(body["candidate_run"]), body["version"], body["channel"],
            body["url"], body["expires"], body["digest"], int(records[0]["id"]), hashlib.sha256(raw).hexdigest(),
            live_version,
        )
    raise Refused(f"no authenticated release record for {head_sha}")


def margin_ok(expires: str, now: dt.datetime) -> bool:
    when = dt.datetime.fromisoformat(expires.replace("Z", "+00:00"))
    return when - now > MARGIN


def check_tip(repo: str, sha: str, token: str) -> None:
    """§4.4, condition 1, and `promote` step 2."""
    tip = _json(f"{GITHUB}/repos/{repo}/commits/main", token)["sha"]
    if tip != sha:
        raise NothingToPromote(f"{sha} is not the tip of main ({tip}): a later merge promotes")


#: GitHub lists at most 3,000 files of a PR; a longer PR cannot be judged.
PR_FILES_MAX = 3000


def admit(repo: str, head_repo: str, head_sha: str, token: str) -> int:
    """§4.1: the PR to preview, or a refusal. Returns its number."""
    if head_repo != repo:
        raise Refused(f"the candidate comes from {head_repo}, a fork: no preview")
    api = f"{GITHUB}/repos/{repo}"
    pulls = [p for p in _json(f"{api}/commits/{head_sha}/pulls", token)
             if p["state"] == "open" and p["head"]["sha"] == head_sha and p["head"]["repo"]["full_name"] == repo]
    if len(pulls) != 1:
        raise Refused(f"{len(pulls)} open PRs have the head {head_sha}; exactly one is needed")
    number = pulls[0]["number"]
    detail = _json(f"{api}/pulls/{number}", token)
    expected = detail.get("changed_files")
    if not isinstance(expected, int) or expected >= PR_FILES_MAX:
        raise Refused(f"PR #{number} changes {expected!r} files: its files cannot all be listed, no preview")
    files = _paged(f"{api}/pulls/{number}/files", token)
    if len(files) != expected:
        raise Refused(f"PR #{number} lists {len(files)} of its {expected} files: no preview")
    changed = [f["filename"] for f in files] + [f["previous_filename"] for f in files if f.get("previous_filename")]
    hits = touches_protected(changed, protected())
    if hits:
        raise Refused(f"PR #{number} touches the protected set ({', '.join(sorted(set(hits)))}): no preview, no live update")
    return number


def decide(repo: str, sha: str, token: str, now: dt.datetime, git=subprocess.run) -> Record:
    """§4.4, `decide`: conditions 1 to 5, with GitHub's API only."""
    api = f"{GITHUB}/repos/{repo}"
    check_tip(repo, sha, token)
    pulls = [p for p in _json(f"{api}/commits/{sha}/pulls", token) if p.get("merged_at")]
    if len(pulls) != 1:
        raise NothingToPromote(f"{sha} is the merge of {len(pulls)} PRs, not one: nothing to promote")
    pr = pulls[0]
    if pr["head"]["repo"]["full_name"] != repo:
        raise Refused(f"PR #{pr['number']} is not from {repo}")
    head = pr["head"]["sha"]
    workflow = _json(f"{api}/actions/workflows/publish.yml", token)["id"]
    runs = _paged(f"{api}/actions/workflows/{workflow}/runs?event=workflow_run&branch=main&status=success", token, "workflow_runs")
    record = select_record(
        runs, head,
        lambda run: _paged(f"{api}/actions/runs/{run['id']}/artifacts", token, "artifacts"),
        lambda artifact: _artifact_json(artifact, token),
    )
    if record.pr != pr["number"]:
        raise Refused(f"the record names PR #{record.pr}, not #{pr['number']}")
    paths = [g for g in inclusion()]
    git(["git", "fetch", "--no-tags", "--depth=1", "origin", head], check=True)
    same = git(["git", "diff", "--quiet", head, sha, "--", *paths], check=False).returncode == 0
    if not same:
        raise Refused(f"the merge changed included content after the preview of {head}: a new preview is needed")
    if not margin_ok(record.expires, now):
        raise Refused(f"the preview expires {record.expires}, within a day: recover through a new PR (§4.5)")
    return record


def _artifact_json(artifact: dict, token: str) -> bytes:
    """The one JSON file of a `release-record` artifact (a zip)."""
    import io
    import zipfile

    body = _download(artifact["archive_download_url"], token)
    with zipfile.ZipFile(io.BytesIO(body)) as archive:
        names = archive.namelist()
        if names != ["release-record.json"]:
            raise Refused(f"artifact {artifact['id']} holds {names}, not release-record.json")
        return archive.read("release-record.json")  # read in memory; nothing is extracted


# --- §4.4: promote -------------------------------------------------------------------


def clone_command(site: str, version: str) -> list[str]:
    """The one place the clone is written (T4b): by version, never by channel."""
    if not version or any(c in version for c in ":/@ "):
        raise Refused(f"{version!r} is not a version ID")
    return ["firebase", "hosting:clone", f"{site}@{version}", f"{site}:live", "--project", os.environ.get("FIREBASE_PROJECT", site)]


def promote(site: str, version: str, live_version: str, token: str, run=subprocess.run) -> str:
    """package_gate §5.3, in one command: already live → end; otherwise live
    must still be the version the preview bound; then the clone."""
    try:
        before = channel_version(channel(site, "live", token))
    except Exception:  # transport included (GIMPL-1-03); nothing cloned
        raise Refused("live could not be read; nothing was cloned") from None
    if before == version:
        return "already live"
    if (before or "none") != live_version:
        raise Refused(f"live changed since this preview ({live_version} → {before or 'none'}): a new PR previews against it (§4.5)")
    result = run(clone_command(site, version), check=False)
    if result.returncode != 0:
        raise Refused(f"hosting:clone exited {result.returncode}")
    try:
        after = channel_version(channel(site, "live", token))
    except Exception:
        raise Refused(f"the clone ran, and live could not be read back: whether it serves {version} is unconfirmed") from None
    if after != version:
        raise Refused(f"live serves {after}, not {version}")
    return "promoted"


# --- §5: the bindings, read back --------------------------------------------------


def check_bindings(policies: dict[str, dict], pool: str, environments: dict[str, str]) -> None:
    """T8's binding oracle: each service account's policy holds exactly one
    binding, `roles/iam.workloadIdentityUser`, with exactly one member — the
    principalSet of its own environment. `environments` maps account → env."""
    for account, env in environments.items():
        bindings = policies[account].get("bindings", [])
        expected = [{"role": "roles/iam.workloadIdentityUser",
                     "members": [f"principalSet://iam.googleapis.com/{pool}/attribute.environment/{env}"]}]
        found = [{"role": b["role"], "members": sorted(b["members"])} for b in bindings]
        if found != expected:
            raise Refused(f"{account}'s policy is {found}, not exactly {expected}")


def firebase_config(root: pathlib.Path, site: str, out: pathlib.Path) -> None:
    """The protected `firebase.json` with the configured site, written at run
    time, so the deploy names the same site every read does (IMPL-1-05)."""
    config = json.loads((root / "firebase.json").read_text(encoding="utf-8"))
    if "site" in config["hosting"] or "target" in config["hosting"]:
        raise Refused("firebase.json must not name a site: it comes from FIREBASE_SITE")
    config["hosting"]["site"] = site
    out.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def expected_condition(repo: str, workflows: list[str]) -> str:
    refs = " || ".join(f"assertion.workflow_ref=='{repo}/{w}@refs/heads/main'" for w in workflows)
    return f"assertion.repository=='{repo}' && assertion.ref=='refs/heads/main' && ({refs})"


REQUIRED_MAPPING = {
    "google.subject": "assertion.sub",
    "attribute.repository": "assertion.repository",
    "attribute.workflow_ref": "assertion.workflow_ref",
    "attribute.ref": "assertion.ref",
    "attribute.environment": "assertion.environment",
}


def check_provider(provider: dict, repo: str, workflows: list[str]) -> None:
    """IMPL-1-06: the provider read back — active, GitHub's issuer, exactly the
    mappings §5 declares and exactly its condition."""
    if provider.get("state") != "ACTIVE" or provider.get("disabled"):
        raise Refused(f"provider state {provider.get('state')}")
    if (provider.get("oidc") or {}).get("issuerUri") != "https://token.actions.githubusercontent.com":
        raise Refused("provider issuer is not GitHub's")
    if provider.get("attributeMapping") != REQUIRED_MAPPING:
        raise Refused(f"provider mapping is {provider.get('attributeMapping')}")
    if " ".join(provider.get("attributeCondition", "").split()) != expected_condition(repo, workflows):
        raise Refused(f"provider condition is {provider.get('attributeCondition')!r}")


# --- the command line ----------------------------------------------------------------


def _summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    print(text)


def _output(values: dict) -> None:
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            for key, value in values.items():
                fh.write(f"{key}={value}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bi_como_codigo.release")
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    b.add_argument("--out", type=pathlib.Path, required=True)
    v = sub.add_parser("verify")
    v.add_argument("--deploy", type=pathlib.Path, required=True)
    v.add_argument("--record", type=pathlib.Path, required=True)
    v.add_argument("--pr", type=int)
    v.add_argument("--head-sha")
    v.add_argument("--site", required=True, help="the site whose live package the candidate is compared with")
    cl = sub.add_parser("check-listing")
    cl.add_argument("--deploy", type=pathlib.Path, required=True)
    cl.add_argument("--record", type=pathlib.Path, required=True)
    bl = sub.add_parser("bind-live")
    bl.add_argument("--site", required=True)
    bl.add_argument("--record", type=pathlib.Path, required=True)
    c = sub.add_parser("check-version")
    for name in ("--record", "--site", "--version", "--base-url"):
        c.add_argument(name, required=True)
    ch = sub.add_parser("check-channel")
    for name in ("--site", "--channel", "--version"):
        ch.add_argument(name, required=True)
    fa = sub.add_parser("fetch-artifact")
    fa.add_argument("--run", type=int, required=True)
    fa.add_argument("--name", required=True)
    fa.add_argument("--out", type=pathlib.Path, required=True)
    fc = sub.add_parser("firebase-config")
    fc.add_argument("--site", required=True)
    cp = sub.add_parser("check-provider")
    cp.add_argument("--provider", type=pathlib.Path, required=True)
    cb = sub.add_parser("check-bindings")
    cb.add_argument("--pool", required=True)
    cb.add_argument("--binding", action="append", required=True, help="account=environment=policy.json")
    sub.add_parser("decide")
    sub.add_parser("check-tip")
    a = sub.add_parser("admit")
    a.add_argument("--head-repo", required=True)
    a.add_argument("--head-sha", required=True)
    sc = sub.add_parser("show-channel")
    sc.add_argument("--site", required=True)
    sc.add_argument("--channel", required=True)
    p = sub.add_parser("promote")
    p.add_argument("--site", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--live-version", required=True)
    args = parser.parse_args(argv)
    token = os.environ.get("GOOGLE_ACCESS_TOKEN", "")
    try:
        if args.command == "build":
            files = build(ROOT, args.out)
            _summary(f"built {len(files)} file(s) into {args.out}")
        elif args.command == "verify":
            body = verify(ROOT, args.deploy, args.pr, args.head_sha, live=lambda: read_live(args.site))
            args.record.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
            _summary(f"verified {len(body['files'])} file(s); digest {body['digest']}; package {body['package_id']}")
        elif args.command == "check-listing":
            check_listing(args.deploy, json.loads(args.record.read_text(encoding="utf-8")))
            _summary("the verified artifact is still what verify listed")
        elif args.command == "bind-live":
            bound = bind_live(args.site, json.loads(args.record.read_text(encoding="utf-8")), token)
            _output({"live_version": bound})
            _summary(f"live is {bound}, as verify compared it")
        elif args.command == "check-version":
            record = json.loads(pathlib.Path(args.record).read_text(encoding="utf-8"))
            check_version(record, args.site, args.version, args.base_url, token)
            _summary(f"version {args.version} is the verified artifact, file for file")
        elif args.command == "check-channel":
            data = channel(args.site, args.channel, token)
            if data is None or channel_version(data) != args.version:
                raise Refused(f"channel {args.channel} no longer serves {args.version}: a new preview and approval are needed (§4.5)")
            status, _, body = _http(f"{HOSTING}/sites/{args.site}/versions/{args.version}", token)
            state = json.loads(body).get("status") if status == 200 else None
            if state != "FINALIZED":
                raise Refused(f"version {args.version} is {state or f'absent ({status})'}: a new preview and approval are needed (§4.5)")
            if not margin_ok(data["expireTime"], dt.datetime.now(dt.timezone.utc)):
                raise Refused(f"channel {args.channel} expires {data['expireTime']}, within a day: recover through a new PR (§4.5)")
            _summary(f"channel {args.channel} still serves {args.version}, expiring {data['expireTime']}")
        elif args.command == "fetch-artifact":
            names = fetch_artifact(os.environ["GITHUB_REPOSITORY"], args.run, args.name, args.out, os.environ["GITHUB_TOKEN"])
            _summary(f"artifact {args.name} of run {args.run}: {len(names)} file(s), extracted safely")
        elif args.command == "firebase-config":
            firebase_config(ROOT, args.site, ROOT / "firebase.json")
            _summary(f"firebase.json names site {args.site}")
        elif args.command == "check-provider":
            check_provider(json.loads(args.provider.read_text(encoding="utf-8")), os.environ["REPO"],
                           [".github/workflows/publish.yml", ".github/workflows/promote.yml"])
            _summary("provider exactly as declared")
        elif args.command == "check-bindings":
            policies, environments = {}, {}
            for item in args.binding:
                account, env, path = item.split("=", 2)
                policies[account] = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
                environments[account] = env
            check_bindings(policies, args.pool, environments)
            _summary(f"bindings exactly as declared for {', '.join(sorted(environments))}")
        elif args.command == "admit":
            number = admit(os.environ["GITHUB_REPOSITORY"], args.head_repo, args.head_sha, os.environ["GITHUB_TOKEN"])
            _output({"pr": number})
            _summary(f"PR #{number} admitted for a preview")
        elif args.command == "check-tip":
            try:  # in `promote`, a later merge after the approval stops the job red
                check_tip(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"], os.environ["GITHUB_TOKEN"])
            except NothingToPromote as later:
                raise Refused(str(later)) from None
            _summary(f"{os.environ['GITHUB_SHA']} is still the tip of main")
        elif args.command == "show-channel":
            data = channel(args.site, args.channel, token)
            if data is None or not channel_version(data):
                raise Refused(f"channel {args.channel} has no version")
            _output({"version": channel_version(data), "url": data["url"], "expires": data["expireTime"]})
            _summary(f"channel {args.channel} serves {channel_version(data)} at {data['url']}, expiring {data['expireTime']}")
        elif args.command == "decide":
            record = decide(os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_SHA"], os.environ["GITHUB_TOKEN"], dt.datetime.now(dt.timezone.utc))
            _output({"promote": "true", **{k: getattr(record, k) for k in ("pr", "version", "channel", "url", "expires", "digest", "artifact_id", "artifact_sha256", "live_version")}})
            _summary(
                f"promote PR #{record.pr}: version {record.version} of channel {record.channel}, preview {record.url}, "
                f"digest {record.digest}, record artifact {record.artifact_id} (sha256 {record.artifact_sha256}), "
                f"preview expiring {record.expires}, previewed against live {record.live_version}"
            )
        elif args.command == "promote":
            _summary(promote(args.site, args.version, args.live_version, token))
    except NothingToPromote as nothing:
        _output({"promote": "false"})
        _summary(f"nothing to promote: {nothing}")
        return 0
    except Refused as refusal:
        _summary(f"refused: {refusal}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
