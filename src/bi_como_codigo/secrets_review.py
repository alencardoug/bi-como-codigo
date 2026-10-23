"""Secrets and `.gitignore` review — the first step of `make check`.

Rule 1 of `CLAUDE.md` §5 says that no secret enters the repository. A rule with
no test is an intention; what this module does is measure the ways of breaking
it:

* `.env` tracked — or no longer ignored;
* a value of `.env` copied into a tracked file;
* `.env.example` with a value filled in;
* a tracked file that `.gitignore` also ignores — the next `git add` misses it;
* a credential written in a tracked file or in any blob of the history,
  recognised by its **shape**, with no value known in advance.

Each finding is one line; empty output is what lets the rest of the check run.
No external tool: `git` and `.env` itself are the oracle.

**Ported from mvp_eng_dados_1** (`src/mvp_ed1/secrets_review.py` at `26b58b3`),
with the detection unchanged except for object literals (`detect`). The
RVF12 codes below are findings of that project's stage-12 final review, kept
because they say why each rule is the way it is.

**Why the history mode cannot depend on `.env`.** Comparing with the current
values is blind exactly where it matters: after a rotation the old value is no
longer known, and the blob that holds it matches nothing. Detection over the
history is by **shape**: assignments in ENV, YAML and JSON, credentials embedded
in URLs, and the known generic forms.

**Placeholder is a property of the value, not of the file.** No extension is
exempt from the scan: a real secret written into a `*.example` is found like any
other. What exempts it is the value being recognisably a template — empty,
`<…>`, `${…}`, `changeme` —, and each template is declared below with its reason.

**Public by design is a property of the value, too** (decision N22 of the plan).
The two demo passwords are shown to every visitor, below the login box; they are
not secrets. They are registered in `docs/public_by_design.yml` by the SHA-256 of
the value, with the reason, and any occurrence of exactly that value passes, in
any file and any commit. Any other value is still a finding.

**Skipped is not verified.** A binary or oversized blob goes into the skipped
list, with object, path and reason, and the list is printed. Counting how many
were skipped would hide exactly the file nobody looked at.

**What is not here.** mvp_eng_dados_1 also has a register of history findings
already treated — rotated, with the history kept. This repository has no such
finding: the only shapes in its history are the two public values. If a real
secret ever enters the history, how to treat it is the Owner's decision, and the
register comes with it.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass

#: What is a secret in `.env` is recognised by the key. Database name, user and
#: port are configuration and legitimately appear in documentation.
SECRET_KEY_PATTERN = re.compile(r"PASSWORD|SECRET|KEY|TOKEN|CREDENTIAL")

#: Below this, a textual coincidence says nothing — except when the value of an
#: assignment repeats the user (`detect`).
MIN_SECRET_LENGTH = 8

#: Shapes that give a credential away regardless of `.env`.
GENERIC_PATTERNS = (
    re.compile(r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                      # AWS access key
    re.compile(r"\bghp_[A-Za-z0-9]{36}\b"),                   # GitHub token
    re.compile(r"\bxox[abp]-[0-9A-Za-z-]{10,}\b"),             # Slack token
    re.compile(r'"private_key_id"\s*:\s*"[0-9a-f]{40}"'),      # GCP service account
)

#: Binary extensions, not read as text.
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".woff", ".woff2", ".zip", ".gz", ".parquet"}

#: Assignment to a sensitive key, in three syntaxes: ENV (`KEY=value`), YAML
#: (`key: value`) and JSON (`"key": "value"`). The quote that **closes** the key
#: is accepted before the separator, case is ignored, and the value stops at a
#: quote or a comma — without that, `{"password": "x", "user": "y"}` would be a
#: single value. The quote that **opens** the value is captured: a quoted value
#: is a string literal, and there is no expression in it (`placeholder`). The
#: minimum length lives in `detect`, because a password equal to the user does
#: not respect it. `senha` is new in this port: what visitors read here is in
#: Portuguese (`CLAUDE.md` §2), and the login screen of the plan writes
#: `Senha: …` — a shape the English words alone did not see.
ASSIGNMENT_PATTERN = re.compile(
    r"""(?ix)
    ["']?(?P<key>[a-z0-9_.-]*
        (?:password|passwd|senha|secret|token|api[_-]?key|private[_-]?key|credential)
        [a-z0-9_.-]*)["']?
    \s*[=:]\s*
    (?P<quote>["']?)(?P<value>[^\s"',]+)
    """
)

#: One `key: 'value'` pair inside an object literal opened by a sensitive
#: assignment — `passwords = {Diretoria:'…', Logistica:'…'}` in JavaScript, or
#: the same in Python or JSON. Only quoted values: inside the braces, an unquoted
#: value is a reference.
OBJECT_PAIR_PATTERN = re.compile(
    r"""(?x)
    ["']?(?P<key>[\w.-]+)["']?\s*:\s*
    (?P<quote>["'])(?P<value>[^"'\n]+)(?P=quote)
    """
)

#: Assignment of a user, in the same three syntaxes — `POSTGRES_USER: airflow`,
#: `"username": "mvp"`. Only values that look like names: a reference is not a user.
USER_PATTERN = re.compile(
    r"""(?ix)
    ["']?[a-z0-9_.-]*user(?:name)?["']?
    \s*[=:]\s*
    (?P<quote>["']?)(?P<value>[a-z0-9_.-]+)(?=["',\s]|$)
    """
)

#: A configuration line — YAML `KEY: value` or ENV `KEY=value`, with a list `- `
#: or `export` in front: the key opens the line and the value closes it. Only
#: there is an **unquoted** value a literal. `user = db_user` (Python, HCL) and
#: `connect(user=db_user, …)` are references to a variable (RVF12-2-02).
#: **Declared limits**, both sides of the same heuristic: `key = value` with
#: spaces in a `.env` is not read as a literal; and Python written with no spaces
#: around `=`, with the key opening the line, is read as ENV (RVF12-3-04).
CONFIG_LINE_PATTERN = re.compile(
    r"""(?x)^\s*(?:-\s+)?(?:export\s+)?["']?[\w.-]+["']?(?:\s*:\s+|=)[^\s"',\#]+\s*(?:\#.*)?$"""
)

#: A credential embedded in a URL: `postgresql://user:password@host/db`.
URL_CREDENTIAL_PATTERN = re.compile(r"://(?P<key>[^/:@\s]+):(?P<value>[^@\s]+)@")

#: Templates — what is **not** a secret, recognised by the value and not by the
#: file. Each one carries its reason, because a list of regexes with no reason
#: becomes something nobody dares to touch.
#
#: The rule that organises all of them: **a credential is a literal; a reference
#: is not.** Applying the assignment pattern to source code without this flags
#: every variable called `password`.
#
#: **A reference is the whole value, not one character of it** (RVF12-03): the
#: reference rules anchor at the start, and the expression rule lives apart.
PLACEHOLDER_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^$"), "empty — what `.env.example` declares"),
    (re.compile(r"^<[^>]*>"), "marker `<…>`"),
    # One brace only: `{{` is a template, and templates answer to `REFERENCE_RULE`.
    # Matching the prefix of `{{Ab9}` and `{{A}}Ab9` let them pass (RVF12-3-01).
    (re.compile(r"^\{(?!\{)[^{}]*\}"), "interpolation — `{var}` of an f-string"),
    (
        re.compile(r"^(var|local|data|module|each|self)\."),
        "Terraform reference or object attribute",
    ),
    (re.compile(r"(?i)^change[_-]?me"), "literal template `changeme`"),
    (re.compile(r"(?i)example|exemplo"), "literal template `example`"),
    (re.compile(r"(?i)^x{3,}$"), "template `xxx…`"),
    (re.compile(r"^\*+$"), "value already masked `***`"),
    (re.compile(r"(?i)^(null|none|nil|true|false)$"), "language literal, not a credential"),
)

#: A reference to a variable or a template: `$VAR`, `$1`, `${…}`, `$(…)`, the
#: `$$` forms of Make and the `{{ … }}` of templates. **The form must be complete
#: and reach the end of the value** (RVF12-2-01): `${Ab9Z7q1`, with no closing
#: brace, is a literal. It is read on the rest of the line, not only on the
#: value, because the value stops at a space or comma and the reference does not:
#: `${DB_PASSWORD:?set it …}` closes after the cut. A quote inside the reference
#: only counts in pairs. `$1` is the positional parameter of the shell
#: (RVF12-2-03); `$1Ab9` is still a literal.
REFERENCE_RULE = (
    re.compile(
        r"""(?x)
        \$\$?(?:
            \{ (?: [^}"'\n] | "[^"\n]*" | '[^'\n]*' )* \}      # ${…}
          | \( (?: [^)"'\n] | "[^"\n]*" | '[^'\n]*' )* \)      # $(…)
          | [A-Za-z_]\w*                                      # $VAR
          | \d                                                # $1
        )
        | \{\{ (?: [^}"'\n] | "[^"\n]*" | '[^'\n]*' )* \}\}    # {{ … }}
        """
    ),
    "reference — `$VAR`, `$1`, `${…}`, `$(…)`, `$$VAR` of Make, `{{ … }}` of a template",
)

#: **Declared limit of this rule:** a hand-written password made only of letters
#: (`correcthorsebattery`) is excused by it. It holds because generated values
#: carry digits, and because the known forms and the comparison with `.env`
#: cover the rest — but it is a choice, not coverage. It does not excuse a
#: password **equal to the user** (RVF12-01), so it lives outside
#: `PLACEHOLDER_RULES`. The final `)` is that of a call closing on its last
#: named argument, `connect(…=db_password)`.
WORD_RULE = (
    re.compile(r"^[A-Za-z][A-Za-z_.\-]*[}\]),;]?$"),
    "single word with no digit — an identifier or template, not a generated value",
)

#: An expression exists only **outside** a string literal: `quote_plus(...)`,
#: `client.token()`, the `\(\S*\)` group of a `sed`, the `(?!…)` of a regex quoted
#: in a document. Inside quotes or a URL, `Ab9(Z7q1` is a literal. **Declared
#: limit:** an unquoted value that starts like a call (`Ab9(…`) is taken for code.
EXPRESSION_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^[A-Za-z_][\w.]*[(\[]"),
        "expression, not a literal — function call or indexing",
    ),
    (
        re.compile(r"^\\?[(\[]"),
        "expression, not a literal — group or class of a regular expression",
    ),
)

#: A blob larger than this is not read — and enters the skipped list, by name.
MAX_BLOB_BYTES = 5 * 1024 * 1024

#: Where the values public by design are registered (N22).
PUBLIC_PATH = pathlib.Path("docs/public_by_design.yml")


def placeholder(
    value: str,
    *,
    literal: bool = False,
    equal_to_user: bool = False,
    context: str | None = None,
) -> str | None:
    """The reason `value` is a template, or `None` if it is a real value.

    `literal` says the value is in a string literal — quoted or in a URL —,
    where there is no expression to excuse. `equal_to_user` drops the
    no-digit word rule: a default pair is not an identifier. `context` is the
    rest of the line from the value on, where the reference is read; without it,
    only the value itself.
    """
    reference = REFERENCE_RULE[0].match(value if context is None else context)
    if reference and reference.end() >= len(value):
        return REFERENCE_RULE[1]
    rules = PLACEHOLDER_RULES
    if not literal:
        rules += EXPRESSION_RULES
    if not equal_to_user:
        rules += (WORD_RULE,)
    for pattern, reason in rules:
        if pattern.search(value):
            return reason
    return None


def mask(value: str) -> str:
    """Two characters and the length. The value is never printed whole.

    Printing the secret to report the secret copies it into the CI output, the
    terminal scrollback and the review dossier.
    """
    return f"{value[:2]}*** ({len(value)} characters)"


def fingerprint(value: str) -> str:
    """The SHA-256 of a value, as the register of public values stores it."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Finding:
    """One occurrence of a credential shape, wherever it is."""

    path: str
    line: int
    key: str
    value: str
    shape: str
    commit: str = ""

    def __str__(self) -> str:
        where = f"{self.commit[:12]}  " if self.commit else ""
        return f"{where}{self.path}:{self.line}  {self.key}={mask(self.value)}  [{self.shape}]"


def _is_literal(line: str, match: re.Match[str]) -> bool:
    """The value of an assignment is a literal: quoted, or on a configuration line."""
    return bool(match.group("quote")) or CONFIG_LINE_PATTERN.match(line) is not None


def _object_pairs(line: str, match: re.Match[str]) -> list[tuple[str, str]]:
    """The quoted `key: value` pairs of an object literal opened by an assignment.

    The literal runs from the value's `{` to the first `}` on the same line.
    Until this port, `passwords = {Diretoria:'…'}` was reported with
    `{Diretoria:` as the value: the shape was found, but not the password, so a
    register by value could not recognise it. **Declared limit:** an object that
    spans several lines is read only on its first line, and nested braces end
    the reading at the first `}`.
    """
    start = match.start("value")
    end = line.find("}", start)
    span = line[start + 1 : end if end != -1 else len(line)]
    return [
        (f"{match.group('key')}.{pair.group('key')}", pair.group("value"))
        for pair in OBJECT_PAIR_PATTERN.finditer(span)
    ]


def detect(text: str) -> list[Finding]:
    """The credential shapes in a text, with no value known in advance.

    Path and commit stay empty here: the caller knows where it read.

    A password equal to the user — the default pair, `airflow`/`airflow` — has
    no minimum length and skips the no-digit word rule; a repeated reference is
    still a template. The user comes from the same URL or from any user
    assignment of the same text, and both sides of the pair must be literals —
    quoted or on a configuration line (`CONFIG_LINE_PATTERN`).

    An assignment whose value opens an object literal (`{`, not `{{` nor a
    complete `{var}`) is read pair by pair, each quoted value as a literal.
    """
    lines = text.splitlines()
    users = {
        match.group("value")
        for line in lines
        for match in USER_PATTERN.finditer(line)
        if _is_literal(line, match)
    }
    findings: list[Finding] = []
    for number, line in enumerate(lines, start=1):
        for match in ASSIGNMENT_PATTERN.finditer(line):
            value = match.group("value")
            context = line[match.start("value"):]
            if (
                value.startswith("{")
                and not value.startswith("{{")
                and placeholder(value, literal=bool(match.group("quote")), context=context) is None
            ):
                for key, pair_value in _object_pairs(line, match):
                    if len(pair_value) < MIN_SECRET_LENGTH or placeholder(
                        pair_value, literal=True
                    ) is not None:
                        continue
                    findings.append(Finding("", number, key, pair_value, "object literal"))
                continue
            equal = value in users and _is_literal(line, match)
            if (not equal and len(value) < MIN_SECRET_LENGTH) or placeholder(
                value,
                literal=bool(match.group("quote")),
                equal_to_user=equal,
                context=context,
            ) is not None:
                continue
            findings.append(Finding("", number, match.group("key"), value, "assignment"))
        for match in URL_CREDENTIAL_PATTERN.finditer(line):
            value = match.group("value")
            equal = value == match.group("key")
            if placeholder(
                value, literal=True, equal_to_user=equal, context=line[match.start("value"):]
            ) is not None:
                continue
            findings.append(
                Finding("", number, f"credential of {match.group('key')}", value, "URL")
            )
        for pattern in GENERIC_PATTERNS:
            match = pattern.search(line)
            if match:
                findings.append(Finding("", number, "generic form", match.group(0), "known form"))
    return findings


def _git(*args: str, root: pathlib.Path) -> list[str]:
    output = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout
    return [line for line in output.split("\0" if "-z" in args else "\n") if line]


def read_env(path: pathlib.Path) -> dict[str, str]:
    """`KEY=value` per line, ignoring comments and blanks; no interpolation."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def secret_values(env: dict[str, str]) -> dict[str, str]:
    """The values of `.env` that, found in a tracked file, are a leak."""
    return {
        key: value
        for key, value in env.items()
        if SECRET_KEY_PATTERN.search(key) and len(value) >= MIN_SECRET_LENGTH
    }


def public_values(root: pathlib.Path) -> dict[str, str]:
    """The registered public values: SHA-256 → the reason, as printed.

    An entry with no reason or with a malformed fingerprint is refused: a
    register that accepts an unexplained value is an allowlist nobody reviews.
    """
    path = root / PUBLIC_PATH
    if not path.exists():
        return {}
    import yaml

    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    result: dict[str, str] = {}
    for entry in raw.get("public", []):
        digest = str(entry.get("sha256", ""))
        reason = str(entry.get("reason", "")).strip()
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or not reason:
            raise ValueError(f"{PUBLIC_PATH}: entry needs a 64-hex sha256 and a reason: {entry!r}")
        result[digest] = f"{entry.get('name', 'public')} — {entry.get('decision', '')}".strip(" —")
    return result


def review(root: pathlib.Path) -> list[str]:
    """Every finding, one line each. An empty list is approval."""
    findings: list[str] = []
    tracked = _git("ls-files", "-z", root=root)

    # 1. .env is not tracked and stays ignored.
    if ".env" in tracked:
        findings.append(".env is tracked by git — remove it from the index and run the history scan")
    ignored = subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=root)
    if ignored.returncode != 0:
        findings.append(".env is not ignored by .gitignore")

    # 2. .env.example declares keys, never values.
    example = root / ".env.example"
    if example.exists():
        for number, line in enumerate(example.read_text(encoding="utf-8").splitlines(), start=1):
            text = line.strip()
            if text and not text.startswith("#") and "=" in text and text.split("=", 1)[1].strip():
                findings.append(f".env.example:{number}: key with a value filled in ({text.split('=', 1)[0]})")
    else:
        findings.append(".env.example does not exist")

    # 3. No value of .env, nor credential shape, in a tracked file.
    secrets = secret_values(read_env(root / ".env"))
    accepted = public_values(root)
    for relative in tracked:
        path = root / relative
        if path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for key, value in secrets.items():
            if value in content:
                findings.append(f"{relative}: contains the value of {key} from .env")
        # The shape detectors apply here too: one declaration, two reaches. What
        # the tracked mode adds is finding today what the history would find
        # tomorrow, before the commit exists.
        for finding in detect(content):
            if fingerprint(finding.value) in accepted:
                continue
            findings.append(
                f"{relative}:{finding.line}: {finding.key}={mask(finding.value)} "
                f"[{finding.shape}]"
            )

    # 4. Tracked and ignored at the same time is a contradiction — .gitignore
    #    swallows the next version of the file with nobody seeing it.
    for relative in _git("ls-files", "-z", "-ci", "--exclude-standard", root=root):
        findings.append(f"{relative}: tracked, but .gitignore ignores it — the next `git add` misses it")

    return findings


# ── The history ─────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Skipped:
    """A blob the scan did not read — named, never only counted."""

    obj: str
    path: str
    reason: str

    def __str__(self) -> str:
        return f"{self.obj[:12]}  {self.path}  skipped: {self.reason}"


def _history_blobs(root: pathlib.Path) -> dict[str, tuple[str, str]]:
    """Each blob that ever existed → (first commit that holds it, path).

    The walk goes from oldest to newest, so the commit recorded is the one that
    **introduced** the content — which is what is cited when rotating.
    """
    by_blob: dict[str, tuple[str, str]] = {}
    for commit in _git("rev-list", "--all", "--reverse", root=root):
        for line in _git("ls-tree", "-r", "--full-tree", commit, root=root):
            header, _, path = line.partition("\t")
            parts = header.split()
            if len(parts) < 3 or parts[1] != "blob":
                continue
            by_blob.setdefault(parts[2], (commit, path))
    return by_blob


def _contents(root: pathlib.Path, objs: list[str]) -> dict[str, bytes]:
    """Reads several blobs in one process — `git cat-file --batch`."""
    if not objs:
        return {}
    process = subprocess.run(
        ["git", "cat-file", "--batch"],
        cwd=root, input="\n".join(objs).encode() + b"\n", capture_output=True, check=True,
    )
    output, bodies, position = process.stdout, {}, 0
    for obj in objs:
        header_end = output.index(b"\n", position)
        parts = output[position:header_end].split()
        size = int(parts[2])
        start = header_end + 1
        bodies[obj] = output[start : start + size]
        position = start + size + 1  # the \n git writes after the body
    return bodies


def history(root: pathlib.Path) -> tuple[list[Finding], list[Skipped], list[str]]:
    """Scans every blob that ever existed. Returns findings, skipped and warnings.

    No value of `.env` takes part: detection is by shape, which is why it sees
    what was rotated later.
    """
    warnings: list[str] = []
    if _git("log", "--all", "--diff-filter=A", "--format=%H", "--", ".env", root=root):
        warnings.append(".env was added to the history once — the blob exists and needs a decision")

    by_blob = _history_blobs(root)
    sizes = {}
    if by_blob:
        stdin = "\n".join(by_blob) + "\n"
        process = subprocess.run(
            ["git", "cat-file", "--batch-check=%(objectname) %(objectsize)"],
            cwd=root, input=stdin, capture_output=True, text=True, check=True,
        )
        for line in process.stdout.split("\n"):
            if line.strip():
                obj, size = line.split()
                sizes[obj] = int(size)

    skipped: list[Skipped] = []
    to_read: list[str] = []
    for obj, (_commit, path) in by_blob.items():
        if pathlib.PurePath(path).suffix.lower() in BINARY_SUFFIXES:
            skipped.append(Skipped(obj, path, "binary extension"))
        elif sizes.get(obj, 0) > MAX_BLOB_BYTES:
            skipped.append(Skipped(obj, path, f"{sizes[obj]} bytes > {MAX_BLOB_BYTES}"))
        else:
            to_read.append(obj)

    findings: list[Finding] = []
    for obj, body in _contents(root, to_read).items():
        commit, path = by_blob[obj]
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            skipped.append(Skipped(obj, path, "not UTF-8 text"))
            continue
        for finding in detect(text):
            findings.append(
                Finding(path, finding.line, finding.key, finding.value, finding.shape, commit)
            )
    return findings, skipped, warnings


def _report_history(root: pathlib.Path) -> int:
    findings, skipped, warnings = history(root)
    accepted = public_values(root)

    not_accepted = []
    public_seen = 0
    for finding in findings:
        if fingerprint(finding.value) in accepted:
            public_seen += 1
        else:
            not_accepted.append(finding)

    if skipped:
        print(f"\nskipped ({len(skipped)}) — skipped is not verified:", file=sys.stderr)
        for skipped_blob in skipped:
            print(f"  {skipped_blob}", file=sys.stderr)

    for warning in warnings:
        print(f"\nWARNING: {warning}", file=sys.stderr)

    if not_accepted:
        print(f"\n{len(not_accepted)} finding(s) in the history:", file=sys.stderr)
        for finding in not_accepted:
            print(f"  {finding}", file=sys.stderr)
        print(
            "\nA real secret in the history is the Owner's decision: rotate it, and record how it "
            f"was treated. A value public by design goes into {PUBLIC_PATH}, with its reason.",
            file=sys.stderr,
        )
        return 1

    if warnings:
        return 1
    print(
        f"history review: nothing found "
        f"({public_seen} occurrence(s) of values public by design, {len(accepted)} registered; "
        f"{len(skipped)} blob(s) skipped)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    history_requested = "--history" in args
    if history_requested:
        args.remove("--history")
    root = pathlib.Path(args[0]) if args else pathlib.Path.cwd()

    if history_requested:
        return _report_history(root)

    findings = review(root)
    for finding in findings:
        print(finding, file=sys.stderr)
    if findings:
        print(f"\nsecrets review: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    print("secrets review: nothing found in the tracked files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
