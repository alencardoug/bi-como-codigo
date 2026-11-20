"""The harness of stage 2.3 (docs/framework_prototype.md §2.2, §2.5.1).

Assembly places the validated package into a copy of a candidate's builder
output; the gate's own `release.verify` then judges the artifact, unchanged,
under a root the harness writes; and each outcome is classified by the stage
that produced it — never read as the candidate's pass or failure when it is
the harness's own.

The classes: `HARNESS_ERROR`, `FORM`, `SCHEMA_ONLY`, `CONTENT`, `COLLISION`,
`PASS`. A `HARNESS_ERROR` or a `COLLISION` stops the run.
"""

from __future__ import annotations

import dataclasses
import gzip
import hashlib
import io
import os
import pathlib
import re
import shutil
import tarfile
import tempfile

import fixture as fx_mod
from bi_como_codigo import contract as c, envelope as e, release

HERE = fx_mod.HERE
DECLARATIONS = HERE / "release"

HARNESS_ERROR = "HARNESS_ERROR"
FORM = "FORM"
SCHEMA_ONLY = "SCHEMA_ONLY"
CONTENT = "CONTENT"
COLLISION = "COLLISION"
PASS = "PASS"
STOPS = frozenset({HARNESS_ERROR, COLLISION})

PACKAGE = "package"


@dataclasses.dataclass(frozen=True)
class Outcome:
    stage: str  # "assembly" or "verify"
    cls: str
    message: str
    detail: dict = dataclasses.field(default_factory=dict)


# --- archives (§2.5.2: outputs are kept) ----------------------------------------------


def tree(root: pathlib.Path) -> list[tuple[str, str, str]]:
    """(path, kind, digest or link target) of every entry, sorted. Unlike
    `release.listing`, it records what the gate refuses instead of refusing it,
    so that assembly copies a builder output as it is and `verify` judges it."""
    out = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            out.append((rel, "symlink", os.readlink(path)))
        elif path.is_file():
            out.append((rel, "file", hashlib.sha256(path.read_bytes()).hexdigest()))
        elif path.is_dir():
            out.append((rel, "dir", ""))
        else:
            out.append((rel, "other", ""))
    return out


def archive(src: pathlib.Path, dest: pathlib.Path) -> str:
    """A reproducible tar.gz of `src` — sorted, no owner, no time — and its
    SHA-256. `dest` must not exist: an archive is never overwritten."""
    if dest.exists():
        raise FileExistsError(f"{dest} exists: an archive is kept, never overwritten")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for rel, kind, _ in tree(src):
            info = tar.gettarinfo(src / rel, arcname=rel)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if kind == "file":
                with open(src / rel, "rb") as handle:
                    tar.addfile(info, handle)
            elif kind in {"dir", "symlink"}:
                tar.addfile(info)
    raw = gzip.compress(buf.getvalue(), mtime=0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def extract(archive_path: pathlib.Path, out: pathlib.Path, digest: str) -> None:
    """An archive is inspected from the archive: its digest checked first."""
    raw = archive_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f"{archive_path} is not the archive of digest {digest}")
    if out.exists():
        raise FileExistsError(f"{out} exists")
    out.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
        tar.extractall(out, filter="tar")


# --- the package, validated on its own (§2.2, assembly step 2) ------------------------


@dataclasses.dataclass(frozen=True)
class ValidatedPackage:
    files: dict[str, str]  # name under package/ → SHA-256
    values: c.Values


def _declared():
    declared = release.profiles(HERE)
    return declared, {p.id: set(p.reports) for p in declared}, {p.id: p.password for p in declared}


def _rows(parquet: bytes) -> list[tuple]:
    import duckdb

    with tempfile.TemporaryDirectory() as tmp:
        path = pathlib.Path(tmp) / "p.parquet"
        path.write_bytes(parquet)
        con = duckdb.connect(":memory:")
        return con.execute(f"SELECT * FROM read_parquet('{path.as_posix()}') ORDER BY year_month, sales_channel_name, category_name").fetchall()


def validate_package(package_dir: pathlib.Path, expected_rows: list[tuple]) -> ValidatedPackage:
    """The gate's own functions, apart from `verify`, and the opened rows equal
    to the expected ones, row for row. Raises `PackageRefused`."""
    try:
        contract = fx_mod.contract()
        _, declared_map, passwords = _declared()
        manifest_raw = (package_dir / "manifest.json").read_bytes()
        manifest = e.validate_manifest(manifest_raw)
        files = {p.name: p.read_bytes() for p in sorted(package_dir.iterdir()) if p.name != "manifest.json"}
        e.check_package(manifest_raw, files, passwords)
        c.inventory_exact(contract, set(manifest.reports))
        c.entitlements_exact({pid: set(p.reports) for pid, p in manifest.profiles.items()}, declared_map)
        key = e.login(manifest, "diretoria", passwords["diretoria"])
        report = manifest.reports[fx_mod.REPORT]
        totals, parquet = e.open_report(manifest, files[report.file], fx_mod.REPORT, key)
        values = c.check_payload(contract, contract.reports[fx_mod.REPORT], totals, parquet)
        if _rows(parquet) != sorted(expected_rows, key=lambda r: (r[0], r[3], r[6])):
            raise PackageRefused("the package does not open to the expected rows")
    except PackageRefused:
        raise
    except Exception as refusal:  # noqa: BLE001 — every refusal of the package is the harness's
        raise PackageRefused(f"{type(refusal).__name__}: {refusal}") from None
    digests = {"manifest.json": hashlib.sha256(manifest_raw).hexdigest()}
    digests |= {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}
    return ValidatedPackage(digests, values)


