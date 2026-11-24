"""§5: the governance metadata of `mvp_eng_dados_2`, bound to the pin by its
blob id, and checked against the view contract by JSON path. Read only with
`git`, in that checkout, with no `GIT_*` variable of the caller's environment.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import subprocess
from dataclasses import dataclass

from . import (
    strict_json,
    METADATA_BLOB,
    METADATA_COLUMNS,
    METADATA_FORMAT,
    METADATA_GRAIN,
    METADATA_MAPPING,
    METADATA_PIN,
    Refused,
)
from .views import ViewContract

PATH = "docs/pacote_de_metadados.json"
FORMAT = 1
LOGISTICA_REPORT = ("P13", "on_time_delivery_rate_by_carrier")  # PLAN §3.2
GRAIN_ROLES = ("grain", "identity")


@dataclass(frozen=True)
class Metadata:
    raw: bytes
    blob: str
    sha256: str
    provenance: object  # the package's own, kept apart from the live row


def _git(checkout: pathlib.Path, *args: str) -> bytes:
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    done = subprocess.run(["git", "-C", str(checkout), *args], capture_output=True, env=env, check=False)
    if done.returncode != 0:
        raise Refused(METADATA_PIN, check="git")
    return done.stdout


def fetch(checkout: pathlib.Path, contract: ViewContract) -> Metadata:
    """The pin is the contract's full commit, the path's blob there is the
    contract's `metadata_blob`, and the bytes are that blob's."""
    commit = _git(checkout, "rev-parse", "--verify", "--quiet", contract.pin + "^{commit}").decode("ascii", "replace").strip()
    if commit != contract.pin:
        raise Refused(METADATA_PIN)
    blob = _git(checkout, "rev-parse", "--verify", "--quiet", f"{contract.pin}:{PATH}").decode("ascii", "replace").strip()
    if blob != contract.metadata_blob:
        raise Refused(METADATA_BLOB)
    raw = _git(checkout, "cat-file", "blob", blob)
    if hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest() != blob:
        raise Refused(METADATA_BLOB)
    return check(raw, blob, contract)


def check(raw: bytes, blob: str, contract: ViewContract) -> Metadata:
    """§5's JSON paths, each refusing on a difference."""
    ok, data = strict_json(raw)
    if not ok or not isinstance(data, dict) or data.get("format") != FORMAT or type(data.get("format")) is not int:
        raise Refused(METADATA_FORMAT)
    questions = data.get("questions")
    if not isinstance(questions, dict):
        raise Refused(METADATA_MAPPING)
    declared = {v.report: f"consumption.{v.view}" for v in contract.views}
    found = {}
    for code, body in questions.items():
        if not isinstance(body, dict) or not isinstance(body.get("view"), str):
            raise Refused(METADATA_MAPPING)
        found[code] = body["view"]
    if found != declared or len(set(found.values())) != len(found):
        raise Refused(METADATA_MAPPING)  # swapped, missing, extra, or two codes for one view
    code, view = LOGISTICA_REPORT
    if declared.get(code) != f"consumption.{view}":
        raise Refused(METADATA_MAPPING, view, "logistica")
    rules, relations = data.get("view_rules"), data.get("relations")
    if not isinstance(rules, dict) or not isinstance(relations, dict):
        raise Refused(METADATA_COLUMNS)
    for v in contract.views:
        name = f"consumption.{v.view}"
        rule = rules.get(name)
        relation = relations.get(name)
        if not isinstance(rule, dict) or not isinstance(rule.get("columns"), dict):
            raise Refused(METADATA_COLUMNS, v.view)
        if not isinstance(relation, dict) or not isinstance(relation.get("columns"), dict):
            raise Refused(METADATA_COLUMNS, v.view)
        names = set(v.names)
        if set(rule["columns"]) != names or set(relation["columns"]) != names:
            raise Refused(METADATA_COLUMNS, v.view)  # names only: physical types are the catalogue's
        grain = set()
        for col, body in rule["columns"].items():
            if not isinstance(body, dict):
                raise Refused(METADATA_GRAIN, v.view)
            if body.get("role") in GRAIN_ROLES:
                grain.add(col)
        if not grain or grain != set(v.grain):
            raise Refused(METADATA_GRAIN, v.view)
    return Metadata(raw, blob, hashlib.sha256(raw).hexdigest(), data.get("provenance"))
