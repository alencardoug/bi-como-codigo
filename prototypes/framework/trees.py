"""Folder trees read, copied and archived without following a link
(docs/framework_prototype.md §2.2, §2.5.2; PROTO-1-01, PROTO-1-03).

Every host-side read of what a sandboxed phase wrote goes through here: the
root is refused if it, or any folder on the way to it, is a link; entries are
read with `lstat`; a link is kept as a link, never followed; a file keeps its
permission bits; a FIFO is carried as a FIFO; an entry no copy can carry —
a socket, a device — is listed, never dropped.
"""

from __future__ import annotations

import dataclasses
import gzip
import hashlib
import io
import os
import pathlib
import stat
import tarfile


class Refused(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Entry:
    rel: str
    kind: str  # "dir", "file", "symlink", "fifo", "other"
    digest: str  # SHA-256 of a file, the target of a link, "" otherwise
    mode: int  # the permission bits

    def key(self) -> tuple:
        return (self.rel, self.kind, self.digest, self.mode)


def real_root(base: pathlib.Path, rel: str = "") -> pathlib.Path:
    """`base/rel`, refused if any component of its absolute path — the
    ancestors of `base` included — is a link, or if it leaves `base`
    (PROTO-2-01). The components are checked as written, before anything
    normalizes them: `a/link/../b` is refused at `link`, never read as `a/b`
    (PROTO-3-02); a `..` anywhere is refused."""
    for part in pathlib.PurePosixPath(rel).parts:
        if part in ("..", "/"):
            raise Refused(f"{rel} leaves {base}")
    path = pathlib.Path(base) / rel
    if not path.is_absolute():
        path = pathlib.Path(os.getcwd()) / path  # the working folder as the kernel resolved it
    if ".." in path.parts:
        raise Refused(f"{path} has a '..' component: a host-side read is checked as written")
    probe = pathlib.Path(path.anchor)
    for part in path.parts[1:]:
        probe = probe / part
        if probe.is_symlink():
            raise Refused(f"{probe} is a link: a host-side read never follows one")
    if not path.is_dir():
        raise Refused(f"{path} is not a folder")
    return path


def entries(root: pathlib.Path) -> list[Entry]:
    """Every entry under `root`, sorted, read with lstat. The root is checked
    by `real_root`, and a folder the walk cannot read refuses the listing,
    naming it — a tree is never listed incomplete (PROTO-2-01)."""
    root = real_root(root)
    out = []
    failures: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False, onerror=lambda e: failures.append(str(e.filename))):
        here = pathlib.Path(dirpath)
        for name in sorted(dirnames + filenames):
            path = here / name
            st = path.lstat()
            rel = path.relative_to(root).as_posix()
            mode = stat.S_IMODE(st.st_mode)
            if stat.S_ISLNK(st.st_mode):
                out.append(Entry(rel, "symlink", os.readlink(path), 0))
            elif stat.S_ISDIR(st.st_mode):
                out.append(Entry(rel, "dir", "", mode))
            elif stat.S_ISREG(st.st_mode):
                with open(path, "rb", opener=lambda p, f: os.open(p, f | os.O_NOFOLLOW)) as handle:
                    out.append(Entry(rel, "file", hashlib.sha256(handle.read()).hexdigest(), mode))
            elif stat.S_ISFIFO(st.st_mode):
                out.append(Entry(rel, "fifo", "", mode))
            else:
                out.append(Entry(rel, "other", "", mode))
        dirnames[:] = [d for d in dirnames if not (here / d).is_symlink()]
    if failures:
        raise Refused(f"folders the walk cannot read: {sorted(failures)}")
    return sorted(out, key=lambda e: e.rel)


def files(root: pathlib.Path) -> dict[str, bytes]:
    """The regular files under `root`, by path; links and special entries are
    not read. Listed and read from the one checked root (PROTO-3-02)."""
    root = real_root(root)
    return {e.rel: (root / e.rel).read_bytes() for e in entries(root) if e.kind == "file"}


