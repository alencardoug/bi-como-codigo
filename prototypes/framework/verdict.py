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


#: The identity each stage is about: a stage counts only on its subject
#: (PROTO-1-04).
SUBJECT = {"build": "build_input", "archive": "builder_digest", "inspect_builder": "builder_digest",
           "assembly": "builder_digest", "verify": "artifact_digest", "inspect_artifact": "artifact_digest"}


def _done(stage: Stage | None) -> bool:
    return stage is not None and stage.status == "done" and stage.cls not in {HARNESS_ERROR, COLLISION}


def _complete(r: Record, name: str) -> bool:
    """Done, and bound to its subject: a build to its input, an archive and the
    builder's inspection to the archived digest, an assembled artifact to its
    digest."""
    st = r.stages.get(name)
    if not _done(st) or getattr(r, SUBJECT[name]) is None:
        return False
    if name == "archive" and r.build_input is None and r.kind == "run":
        return False
    if name == "assembly" and st.cls == PASS and r.artifact_digest is None:
        return False
    return True


def _mandatory(form: bool) -> tuple[str, ...]:
    return STAGES[:4] if form else STAGES  # verify does not apply to an artifact that was not assembled


def _effective(r: Record, later: list[Record]) -> tuple[dict[str, Stage], list[str]]:
    """The run's stages with what later records completed on the same subjects,
    in order, and the mandatory stages still open."""
    stages = {name: r.stages[name] for name in STAGES if name in r.stages and _complete(r, name)}
    form = "assembly" in stages and stages["assembly"].cls == FORM
    missing = [s for s in _mandatory(form) if s not in stages]
    if not missing:
        return stages, []
    if "build" in missing or "archive" in missing:
        # Closed only by a later run of the same build input carried through every stage.
        for n, s in enumerate(later):
            if s.kind == "run" and r.build_input is not None and s.build_input == r.build_input:
                own, still = _effective(s, later[n + 1:])
                if not still:
                    return own, []
        return stages, missing
    position = -1  # what later evidence has closed so far, in order
    if "inspect_builder" not in stages:
        for n, s in enumerate(later):
            if s.builder_digest == r.builder_digest and _complete(s, "inspect_builder"):
                stages["inspect_builder"] = s.stages["inspect_builder"]
                position = n
                break
        else:
            return stages, [m for m in _mandatory(form) if m not in stages]
    tail = [t for t in TAIL if t not in stages]
    if tail:
        artifact = r.artifact_digest if "assembly" in stages else None
        if artifact is not None:
            for t in tail:  # an artifact that exists is closed only by the same artifact checked again
                for n, s in enumerate(later):
                    if n > position and s.artifact_digest == artifact and _complete(s, t):
                        stages[t] = s.stages[t]
                        break
        else:
            for n, s in enumerate(later):  # resumed from the inspected builder digest: all three, after it
                if n > position and s.builder_digest == r.builder_digest and all(_complete(s, t) for t in TAIL):
                    stages.update({t: s.stages[t] for t in TAIL})
                    break
    form = "assembly" in stages and stages["assembly"].cls == FORM
    return stages, [m for m in _mandatory(form) if m not in stages]


def _unresolved_inconclusive(records: list[Record]) -> list[str]:
    """An inconclusive file is resolved only by re-inspecting that archive."""
    out = []
    for n, r in enumerate(records):
        for stage, key in INSPECTIONS.items():
            st = r.stages.get(stage)
            if st is None or not st.inconclusive:
                continue
            target = getattr(r, key)
            if target is None or not any(getattr(s, key) == target and _complete(s, stage) and not s.stages[stage].inconclusive
                                         for s in records[n + 1:]):
                out.append(f"{r.id}: {stage} of {target} inconclusive")
    return out


def _stop(r: Record) -> tuple[str, str] | None:
    """(the stage, why) of a record's stop."""
    if r.draw_exhausted:
        return "draw", "the draw exhausted"
    for name in STAGES:
        st = r.stages.get(name)
        if st is None:
            continue
        if st.status == "interrupted":
            return name, f"{name} interrupted"
        if st.status == "error" or st.cls in {HARNESS_ERROR, COLLISION}:
            return name, f"{name} ended in {st.cls or 'an error'}"
    return None


def _open_stop(n: int, records: list[Record]) -> str | None:
    """A stop stays until a later record completes that stage on the same
    subject — an unrelated resume does not close it (PROTO-1-04)."""
    stop = _stop(records[n])
    if stop is None:
        return None
    stage, why = stop
    r = records[n]
    for s in records[n + 1:]:
        if stage == "draw":
            if _complete(s, "assembly"):
                return None
        elif getattr(s, SUBJECT[stage]) == getattr(r, SUBJECT[stage]) and getattr(r, SUBJECT[stage]) is not None and _complete(s, stage):
            return None
    return f"{r.id}: {why}"


def _confirmed_content(r: Record) -> bool:
    """Content counts only from a stage that completed: a finding recorded by an
    errored inspection is not confirmed (PROTO-1-04)."""
    verify = r.stages.get("verify")
    if verify is not None and verify.status == "done" and verify.cls == CONTENT:
        return True
    return any(r.stages.get(s) is not None and r.stages[s].status == "done" and r.stages[s].findings for s in INSPECTIONS)


def verdict(records: list[Record]) -> Verdict:
    if any(r.label != "judged" for r in records):
        raise NotJudged(", ".join(r.id for r in records if r.label != "judged"))
    for r in records:
        if _confirmed_content(r):
            return Verdict(FAILS, f"{r.id}: content in the build output; a later run does not undo it")
    runs = [r for r in records if r.kind == "run"]
    if not runs or any(r.not_possible for r in records):
        return Verdict(NOT_RUN, "the encrypted route is not possible" if any(r.not_possible for r in records) else "no run")
    last_run = max(n for n, r in enumerate(records) if r.kind == "run")
    stops = [x for x in (_open_stop(n, records) for n in range(last_run, len(records))) if x]
    if stops:
        return Verdict(STOPPED, "; ".join(stops) + "; repeated before any verdict")
    open_ = []
    for n, r in enumerate(records):
        if r.kind == "run":
            _, missing = _effective(r, records[n + 1:])
            open_ += [f"{r.id}: {s} missing" for s in missing]
    open_ += _unresolved_inconclusive(records)
    if open_:
        return Verdict(NOT_ESTABLISHED, "; ".join(open_))
    latest = records[last_run]
    stages, _ = _effective(latest, records[last_run + 1:])
    if stages["assembly"].cls == FORM or stages["verify"].cls in {FORM, SCHEMA_ONLY}:
        return Verdict(COST, f"{latest.id}: {stages['assembly'].cls if stages['assembly'].cls == FORM else stages['verify'].cls}")
    if stages["verify"].cls == PASS:
        return Verdict(PASSES, f"{latest.id}: every stage complete, verify passed, nothing found")
    return Verdict(NOT_ESTABLISHED, f"{latest.id}: verify ended in {stages['verify'].cls}")
