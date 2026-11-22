"""The pinned third-party bodies of a candidate (docs/framework_prototype.md §2.4).

Every file a candidate loads from jsDelivr is declared in its `cdn.json` by
npm package, version and file. The digests are taken once, by this harness:
the package's tarball is fetched from the registry by the registry's own
record of its URL and integrity (`npm_offline.third_party`), the file is read
from it, and jsDelivr's body at `https://cdn.jsdelivr.net/npm/<package>@<version>/<file>`
must be the same bytes. The declaration then carries, per file, the URL, the
SHA-256 and the subresource-integrity token the own build writes into its page.

A DuckDB extension the engine would load at run time is published by DuckDB
on `extensions.duckdb.org`, not on npm: it is declared by its URL, its body
taken from there, and a digest already declared must be the one served.

    uv run --frozen --group prototype python prototypes/framework/cdn.py take own/cdn.json
    uv run --frozen --group prototype python prototypes/framework/cdn.py check own/cdn.json
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import pathlib
import sys
import tarfile

import npm_offline as npm

HERE = pathlib.Path(__file__).resolve().parent
JSDELIVR = "https://cdn.jsdelivr.net/npm/"
EXTENSIONS = "https://extensions.duckdb.org/"
TARBALLS = HERE / "runs" / "third_party"


class Refused(Exception):
    pass


def url(package: str, version: str, file: str) -> str:
    return f"{JSDELIVR}{package}@{version}/{file}"


def sri(data: bytes) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()


def from_tarball(tarball: pathlib.Path, file: str) -> bytes:
    with tarfile.open(fileobj=io.BytesIO(tarball.read_bytes()), mode="r:gz") as tar:
        member = tar.getmember(f"package/{file}")
        if not member.isfile():
            raise Refused(f"{tarball.name}: {file} is not a plain file")
        return tar.extractfile(member).read()


def _cdn_get(address: str) -> bytes:
    return npm._https_get(address, (JSDELIVR, EXTENSIONS))


def take(declaration: pathlib.Path, *, tarballs: pathlib.Path = TARBALLS, get_registry=npm._https_get, get_cdn=_cdn_get) -> dict:
    """Each declared file read from its npm tarball and from jsDelivr, the two
    compared byte for byte, the digests written into the declaration."""
    decl = json.loads(declaration.read_text(encoding="utf-8"))
    for f in decl["files"]:
        if f["role"] == "extension":
            if not f["url"].startswith(EXTENSIONS):
                raise Refused(f"{f['url']}: an extension comes from {EXTENSIONS}")
            served = get_cdn(f["url"])
            if f.get("sha256") and hashlib.sha256(served).hexdigest() != f["sha256"]:
                raise Refused(f"{f['url']}: not the declared bytes")
            f.update({"bytes": len(served), "sha256": hashlib.sha256(served).hexdigest(), "integrity": sri(served)})
            continue
        tarball = npm.third_party(f["package"], f["version"], tarballs, get=get_registry)
        published = from_tarball(tarball, f["file"])
        address = url(f["package"], f["version"], f["file"])
        served = get_cdn(address)
        if served != published:
            raise Refused(f"{address}: jsDelivr's body is not the npm tarball's file")
        f.update({"url": address, "bytes": len(published), "sha256": hashlib.sha256(published).hexdigest(), "integrity": sri(published)})
    declaration.write_text(json.dumps(decl, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return decl


def check(declaration: pathlib.Path, get_cdn=_cdn_get) -> list[str]:
    """jsDelivr still serves each declared body; the URLs whose bytes differ."""
    decl = json.loads(declaration.read_text(encoding="utf-8"))
    return [f["url"] for f in decl["files"] if hashlib.sha256(get_cdn(f["url"])).hexdigest() != f["sha256"]]


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("take", "check"):
        raise SystemExit("usage: cdn.py take|check <cdn.json>")
    target = pathlib.Path(sys.argv[2])
    if not target.is_absolute():
        target = HERE / target
    if sys.argv[1] == "take":
        for f in take(target)["files"]:
            print(f["sha256"], f["bytes"], f["url"])
    else:
        changed = check(target)
        print("\n".join(changed) if changed else "every declared body is served as pinned")
        raise SystemExit(1 if changed else 0)
