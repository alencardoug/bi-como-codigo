"""§10: where clear data may be written — the path rule, decided by the
filesystem alone and never by asking Git; the private run directory; the
drafts; and the result, renamed into place in one step.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import fcntl
import os
import pathlib
import re
import shutil
import signal
import tempfile

from . import INTERRUPTED, PATH_EXISTS, PATH_REFUSED, RUN_LEFTOVER, RUN_LOCKED, Refused

SAFE = re.compile(r"[A-Za-z0-9._/-]+")
RUN_PREFIX = "run-"
RESULT_PREFIX = ".bice-result-"
LOCK = ".bice-export.lock"
DRAFTS = "drafts"


def protected_roots(environ: dict[str, str], repo: pathlib.Path) -> list[pathlib.Path]:
    """This repository and the two eng_dados checkouts, resolved — checked
    explicitly, even without a `.git`."""
    roots = [repo]
    for name in ("ENG_DADOS_DIR", "ENG_DADOS_2_DIR"):
        if environ.get(name):
            roots.append(pathlib.Path(environ[name]))
    return [pathlib.Path(os.path.realpath(r)) for r in roots]


def check(path: pathlib.Path | str, protected: list[pathlib.Path]) -> pathlib.Path:
    """The rule of §10, on the resolved path: no `.git` entry in it or any
    ancestor, not under a protected root, and only `[A-Za-z0-9._/-]`.
    Returns the resolved path."""
    real = pathlib.Path(os.path.realpath(path))
    if not SAFE.fullmatch(real.as_posix()):
        raise Refused(PATH_REFUSED, check="characters")
    for ancestor in (real, *real.parents):
        if os.path.lexists(ancestor / ".git"):
            raise Refused(PATH_REFUSED, check="worktree")
    for root in protected:
        if real == root or root in real.parents:
            raise Refused(PATH_REFUSED, check="protected")
    return real


def staging_root(path: str | None, protected: list[pathlib.Path]) -> pathlib.Path:
    if not path:
        raise Refused(PATH_REFUSED, check="BICE_EXPORT_STAGING")
    real = check(path, protected)
    if not real.is_dir():
        raise Refused(PATH_REFUSED, check="BICE_EXPORT_STAGING")
    return real


class RunDirectory:
    """§10: under an exclusive lock, a fresh `mkdtemp` directory, mode 0700, the
    process's working directory and temporary directory while the run lasts,
    and removed when it ends — on success, a refusal, an exception or an
    interrupt. A leftover from a run killed outright refuses the next run."""

    def __init__(self, staging: pathlib.Path, protected: list[pathlib.Path]):
        self.staging = staging
        self.protected = protected
        self.path: pathlib.Path | None = None

    def __enter__(self) -> pathlib.Path:
        self._lock = open(self.staging / LOCK, "a+b")
        try:
            fcntl.flock(self._lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self._lock.close()
            raise Refused(RUN_LOCKED) from None
        try:
            if any(p.name.startswith((RUN_PREFIX, RESULT_PREFIX)) for p in self.staging.iterdir()):
                raise Refused(RUN_LEFTOVER)
            self.path = check(tempfile.mkdtemp(prefix=RUN_PREFIX, dir=self.staging), self.protected)
            os.chmod(self.path, 0o700)
            self._cwd = os.getcwd()
            self._tmpdir = os.environ.get("TMPDIR")
            self._tempdir = tempfile.tempdir
            os.chdir(self.path)
            os.environ["TMPDIR"] = str(self.path)
            tempfile.tempdir = str(self.path)
            self._term = signal.signal(signal.SIGTERM, _interrupt)
        except BaseException:
            self._release()
            raise
        return self.path

    def __exit__(self, *_exc) -> None:
        self._release()

    def _release(self) -> None:
        if hasattr(self, "_term"):
            signal.signal(signal.SIGTERM, self._term)
        if hasattr(self, "_cwd"):
            os.chdir(self._cwd)
            if self._tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = self._tmpdir
            tempfile.tempdir = self._tempdir
        if self.path is not None:
            shutil.rmtree(self.path, ignore_errors=True)
        with contextlib.suppress(OSError):
            fcntl.flock(self._lock, fcntl.LOCK_UN)
        self._lock.close()


def _interrupt(_signum, _frame):
    raise Refused(INTERRUPTED)


def publish(destination: str | None, files: dict[str, bytes], protected: list[pathlib.Path]) -> pathlib.Path:
    """§10, the result: written into a sibling temporary directory, then
    renamed into place in one step. The destination must not exist."""
    if not destination:
        raise Refused(PATH_REFUSED, check="BICE_EXPORT_DIR")
    target = check(destination, protected)
    if os.path.lexists(target):
        raise Refused(PATH_EXISTS)
    if not target.parent.is_dir():
        raise Refused(PATH_REFUSED, check="BICE_EXPORT_DIR")
    tmp = check(tempfile.mkdtemp(prefix=RESULT_PREFIX, dir=target.parent), protected)
    try:
        for rel, data in files.items():
            dest = tmp / rel
            check(dest.parent, protected)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "xb") as f:
                f.write(data)
        if os.path.lexists(target):
            raise Refused(PATH_EXISTS)
        os.rename(tmp, target)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return target


def draft_path(staging: pathlib.Path, protected: list[pathlib.Path], stem: str, now: dt.datetime | None = None) -> pathlib.Path:
    """§10, the drafts: `<staging>/drafts/<stem>.<UTC time>.json`, which outlives
    the run. Never under `release/`: the rule refuses any path in this repository."""
    drafts = staging / DRAFTS
    drafts.mkdir(mode=0o700, exist_ok=True)
    check(drafts, protected)
    when = (now or dt.datetime.now(dt.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    path = drafts / f"{stem}.{when}.json"
    if os.path.lexists(path):
        raise Refused(PATH_EXISTS)
    return check(path, protected)