class PackageRefused(Exception):
    pass


# --- assembly (§2.2) -----------------------------------------------------------------


def assemble(builder: pathlib.Path, package_dir: pathlib.Path, expected_rows: list[tuple],
             artifact: pathlib.Path) -> tuple[Outcome, ValidatedPackage | None]:
    """Steps 1 to 4 of §2.2. The artifact must not exist."""
    if (builder / PACKAGE).exists() or (builder / PACKAGE).is_symlink():
        return Outcome("assembly", FORM, "the builder output has its own package/ entry"), None
    try:
        validated = validate_package(package_dir, expected_rows)
    except PackageRefused as refusal:
        return Outcome("assembly", HARNESS_ERROR, f"package refused by its own validation: {refusal}"), None
    if artifact.exists():
        return Outcome("assembly", HARNESS_ERROR, f"{artifact} exists: an artifact is assembled fresh"), None
    shutil.copytree(builder, artifact, symlinks=True)
    (artifact / PACKAGE).mkdir()
    for name in validated.files:
        shutil.copyfile(package_dir / name, artifact / PACKAGE / name)
    placed = tree(artifact)
    rest = [entry for entry in placed if entry[0] != PACKAGE and not entry[0].startswith(PACKAGE + "/")]
    package = {rel[len(PACKAGE) + 1:]: digest for rel, kind, digest in placed if rel.startswith(PACKAGE + "/")}
    if rest != tree(builder) or package != validated.files:
        return Outcome("assembly", HARNESS_ERROR, "the artifact is not the builder output plus the validated package"), None
    return Outcome("assembly", PASS, "assembled", {"package": validated.files}), validated


# --- verify, under a root of the harness's own (§2.5.1) ------------------------------


def write_root(run: pathlib.Path, lists: pathlib.Path, declarations: pathlib.Path = DECLARATIONS) -> pathlib.Path:
    """`<run>/root/release/`: the three shared declarations and the candidate's
    two lists, copied. `verify` appends `release/` itself."""
    root = run / "root"
    (root / "release").mkdir(parents=True)
    for name in ("contract.json", "profiles.json", "public_values.json"):
        if (declarations / name).exists():
            shutil.copyfile(declarations / name, root / "release" / name)
    for name in ("include.txt", "media_types.txt"):
        if (lists / name).exists():
            shutil.copyfile(lists / name, root / "release" / name)
    return root


#: §2.5.1's table, by the gate's own messages; first match wins. A message
#: none of them matches is HARNESS_ERROR.
_TABLE: list[tuple[re.Pattern, str]] = [(re.compile(p), cls) for p, cls in [
    (r"^include\.txt: .* is not a path under site/$", HARNESS_ERROR),
    (r"^(public_values_invalid|contract_invalid|declarations_agree)\b", HARNESS_ERROR),
    (r"^0 package manifests in the artifact", HARNESS_ERROR),
    (r"^[2-9][0-9]* package manifests in the artifact|^1[0-9]+ package manifests in the artifact", FORM),
    (r"^package manifest refused: ", HARNESS_ERROR),
    (r" is in the manifest and not in the artifact$", HARNESS_ERROR),
    (r"^envelopes not in the manifest: ", HARNESS_ERROR),
    (r"^(inventory_exact|entitlements_exact)\b", HARNESS_ERROR),
    (r"^package refused: ", HARNESS_ERROR),
    (r"^(totals_shape|totals_version|totals_rows|totals_sums|schema_exact|not_null|grain_unique|content_bound|parquet_unreadable)\b", HARNESS_ERROR),
    (r" is not under the inclusion list$", FORM),
    (r": extension not in media_types\.txt$", FORM),
    (r" is a source map$", FORM),
    (r" references a source map$", FORM),
    (r" is under Hosting's reserved __/ URLs$", FORM),
    (r" is a symbolic link$", FORM),
    (r" is not a plain file$", FORM),
    (r" holds a Parquet magic outside an envelope$", "PARQUET"),
    (r" holds a clear payload outside an envelope$", CONTENT),
    (r" holds a data key in the clear$", CONTENT),
    (r"^(clear_value|clear_totals) \(in .+\)$", "REPRODUCE"),
]]

