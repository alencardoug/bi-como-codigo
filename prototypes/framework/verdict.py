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
    draw_clean: bool = False  # a clean draw recorded against this builder output
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


def _attached(records: list[Record]) -> set[tuple[int, str]]:
    """Every (record, stage) that counts, in the order the records were made: a
    stage counts only after what it is about was established by an earlier
    stage — its run's own stages before it, or an earlier record on the same
    digest. A builder's inspection needs that archive, assembly that inspected
    builder output, `verify` and the artifact's inspection that assembled
    artifact. A resume archives nothing: a run that failed before its archive is
    closed by a later run (§2.5.4). A resume no earlier run explains counts for
    nothing (PROTO-3-01)."""
    archived: set[str] = set()
    inspected: set[str] = set()
    assembled: set[str] = set()
    ok: set[tuple[int, str]] = set()
    for n, r in enumerate(records):
        for name in STAGES:
            if name not in r.stages:
                if r.kind == "run":
                    break  # a run's stage counts only after every stage before it
                continue
            if not _complete(r, name):
                break
            if name in ("build", "archive"):
                good = r.kind == "run"
            elif name == "inspect_builder":
                good = r.builder_digest in archived
            elif name == "assembly":
                good = r.builder_digest in inspected
            else:
                good = r.artifact_digest in assembled
            if not good:
                break
            ok.add((n, name))
            if name == "archive":
                archived.add(r.builder_digest)
            elif name == "inspect_builder":
                inspected.add(r.builder_digest)
            elif name == "assembly" and r.artifact_digest is not None:
                assembled.add(r.artifact_digest)
    return ok


def _effective(n: int, records: list[Record], ok: set[tuple[int, str]]) -> tuple[dict[str, Stage], list[str]]:
    """Run *n*'s stages with what later records completed on the same subjects,
    each one after the stage before it (PROTO-3-01), and the mandatory stages
    still open."""
    r = records[n]
    stages: dict[str, Stage] = {}
    for name in STAGES:
        if (n, name) not in ok:
            break
        stages[name] = r.stages[name]
    form = "assembly" in stages and stages["assembly"].cls == FORM
    missing = [s for s in _mandatory(form) if s not in stages]
    if not missing:
        return stages, []
    if "build" in missing or "archive" in missing:
        # Closed only by a later run of the same build input carried through every stage.
        for m in range(n + 1, len(records)):
            s = records[m]
            if s.kind == "run" and r.build_input is not None and s.build_input == r.build_input:
                own, still = _effective(m, records, ok)
                if not still:
                    return own, []
        return stages, missing
    position = n  # the record that closed the last stage so far: later stages come from it or after it
    if "inspect_builder" not in stages:
        for m in range(n + 1, len(records)):
            if records[m].builder_digest == r.builder_digest and (m, "inspect_builder") in ok:
                stages["inspect_builder"] = records[m].stages["inspect_builder"]
                position = m
                break
        else:
            return stages, [s for s in _mandatory(form) if s not in stages]
    if "assembly" not in stages:
        # Resumed from the inspected builder digest: a refusal by form needs
        # nothing after it; otherwise assembly, verify and the artifact's
        # inspection, all of them, in one resume.
        for m in range(position + 1, len(records)):
            s = records[m]
            if s.builder_digest != r.builder_digest:
                continue
            if (m, "assembly") in ok and s.stages["assembly"].cls == FORM:
                stages["assembly"] = s.stages["assembly"]
                break
            if all((m, t) in ok for t in TAIL):
                stages.update({t: s.stages[t] for t in TAIL})
                break
    elif r.artifact_digest is not None:
        # An artifact that exists is closed only by the same artifact checked
        # again, each stage after the one before it.
        for t in TAIL:
            if t in stages:
                continue
            for m in range(position + 1, len(records)):
                if records[m].artifact_digest == r.artifact_digest and (m, t) in ok:
                    stages[t] = records[m].stages[t]
                    position = m
                    break
            else:
                break
    form = "assembly" in stages and stages["assembly"].cls == FORM
    return stages, [s for s in _mandatory(form) if s not in stages]


