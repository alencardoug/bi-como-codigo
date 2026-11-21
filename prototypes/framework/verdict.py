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
    draw_clean: bool = False  # a clean draw recorded against this builder output, of the fixture below
    fixture: str | None = None  # the drawn fixture's digest: of a clean draw, or of the package an assembly sealed
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


@dataclasses.dataclass(frozen=True)
class _History:
    """Every stage attempt that counts, complete or not: `eligible` holds
    (record, stage) for an attempt made after what it is about was established
    before it — its run's own stages before it, or an earlier record on the
    same digest —, `complete` those of them that completed. One rule for
    findings, gaps, stops and closures (PROTO-4-02)."""
    eligible: frozenset
    complete: frozenset


def _history(records: list[Record]) -> _History:
    """The prerequisites, in the order the records were made: the builder's
    inspection needs that archive; assembly that inspected builder output;
    `verify` an artifact assembled (a refusal by form assembles none); the
    artifact's inspection that artifact verified. A resume archives nothing —
    a run that failed before its archive is closed by a later run (§2.5.4) —
    and a resume no earlier record explains counts for nothing (PROTO-3-01).
    In a record, a stage that is missing in a run, or that did not complete,
    ends what counts of it."""
    archived: set[str] = set()
    inspected: set[str] = set()
    assembled: set[str] = set()
    verified: set[str] = set()
    eligible: set[tuple[int, str]] = set()
    complete: set[tuple[int, str]] = set()
    for n, r in enumerate(records):
        for name in STAGES:
            if name not in r.stages:
                if r.kind == "run":
                    break
                continue
            subject = getattr(r, SUBJECT[name])
            if name in ("build", "archive"):
                good = r.kind == "run"
            elif name == "inspect_builder":
                good = subject in archived
            elif name == "assembly":
                good = subject in inspected
            elif name == "verify":
                good = subject in assembled
            else:
                good = subject in verified
            if not good or subject is None:
                break
            eligible.add((n, name))
            if not _complete(r, name):
                break
            complete.add((n, name))
            if name == "archive":
                archived.add(subject)
            elif name == "inspect_builder":
                inspected.add(subject)
            elif name == "assembly" and r.stages[name].cls == PASS:
                assembled.add(r.artifact_digest)
            elif name == "verify":
                verified.add(subject)
    return _History(frozenset(eligible), frozenset(complete))


def _after(position: tuple[int, int], m: int, name: str) -> bool:
    """Record *m*'s stage comes after `position` — a later record, or a later
    stage of the same record (PROTO-4-01)."""
    return (m, STAGES.index(name)) > position


def _clean_draw(n: int, records: list[Record]) -> int | None:
    """The first record after *n* that recorded a clean draw against run *n*'s
    builder output."""
    r = records[n]
    for m in range(n + 1, len(records)):
        s = records[m]
        if r.builder_digest is not None and s.builder_digest == r.builder_digest and s.draw_clean:
            return m
    return None


def _effective(n: int, records: list[Record], h: _History) -> tuple[dict[str, Stage], list[str]]:
    """Run *n*'s stages with what later records completed on the same
    subjects, each after the one before it, and the mandatory stages still
    open."""
    r = records[n]
    stages: dict[str, Stage] = {}
    position = (n, -1)
    for name in STAGES:
        if (n, name) not in h.complete:
            break
        stages[name] = r.stages[name]
        position = (n, STAGES.index(name))
    form = "assembly" in stages and stages["assembly"].cls == FORM
    missing = [s for s in _mandatory(form) if s not in stages]
    if not missing:
        return stages, []
    if "build" in missing or "archive" in missing:
        # Closed only by a later run of the same build input carried through every stage.
        for m in range(n + 1, len(records)):
            s = records[m]
            if s.kind == "run" and r.build_input is not None and s.build_input == r.build_input:
                own, still = _effective(m, records, h)
                if not still:
                    return own, []
        return stages, missing
    if "inspect_builder" not in stages:
        found = next((m for m in range(n + 1, len(records))
                      if records[m].builder_digest == r.builder_digest and (m, "inspect_builder") in h.complete), None)
        if found is None:
            return stages, [s for s in _mandatory(form) if s not in stages]
        stages["inspect_builder"] = records[found].stages["inspect_builder"]
        position = (found, STAGES.index("inspect_builder"))
    fixture = None
    if r.draw_exhausted:
        # The draw of this run found no clean fixture: what replaces its tail
        # comes after a clean draw against the same builder output, with the
        # fixture that draw gave (PROTO-4-03).
        drawn = _clean_draw(n, records)
        if drawn is None:
            return stages, [s for s in _mandatory(form) if s not in stages]
        position = max(position, (drawn, STAGES.index("inspect_builder")))  # in a record, the draw comes before assembly
        fixture = records[drawn].fixture
    artifact = r.artifact_digest if "assembly" in stages else None
    if "assembly" not in stages:
        for m in range(len(records)):
            s = records[m]
            if not _after(position, m, "assembly") or s.builder_digest != r.builder_digest or (m, "assembly") not in h.complete:
                continue
            if fixture is not None and s.fixture != fixture:
                continue
            stages["assembly"] = s.stages["assembly"]
            position = (m, STAGES.index("assembly"))
            artifact = s.artifact_digest if s.stages["assembly"].cls == PASS else None
            break
    if "assembly" in stages and stages["assembly"].cls != FORM and artifact is not None:
        # An artifact that exists is closed only by the same artifact checked
        # again, each stage after the one before it.
        for t in ("verify", "inspect_artifact"):
            if t in stages:
                continue
            found = next((m for m in range(len(records)) if _after(position, m, t)
                          and records[m].artifact_digest == artifact and (m, t) in h.complete), None)
            if found is None:
                break
            stages[t] = records[found].stages[t]
            position = (found, STAGES.index(t))
    form = "assembly" in stages and stages["assembly"].cls == FORM
    return stages, [s for s in _mandatory(form) if s not in stages]


