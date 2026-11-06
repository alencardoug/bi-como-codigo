"""M48: the counter-proof of every predicate of the envelope (§6.5).

For each `predicate_id` of each reader — `src/bi_como_codigo/envelope.py` and
`web/envelope.mjs` —, a copy of the module is written to a temporary
directory with that one predicate's `require` taking its condition as true,
and the dedicated cases of the predicate are run against the copy. A case is
*killed* when it no longer ends in its original code and `predicate_id`.
Every dedicated case of every predicate must be killed.

Run from the repository root, with the locked environment:

    uv run --frozen python evidence/20261106/m48_counter_proof.py

It writes only under a temporary directory, and prints one line per
predicate and a summary; it exits 1 if any case survives.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).resolve().parent
PY_MODULE = ROOT / "src" / "bi_como_codigo" / "envelope.py"
JS_MODULE = ROOT / "web" / "envelope.mjs"
REQUIRE = re.compile(r'^(?P<indent>\s*)require\((?P<cond>.*), (?P<code>[A-Z_]+), "(?P<pid>[a-z0-9_]+)"\)(?P<end>;?)$')


def predicates(source: str) -> list[str]:
    seen: list[str] = []
    for line in source.splitlines():
        m = REQUIRE.match(line)
        if m and m["pid"] not in seen:
            seen.append(m["pid"])
    return seen


def mutate(source: str, pid: str, true: str) -> str:
    out, hits = [], 0
    for line in source.splitlines():
        m = REQUIRE.match(line)
        if m and m["pid"] == pid:
            line = f'{m["indent"]}require({true}, {m["code"]}, "{pid}"){m["end"]}'
            hits += 1
        out.append(line)
    assert hits, pid
    return "\n".join(out) + "\n"


def run_python(tmp: pathlib.Path, pid: str) -> list[dict]:
    src = tmp / "py" / pid / "src"
    (src / "bi_como_codigo").mkdir(parents=True)
    (src / "bi_como_codigo" / "__init__.py").write_text("")
    (src / "bi_como_codigo" / "envelope.py").write_text(mutate(PY_MODULE.read_text(), pid, "True"))
    proc = subprocess.run(
        [sys.executable, str(HERE / "m48_worker.py"), str(src), pid],
        capture_output=True, text=True, cwd=ROOT,
    )
    if proc.returncode != 0:
        raise SystemExit(f"python worker failed on {pid}:\n{proc.stderr}")
    return json.loads(proc.stdout)


def run_js(tmp: pathlib.Path, pid: str) -> list[dict]:
    module = tmp / "js" / pid / "envelope.mjs"
    module.parent.mkdir(parents=True)
    module.write_text(mutate(JS_MODULE.read_text(), pid, "true"))
    proc = subprocess.run(
        ["node", str(HERE / "m48_worker.mjs"), str(module), pid],
        capture_output=True, text=True, cwd=ROOT,
    )
    if proc.returncode != 0:
        raise SystemExit(f"node worker failed on {pid}:\n{proc.stderr}")
    return json.loads(proc.stdout)


def main() -> int:
    survivors = 0
    total = 0
    with tempfile.TemporaryDirectory(prefix="m48-") as name:
        tmp = pathlib.Path(name)
        for language, module, runner in (("python", PY_MODULE, run_python), ("javascript", JS_MODULE, run_js)):
            pids = predicates(module.read_text())
            print(f"== {language}: {len(pids)} predicates in {module.relative_to(ROOT)}")
            for pid in pids:
                results = runner(tmp, pid)
                if not results:
                    print(f"  {pid}: NO DEDICATED CASE")
                    survivors += 1
                    continue
                alive = [r for r in results if not r["killed"]]
                total += len(results)
                survivors += len(alive)
                verdict = "killed" if not alive else "SURVIVED: " + ", ".join(r["case"] for r in alive)
                ends = sorted({r["end"] for r in results})
                print(f"  {pid}: {len(results)} case(s) {verdict}; mutant ends: {'; '.join(ends)}")
    print(f"== {total} dedicated case runs, {survivors} surviving")
    return 1 if survivors else 0


if __name__ == "__main__":
    raise SystemExit(main())
