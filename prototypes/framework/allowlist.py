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

REPO = pathlib.Path(__file__).resolve().parents[2]


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
    """`git ls-files` of `prefix` at `commit`, each file read from its blob.
    `dest_prefix` replaces `prefix` in the work folder."""
    lines = _git("ls-tree", "-r", commit, "--", prefix).decode().splitlines()
    if not lines:
        raise Refused(f"nothing is tracked under {prefix} at {commit}")
    out = []
    for line in lines:
        meta, name = line.split("\t", 1)
        mode = meta.split()[0]
        if mode not in ("100644", "100755"):
            raise Refused(f"{name} is not a plain tracked file")
        blob = _git("show", f"{commit}:{name}")
        rel = name[len(prefix):].lstrip("/") if name.startswith(prefix) and name != prefix else pathlib.PurePosixPath(name).name
        out.append(Entry(f"{dest_prefix}{rel}", hashlib.sha256(blob).hexdigest(), f"git:{commit}:{name}", mode == "100755"))
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
    stay inside the folder."""
    out = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            out.append(Entry(f"{dest_prefix}{path.relative_to(root).as_posix()}", f"symlink:{_link_target(root, path)}", ""))
        elif path.is_file():
            out.append(Entry(f"{dest_prefix}{path.relative_to(root).as_posix()}", hashlib.sha256(path.read_bytes()).hexdigest(),
                             str(path), os.access(path, os.X_OK)))
    return Allowlist(tuple(out))


def single(dest: str, data_path: pathlib.Path) -> Allowlist:
    return Allowlist((Entry(dest, hashlib.sha256(data_path.read_bytes()).hexdigest(), str(data_path), os.access(data_path, os.X_OK)),))


def _content(entry: Entry) -> bytes:
    if entry.source.startswith("git:"):
        _, commit, name = entry.source.split(":", 2)
        return _git("show", f"{commit}:{name}")
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
    every listed one is there with its digest."""
    listed = {e.dest: (e.sha256, e.executable and not e.sha256.startswith("symlink:")) for e in allow.entries}
    found = {}
    for path in sorted(work.rglob("*")):
        rel = path.relative_to(work).as_posix()
        if path.is_symlink():
            found[rel] = (f"symlink:{_link_target(work, path)}", False)
        elif not path.is_file() and not path.is_dir():
            raise Refused(f"{rel} is not a plain file, a folder or a link")
        elif path.is_file():
            found[rel] = (hashlib.sha256(path.read_bytes()).hexdigest(), os.access(path, os.X_OK))
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