def _unresolved_inconclusive(records: list[Record], h: _History) -> list[str]:
    """An inconclusive file counts as the stage that read it counts, and is
    resolved only by re-inspecting that archive (PROTO-4-02)."""
    out = []
    for n, name in sorted(h.complete):
        if name not in INSPECTIONS or not records[n].stages[name].inconclusive:
            continue
        key = INSPECTIONS[name]
        target = getattr(records[n], key)
        if not any(getattr(records[m], key) == target and (m, name) in h.complete and not records[m].stages[name].inconclusive
                   for m in range(n + 1, len(records))):
            out.append(f"{records[n].id}: {name} of {target} inconclusive")
    return out


def _stop(n: int, r: Record, h: _History) -> tuple[str, str] | None:
    """(the stage, why) of a record's stop: an attempt that counts and failed,
    or a draw exhausted. An attempt no earlier record explains stops nothing
    (PROTO-4-02)."""
    if r.draw_exhausted:
        return "draw", "the draw exhausted"
    for name in STAGES:
        st = r.stages.get(name)
        if st is None or (n, name) not in h.eligible:
            continue
        if st.status == "interrupted":
            return name, f"{name} interrupted"
        if st.status == "error" or st.cls in {HARNESS_ERROR, COLLISION}:
            return name, f"{name} ended in {st.cls or 'an error'}"
    return None


def _open_stop(n: int, records: list[Record], h: _History) -> str | None:
    """A stop stays until a later record completes that stage on the same
    subject — an unrelated resume does not close it (PROTO-1-04) —; a draw,
    until a clean draw is recorded against the same builder output."""
    stop = _stop(n, records[n], h)
    if stop is None:
        return None
    stage, why = stop
    r = records[n]
    if stage == "draw":
        return None if _clean_draw(n, records) is not None else f"{r.id}: {why}"
    subject = getattr(r, SUBJECT[stage])
    if subject is not None and any(getattr(records[m], SUBJECT[stage]) == subject and (m, stage) in h.complete
                                   for m in range(n + 1, len(records))):
        return None
    return f"{r.id}: {why}"


def _content(records: list[Record], h: _History) -> str | None:
    """The first record whose content counts: from an attempt that counts and
    completed (PROTO-1-04, PROTO-2-04, PROTO-3-01, PROTO-4-02)."""
    for n, name in sorted(h.complete):
        st = records[n].stages[name]
        if (name == "verify" and st.cls == CONTENT) or (name in INSPECTIONS and st.findings):
            return records[n].id
    return None


def verdict(records: list[Record]) -> Verdict:
    if any(r.label != "judged" for r in records):
        raise NotJudged(", ".join(r.id for r in records if r.label != "judged"))
    h = _history(records)
    found = _content(records, h)
    if found is not None:
        return Verdict(FAILS, f"{found}: content in the build output; a later run does not undo it")
    runs = [r for r in records if r.kind == "run"]
    if not runs or any(r.not_possible for r in records):
        return Verdict(NOT_RUN, "the encrypted route is not possible" if any(r.not_possible for r in records) else "no run")
    last_run = max(n for n, r in enumerate(records) if r.kind == "run")
    stops = [x for x in (_open_stop(n, records, h) for n in range(last_run, len(records))) if x]
    if stops:
        return Verdict(STOPPED, "; ".join(stops) + "; repeated before any verdict")
    open_ = []
    for n, r in enumerate(records):
        if r.kind == "run":
            _, missing = _effective(n, records, h)
            open_ += [f"{r.id}: {s} missing" for s in missing]
    open_ += _unresolved_inconclusive(records, h)
    if open_:
        return Verdict(NOT_ESTABLISHED, "; ".join(open_))
    latest = records[last_run]
    stages, _ = _effective(last_run, records, h)
    if stages["assembly"].cls == FORM or stages["verify"].cls in {FORM, SCHEMA_ONLY}:
        return Verdict(COST, f"{latest.id}: {stages['assembly'].cls if stages['assembly'].cls == FORM else stages['verify'].cls}")
    if stages["verify"].cls == PASS:
        return Verdict(PASSES, f"{latest.id}: every stage complete, verify passed, nothing found")
    return Verdict(NOT_ESTABLISHED, f"{latest.id}: verify ended in {stages['verify'].cls}")
