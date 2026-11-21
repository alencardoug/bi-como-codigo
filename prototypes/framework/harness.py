"""The harness of stage 2.3 (docs/framework_prototype.md §2.2, §2.5.1).

Assembly places the validated package into a copy of a candidate's builder
output; the gate's own `release.verify` then judges the artifact, unchanged,
under a root the harness writes; and each outcome is classified by the stage
that produced it — never read as the candidate's pass or failure when it is
the harness's own.

The classes: `HARNESS_ERROR`, `FORM`, `SCHEMA_ONLY`, `CONTENT`, `COLLISION`,
`PASS`. A `HARNESS_ERROR` or a `COLLISION` stops the run.

`verify` is bound to what assembly produced (PROTO-1-02): the artifact's tree,
modes and links included, must be the assembled one before and after the gate
runs, so that a package or a file changed after assembly is the harness's
error, never a verdict. A control's hand-made addition is declared to assembly
and enters the tree there.
"""

from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import re
import tempfile

import fixture as fx_mod
import trees
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


def tree(root: pathlib.Path) -> list[tuple]:
    """(path, kind, digest or link target, mode) of every entry, sorted, read
    without following a link. Unlike `release.listing`, it records what the gate
    refuses instead of refusing it, so that `verify` judges it."""
    return [entry.key() for entry in trees.entries(root)]


archive = trees.archive
extract = trees.extract


# --- the package, validated on its own (§2.2, assembly step 2) ------------------------


@dataclasses.dataclass(frozen=True)
class ValidatedPackage:
    files: dict[str, str]  # name under package/ → SHA-256
    values: c.Values
    artifact: tuple = ()  # the assembled artifact's tree, which verify is bound to
    builder: tuple | None = None  # the builder output's tree it was assembled from, which reproduction is bound to; () is an empty one
    label: str = "judged"  # "control" when hand-made additions entered the artifact


