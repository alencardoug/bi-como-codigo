"""Writes the fixture package of stage 2.2 into `site/package/`.

The package is the envelope's producer run over stand-ins — a minimal Parquet
framing and a one-key JSON of control totals per report — under the profile
declaration `release/profiles.json`. It carries no report data. Each run draws
new keys, salts and IVs, so its bytes differ every time; the publishing
pipeline checks whatever is committed (docs/publishing_pipeline.md §4.2).

    uv run --frozen python tests/site_fixture.py
"""

from __future__ import annotations

import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT / "src") not in sys.path:
    sys.path.append(str(ROOT / "src"))

from bi_como_codigo import envelope as e, release  # noqa: E402

OUT = ROOT / "site" / "package"


def payloads(declared: list[e.DeclaredProfile]) -> dict[str, tuple[bytes, bytes]]:
    reports = sorted({r for p in declared for r in p.reports})
    return {r: (b'{"fixture": "%s"}' % r.encode(), b"PAR1" + r.encode().ljust(4, b"_")[:4] + b"PAR1") for r in reports}


def main() -> int:
    declared = release.profiles(ROOT)
    manifest, files = e.encrypt_package(declared, payloads(declared))
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    (OUT / "manifest.json").write_bytes(manifest)
    for name, data in files.items():
        (OUT / name).write_bytes(data)
    print(f"wrote {OUT.relative_to(ROOT)}: manifest.json and {len(files)} envelope(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
