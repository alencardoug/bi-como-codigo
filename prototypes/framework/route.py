"""The encrypted route's builds and the run's state (docs/framework_prototype.md
§2.2, §5, §7 step 3).

A build of the encrypted route reads its candidate's tracked sources at a
recorded commit and `web/envelope.mjs`, and nothing of any fixture: its work
folder is assembled fresh from an allowlist — archived with the build —,
checked before the phase, and the phase runs in the sandbox with no network,
after the sandbox's probe has passed through the same wrapper. The builder
output is copied out by the harness and archived reproducibly; its digest is
the builder output's identity.

The run's state is one file, `runs/state.json`, ignored by Git, keyed by
identities (§5, FPROTO-6-07): each build invocation's own id and build input —
the allowlist's digest —, the builder output's digest, and the harness inputs
— the Git trees of `prototypes/framework/` (declarations, `cdn.json`,
lockfiles and the sandbox wrapper among them) and of the gate's package, and
`web/envelope.mjs`. **Any** build invocation of either candidate discards the
draw, both artifacts and every measure, even when it reproduces the same
bytes; so does a change of the harness inputs. Every stage run is appended as
a `verdict.Record`.

    uv run --frozen --group prototype python prototypes/framework/route.py own --commit <sha>
"""

from __future__ import annotations

import dataclasses
import json
import os
import pathlib
import secrets
import shutil
import subprocess
import tempfile
import time

import allowlist as al
import sandbox as sb
import trees
import verdict as v

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[1]
RUNS = HERE / "runs"
#: What the harness is made of, by path in the repository, at a commit (§5).
HARNESS_PATHS = ("prototypes/framework", "src/bi_como_codigo", "web/envelope.mjs")
OWN_BUILD = ["/usr/bin/python3", "-I", "build.py", "package"]


class Refused(Exception):
    pass


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True, text=True).stdout.strip()


def harness_inputs(commit: str, *, require_clean: bool = True) -> dict[str, str]:
    """The Git object of each harness path at `commit`. The harness that runs is
    the working tree, so it must be that commit's: a tracked change or an
    untracked file under those paths refuses the run."""
    if require_clean:
        dirty = _git("status", "--porcelain", "--untracked-files=all", "--", *HARNESS_PATHS)
        if dirty or _git("rev-parse", "HEAD") != _git("rev-parse", f"{commit}^{{commit}}"):
            raise Refused(f"the harness is not {commit} as committed:\n{dirty or 'HEAD is another commit'}")
    return {path: _git("rev-parse", f"{commit}:{path}") for path in HARNESS_PATHS}


# --- the state ------------------------------------------------------------------------------

def _empty() -> dict:
    return {"harness": None, "builds": {}, "draw": None, "artifacts": {}, "measures": {}, "records": [], "discarded": []}


def load(runs: pathlib.Path = RUNS) -> dict:
    path = runs / "state.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else _empty()


def save(state: dict, runs: pathlib.Path = RUNS) -> None:
    runs.mkdir(parents=True, exist_ok=True)
    tmp = runs / f".state.{secrets.token_hex(4)}.json"
    tmp.write_text(json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, runs / "state.json")


def discard(state: dict, why: str) -> None:
    """The draw, both artifacts and every measure, gone — recorded with why."""
    gone = {k: state[k] for k in ("draw", "artifacts", "measures") if state[k]}
    state.update(draw=None, artifacts={}, measures={})
    state["discarded"].append({"at": _now(), "why": why, "what": sorted(gone)})


def enter_harness(state: dict, inputs: dict[str, str]) -> None:
    if state["harness"] is not None and state["harness"] != inputs:
        discard(state, "the harness inputs changed")
    state["harness"] = inputs


def records(state: dict) -> list[v.Record]:
    return [v.Record(**{**r, "stages": {k: v.Stage(**s) for k, s in r["stages"].items()}}) for r in state["records"]]


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --- a build of the encrypted route -----------------------------------------------------------