class PackageRefused(Exception):
    pass


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
    to the expected ones, row for row. The package folder holds plain files
    only. Raises `PackageRefused`."""
    try:
        listed = trees.entries(trees.real_root(package_dir))
        if any(x.kind != "file" or "/" in x.rel for x in listed):
            raise PackageRefused("the package folder holds something other than plain files")
        raw = {x.rel: (package_dir / x.rel).read_bytes() for x in listed}
        contract = fx_mod.contract()
        _, declared_map, passwords = _declared()
        manifest_raw = raw.pop("manifest.json")
        manifest = e.validate_manifest(manifest_raw)
        files = raw
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


# --- assembly (§2.2) -----------------------------------------------------------------


def assemble(builder: pathlib.Path, package_dir: pathlib.Path, expected_rows: list[tuple],
             artifact: pathlib.Path, *, control_additions: dict[str, bytes] | None = None
             ) -> tuple[Outcome, ValidatedPackage | None]:
    """Steps 1 to 4 of §2.2. The artifact must not exist. `control_additions`
    are a control's hand-made files, placed after the builder output and
    recorded as such; a judged run has none."""
    try:
        trees.real_root(builder)
    except trees.Refused as refusal:
        return Outcome("assembly", HARNESS_ERROR, f"the builder output cannot be read: {refusal}"), None
    if (builder / PACKAGE).exists() or (builder / PACKAGE).is_symlink():
        return Outcome("assembly", FORM, "the builder output has its own package/ entry"), None
    try:
        validated = validate_package(package_dir, expected_rows)
    except PackageRefused as refusal:
        return Outcome("assembly", HARNESS_ERROR, f"package refused by its own validation: {refusal}"), None
    if artifact.exists() or artifact.is_symlink():
        return Outcome("assembly", HARNESS_ERROR, f"{artifact} exists: an artifact is assembled fresh"), None
    for rel in control_additions or {}:
        pure = pathlib.PurePosixPath(rel)
        if pure.is_absolute() or ".." in pure.parts or str(pure) != rel or not rel or pure.parts[0] == PACKAGE:
            return Outcome("assembly", HARNESS_ERROR, f"a control addition outside the artifact or under package/: {rel!r}"), None
    try:
        uncarried = trees.copy(builder, artifact)
        if uncarried:  # a socket or a device: the gate would refuse it as not a plain file
            return Outcome("assembly", FORM, f"entries no copy can carry: {uncarried}", {"entries": uncarried}), None
        for rel, data in (control_additions or {}).items():
            _add_contained(artifact, rel, data)
        (artifact / PACKAGE).mkdir()
        for name in validated.files:
            (artifact / PACKAGE / name).write_bytes((package_dir / name).read_bytes())
        placed = tree(artifact)
    except (OSError, trees.Refused) as error:
        return Outcome("assembly", HARNESS_ERROR, f"the copy failed: {type(error).__name__}: {error}"), None
    added = set(control_additions or {})
    rest = [x for x in placed if x[0] != PACKAGE and not x[0].startswith(PACKAGE + "/") and x[0] not in added
            and not any(a.startswith(x[0] + "/") for a in added if x[1] == "dir" and not (builder / x[0]).is_dir())]
    package = {x[0][len(PACKAGE) + 1:]: x[2] for x in placed if x[0].startswith(PACKAGE + "/") and x[1] == "file"}
    package_kinds = {x[1] for x in placed if x[0].startswith(PACKAGE + "/")}
    if rest != tree(builder) or package != validated.files or package_kinds - {"file"}:
        return Outcome("assembly", HARNESS_ERROR, "the artifact is not the builder output plus the validated package"), None
    bound = dataclasses.replace(validated, artifact=tuple(placed), builder=tuple(tree(builder)),
                                label="control" if added else "judged")
    return Outcome("assembly", PASS, "assembled", {"package": validated.files, "control_additions": sorted(added)}), bound


def _add_contained(artifact: pathlib.Path, rel: str, data: bytes) -> None:
    """One control addition, created inside the artifact through real folders
    only, never over an existing entry (PROTO-2-02)."""
    import os

    here = artifact
    for part in pathlib.PurePosixPath(rel).parts[:-1]:
        here = here / part
        if here.is_symlink():
            raise trees.Refused(f"a control addition through a link: {rel}")
        if not here.exists():
            here.mkdir()
        elif not here.is_dir():
            raise trees.Refused(f"a control addition under a file: {rel}")
    target = here / pathlib.PurePosixPath(rel).name
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)


# --- verify, under a root of the harness's own (§2.5.1) ------------------------------


def write_root(run: pathlib.Path, lists: pathlib.Path, declarations: pathlib.Path = DECLARATIONS) -> pathlib.Path:
    """`<run>/root/release/`: the three shared declarations and the candidate's
    two lists, copied. `verify` appends `release/` itself."""
    root = run / "root"
    (root / "release").mkdir(parents=True)
    for name in ("contract.json", "profiles.json", "public_values.json"):
        if (declarations / name).exists():
            (root / "release" / name).write_bytes((declarations / name).read_bytes())
    for name in ("include.txt", "media_types.txt"):
        if (lists / name).exists():
            (root / "release" / name).write_bytes((lists / name).read_bytes())
    return root


_TOTALS_CODES = "totals_shape|totals_version|totals_rows|totals_sums|schema_exact|not_null|grain_unique|content_bound|parquet_unreadable"
_REFUSAL_ARGS = r"(?: \(report [A-Z0-9_]+(?:, column [a-z][a-z0-9_]*)?\))?"

#: §2.5.1's table, by the exact forms of the gate's messages (release.py,
#: contract.py). A form with `file` names an entry of the artifact, which must
#: exist; a message that matches no form, or forms of different classes, is
#: HARNESS_ERROR (PROTO-1-02).
_TABLE: list[tuple[re.Pattern, str]] = [(re.compile(p), cls) for p, cls in [
    (r"include\.txt: .+ is not a path under site/", HARNESS_ERROR),
    (r"(?:public_values_invalid|contract_invalid|declarations_agree)", HARNESS_ERROR),
    (r"0 package manifests in the artifact; exactly one is expected", HARNESS_ERROR),
    (r"(?:[2-9]|[1-9][0-9]+) package manifests in the artifact; exactly one is expected", FORM),
    (r"package manifest refused: .+", HARNESS_ERROR),
    (r"(?P<entry>[^/]+) is in the manifest and not in the artifact", HARNESS_ERROR),
    (r"envelopes not in the manifest: \[.*\]", HARNESS_ERROR),
    (r"(?:inventory_exact|entitlements_exact)", HARNESS_ERROR),
    (r"package refused: .+", HARNESS_ERROR),
    (rf"(?:{_TOTALS_CODES}){_REFUSAL_ARGS}", HARNESS_ERROR),
    (r"parquet_unreadable: a report could not be checked", HARNESS_ERROR),
    (r"(?P<file>.+) is not under the inclusion list", FORM),
    (r"(?P<file>.+): extension not in media_types\.txt", FORM),
    (r"(?P<file>.+) is a source map", FORM),
    (r"(?P<file>.+) references a source map", FORM),
    (r"(?P<file>.+) is under Hosting's reserved __/ URLs", FORM),
    (r"(?P<file>.+) is a symbolic link", FORM),
    (r"(?P<file>.+) is not a plain file", FORM),
    (r"(?P<file>.+) holds a Parquet magic outside an envelope", "PARQUET"),
    (r"(?P<file>.+) holds a clear payload outside an envelope", CONTENT),
    (r"(?P<file>.+) holds a data key in the clear", CONTENT),
    (r"(?P<code>clear_value|clear_totals) \(in (?P<file>.+)\)", "REPRODUCE"),
]]


def run_gate(artifact: pathlib.Path, builder: pathlib.Path, root: pathlib.Path, validated: ValidatedPackage | None,
             *, role_override: str | None = None, table_control: bool = False) -> Outcome:
    """`release.verify` unchanged, then the class of its outcome — with no
    binding to the assembled tree. Only the controls of §2.5.1's table may use
    it, and they say so; a run is judged through `verify` (PROTO-2-02)."""
    if not table_control:
        raise ValueError("run_gate is unbound: only a control of §2.5.1's table calls it, with table_control=True")
    try:
        release.verify(root, artifact, live=lambda: release.NO_LIVE)
    except release.Refused as refusal:
        return classify(str(refusal), artifact, builder, root, validated, role_override)
    except Exception as error:  # noqa: BLE001
        return Outcome("verify", HARNESS_ERROR, f"{type(error).__name__} raised by verify")
    return Outcome("verify", PASS, "verified")


def verify(artifact: pathlib.Path, builder: pathlib.Path, root: pathlib.Path,
           validated: ValidatedPackage | None, *, role_override: str | None = None, label: str = "judged") -> Outcome:
    """The gate on the assembled artifact. `builder` is the extracted archive of
    the builder output it was assembled from; `validated` what assembly returned.
    `label` is the run's: a judged run refuses an assembly that took a control's
    additions. `role_override` exists for the collision control alone."""
    if validated is None or not validated.artifact:
        return Outcome("verify", HARNESS_ERROR, "no assembled artifact to verify")
    if label == "judged" and (validated.label != "judged" or role_override is not None):
        return Outcome("verify", HARNESS_ERROR, f"control evidence ({validated.label} assembly, role {role_override}) on a judged run")
    try:
        before = tuple(tree(artifact))
    except (OSError, trees.Refused) as error:
        return Outcome("verify", HARNESS_ERROR, f"the artifact cannot be read: {type(error).__name__}")
    if before != validated.artifact:
        return Outcome("verify", HARNESS_ERROR, "the artifact is not the one assembled with the validated package")
    outcome = run_gate(artifact, builder, root, validated, role_override=role_override, table_control=True)
    try:
        after = tuple(tree(artifact))
    except (OSError, trees.Refused):
        after = None
    if after != validated.artifact:
        return Outcome("verify", HARNESS_ERROR, "the artifact changed while it was verified")
    return outcome


def classify(message: str, artifact: pathlib.Path, builder: pathlib.Path, root: pathlib.Path,
             validated: ValidatedPackage | None, role_override: str | None = None) -> Outcome:
    try:
        entries = {x[0]: x[1] for x in tree(artifact)}
    except (OSError, trees.Refused):
        return Outcome("verify", HARNESS_ERROR, f"{message}: the artifact cannot be listed")
    matches = []
    for pattern, cls in _TABLE:
        m = pattern.fullmatch(message)
        if not m:
            continue
        named = m.groupdict().get("file")
        if named is not None and named not in entries:
            continue
        matches.append((cls, m))
    if not matches:
        return Outcome("verify", HARNESS_ERROR, f"a refusal the table does not list: {message}")
    if len({cls for cls, _ in matches}) > 1:
        return Outcome("verify", HARNESS_ERROR, f"a refusal of more than one form: {message}")
    cls, m = matches[0]
    if cls == "PARQUET":
        rel = m["file"]
        try:
            data = trees.files(artifact).get(rel)
            if data is None:
                return Outcome("verify", HARNESS_ERROR, f"{message}: the named file is not a plain file")
            shape = fx_mod.schema_only(data)
        except (OSError, fx_mod.SchemaFault) as error:
            return Outcome("verify", HARNESS_ERROR, f"{message}: the schema check failed: {type(error).__name__}")
        return Outcome("verify", SCHEMA_ONLY if shape else CONTENT, message, {"file": rel})
    if cls == "REPRODUCE":
        return _reproduce(m["code"], m["file"], message, artifact, builder, root, validated, role_override)
    return Outcome("verify", cls, message, {"file": m["file"]} if m.groupdict().get("file") else {})


def _reproduce(code: str, rel: str, message: str, artifact: pathlib.Path, builder: pathlib.Path, root: pathlib.Path,
               validated: ValidatedPackage | None, role_override: str | None) -> Outcome:
    """FPROTO-4-05: the gate's own search, re-run on the named file with the
    same values, public set and haystack role, must give the same code; then a
    file identical to the builder output's is a collision, any other content.
    Every read is inside the harness's own handling."""
    if validated is None:
        return Outcome("verify", HARNESS_ERROR, f"{message}: no validated package to reproduce it with")
    try:
        # The builder output assembly used (PROTO-2-03); an empty one is a
        # snapshot like any other, and no snapshot is no assembly (PROTO-3-04).
        if validated.builder is None:
            return Outcome("verify", HARNESS_ERROR, f"{message}: the package was never assembled with a builder output")
        if tuple(tree(builder)) != validated.builder:
            return Outcome("verify", HARNESS_ERROR, f"{message}: the builder output given is not the one assembled")
        public = c.load_public_values((root / "release" / "public_values.json").read_bytes())
        data = trees.files(artifact)[rel]
        is_manifest = rel == f"{PACKAGE}/manifest.json"
        role = role_override or ("labels" if is_manifest else "file")
        haystack = c.manifest_labels(e.validate_manifest(data)) if role == "labels" else data
        try:
            c.inspect({rel: haystack}, [validated.values], public)
            reproduced = None
        except c.Refused as again:
            reproduced = (again.code, again.where)
        original = trees.files(builder).get(rel) if not is_manifest else None
    except Exception as error:  # noqa: BLE001
        return Outcome("verify", HARNESS_ERROR, f"{message}: reproduction failed with {type(error).__name__}")
    if reproduced != (code, rel):
        return Outcome("verify", HARNESS_ERROR, f"{message}: the reproduction gave {reproduced}")
    if original is not None and original == data:
        found = [(k, n) for k, n in c.needles([validated.values], public) if n in haystack]
        return Outcome("verify", COLLISION, message, {"file": rel, "classes": sorted({needle_class(k, n, validated.values) for k, n in found})})
    return Outcome("verify", CONTENT, message, {"file": rel})


def needle_class(code: str, needle: bytes, values: c.Values) -> str:
    """A needle's class, for the record — never its value: the spelling is
    taken back to its canonical value first (PROTO-1-09)."""
    import json

    if code == c.CLEAR_TOTALS:
        return "totals"
    text = needle.decode("utf-8", "replace")
    if text in values.texts:
        return "calendar" if re.fullmatch(r"[0-9]{4}-[0-9]{2}", text) else "label"
    canonical = {s: n for n in values.numbers for s in c.spellings(n)}.get(text, text)
    if canonical == str(json.loads(values.totals_raw)["rows"]):
        return "row_count"
    years = {t[:4] for t in values.texts if re.fullmatch(r"[0-9]{4}-[0-9]{2}", t)}
    if canonical in years:
        return "calendar"
    return "number"
