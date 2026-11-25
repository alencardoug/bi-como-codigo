"""Writes the third-party pins of the report pages from `site/app/cdn.json`
(docs/report_page.md §3.1, C1): there is no build, so what a page serves is
what is committed, and this script is how the committed pins are written.

- In each page of `site/relatorios/*.html`, the block between
  `<!-- bice:pins -->` and `<!-- /bice:pins -->`: the import map — each
  `module` under its specifier, with its integrity, and `apache-arrow` mapped
  to the page's own `app/arrow.mjs` — and each `script` as a classic script
  with its integrity.
- `site/app/pins.mjs`: the bodies the page fetches itself — the engine's
  worker and WASM, the Parquet extension —, each with its URL and integrity.

    uv run --frozen python tests/report_pins.py          # write
    uv run --frozen python tests/report_pins.py --check  # exit 1 if anything differs

`tests/test_report_page.py` runs the check in `make check`.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "site" / "app"
PAGES = ROOT / "site" / "relatorios"
BLOCK = re.compile(r"<!-- bice:pins -->\n.*?<!-- /bice:pins -->", re.S)
HOSTS = {"extension": "https://extensions.duckdb.org/"}
NPM = "https://cdn.jsdelivr.net/npm/"


def declared() -> list[dict]:
    files = json.loads((APP / "cdn.json").read_text(encoding="utf-8"))["files"]
    for f in files:
        host = HOSTS.get(f["role"], NPM)
        if not f["url"].startswith(host) or not f["integrity"].startswith("sha384-"):
            raise SystemExit(f"cdn.json: {f['name']} is not pinned on {host} with a sha384 integrity")
    return files


def block(files: list[dict]) -> str:
    imports = {f["specifier"]: f["url"] for f in files if f["role"] == "module"}
    imports["apache-arrow"] = "../app/arrow.mjs"  # the bundle imports it by name; the UMD script defines it
    integrity = {f["url"]: f["integrity"] for f in files if f["role"] == "module"}
    importmap = json.dumps({"imports": dict(sorted(imports.items())), "integrity": dict(sorted(integrity.items()))}, indent=1)
    scripts = "".join(
        f'<script src="{f["url"]}" integrity="{f["integrity"]}" crossorigin="anonymous"></script>\n'
        for f in files if f["role"] == "script"
    )
    return f'<!-- bice:pins -->\n<script type="importmap">\n{importmap}\n</script>\n{scripts}<!-- /bice:pins -->'


def pins_module(files: list[dict]) -> str:
    fetched = {
        f["name"]: {"url": f["url"], "integrity": f["integrity"], **({"extension": f["extension"]} if "extension" in f else {})}
        for f in files if f["role"] in ("fetch", "extension")
    }
    return ("// The bodies the report pages fetch themselves, each with its integrity: written by\n"
            "// tests/report_pins.py from site/app/cdn.json, never by hand.\n"
            f"export default {json.dumps(fetched, indent=1, sort_keys=True)};\n")


def expected() -> dict[pathlib.Path, str]:
    files = declared()
    out = {APP / "pins.mjs": pins_module(files)}
    for page in sorted(PAGES.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        if len(BLOCK.findall(text)) != 1:
            raise SystemExit(f"{page.relative_to(ROOT)}: needs exactly one bice:pins block")
        out[page] = BLOCK.sub(lambda _m: block(files), text)
    return out


def main(argv: list[str]) -> int:
    stale = []
    for path, text in expected().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != text:
            stale.append(path.relative_to(ROOT).as_posix())
            if "--check" not in argv:
                path.write_text(text, encoding="utf-8")
    if "--check" in argv and stale:
        print("pins differ from site/app/cdn.json: " + ", ".join(stale) + " — run tests/report_pins.py")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