def copy(src: pathlib.Path, dst: pathlib.Path) -> list[str]:
    """`src` recreated at `dst`, which must not exist: folders, files with their
    modes, links as links, FIFOs as FIFOs. Returns the entries no copy can carry."""
    if dst.exists() or dst.is_symlink():
        raise FileExistsError(f"{dst} exists")
    src = real_root(src)  # listed and read from the one checked root (PROTO-3-02)
    dst.mkdir(parents=True)
    uncarried = []
    listed = entries(src)
    for e in listed:
        target = dst / e.rel
        if e.kind == "dir":
            target.mkdir()
        elif e.kind == "file":
            target.write_bytes((src / e.rel).read_bytes())
        elif e.kind == "symlink":
            os.symlink(e.digest, target)
        elif e.kind == "fifo":
            os.mkfifo(target)
        else:
            uncarried.append(e.rel)
    for e in reversed(listed):  # modes last, so that a read-only folder is still filled
        if e.kind in ("dir", "file", "fifo"):
            os.chmod(dst / e.rel, e.mode)
    os.chmod(dst, stat.S_IMODE(src.lstat().st_mode))
    return uncarried


def archive(src: pathlib.Path, dest: pathlib.Path) -> str:
    """A reproducible tar.gz of `src` — sorted, no owner, no time, modes kept,
    links and FIFOs as such — and its SHA-256. `dest` must not exist. An entry
    a tar cannot carry refuses the archive, naming it."""
    if dest.exists():
        raise FileExistsError(f"{dest} exists: an archive is kept, never overwritten")
    src = real_root(src)  # listed and read from the one checked root (PROTO-3-02)
    listed = entries(src)
    other = [e.rel for e in listed if e.kind == "other"]
    if other:
        raise Refused(f"entries no archive can carry: {other}")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for e in listed:
            info = tarfile.TarInfo(e.rel)
            info.mode, info.mtime, info.uid, info.gid, info.uname, info.gname = e.mode, 0, 0, 0, "", ""
            if e.kind == "dir":
                info.type = tarfile.DIRTYPE
                tar.addfile(info)
            elif e.kind == "file":
                data = (src / e.rel).read_bytes()
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
            elif e.kind == "symlink":
                info.type, info.linkname = tarfile.SYMTYPE, e.digest
                tar.addfile(info)
            elif e.kind == "fifo":
                info.type = tarfile.FIFOTYPE
                tar.addfile(info)
    raw = gzip.compress(buf.getvalue(), mtime=0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def _keep_mode(member: tarfile.TarInfo, path: str) -> tarfile.TarInfo:
    """The `tar` filter's refusals — links leaving the folder, devices — with
    the archived permission bits kept as they were, setgid and sticky included
    (PROTO-2-01)."""
    checked = tarfile.tar_filter(member, path)
    return checked.replace(mode=member.mode & 0o7777, deep=False) if member.isfile() or member.isdir() or member.isfifo() else checked


def extract(archive_path: pathlib.Path, out: pathlib.Path, digest: str) -> None:
    """An archive is inspected from the archive: its digest checked first."""
    raw = archive_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"{archive_path} is not the archive of digest {digest}")
    if out.exists():
        raise FileExistsError(f"{out} exists")
    out.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        members = sorted(tar.getmembers(), key=lambda m: m.name)
        bad = [m.name for m in members if m.name.startswith("/") or ".." in pathlib.PurePosixPath(m.name).parts]
        if bad:  # every later attribute is applied inside `out` only (PROTO-2-14)
            raise Refused(f"archive members outside the folder: {bad}")
        dirs = [m for m in members if m.isdir()]
        tar.extractall(out, members=[m for m in members if not m.isdir()] + dirs, filter=_keep_mode)
    for m in dirs:
        target = out / m.name
        if not os.path.abspath(target).startswith(os.path.abspath(out) + os.sep) or target.is_symlink():
            raise Refused(f"{m.name} resolves outside the folder")
        os.chmod(target, m.mode & 0o7777)