def _unresolved_inconclusive(records: list[Record], ok: set[tuple[int, str]]) -> list[str]:
    """An inconclusive file is resolved only by re-inspecting that archive."""
    out = []
    for n, r in enumerate(records):
        for stage, key in INSPECTIONS.items():
            st = r.stages.get(stage)
            if st is None or not st.inconclusive:
                continue
            target = getattr(r, key)
            if target is None or not any(getattr(records[m], key) == target and (m, stage) in ok
                                         and not records[m].stages[stage].inconclusive
                                         for m in range(n + 1, len(records))):
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


def _open_stop(n: int, records: list[Record], ok: set[tuple[int, str]]) -> str | None:
    """A stop stays until a later record completes that stage on the same
    subject — an unrelated resume does not close it (PROTO-1-04)."""
    stop = _stop(records[n])
    if stop is None:
        return None
    stage, why = stop
    r = records[n]
    for m in range(n + 1, len(records)):
        s = records[m]
        if stage == "draw":
            # Repeated only by a clean draw recorded against the same builder
            # output: an assembly, even refused by form, says nothing of the
            # draw (PROTO-3-01).
            if r.builder_digest is not None and s.builder_digest == r.builder_digest and s.draw_clean:
                return None
        elif getattr(r, SUBJECT[stage]) is not None and getattr(s, SUBJECT[stage]) == getattr(r, SUBJECT[stage]) and (m, stage) in ok:
            return None
    return f"{r.id}: {why}"


def _content(records: list[Record], ok: set[tuple[int, str]]) -> str | None:
    """The first record whose content counts: from a stage that completed, bound
    to its subject and after what it is about (PROTO-1-04, PROTO-2-04,
    PROTO-3-01)."""
    for n, name in sorted(ok):
        st = records[n].stages[name]
        if (name == "verify" and st.cls == CONTENT) or (name in INSPECTIONS and st.findings):
            return records[n].id
    return None


def verdict(records: list[Record]) -> Verdict:
    if any(r.label != "judged" for r in records):
        raise NotJudged(", ".join(r.id for r in records if r.label != "judged"))
    ok = _attached(records)
    found = _content(records, ok)
    if found is not None:
        return Verdict(FAILS, f"{found}: content in the build output; a later run does not undo it")
    runs = [r for r in records if r.kind == "run"]
    if not runs or any(r.not_possible for r in records):
        return Verdict(NOT_RUN, "the encrypted route is not possible" if any(r.not_possible for r in records) else "no run")
    last_run = max(n for n, r in enumerate(records) if r.kind == "run")
    stops = [x for x in (_open_stop(n, records, ok) for n in range(last_run, len(records))) if x]
    if stops:
        return Verdict(STOPPED, "; ".join(stops) + "; repeated before any verdict")
    open_ = []
    for n, r in enumerate(records):
        if r.kind == "run":
            _, missing = _effective(n, records, ok)
            open_ += [f"{r.id}: {s} missing" for s in missing]
    open_ += _unresolved_inconclusive(records, ok)
    if open_:
        return Verdict(NOT_ESTABLISHED, "; ".join(open_))
    latest = records[last_run]
    stages, _ = _effective(last_run, records, ok)
    if stages["assembly"].cls == FORM or stages["verify"].cls in {FORM, SCHEMA_ONLY}:
        return Verdict(COST, f"{latest.id}: {stages['assembly'].cls if stages['assembly'].cls == FORM else stages['verify'].cls}")
    if stages["verify"].cls == PASS:
        return Verdict(PASSES, f"{latest.id}: every stage complete, verify passed, nothing found")
    return Verdict(NOT_ESTABLISHED, f"{latest.id}: verify ended in {stages['verify'].cls}")
