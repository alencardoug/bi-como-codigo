"""The verdict cases of §2.5.5: synthetic histories, judged within the test and
kept apart from any candidate's history."""

from __future__ import annotations

import dataclasses

import pytest

import verdict as v
from harness import CONTENT, FORM, HARNESS_ERROR, PASS, SCHEMA_ONLY

S = v.Stage


def run(id, *, inp="in1", builder="b1", artifact="a1", **stages):
    """A full clean run, with the given stages replaced (None removes one)."""
    base = {"build": S(), "archive": S(), "inspect_builder": S(), "assembly": S(cls=PASS), "verify": S(cls=PASS), "inspect_artifact": S()}
    for name, st in stages.items():
        if st is None:
            base.pop(name)
        else:
            base[name] = st
    return v.Record(id, build_input=inp, builder_digest=builder if "archive" in base else None,
                    artifact_digest=artifact if "assembly" in base and base["assembly"].cls == PASS else None, stages=base)


def resume(id, *, builder="b1", artifact=None, **stages):
    return v.Record(id, kind="resume", builder_digest=builder, artifact_digest=artifact, stages=stages)


TAIL_NONE = {"assembly": None, "verify": None, "inspect_artifact": None}
INTERRUPTED = S(status="interrupted")

CASES = {
    "no run": ([], v.NOT_RUN),
    "interrupted before its archive, then a clean retry of the same build input": (
        [run("r1", build=INTERRUPTED, archive=None, inspect_builder=None, **TAIL_NONE), run("r2", builder="b2", artifact="a2")], v.PASSES),
    "the same retry archived and never inspected": (
        [run("r1", build=INTERRUPTED, archive=None, inspect_builder=None, **TAIL_NONE), run("r2", builder="b2", inspect_builder=None, **TAIL_NONE)],
        v.NOT_ESTABLISHED),
    "archived not inspected, then that archive inspected and clean, nothing after": (
        [run("r1", inspect_builder=None, **TAIL_NONE), resume("x1", inspect_builder=S())], v.NOT_ESTABLISHED),
    "the same, then assembly, verify and the artifact's inspection resumed on that archive": (
        [run("r1", inspect_builder=None, **TAIL_NONE), resume("x1", inspect_builder=S()),
         resume("x2", artifact="a1", assembly=S(cls=PASS), verify=S(cls=PASS), inspect_artifact=S())], v.PASSES),
    "the same inspection done on another archive instead": (
        [run("r1", inspect_builder=None, **TAIL_NONE), resume("x1", builder="b9", inspect_builder=S())], v.NOT_ESTABLISHED),
    "an inspected builder output whose assembly ended in HARNESS_ERROR, then resumed on that digest": (
        [run("r1", assembly=S(cls=HARNESS_ERROR), verify=None, inspect_artifact=None),
         resume("x1", artifact="a1", assembly=S(cls=PASS), verify=S(cls=PASS), inspect_artifact=S())], v.PASSES),
    "a build interrupted": ([run("r1", build=INTERRUPTED, archive=None, inspect_builder=None, **TAIL_NONE)], v.STOPPED),
    "the draw exhausted": ([v.Record("r1", build_input="in1", builder_digest="b1", stages={"build": S(), "archive": S(), "inspect_builder": S()}, draw_exhausted=True)], v.STOPPED),
    "an earlier inconclusive file, then a pass of another artifact": (
        [run("r1", inspect_artifact=S(inconclusive=1)), run("r2", builder="b2", artifact="a2")], v.NOT_ESTABLISHED),
    "the same, then that archive re-inspected and clean": (
        [run("r1", inspect_artifact=S(inconclusive=1)), run("r2", builder="b2", artifact="a2"),
         resume("x1", artifact="a1", inspect_artifact=S())], v.PASSES),
    "an assembly FORM with its builder output inspected": ([run("r1", assembly=S(cls=FORM), verify=None, inspect_artifact=None)], v.COST),
    "the same without that inspection": ([run("r1", inspect_builder=None, assembly=S(cls=FORM), verify=None, inspect_artifact=None)], v.NOT_ESTABLISHED),
    "a content failure followed by a HARNESS_ERROR": (
        [run("r1", verify=S(cls=CONTENT)), run("r2", builder="b2", verify=S(cls=HARNESS_ERROR), inspect_artifact=None)], v.FAILS),
}


@pytest.mark.parametrize("name", CASES)
def test_each_case_of_the_table(name):
    records, expected = CASES[name]
    assert v.verdict(records).name == expected, v.verdict(records).reason


def test_a_finding_in_the_builder_output_fails_and_a_later_clean_run_does_not_undo_it():
    assert v.verdict([run("r1", inspect_builder=S(findings=1)), run("r2", builder="b2", artifact="a2")]).name == v.FAILS


def test_schema_only_and_a_verify_form_are_costs():
    assert v.verdict([run("r1", verify=S(cls=SCHEMA_ONLY))]).name == v.COST
    assert v.verdict([run("r1", verify=S(cls=FORM))]).name == v.COST


def test_the_encrypted_route_not_possible_is_not_run():
    assert v.verdict([v.Record("a3", not_possible=True)]).name == v.NOT_RUN


def test_no_control_or_probe_record_enters_a_history():
    with pytest.raises(v.NotJudged):
        v.verdict([run("r1"), v.Record("c1", label="control")])


# --- identities, order and stops (PROTO-1-04) ---------------------------------------


