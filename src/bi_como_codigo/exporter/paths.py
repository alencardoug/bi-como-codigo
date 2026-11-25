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

from . import CLEANUP_FAILED, INTERRUPTED, PATH_EXISTS, PATH_REFUSED, RUN_LEFTOVER, RUN_LOCKED, Refused

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
        """The private files first, whatever else fails (XIMPL-1-04). While
        cleaning, SIGINT and SIGTERM are only noted — Python runs signal
        handlers in the main thread, whichever thread the kernel picked, so a
        signal mask would not hold them —, the run directory is removed and its
        removal checked, then the environment, the lock and the caller's signal
        handler are restored, and the caller's directory comes last: if it
        vanished, the process stays in the staging root. The handlers come back
        SIGTERM first and SIGINT last, so a SIGINT between the two is still
        noted (XIMPL-2-05). A noted signal then ends the run as it would have
        mid-run — SIGINT as `KeyboardInterrupt`, SIGTERM as `interrupted` —, and
        the caller publishes nothing. A run directory that could not be removed
        refuses, and the next run refuses on it as a leftover."""
        noted: list[int] = []
        saved_int = signal.signal(signal.SIGINT, lambda signum, _frame: noted.append(signum))
        saved_term = signal.signal(signal.SIGTERM, lambda signum, _frame: noted.append(signum))
        failed = False
        try:
            if self.path is not None:
                with contextlib.suppress(OSError):
                    os.chdir(self.staging)
                remove_tree(self.path)
                failed = os.path.lexists(self.path)
            if hasattr(self, "_tmpdir"):
                if self._tmpdir is None:
                    os.environ.pop("TMPDIR", None)
                else:
                    os.environ["TMPDIR"] = self._tmpdir
                tempfile.tempdir = self._tempdir
            with contextlib.suppress(OSError):
                fcntl.flock(self._lock, fcntl.LOCK_UN)
            with contextlib.suppress(OSError):
                self._lock.close()
            if hasattr(self, "_cwd"):
                with contextlib.suppress(OSError):
                    os.chdir(self._cwd)
        finally:
            signal.signal(signal.SIGTERM, self._term if hasattr(self, "_term") else saved_term)
            signal.signal(signal.SIGINT, saved_int)
        if failed:
            raise Refused(CLEANUP_FAILED)
        if signal.SIGINT in noted:
            raise KeyboardInterrupt
        if signal.SIGTERM in noted:
            raise Refused(INTERRUPTED, check="cleanup")


def remove_tree(path: pathlib.Path) -> None:
    """The removal of the run directory; its outcome is checked by the caller."""
    shutil.rmtree(path, ignore_errors=True)


def _interrupt(_signum, _frame):
    raise Refused(INTERRUPTED)


RENAME_NOREPLACE = 1
AT_FDCWD = -100


def rename_noreplace(source: pathlib.Path, target: pathlib.Path) -> None:
    """`renameat2(RENAME_NOREPLACE)`: the result is put in place in one step,
    and never over a destination that appeared since it was checked
    (XIMPL-1-13). Where the call is not available, nothing is renamed."""
    import ctypes
    import errno

    libc = ctypes.CDLL(None, use_errno=True)
    renameat2 = getattr(libc, "renameat2", None)
    if renameat2 is None:
        raise Refused(PATH_REFUSED, check="renameat2")
    if renameat2(AT_FDCWD, os.fsencode(source), AT_FDCWD, os.fsencode(target), RENAME_NOREPLACE) != 0:
        code = ctypes.get_errno()
        raise Refused(PATH_EXISTS if code == errno.EEXIST else PATH_REFUSED, check=None if code == errno.EEXIST else "rename")


def publish(destination: str | None, files: dict[str, bytes], protected: list[pathlib.Path]) -> pathlib.Path:
    """§10, the result: written into a sibling temporary directory, then
    renamed into place in one step. The destination must not exist.

    Signals have a defined outcome here too (XIMPL-3-02): while the files are
    written, SIGTERM refuses `interrupted`, check `publish`, and the sibling is
    removed — no result, nothing partial; around the rename, SIGINT and SIGTERM
    are noted, and one noted ends the command with `interrupted`, check
    `published`: the result is complete, in place."""
    if not destination:
        raise Refused(PATH_REFUSED, check="BICE_EXPORT_DIR")
    target = check(destination, protected)
    if os.path.lexists(target):
        raise Refused(PATH_EXISTS)
    if not target.parent.is_dir():
        raise Refused(PATH_REFUSED, check="BICE_EXPORT_DIR")
    saved_term = signal.signal(signal.SIGTERM, _interrupt_publication)
    tmp = None
    try:
        tmp = check(tempfile.mkdtemp(prefix=RESULT_PREFIX, dir=target.parent), protected)
        for rel, data in files.items():
            dest = tmp / rel
            check(dest.parent, protected)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "xb") as f:
                f.write(data)
        noted: list[int] = []
        signal.signal(signal.SIGTERM, lambda signum, _frame: noted.append(signum))
        saved_int = signal.signal(signal.SIGINT, lambda signum, _frame: noted.append(signum))
        try:
            rename_noreplace(tmp, target)
            tmp = None
        finally:
            signal.signal(signal.SIGINT, saved_int)
    except BaseException:
        if tmp is not None:
            shutil.rmtree(tmp, ignore_errors=True)
        raise
    finally:
        signal.signal(signal.SIGTERM, saved_term)
    if noted:
        raise Refused(INTERRUPTED, check="published")
    return target


def _interrupt_publication(_signum, _frame):
    raise Refused(INTERRUPTED, check="publish")


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
