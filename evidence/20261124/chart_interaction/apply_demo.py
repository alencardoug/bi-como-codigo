"""Build the chart demonstration of 2026-11-24 over one of Candidate B's artifacts: copy it to
<out>, put this folder's p01.report.json, page.mjs and page.css in place of the artifact's own
— whose names it keeps —, and write their new SHA-384 into index.html, whose import map and
tags carry each file's integrity. The artifact itself is not touched.

    python3 -I evidence/20261124/chart_interaction/apply_demo.py <artifact> <out>
"""
import base64
import hashlib
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
artifact, out = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
if out.exists():
    sys.exit(f"{out} exists")
shutil.copytree(artifact, out)


def sri(data: bytes) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(data).digest()).decode()


html = (out / "index.html").read_text(encoding="utf-8")
for ours, pattern in (("p01.report.json", "p01.report.*.json"), ("page.mjs", "page.*.mjs"), ("page.css", "page.*.css")):
    (target,) = out.glob(pattern)
    old, new = target.read_bytes(), (HERE / ours).read_bytes()
    if html.count(sri(old)) != 1:
        sys.exit(f"{target.name}: its integrity is not in index.html exactly once")
    html = html.replace(sri(old), sri(new))
    target.write_bytes(new)
    print(target.name, "replaced by", ours)
(out / "index.html").write_text(html, encoding="utf-8")