_FILE = re.compile(r"^(?P<file>.+?) (holds a Parquet magic|holds a clear payload|holds a data key)")
_INSPECT = re.compile(r"^(?P<code>clear_value|clear_totals) \(in (?P<file>.+)\)$")


def verify(artifact: pathlib.Path, builder: pathlib.Path, root: pathlib.Path,
           validated: ValidatedPackage | None, *, role_override: str | None = None) -> Outcome:
    """`release.verify` unchanged, then the class of its outcome. `builder` is
    the extracted archive of the builder output the artifact was assembled from;
    `validated` the package assembly validated. `role_override` exists for the
    collision control alone: it gives the reproduction another haystack role."""
    try:
        release.verify(root, artifact, live=lambda: release.NO_LIVE)
    except release.Refused as refusal:
        return classify(str(refusal), artifact, builder, root, validated, role_override)
    except Exception as error:  # noqa: BLE001
        return Outcome("verify", HARNESS_ERROR, f"{type(error).__name__} raised by verify")
    return Outcome("verify", PASS, "verified")


def classify(message: str, artifact: pathlib.Path, builder: pathlib.Path, root: pathlib.Path,
             validated: ValidatedPackage | None, role_override: str | None = None) -> Outcome:
    for pattern, cls in _TABLE:
        if not pattern.search(message):
            continue
        if cls == "PARQUET":
            rel = _FILE.match(message)["file"]
            return Outcome("verify", SCHEMA_ONLY if schema_only((artifact / rel).read_bytes()) else CONTENT, message, {"file": rel})
        if cls == "REPRODUCE":
            return _reproduce(message, artifact, builder, root, validated, role_override)
        return Outcome("verify", cls, message)
    return Outcome("verify", HARNESS_ERROR, f"a refusal the table does not list: {message}")


def schema_only(data: bytes) -> bool:
    """A Parquet with P01's schema — names and types — and zero rows."""
    import duckdb

    report = fx_mod.contract().reports[fx_mod.REPORT]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "f.parquet"
            path.write_bytes(data)
            con = duckdb.connect(":memory:")
            schema = [(r[0], r[1]) for r in con.execute(f"DESCRIBE SELECT * FROM read_parquet('{path.as_posix()}')").fetchall()]
            rows = con.execute(f"SELECT count(*) FROM read_parquet('{path.as_posix()}')").fetchone()[0]
    except Exception:  # noqa: BLE001 — not a Parquet that parses is not schema only
        return False
    return schema == [(col.name, col.type) for col in report.columns] and rows == 0


def _reproduce(message: str, artifact: pathlib.Path, builder: pathlib.Path, root: pathlib.Path,
               validated: ValidatedPackage | None, role_override: str | None) -> Outcome:
    """FPROTO-4-05: the gate's own search, re-run on the named file with the
    same values, public set and haystack role, must give the same code; then a
    file identical to the builder output's is a collision, any other content."""
    m = _INSPECT.match(message)
    code, rel = m["code"], m["file"]
    if validated is None:
        return Outcome("verify", HARNESS_ERROR, f"{message}: no validated package to reproduce it with")
    try:
        public = c.load_public_values((root / "release" / "public_values.json").read_bytes())
        data = (artifact / rel).read_bytes()
        is_manifest = rel == f"{PACKAGE}/manifest.json"
        role = role_override or ("labels" if is_manifest else "file")
        haystack = c.manifest_labels(e.validate_manifest(data)) if role == "labels" else data
        try:
            c.inspect({rel: haystack}, [validated.values], public)
            reproduced = None
        except c.Refused as again:
            reproduced = (again.code, again.where)
    except Exception as error:  # noqa: BLE001
        return Outcome("verify", HARNESS_ERROR, f"{message}: reproduction failed with {type(error).__name__}")
    if reproduced != (code, rel):
        return Outcome("verify", HARNESS_ERROR, f"{message}: the reproduction gave {reproduced}")
    original = builder / rel
    if original.is_file() and not original.is_symlink() and original.read_bytes() == (artifact / rel).read_bytes():
        found = [(k, n) for k, n in c.needles([validated.values], public) if n in haystack]
        return Outcome("verify", COLLISION, message, {"file": rel, "classes": sorted({needle_class(k, n, validated.values) for k, n in found})})
    return Outcome("verify", CONTENT, message, {"file": rel})


def needle_class(code: str, needle: bytes, values: c.Values) -> str:
    """A needle's class, for the record — never its value."""
    if code == c.CLEAR_TOTALS:
        return "totals"
    text = needle.decode("utf-8", "replace")
    if text in values.texts:
        return "calendar" if re.fullmatch(r"[0-9]{4}-[0-9]{2}", text) else "label"
    rows = json_rows(values)
    if text == rows:
        return "row_count"
    return "number"


def json_rows(values: c.Values) -> str:
    import json

    return str(json.loads(values.totals_raw)["rows"])