def test_done_stages_with_no_identities_do_not_pass():
    stages = {n: S(cls=PASS) if n in ("assembly", "verify") else S() for n in v.STAGES}
    assert v.verdict([v.Record("r1", stages=stages)]).name == v.NOT_ESTABLISHED


def test_tail_evidence_before_the_builders_inspection_does_not_close_it():
    records = [run("r1", inspect_builder=None, **TAIL_NONE),
               resume("x1", artifact="a1", assembly=S(cls=PASS), verify=S(cls=PASS), inspect_artifact=S()),
               resume("x2", inspect_builder=S())]
    assert v.verdict(records).name == v.NOT_ESTABLISHED


def test_a_finding_of_an_errored_inspection_is_not_confirmed_content():
    records = [run("r1", inspect_artifact=S(status="error", findings=1))]
    assert v.verdict(records).name == v.STOPPED


def test_a_stop_stays_after_an_unrelated_resume():
    records = [run("r1", assembly=S(cls=HARNESS_ERROR), verify=None, inspect_artifact=None),
               resume("x1", builder="b9", inspect_builder=S())]
    assert v.verdict(records).name == v.STOPPED


def test_a_full_retry_of_the_same_input_after_an_interruption_passes_and_another_input_does_not_close_it():
    interrupted = run("r1", build=INTERRUPTED, archive=None, inspect_builder=None, **TAIL_NONE)
    assert v.verdict([interrupted, run("r2", builder="b2", artifact="a2")]).name == v.PASSES
    assert v.verdict([interrupted, run("r2", inp="in9", builder="b2", artifact="a2")]).name == v.NOT_ESTABLISHED


# --- round 2 (PROTO-2-04) -----------------------------------------------------------


def test_content_with_no_artifact_digest_does_not_fail():
    stages = {n: S() for n in v.STAGES} | {"assembly": S(cls=PASS), "verify": S(cls=CONTENT)}
    record = v.Record("r1", build_input="in1", builder_digest="b1", artifact_digest=None, stages=stages)
    assert v.verdict([record]).name != v.FAILS


def test_a_tail_recorded_before_the_builders_inspection_does_not_close_it():
    records = [run("r1", inspect_builder=None), resume("x1", inspect_builder=S())]
    assert v.verdict(records).name == v.NOT_ESTABLISHED


def test_a_resumed_assembly_refused_by_form_is_a_cost():
    records = [run("r1", assembly=S(cls=HARNESS_ERROR), verify=None, inspect_artifact=None),
               resume("x1", assembly=S(cls=FORM))]
    assert v.verdict(records).name == v.COST


def test_an_exhausted_draw_stays_stopped_after_a_resume_on_another_builder():
    exhausted = v.Record("r1", build_input="in1", builder_digest="b1", stages={"build": S(), "archive": S(), "inspect_builder": S()},
                         draw_exhausted=True)
    records = [exhausted, resume("x1", builder="b9", artifact="a9", assembly=S(cls=PASS), verify=S(cls=PASS), inspect_artifact=S())]
    assert v.verdict(records).name == v.STOPPED
    closed = [exhausted, dataclasses.replace(resume("x1", artifact="a1", assembly=S(cls=PASS), verify=S(cls=PASS), inspect_artifact=S()),
                                             draw_clean=True)]
    assert v.verdict(closed).name == v.PASSES


def test_a_bound_content_finding_survives_a_later_harness_error():
    records = [run("r1", inspect_artifact=S(findings=1)), run("r2", builder="b2", verify=S(cls=HARNESS_ERROR), inspect_artifact=None)]
    assert v.verdict(records).name == v.FAILS


# --- round 3 (PROTO-3-01) -----------------------------------------------------------


def test_content_recorded_before_the_builders_inspection_does_not_fail():
    records = [run("r1", inspect_builder=None, verify=S(cls=CONTENT))]
    assert v.verdict(records).name == v.NOT_ESTABLISHED


def test_content_in_a_resume_no_earlier_run_explains_does_not_fail():
    records = [run("r1"), resume("x1", builder="b9", artifact="a9", verify=S(cls=CONTENT), inspect_artifact=S(findings=1))]
    assert v.verdict(records).name == v.PASSES
    attached = [run("r1"), resume("x1", artifact="a1", inspect_artifact=S(findings=1))]
    assert v.verdict(attached).name == v.FAILS


def test_the_artifacts_inspection_before_its_verify_does_not_pass():
    records = [run("r1", verify=S(cls=HARNESS_ERROR), inspect_artifact=None),
               resume("x1", artifact="a1", inspect_artifact=S()), resume("x2", artifact="a1", verify=S(cls=PASS))]
    assert v.verdict(records).name == v.NOT_ESTABLISHED
    in_order = records[:1] + [resume("x2", artifact="a1", verify=S(cls=PASS)), resume("x1", artifact="a1", inspect_artifact=S())]
    assert v.verdict(in_order).name == v.PASSES


def test_an_exhausted_draw_is_not_closed_by_an_assembly_refused_by_form():
    exhausted = v.Record("r1", build_input="in1", builder_digest="b1", stages={"build": S(), "archive": S(), "inspect_builder": S()},
                         draw_exhausted=True)
    assert v.verdict([exhausted, resume("x1", assembly=S(cls=FORM))]).name == v.STOPPED
    assert v.verdict([exhausted, dataclasses.replace(resume("x1", assembly=S(cls=FORM)), draw_clean=True)]).name == v.COST