def prove_sandbox() -> sb.Proof:
    """§5: the probe through the wrapper the phase uses, before the phase."""
    with tempfile.TemporaryDirectory(prefix="bice-route-") as tmp, \
            sb.planted(pathlib.Path(tmp) / "sentinel") as sentinel, \
            sb.planted(HERE / "clear" / f"planted-{secrets.token_hex(4)}") as clear_sentinel:
        work = pathlib.Path(tmp) / "probe-work"
        work.mkdir()
        return sb.prove(work, absent=sb.host_absent(REPO, sentinel, clear_sentinel))


def own_allowlist(commit: str) -> al.Allowlist:
    """B's build inputs: its tracked sources and the envelope's reader, at the
    commit. No fixture, no package, no clear-mode file (§2.2)."""
    return al.tracked(commit, "prototypes/framework/own/") + al.tracked(commit, "web/envelope.mjs")


def build(candidate: str, commit: str, allow: al.Allowlist, argv: list[str], output: str, *, runs: pathlib.Path = RUNS,
          require_clean: bool = True, prove=prove_sandbox, timeout: float = 3600) -> dict:
    """One build invocation: recorded first — so that an interrupted one still
    discards what came before —, then the sandbox's proof, the work folder from
    the allowlist and its check, the build with no network, the copy-out and
    the archive."""
    state = load(runs)
    enter_harness(state, harness_inputs(commit, require_clean=require_clean))
    run_id = f"{candidate}-{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{secrets.token_hex(4)}"
    folder = runs / candidate / run_id
    folder.mkdir(parents=True)
    build_input = al.archive_list(allow, folder / "allowlist.json")
    entry = {"id": run_id, "candidate": candidate, "commit": commit, "build_input": build_input, "harness": state["harness"],
             "started": _now(), "status": "started"}
    discard(state, f"build {run_id} of {candidate}")
    state["builds"][candidate] = entry
    record = v.Record(run_id, build_input=build_input, stages={"build": v.Stage(status="interrupted")})
    state["records"].append(dataclasses.asdict(record))
    save(state, runs)

    def finish(stages: dict[str, v.Stage], **extra) -> dict:
        entry.update(extra, finished=_now())
        state["records"][-1] = dataclasses.asdict(dataclasses.replace(record, builder_digest=extra.get("builder_digest"), stages=stages))
        save(state, runs)
        return entry

    proof = prove()
    entry["sandbox_proof"] = {"passed": proof.passed, "checks": proof.checks}
    if not proof.passed:
        return finish({"build": v.Stage(status="error")}, status="sandbox probe failed")
    work = folder / "work"
    al.assemble(allow, work)
    al.check(allow, work)
    t0 = time.time()
    done = sb.run(work, argv, timeout=timeout)
    seconds = round(time.time() - t0, 2)
    (folder / "build.log").write_bytes(b"$ " + " ".join(argv).encode() + b"\n" + done.stdout + b"\n--- stderr\n" + done.stderr)
    if done.returncode != 0:
        return finish({"build": v.Stage(status="error")}, status=f"build exited {done.returncode}", seconds=seconds)
    builder = folder / "builder"
    uncarried = al.copy_out(work, output, builder)
    if uncarried:
        return finish({"build": v.Stage(status="error")}, status="the build wrote entries no copy can carry", uncarried=uncarried)
    shutil.rmtree(work)
    digest = trees.archive(builder, folder / "builder.tar.gz")
    files = [p for p in builder.rglob("*") if p.is_file()]
    return finish({"build": v.Stage(), "archive": v.Stage()}, status="archived", builder_digest=digest,
                  archive=str((folder / "builder.tar.gz").relative_to(runs)), seconds=seconds,
                  files=len(files), bytes=sum(p.stat().st_size for p in files))


def build_own(commit: str, **kwargs) -> dict:
    return build("own", commit, own_allowlist(commit), OWN_BUILD, "build", **kwargs)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("candidate", choices=["own"])
    parser.add_argument("--commit", required=True, help="the commit whose tracked sources are built, and whose harness runs")
    args = parser.parse_args()
    result = build_own(args.commit)
    print(json.dumps(result, indent=1))
    raise SystemExit(0 if result["status"] == "archived" else 1)
