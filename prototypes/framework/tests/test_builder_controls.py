"""The controls of §2.5.5 as they run on a candidate's builder output
(`builder_controls.py`), on a hand-made one: each control meets its own
expected diagnosis, and its verdict is that of a leak — or of a form, or clean."""

from __future__ import annotations

import pytest

import builder_controls as bc
import fixture as f
import harness as h
import verdict as v

SEED = 20261120


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("controls")
    fx = f.generate(SEED)[0]
    f.write(fx, tmp / "fx")
    made = tmp / "made"
    made.mkdir()
    (made / "index.html").write_text("<!doctype html><title>P01</title>")
    digest = h.archive(made, tmp / "builder.tar.gz")
    h.extract(tmp / "builder.tar.gz", tmp / "builder", digest)
    return {r["control"]: r for r in bc.run("own", tmp / "builder", digest, tmp / "fx" / "package", fx, tmp / "out")}


def test_every_control_meets_its_expected_diagnosis(ran):
    assert len(ran) == len(bc.table(f.generate(SEED)[0]))
    assert [name for name, r in ran.items() if not r["as_expected"]] == []


@pytest.mark.parametrize("name, verdict", [
    ("clean metadata", v.PASSES),
    ("package only, with a form refusal", v.COST),
    ("a fixed label", v.FAILS),
    ("Arrow IPC", v.FAILS),
    ("a label in a .map", v.FAILS),
    ("assembly form: a package/ of the builder's", v.COST),
])
def test_each_control_is_judged_as_its_leak_or_form_makes_it(ran, name, verdict):
    assert ran[name]["verdict"] == verdict, ran[name]
