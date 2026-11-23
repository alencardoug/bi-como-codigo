"""The encrypted route's inputs as an allowlist (docs/framework_prototype.md
§2.2).

The work folder of every install and every build is assembled fresh from a
list the harness writes and archives — the destination path and SHA-256 of
each file, and where it comes from —, and before each phase every file in the
folder is compared with the list: an extra, missing or changed file refuses
the phase, naming it. The candidate's tracked sources come from the blobs of a
recorded commit, never from the working tree.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import pathlib
import subprocess

import roots

REPO = roots.CHECKOUT  # its Git objects (CMP-3-03)


class Refused(Exception):
    """A phase refused before it starts."""


@dataclasses.dataclass(frozen=True)
class Entry:
    dest: str  # path in the work folder
    sha256: str  # or "symlink:<relative target>", for a link inside the folder
    source: str  # "git:<commit>:<path>", a host path, or "" for a link
    executable: bool = False


@dataclasses.dataclass(frozen=True)
class Allowlist:
    entries: tuple[Entry, ...]

    @property
    def digest(self) -> str:
        """The build input's identity (§5): the digest of the list itself."""
        return hashlib.sha256(self.dumps().encode()).hexdigest()

    def dumps(self) -> str:
        return json.dumps([dataclasses.asdict(e) for e in sorted(self.entries, key=lambda e: e.dest)], indent=1) + "\n"

    def __add__(self, other: "Allowlist") -> "Allowlist":
        dests = {e.dest for e in self.entries}
        clash = sorted(dests & {e.dest for e in other.entries})
        if clash:
            raise Refused(f"two inputs for {clash[0]}")
        return Allowlist(self.entries + other.entries)


def _git(*args: str) -> bytes:
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True).stdout


def tracked(commit: str, prefix: str, dest_prefix: str = "") -> Allowlist:
    """The files tracked under `prefix` at `commit`, from NUL-delimited
    `git ls-tree` output — a name Git would quote is read as it is — each read
    from its own blob id (PROTO-1-14). `dest_prefix` replaces `prefix` in the
    work folder."""
    records = [r for r in _git("ls-tree", "-r", "-z", "--full-tree", commit, "--", prefix).split(b"\0") if r]
    if not records:
        raise Refused(f"nothing is tracked under {prefix} at {commit}")
    out = []
    for record in records:
        meta, raw_name = record.split(b"\t", 1)
        mode, kind, oid = meta.decode().split()
        name = raw_name.decode("utf-8", "surrogateescape")
        if kind != "blob" or mode not in ("100644", "100755"):
            raise Refused(f"{name} is not a plain tracked file")
        blob = _git("cat-file", "blob", oid)
        rel = name[len(prefix):].lstrip("/") if name.startswith(prefix) and name != prefix else pathlib.PurePosixPath(name).name
        out.append(Entry(f"{dest_prefix}{rel}", hashlib.sha256(blob).hexdigest(), f"git:{oid}:{name}", mode == "100755"))
    return Allowlist(tuple(out))


def _link_target(root: pathlib.Path, path: pathlib.Path) -> str:
    target = os.readlink(path)
    resolved = (path.parent / target).resolve()
    if os.path.isabs(target) or not resolved.is_relative_to(root.resolve()):
        raise Refused(f"{path.relative_to(root)} links outside its folder")
    return target


def files(root: pathlib.Path, dest_prefix: str = "") -> Allowlist:
    """Every file under a host folder — an npm cache, an install's
    `node_modules/` — by its digest; a link by its relative target, which must
    stay inside the folder. A folder the walk cannot read refuses the list,
    naming it (PROTO-3-03)."""
    root = _checked_root(root)
    out = []
    for e in _walk(root):
        path = root / e.rel
        if e.kind == "symlink":
            out.append(Entry(f"{dest_prefix}{e.rel}", f"symlink:{_link_target(root, path)}", ""))
        elif e.kind == "file":
            out.append(Entry(f"{dest_prefix}{e.rel}", e.digest, str(path), os.access(path, os.X_OK)))
    return Allowlist(tuple(out))


def _checked_root(root: pathlib.Path) -> pathlib.Path:
    import trees

    try:
        return trees.real_root(root)
    except trees.Refused as refusal:
        raise Refused(str(refusal)) from None


def _walk(root: pathlib.Path) -> list:
    """Every entry under `root` with lstat, never following a link; a folder
    the walk cannot read refuses it, naming the folder — `Path.rglob` leaves
    such a subtree out in silence (PROTO-3-03)."""
    import trees

    try:
        return trees.entries(root)
    except trees.Refused as refusal:
        raise Refused(str(refusal)) from None


def single(dest: str, data_path: pathlib.Path) -> Allowlist:
    return Allowlist((Entry(dest, hashlib.sha256(data_path.read_bytes()).hexdigest(), str(data_path), os.access(data_path, os.X_OK)),))


def _content(entry: Entry) -> bytes:
    if entry.source.startswith("git:"):
        _, oid, _name = entry.source.split(":", 2)
        return _git("cat-file", "blob", oid)
    return pathlib.Path(entry.source).read_bytes()


def assemble(allow: Allowlist, work: pathlib.Path) -> None:
    """A fresh work folder holding exactly the list, each file checked."""
    if work.exists():
        raise Refused(f"{work} exists: a work folder is assembled fresh")
    work.mkdir(parents=True)
    for entry in sorted(allow.entries, key=lambda e: e.sha256.startswith("symlink:")):
        dest = work / entry.dest
        if entry.sha256.startswith("symlink:"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(entry.sha256[len("symlink:"):], dest)
            continue
        data = _content(entry)
        if hashlib.sha256(data).hexdigest() != entry.sha256:
            raise Refused(f"{entry.dest} is not the listed file")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        dest.chmod(0o755 if entry.executable else 0o644)


def check(allow: Allowlist, work: pathlib.Path) -> None:
    """Before each phase: every file in the work folder is a listed one, and
    every listed one is there with its digest. A folder the walk cannot read
    refuses the check, naming it: a work folder is never judged on part of
    itself (PROTO-3-03)."""
    listed = {e.dest: (e.sha256, e.executable and not e.sha256.startswith("symlink:")) for e in allow.entries}
    work = _checked_root(work)
    found = {}
    for e in _walk(work):
        path = work / e.rel
        if e.kind == "symlink":
            found[e.rel] = (f"symlink:{_link_target(work, path)}", False)
        elif e.kind == "file":
            found[e.rel] = (e.digest, os.access(path, os.X_OK))
        elif e.kind != "dir":
            raise Refused(f"{e.rel} is not a plain file, a folder or a link")
    for rel in sorted(found):
        if rel not in listed:
            raise Refused(f"{rel} is not in the allowlist")
        if found[rel] != listed[rel]:
            raise Refused(f"{rel} is not the listed file")
    for rel in sorted(listed):
        if rel not in found:
            raise Refused(f"{rel} is listed and missing")


def archive_list(allow: Allowlist, dest: pathlib.Path) -> str:
    if dest.exists():
        raise FileExistsError(f"{dest} exists")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(allow.dumps(), encoding="utf-8")
    return allow.digest


def copy_out(work: pathlib.Path, rel: str, out: pathlib.Path) -> list[str]:
    """The builder output is copied out of the work folder by the harness,
    outside the sandbox, without following a link — the output's root and the
    folders on the way to it included (PROTO-1-01). Returns the entries no copy
    can carry, for the run to record."""
    import trees

    try:
        source = trees.real_root(work, rel)
    except trees.Refused as refusal:
        raise Refused(str(refusal)) from None
    return trees.copy(source, out)
