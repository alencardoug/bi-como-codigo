"""The fetcher and the offline install (docs/framework_prototype.md §2.2, §5).

The fetcher reads a candidate's lockfile and downloads each tarball it
records with plain HTTPS GETs, from `registry.npmjs.org` only, each checked
against the lockfile's `integrity`, into a content-addressed cache with its
listing. Nothing of a package runs during the fetch.

The install runs in the sandbox with no network: npm loads the cached
tarballs into its own cache (`npm cache add`, offline), then `npm ci
--offline --ignore-scripts` installs from it. A script found necessary is run
alone, by package, with `npm rebuild <package>`, offline, and recorded.
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import shutil
import urllib.request

import allowlist as al
import sandbox as sb

REGISTRY = "https://registry.npmjs.org/"
TARBALLS = ".tarballs"
ALGORITHMS = {"sha512": hashlib.sha512, "sha384": hashlib.sha384, "sha256": hashlib.sha256, "sha1": hashlib.sha1}


class Refused(Exception):
    pass


def entries(lock: dict) -> list[tuple[str, str, str]]:
    """(path in the lockfile, resolved URL, integrity) of every package to
    fetch. A link, the root and a bundled dependency are not fetched; anything
    else with no registry URL or no integrity is refused."""
    if lock.get("lockfileVersion") not in (2, 3):
        raise Refused("the lockfile is not of version 2 or 3")
    out = []
    for name, body in sorted(lock.get("packages", {}).items()):
        if name == "" or body.get("link") or body.get("inBundle"):
            continue
        resolved, integrity = body.get("resolved"), body.get("integrity")
        if not resolved or not integrity:
            raise Refused(f"{name} has no resolved URL or no integrity")
        if not resolved.startswith(REGISTRY):
            raise Refused(f"{name} resolves outside {REGISTRY}")
        out.append((name, resolved, integrity))
    return out


def verify_integrity(data: bytes, integrity: str) -> bool:
    """Subresource integrity: the strongest algorithm listed must match."""
    by_alg: dict[str, list[str]] = {}
    for token in integrity.split():
        alg, _, digest = token.partition("-")
        if alg in ALGORITHMS:
            by_alg.setdefault(alg, []).append(digest.split("?")[0])
    for alg in ALGORITHMS:  # strongest first
        if alg in by_alg:
            actual = base64.b64encode(ALGORITHMS[alg](data).digest()).decode()
            return actual in by_alg[alg]
    return False


def _https_get(url: str) -> bytes:
    if not url.startswith(REGISTRY):
        raise Refused(f"{url} is not on {REGISTRY}")

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    request = urllib.request.Request(url, headers={"User-Agent": "bice-prototype-fetcher", "Accept": "application/octet-stream"})
    with opener.open(request, timeout=120) as response:
        if response.status != 200:
            raise Refused(f"{url} answered {response.status}")
        return response.read()


def fetch(lockfile: pathlib.Path, cache: pathlib.Path, get=_https_get) -> dict:
    """Every tarball of the lockfile into `cache/`, named by the SHA-256 of its
    bytes, and `cache/listing.json`. A tarball already there is checked again,
    never trusted."""
    lock = json.loads(lockfile.read_text(encoding="utf-8"))
    cache.mkdir(parents=True, exist_ok=True)
    listing = []
    for name, resolved, integrity in entries(lock):
        known = [p for p in cache.glob("*.tgz") if (cache / f"{p.name}.integrity").is_file()
                 and (cache / f"{p.name}.integrity").read_text() == integrity]
        data = known[0].read_bytes() if known else get(resolved)
        if not verify_integrity(data, integrity):
            raise Refused(f"{name}: the tarball does not match the lockfile's integrity")
        sha = hashlib.sha256(data).hexdigest()
        path = cache / f"{sha}.tgz"
        if not path.exists():
            path.write_bytes(data)
            (cache / f"{sha}.tgz.integrity").write_text(integrity)
        listing.append({"package": name, "resolved": resolved, "integrity": integrity, "file": path.name, "sha256": sha})
    record = {"lockfile_sha256": hashlib.sha256(lockfile.read_bytes()).hexdigest(), "tarballs": listing}
    (cache / "listing.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    return record


def cache_allowlist(cache: pathlib.Path, record: dict) -> al.Allowlist:
    """The tarballs the listing names, under `.tarballs/` of the work folder."""
    seen: dict[str, al.Entry] = {}
    for t in record["tarballs"]:
        path = cache / t["file"]
        seen.setdefault(t["file"], al.Entry(f"{TARBALLS}/{t['file']}", t["sha256"], str(path)))
    return al.Allowlist(tuple(seen.values()))


#: npm loads the harness's tarballs into its own cache, offline, then installs
#: from it with no script; the tarballs folder is removed before the install.
INSTALL = (f"set -e; if [ -d {TARBALLS} ]; then (cd {TARBALLS} && ls | grep '\\.tgz$' | sed 's|^|./|' "
           f"| xargs -r npm cache add --offline --cache {sb.WORK}/.npm-cache --loglevel=error); rm -rf {TARBALLS}; fi; "
           f"npm ci --offline --ignore-scripts --no-audit --no-fund --cache {sb.WORK}/.npm-cache")


def install(allow: al.Allowlist, work: pathlib.Path, *, options: sb.Options = sb.Options(), timeout: float = 1800):
    """The install phase: a fresh work folder from the allowlist, checked, then
    the offline install in the sandbox. Returns the completed process."""
    al.assemble(allow, work)
    al.check(allow, work)
    return sb.run(work, ["/usr/bin/sh", "-c", INSTALL], options=options, timeout=timeout)


def keep_install(work: pathlib.Path, out: pathlib.Path) -> al.Allowlist:
    """The install's `node_modules/`, copied out by the harness, and its listing
    — the build phase's input beside the sources."""
    if out.exists():
        raise FileExistsError(f"{out} exists")
    shutil.copytree(work / "node_modules", out, symlinks=True)
    return al.files(out, "node_modules/")
