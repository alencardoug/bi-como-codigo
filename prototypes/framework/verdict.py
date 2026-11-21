"""The verdict of stage 2.3 (docs/framework_prototype.md §2.5.4).

One function over every judged record of a candidate's encrypted route. A
run is six stages — build, archive, the inspection of the builder output,
assembly, `verify`, the inspection of the artifact — each with its outcome or
its absence; a *resume* is a later record that completes stages of an
earlier run on the same digests. The browser diagnostic is not a stage (N96).

The precedence, first match wins: fails, not run, stopped, not established,
a cost, passes.
"""

from __future__ import annotations

import dataclasses

from harness import COLLISION, CONTENT, FORM, HARNESS_ERROR, PASS, SCHEMA_ONLY

STAGES = ("build", "archive", "inspect_builder", "assembly", "verify", "inspect_artifact")
INSPECTIONS = {"inspect_builder": "builder_digest", "inspect_artifact": "artifact_digest"}
TAIL = ("assembly", "verify", "inspect_artifact")

FAILS = "fails the criterion"
NOT_RUN = "not run"
STOPPED = "stopped"
NOT_ESTABLISHED = "not established"
COST = "a cost"
PASSES = "passes"


@dataclasses.dataclass(frozen=True)
class Stage:
    status: str = "done"  # "done", "interrupted" or "error"
    cls: str | None = None  # the class of assembly and verify
    findings: int = 0
    inconclusive: int = 0


@dataclasses.dataclass(frozen=True)
class Record:
    id: str
    label: str = "judged"  # "judged", "probe" or "control" — set when the run starts
    kind: str = "run"  # "run", or "resume" of stages of an earlier run on its digests
    build_input: str | None = None  # the allowlist's digest
    builder_digest: str | None = None
    artifact_digest: str | None = None
    stages: dict[str, Stage] = dataclasses.field(default_factory=dict)
    draw_exhausted: bool = False
    not_possible: bool = False  # A3: the encrypted route is not possible, with its probe


@dataclasses.dataclass(frozen=True)
class Verdict:
    name: str
    reason: str


class NotJudged(Exception):
    """A probe's or a control's record in a candidate's history."""


def _complete(stage: Stage | None) -> bool:
    return stage is not None and stage.status == "done" and stage.cls not in {HARNESS_ERROR, COLLISION}


def _mandatory(stages: dict[str, Stage]) -> tuple[str, ...]:
    assembly = stages.get("assembly")
    if _complete(assembly) and assembly.cls == FORM:
        return STAGES[:4]  # verify does not apply to an artifact that was not assembled
    return STAGES


def _effective(r: Record, later: list[Record]) -> tuple[dict[str, Stage], list[str]]:
    """The run's stages with what later records completed on the same
    digests, and the mandatory stages still open."""
    stages = {name: st for name, st in r.stages.items() if _complete(st)}
    missing = [s for s in _mandatory(r.stages) if s not in stages]
    if not missing:
        return stages, []
    if "build" in missing or "archive" in missing:
        # Closed only by a later run of the same build input carried through every stage.
        for n, s in enumerate(later):
            if s.kind == "run" and s.build_input is not None and s.build_input == r.build_input:
                own, still = _effective(s, later[n + 1:])
                if not still and "archive" in own:
                    return own, []
        return stages, missing
    if "inspect_builder" in missing:
        for s in later:
            if s.builder_digest == r.builder_digest and _complete(s.stages.get("inspect_builder")):
                stages["inspect_builder"] = s.stages["inspect_builder"]
                break
    tail = [t for t in TAIL if t in missing]
    if tail:
        if r.artifact_digest is not None:
            for t in tail:  # an artifact that exists is closed only by the same artifact checked again
                for s in later:
                    if s.artifact_digest == r.artifact_digest and _complete(s.stages.get(t)):
                        stages[t] = s.stages[t]
                        break
        else:
            for s in later:  # resumed from the inspected builder digest: all three of them
                if s.builder_digest == r.builder_digest and all(_complete(s.stages.get(t)) for t in TAIL):
                    stages.update({t: s.stages[t] for t in TAIL})
                    break
    return stages, [s for s in _mandatory(stages if "assembly" in stages else r.stages) if s not in stages]


def _unresolved_inconclusive(records: list[Record]) -> list[str]:
    """An inconclusive file is resolved only by re-inspecting that archive."""
    out = []
    for n, r in enumerate(records):
        for stage, key in INSPECTIONS.items():
            st = r.stages.get(stage)
            if st is None or not st.inconclusive:
                continue
            target = getattr(r, key)
            if not any(getattr(s, key) == target and _complete(s.stages.get(stage)) and not s.stages[stage].inconclusive
                       for s in records[n + 1:]):
                out.append(f"{r.id}: {stage} of {target} inconclusive")
    return out


def _stops(r: Record) -> str | None:
    if r.draw_exhausted:
        return "the draw exhausted"
    for name, st in r.stages.items():
        if st.status == "interrupted":
            return f"{name} interrupted"
        if st.status == "error" or st.cls in {HARNESS_ERROR, COLLISION}:
            return f"{name} ended in {st.cls or 'an error'}"
    return None


def verdict(records: list[Record]) -> Verdict:
    if any(r.label != "judged" for r in records):
        raise NotJudged(", ".join(r.id for r in records if r.label != "judged"))
    for r in records:
        if (r.stages.get("verify") and r.stages["verify"].cls == CONTENT) or any(
                r.stages.get(s) and r.stages[s].findings for s in INSPECTIONS):
            return Verdict(FAILS, f"{r.id}: content in the build output; a later run does not undo it")
    runs = [r for r in records if r.kind == "run"]
    if not runs or any(r.not_possible for r in records):
        return Verdict(NOT_RUN, "the encrypted route is not possible" if any(r.not_possible for r in records) else "no run")
    stop = _stops(records[-1])
    if stop:
        return Verdict(STOPPED, f"{records[-1].id}: {stop}; repeated before any verdict")
    open_ = []
    for n, r in enumerate(records):
        if r.kind == "run":
            _, missing = _effective(r, records[n + 1:])
            open_ += [f"{r.id}: {s} missing" for s in missing]
    open_ += _unresolved_inconclusive(records)
    if open_:
        return Verdict(NOT_ESTABLISHED, "; ".join(open_))
    latest = runs[-1]
    stages, _ = _effective(latest, records[records.index(latest) + 1:])
    if stages["assembly"].cls == FORM or (stages.get("verify") and stages["verify"].cls in {FORM, SCHEMA_ONLY}):
        return Verdict(COST, f"{latest.id}: {stages['assembly'].cls if stages['assembly'].cls == FORM else stages['verify'].cls}")
    if stages["verify"].cls == PASS:
        return Verdict(PASSES, f"{latest.id}: every stage complete, verify passed, nothing found")
    return Verdict(NOT_ESTABLISHED, f"{latest.id}: verify ended in {stages['verify'].cls}")
