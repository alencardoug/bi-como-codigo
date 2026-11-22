"""The build of Candidate B (docs/framework_prototype.md §4): Python's standard
library only, run in the sandbox with no network, in a work folder holding
exactly its allowlist.

It copies the page's own files into `build/`, each named by its content hash,
and writes `build/index.html` from the template: the import map — every own
module and the engine's bundle, each with its integrity —, the pinned classic
scripts of `cdn.json` with theirs, and the page's entry module. It installs
nothing and fetches nothing.

    python3 build.py package   # the encrypted route: the envelope's reader as the source
    python3 build.py clear     # the clear mode: the clear fixture's Parquet beside the page

The clear mode reads `data/p01.parquet` from the work folder and copies it to
`build/data/p01.parquet`; the encrypted route's allowlist never holds it.
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path.cwd()
OUT = HERE / "build"

#: The page's own modules, by the specifier its code imports them with.
MODULES = {
    "./report.mjs": "report.mjs",
    "./p01.report.json": "p01.report.json",
    "./pins.mjs": None,  # written by this build from cdn.json
    "apache-arrow": "arrow.mjs",
}
SOURCES = {"package": "source.package.mjs", "clear": "source.clear.mjs"}


def sri(data: bytes) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()


def hashed(name: str, data: bytes) -> str:
    stem, dot, ext = name.rpartition(".")
    return f"{stem}.{hashlib.sha256(data).hexdigest()[:16]}.{ext}"


def emit(name: str, data: bytes) -> tuple[str, str]:
    """`data` written into the output under its hashed name; its URL and integrity."""
    target = hashed(name, data)
    (OUT / target).write_bytes(data)
    return f"./{target}", sri(data)


def pins_module(cdn: dict) -> bytes:
    fetched = {f["name"]: {"url": f["url"], "integrity": f["integrity"], **({"extension": f["extension"]} if "extension" in f else {})}
               for f in cdn["files"] if f["role"] in ("fetch", "extension")}
    return ("// The bodies the page fetches from jsDelivr with their integrity (cdn.json), written by build.py.\n"
            f"export default {json.dumps(fetched, indent=1, sort_keys=True)};\n").encode()


def build(mode: str) -> dict:
    if mode not in SOURCES:
        raise SystemExit(f"unknown mode {mode}: package or clear")
    if OUT.exists():
        raise SystemExit("build/ exists: the build writes a fresh output")
    OUT.mkdir()
    cdn = json.loads((HERE / "cdn.json").read_text(encoding="utf-8"))
    for f in cdn["files"]:
        host = "https://extensions.duckdb.org/" if f["role"] == "extension" else "https://cdn.jsdelivr.net/npm/"
        if not f.get("integrity") or not f["url"].startswith(host):
            raise SystemExit(f"cdn.json: {f['name']} is not pinned on {host}")

    imports, integrity = {}, {}
    modules = dict(MODULES, **{"./source.mjs": SOURCES[mode]})
    if mode == "package":
        modules["./envelope.mjs"] = "envelope.mjs"
    for specifier, name in sorted(modules.items()):
        data = pins_module(cdn) if name is None else (HERE / name).read_bytes()
        url, token = emit("pins.mjs" if name is None else name, data)
        imports[specifier] = url
        integrity[url] = token
    for f in cdn["files"]:
        if f["role"] == "module":
            imports[f["specifier"]] = f["url"]
            integrity[f["url"]] = f["integrity"]
    importmap = json.dumps({"imports": dict(sorted(imports.items())), "integrity": dict(sorted(integrity.items()))}, indent=1)
    scripts = "".join(f'<script src="{f["url"]}" integrity="{f["integrity"]}" crossorigin="anonymous"></script>\n'
                      for f in cdn["files"] if f["role"] == "script")
    css_url, css_token = emit("page.css", (HERE / "page.css").read_bytes())
    page_url, page_token = emit("page.mjs", (HERE / "page.mjs").read_bytes())

    html = (HERE / "index.html").read_text(encoding="utf-8")
    pins_marker = next(line for line in html.splitlines() if "<!-- bice:pins" in line)
    entry_marker = next(line for line in html.splitlines() if "<!-- bice:entry" in line)
    html = html.replace('<link rel="stylesheet" href="page.css">', f'<link rel="stylesheet" href="{css_url}" integrity="{css_token}">')
    html = html.replace(pins_marker, f'<script type="importmap">\n{importmap}\n</script>\n{scripts}'.rstrip("\n"))
    html = html.replace(entry_marker, f'<script type="module" src="{page_url}" integrity="{page_token}"></script>')
    (OUT / "index.html").write_text(html, encoding="utf-8")

    if mode == "clear":
        (OUT / "data").mkdir()
        (OUT / "data" / "p01.parquet").write_bytes((HERE / "data" / "p01.parquet").read_bytes())
    files = sorted(str(p.relative_to(OUT)) for p in OUT.rglob("*") if p.is_file())
    return {"mode": mode, "files": files}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 build.py package|clear")
    print(json.dumps(build(sys.argv[1]), indent=1))
