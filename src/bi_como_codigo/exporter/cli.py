"""The exporter's commands, and what a refusal prints (§10).

    catalogue   §3 check 7  checks 1 to 6, then the source OIDs and modifiers, the
                            session's defaults and the collation; no row. Writes a
                            draft into the staging root's drafts/
    propose     §4.4        the draft of release/views.json, from a capture, M59's
                            profile, the metadata package at the pin and a catalogue
    contract    §4.4        release/contract.json generated from release/views.json;
                            with --check, only compared
    run         §3–§10      the export, into BICE_EXPORT_DIR
    evidence    §9          Git's copy of a receipt, read strictly first
    collisions  §10, N108   the honest values found in the committed public files

    uv run --frozen python -m bi_como_codigo.exporter <command> [options]

The boundary catches every exception and prints a fixed refusal code, the view
and the check where there is one, and the exception's class name — never a
message, a traceback, a value or the connection string. There is no debug mode.
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys

from . import UNEXPECTED, Refused

ROOT = pathlib.Path(__file__).resolve().parents[3]
CAPTURE = "evidence/20261119/capture.out.txt"
PROFILE = "evidence/20261124/m59_profile.out.txt"


def refusal_line(exc: BaseException) -> str:
    """What the boundary prints for any exception: names, never a message."""
    if isinstance(exc, Refused):
        parts = [f"refused: {exc.code}"]
        if exc.view:
            parts.append(f"view {exc.view}")
        if exc.check:
            parts.append(f"check {exc.check}")
        parts.append(f"class {exc.cause or type(exc).__name__}")
        return "; ".join(parts)
    return f"refused: {UNEXPECTED}; class {type(exc).__name__}"


def _catalogue(args, environ) -> int:
    from . import paths, propose as P, source as s

    found = s.settings(environ)
    protected = paths.protected_roots(environ, ROOT)
    staging = paths.staging_root(environ.get("BICE_EXPORT_STAGING"), protected)
    capture = P.parse_capture((ROOT / args.capture).read_text(encoding="utf-8"))
    if found.user != capture.login:
        raise Refused(s.FACT_LOGIN)
    with paths.RunDirectory(staging, protected) as run_dir:
        source = s.connect(found, run_dir / "absent")
        try:
            body = s.catalogue(source, capture.login, set(capture.columns), capture.provenance)
        finally:
            try:
                source.close()
            except Exception:
                pass
    import json

    out = paths.draft_path(staging, protected, "catalogue")
    with open(out, "xb") as f:
        f.write((json.dumps(body, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    print(f"catalogue written: {out}")
    return 0


def _propose(args, environ) -> int:
    import json
    import subprocess

    from . import metadata as m, paths, propose as P

    protected = paths.protected_roots(environ, ROOT)
    staging = paths.staging_root(environ.get("BICE_EXPORT_STAGING"), protected)
    checkout = environ.get("ENG_DADOS_2_DIR")
    if not checkout:
        raise Refused("environment_invalid", check="ENG_DADOS_2_DIR")
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}

    def git(*a: str) -> bytes:
        done = subprocess.run(["git", "-C", checkout, *a], capture_output=True, env=env, check=False)
        if done.returncode != 0:
            raise Refused(m.METADATA_PIN, check="git")
        return done.stdout

    if git("rev-parse", "--verify", "--quiet", args.pin + "^{commit}").decode().strip() != args.pin:
        raise Refused(m.METADATA_PIN)
    blob = git("rev-parse", "--verify", "--quiet", f"{args.pin}:{m.PATH}").decode().strip()
    raw = git("cat-file", "blob", blob)
    draft = P.propose(
        P.parse_capture((ROOT / args.capture).read_text(encoding="utf-8")),
        P.parse_profile((ROOT / args.profile).read_text(encoding="utf-8")),
        json.loads(raw),
        P.parse_catalogue(pathlib.Path(args.catalogue).read_bytes()),
        args.pin,
        blob,
    )
    out = paths.draft_path(staging, protected, "views")
    with open(out, "xb") as f:
        f.write(P.dump(draft))
    print(f"draft written: {out}")
    return 0


def _contract(args, _environ) -> int:
    from . import views as v

    views = v.load((ROOT / "release" / "views.json").read_bytes())
    path = ROOT / "release" / "contract.json"
    if args.check:
        v.check_generated(views, path.read_bytes())
        print("release/contract.json is the generated one")
        return 0
    path.write_bytes(v.report_contract(views))
    print("release/contract.json written from release/views.json")
    return 0


def _run(_args, environ) -> int:
    from . import run

    body = run.export(ROOT, environ)
    print(f"exported: {len(body['views'])} views; result in {environ['BICE_EXPORT_DIR']}")
    return 0


def _evidence(args, _environ) -> int:
    from . import receipt as rc

    body = rc.load(pathlib.Path(args.receipt).read_bytes())
    target = pathlib.Path(args.out).resolve()
    if ROOT / "evidence" not in target.parents:
        raise Refused("path_refused", check="evidence")
    target.mkdir(parents=True, exist_ok=True)
    out = target / "export_run.json"
    with open(out, "xb") as f:
        f.write(rc.dump(body))
    print(f"evidence written: {out.relative_to(ROOT)}")
    return 0


def _collisions(args, environ) -> int:
    from . import collisions

    for line in collisions.report(ROOT, environ):
        print(line)
    return 0


def main(argv: list[str] | None = None, environ=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m bi_como_codigo.exporter", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("catalogue")
    p.add_argument("--capture", default=CAPTURE)
    p = sub.add_parser("propose")
    p.add_argument("--catalogue", required=True)
    p.add_argument("--pin", required=True)
    p.add_argument("--capture", default=CAPTURE)
    p.add_argument("--profile", default=PROFILE)
    p = sub.add_parser("contract")
    p.add_argument("--check", action="store_true")
    sub.add_parser("run")
    p = sub.add_parser("evidence")
    p.add_argument("receipt")
    p.add_argument("out")
    sub.add_parser("collisions")
    args = parser.parse_args(argv)
    environ = os.environ if environ is None else environ
    commands = {"catalogue": _catalogue, "propose": _propose, "contract": _contract, "run": _run,
                "evidence": _evidence, "collisions": _collisions}
    try:
        return commands[args.command](args, environ)
    except BaseException as exc:  # noqa: BLE001 - the boundary: every exception, by name only
        if isinstance(exc, SystemExit):
            raise
        print(refusal_line(exc), file=sys.stderr)
        return 1
