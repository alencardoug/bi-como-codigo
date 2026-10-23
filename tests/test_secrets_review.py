"""The secrets review of `make check`, proved on a throwaway repository.

Each way of breaking rule 1 has its counter-proof: the test builds a clean
repository that passes, introduces the break and requires the finding.

Ported from mvp_eng_dados_1 (`tests/test_secrets_review.py` at `26b58b3`); the
tests of object literals and of the register of public values are new here.

**The fictitious values of this file are built in parts.** Written whole, the
review itself would flag this file — which is exactly what it must do, so the
fixture obeys the rule it proves. The name of the constant matters too: `SENHA`
does not match the assignment detector, `PASSWORD` would.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import textwrap

import pytest

from bi_como_codigo import secrets_review

#: Fictitious values, in parts. None of them ever existed anywhere.
SENHA = "s3nh4-" + "muito-longa-e-aleatoria"
SENHA_ROTACIONADA = "s3nh4-" + "nova-depois-da-rotacao-9f2c"
SEGREDO_JWT = "jwt" + "0123456789abcdef"
TOKEN_GITHUB = "ghp_" + "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8"
DEMO = "demo_" + "publica_42"
OUTRA = "outra_" + "privada_77"


def _git(root: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _commit(root: pathlib.Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write_env(root: pathlib.Path, password: str) -> None:
    (root / ".env").write_text(
        textwrap.dedent(
            f"""\
            FIREBASE_PROJECT=bi-como-codigo
            EXPORT_DB_PASSWORD={password}
            SIGNING_SECRET={SEGREDO_JWT}
            """
        ),
        encoding="utf-8",
    )


def _register(root: pathlib.Path, *entries: str) -> None:
    (root / "docs").mkdir(exist_ok=True)
    (root / secrets_review.PUBLIC_PATH).write_text(
        "public:\n" + "".join(entries), encoding="utf-8"
    )


def _entry(value: str, reason: str = "shown to every visitor (N22)") -> str:
    return (
        f"  - name: demo\n    sha256: {secrets_review.fingerprint(value)}\n"
        f"    decision: N22\n    reason: {reason}\n"
    )


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.local")
    _git(tmp_path, "config", "user.name", "test")
    (tmp_path / ".gitignore").write_text(".env\n*.log\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text(
        textwrap.dedent(
            """\
            # template
            FIREBASE_PROJECT=
            EXPORT_DB_PASSWORD=
            SIGNING_SECRET=
            """
        ),
        encoding="utf-8",
    )
    _write_env(tmp_path, SENHA)
    (tmp_path / "docs.md").write_text(
        "The project is bi-como-codigo and the password comes from .env.\n", encoding="utf-8"
    )
    _commit(tmp_path, "base")
    return tmp_path


def test_clean_repository_passes_and_the_project_name_is_not_a_secret(repo: pathlib.Path) -> None:
    assert secrets_review.review(repo) == []
    assert set(secrets_review.secret_values(secrets_review.read_env(repo / ".env"))) == {
        "EXPORT_DB_PASSWORD", "SIGNING_SECRET",
    }


def test_env_value_in_a_tracked_file_is_flagged_with_its_key(repo: pathlib.Path) -> None:
    (repo / "connector.yml").write_text(f"password: {SENHA}\n", encoding="utf-8")
    _git(repo, "add", "connector.yml")
    findings = secrets_review.review(repo)
    assert "connector.yml: contains the value of EXPORT_DB_PASSWORD from .env" in findings
    # The shape detector finds it too, without reading `.env` — one declaration,
    # two reaches.
    assert any("connector.yml:1: password=" in f for f in findings), findings


def test_env_example_with_a_value_and_tracked_env_are_flagged(repo: pathlib.Path) -> None:
    (repo / ".env.example").write_text(
        "FIREBASE_PROJECT=\nEXPORT_DB_PASSWORD=abc\n", encoding="utf-8"
    )
    _git(repo, "add", "-f", ".env", ".env.example")
    findings = secrets_review.review(repo)
    assert ".env is tracked by git — remove it from the index and run the history scan" in findings
    assert ".env.example:2: key with a value filled in (EXPORT_DB_PASSWORD)" in findings
    assert ".env: contains the value of EXPORT_DB_PASSWORD from .env" in findings
    assert ".env: tracked, but .gitignore ignores it — the next `git add` misses it" in findings


def test_generic_credential_form_is_flagged_without_env(repo: pathlib.Path) -> None:
    # Built in parts: written whole, the review would flag this file.
    header = "-----BEGIN " + "RSA PRIVATE KEY-----"
    (repo / "key.pem").write_text(f"{header}\nMIIE...\n", encoding="utf-8")
    (repo / ".env").unlink()
    _git(repo, "add", "key.pem")
    findings = secrets_review.review(repo)
    assert len(findings) == 1, findings
    assert findings[0].startswith("key.pem:1: generic form=")
    assert "[known form]" in findings[0]


def test_gitignore_that_stops_ignoring_env_is_flagged(repo: pathlib.Path) -> None:
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
    assert secrets_review.review(repo) == [".env is not ignored by .gitignore"]


def test_this_repository_passes() -> None:
    """The rule holds for the real repository, not only for the throwaway one."""
    root = pathlib.Path(__file__).resolve().parent.parent
    assert secrets_review.review(root) == []


# ── The history ─────────────────────────────────────────────────────────────
#
# The tracked mode is blind to the past by construction: it compares with the
# values of the **current** `.env`. The history scan detects by **shape**, and
# these tests prove it sees exactly where the other one does not.


def test_rotated_password_leaves_the_tracked_mode_and_the_history_finds_it(repo):
    """The counter-proof that justifies the whole history mode."""
    (repo / "connector.yml").write_text(f"password: {SENHA}\n", encoding="utf-8")
    leak = _commit(repo, "leak")

    (repo / "connector.yml").unlink()
    _write_env(repo, SENHA_ROTACIONADA)
    _commit(repo, "remove the file and rotate the password")

    # The tracked mode passes — and passing is exactly the problem.
    assert secrets_review.review(repo) == []
    assert SENHA not in (repo / ".env").read_text(encoding="utf-8")

    findings, _skipped, _warnings = secrets_review.history(repo)
    leaked = [f for f in findings if f.path == "connector.yml"]
    assert len(leaked) == 1, findings
    assert leaked[0].commit == leak
    assert leaked[0].key == "password"
    assert leaked[0].value == SENHA
    # The value is not printed: two characters and the length.
    assert str(leaked[0]).endswith(f"password=s3*** ({len(SENHA)} characters)  [assignment]")
    assert SENHA not in str(leaked[0])


def test_the_same_password_is_found_in_env_yaml_and_json(repo):
    """The three syntaxes. JSON needs the quote that **closes** the key."""
    (repo / "service.env").write_text(f"DB_PASSWORD={SENHA}\n", encoding="utf-8")
    (repo / "connector.yml").write_text(f"password: {SENHA}\n", encoding="utf-8")
    (repo / "state.json").write_text(
        '{"user": "mvp", "password": "%s", "port": 5432}\n' % SENHA, encoding="utf-8"
    )
    _commit(repo, "leak in the three forms")

    for file in ("service.env", "connector.yml", "state.json"):
        (repo / file).unlink()
    _write_env(repo, SENHA_ROTACIONADA)
    _commit(repo, "remove and rotate")

    assert secrets_review.review(repo) == []
    findings, _s, _w = secrets_review.history(repo)
    by_file = {f.path: f for f in findings}
    assert {"service.env", "connector.yml", "state.json"} <= set(by_file)
    for file in ("service.env", "connector.yml", "state.json"):
        assert by_file[file].value == SENHA, file


def test_credential_in_a_url_is_found(repo):
    (repo / "profiles.yml").write_text(
        f"url: postgresql://mvp:{SENHA}@localhost:5432/warehouse\n", encoding="utf-8"
    )
    _commit(repo, "url with a credential")
    (repo / "profiles.yml").unlink()
    _commit(repo, "remove")

    findings, _s, _w = secrets_review.history(repo)
    urls = [f for f in findings if f.shape == "URL"]
    assert len(urls) == 1, findings
    assert urls[0].value == SENHA


def test_generic_form_in_an_old_blob(repo):
    (repo / "ci.yml").write_text(f"token: {TOKEN_GITHUB}\n", encoding="utf-8")
    _commit(repo, "token")
    (repo / "ci.yml").unlink()
    _commit(repo, "remove")

    findings, _s, _w = secrets_review.history(repo)
    shapes = {f.shape for f in findings if f.path == "ci.yml"}
    assert "known form" in shapes, findings


def test_placeholder_in_env_example_is_not_flagged(repo):
    """A key declared with no value is what `.env.example` **must** have."""
    findings, _s, _w = secrets_review.history(repo)
    assert [f for f in findings if f.path == ".env.example"] == []
    assert secrets_review.placeholder("") is not None
    assert secrets_review.placeholder("${DB_PASSWORD}") is not None
    assert secrets_review.placeholder("<your-password-here>") is not None
    assert secrets_review.placeholder(SENHA) is None


def test_real_secret_in_an_example_file_is_found(repo):
    """No extension is exempt: the template is a property of the **value**."""
    (repo / "config.example.yml").write_text(f"api_key: {SENHA}\n", encoding="utf-8")
    _commit(repo, "real secret in a template file")

    findings, _s, _w = secrets_review.history(repo)
    in_example = [f for f in findings if f.path == "config.example.yml"]
    assert len(in_example) == 1, findings
    assert in_example[0].value == SENHA


def test_large_blob_appears_in_the_skipped_list(repo):
    """Skipped is not verified — so it is named, not only counted."""
    large = repo / "dump.sql"
    large.write_text("-- " + ("x" * (secrets_review.MAX_BLOB_BYTES + 10)), encoding="utf-8")
    _commit(repo, "large file")

    _findings, skipped, _w = secrets_review.history(repo)
    by_path = {s.path: s for s in skipped}
    assert "dump.sql" in by_path, skipped
    assert "bytes >" in by_path["dump.sql"].reason
    assert by_path["dump.sql"].obj


def test_env_in_the_history_is_a_warning_even_with_no_finding(repo):
    """A `.env` that was ever tracked leaves a blob, and the blob is the question."""
    _git(repo, "add", "-f", ".env")
    _commit(repo, "add .env by mistake")
    _git(repo, "rm", "-q", "--cached", ".env")
    _commit(repo, "remove from the index")

    _findings, _skipped, warnings = secrets_review.history(repo)
    assert any(".env was added to the history once" in w for w in warnings), warnings


# ── Object literals (new in this port) ─────────────────────────────────────


def test_object_literal_is_read_pair_by_pair():
    """`passwords = {A:'…', B:'…'}` yields the passwords, not `{A:`.

    Before this port the finding's value was `{Diretoria:` — the shape was
    seen, but a register by value could not recognise the password.
    """
    key = "pass" + "words"
    text = f"const {key} = {{Diretoria:'{DEMO}', Logistica:'{OUTRA}'}};"
    findings = secrets_review.detect(text)
    assert [(f.key, f.value, f.shape) for f in findings] == [
        (f"{key}.Diretoria", DEMO, "object literal"),
        (f"{key}.Logistica", OUTRA, "object literal"),
    ]


def test_the_portuguese_word_for_password_is_a_sensitive_key():
    """What visitors read is in Portuguese: `Senha: …` is an assignment too."""
    findings = secrets_review.detect(f"Login: Diretoria\nSen" + f"ha: {DEMO}\n")
    assert [(f.line, f.key, f.value) for f in findings] == [(2, "Sen" + "ha", DEMO)]


@pytest.mark.parametrize(
    "text",
    [
        "{k} = {{a: ref_a, b: ref_b}}",  # unquoted: references
        "{k} = {{a: 'short'}}",  # below the minimum length
        "{k} = {{a: '${{SECRET}}'}}",  # a reference inside quotes
        "{k}: '{{{{ env_var(\"X\") }}}}'",  # a template, not an object
        "url = f'{k}={{value}}'",  # a complete `{var}` interpolation
    ],
    ids=["references", "short", "reference-in-quotes", "template", "interpolation"],
)
def test_object_literal_keeps_the_templates(text):
    assert secrets_review.detect(text.format(k="pass" + "words")) == []


# ── The register of values public by design (new in this port) ─────────────


def test_registered_public_value_passes_and_another_value_on_the_same_shape_does_not(repo):
    key = "pass" + "words"
    (repo / "login.js").write_text(
        f"const {key} = {{Diretoria:'{DEMO}', Logistica:'{OUTRA}'}};\n", encoding="utf-8"
    )
    _git(repo, "add", "login.js")
    findings = secrets_review.review(repo)
    assert len(findings) == 2, findings

    _register(repo, _entry(DEMO))
    findings = secrets_review.review(repo)
    assert findings == [f"login.js:1: {key}.Logistica={secrets_review.mask(OUTRA)} [object literal]"]


def test_history_accepts_a_registered_value_and_counts_it(repo, capsys):
    (repo / "plan.md").write_text(f"password: {DEMO}\n", encoding="utf-8")
    _commit(repo, "the demo password, public by design")
    assert secrets_review.main([str(repo), "--history"]) == 1

    _register(repo, _entry(DEMO))
    _commit(repo, "register it")
    assert secrets_review.main([str(repo), "--history"]) == 0
    output = capsys.readouterr()
    assert "1 occurrence(s) of values public by design, 1 registered" in output.out
    assert DEMO not in output.out and DEMO not in output.err


@pytest.mark.parametrize(
    "entry",
    [
        "  - name: demo\n    sha256: abc\n    reason: short digest\n",
        "  - name: demo\n    sha256: {digest}\n",
        "  - name: demo\n    sha256: {digest}\n    reason: '  '\n",
    ],
    ids=["malformed-digest", "no-reason", "blank-reason"],
)
def test_register_entry_needs_a_digest_and_a_reason(repo, entry):
    """A register that accepts an unexplained value is an allowlist nobody reviews."""
    _register(repo, entry.format(digest=secrets_review.fingerprint(DEMO)))
    with pytest.raises(ValueError, match="needs a 64-hex sha256 and a reason"):
        secrets_review.public_values(repo)


def test_the_register_holds_the_two_demo_passwords():
    """The register of this repository has exactly the two profiles of N22."""
    root = pathlib.Path(__file__).resolve().parent.parent
    import yaml

    raw = yaml.safe_load((root / secrets_review.PUBLIC_PATH).read_text(encoding="utf-8"))
    assert sorted(e["name"] for e in raw["public"]) == ["Diretoria", "Logística"]
    assert len(secrets_review.public_values(root)) == 2


# ── Templates do not excuse literals (mvp_eng_dados_1, stage-12 final review) ─


@pytest.mark.parametrize("symbol", ["x", "$", "(", "[", "{{"])
def test_quoted_literal_with_a_symbol_in_the_middle_is_found(symbol):
    """RVF12-03: `$`, `(` and `[` inside a JSON value do not make it a reference."""
    key = "pass" + "word"
    value = "Ab9" + symbol + "Z7q1"
    findings = secrets_review.detect(json.dumps({key: value}))
    assert [(f.key, f.value) for f in findings] == [(key, value)]


def test_references_and_expressions_are_still_templates():
    """The tightening must not bring back the false findings the rules avoid."""
    text = "\n".join(
        [
            "PGPASSWORD=$$CLIENT_SECRET",
            'password: "${DB_PASSWORD}"',
            "secret: ${JWT_SECRET:?set it in .env}",
            'password = quote_plus(os.environ["EXPORT_DB_PASSWORD"])',
            "token = client.token()",
            r"s/.*Client-Secret: \(\S*\).*/CLIENT_SECRET=\1/p",
            r"POSTGRES_PASSWORD: (?!\$)\S+",
            "password = var.source_db_password",
            'echo "SOURCE_DB_PASSWORD=$$(pw)"; \\',
            'token_url     = "${trimsuffix(var.server_url, "/")}/applications/token"',
            "password: \"{{ env_var('DBT_PASSWORD') }}\"",
        ]
    )
    assert secrets_review.detect(text) == []


@pytest.mark.parametrize(
    "value",
    ["${Ab9Z7q1", "$(Ab9Z7q1", "{{Ab9Z7q1", "{{Ab9Z7q1}", "${A}Ab9Z7q1", "{{A}}Ab9Z7q1", "$1Ab9Z7q1"],
)
@pytest.mark.parametrize("syntax", ["json", "yaml"])
def test_incomplete_reference_or_one_followed_by_a_literal_is_found(value, syntax):
    """RVF12-2-01 and RVF12-3-01: a reference is a complete form reaching the end."""
    key = "pass" + "word"
    text = json.dumps({key: value}) if syntax == "json" else f"{key}: {value}"
    findings = secrets_review.detect(text)
    assert [(f.key, f.value) for f in findings] == [(key, value)]


def test_positional_parameter_of_the_shell_is_a_reference():
    """RVF12-2-03: `$1` in a script's URL is the parameter, not the password."""
    url = 'url="postgresql' + "://" + "reader:" + "$1" + '@localhost/db"'
    assert secrets_review.detect(url) == []


def test_password_equal_to_the_user_is_found_even_short_and_without_digits():
    """RVF12-01: the default pair, in the URL or in an assignment of the same text."""
    user = "air" + "flow"
    key = "POSTGRES_" + "PASSWORD"
    compose = "\n".join(
        [
            f"CONN: postgresql+psycopg2://{user}:{user}@airflow_db:5432/{user}",
            f"POSTGRES_USER: {user}",
            f"{key}: {user}",
        ]
    )
    assert secrets_review.placeholder(user) is not None

    findings = secrets_review.detect(compose)
    assert [(f.line, f.shape, f.value) for f in findings] == [
        (1, "URL", user),
        (3, "assignment", user),
    ]

    templates = "\n".join(
        [
            "url = f'postgresql://{user}:{user}@localhost/db'",
            "CONN: postgresql://${DB_USER}:${DB_USER}@airflow_db/airflow",
        ]
    )
    assert secrets_review.detect(templates) == []


@pytest.mark.parametrize(
    "text",
    [
        "{u} = db_user\n{s} = db_user\n",
        "connect(\n    {u}=db_user,\n    {s}=db_user,\n)\n",
    ],
    ids=["python_assignment", "named_arguments"],
)
def test_repeated_identifier_in_code_is_not_a_default_pair(text):
    """RVF12-2-02: user and password bound to the same variable are references."""
    assert secrets_review.detect(text.format(u="u" + "ser", s="pass" + "word")) == []


def test_identifier_in_the_last_named_argument_is_a_reference():
    """The `)` that closes the call does not make the identifier a value."""
    password = "pass" + "word"
    assert secrets_review.detect(f"connect({password}=db_password)") == []
    assert secrets_review.detect(f"connect(user=db_user, {password}=db_user)") == []


@pytest.mark.parametrize(
    "text",
    [
        '{{"username": "reader", "{s}": "reader"}}',
        '{u} = "reader"\n{s} = "reader"\n',
        "POSTGRES_USER=reader\nPOSTGRES_{S}=reader\n",
        "environment:\n  - POSTGRES_USER=reader\n  - POSTGRES_{S}=reader\n",
    ],
    ids=["json", "quoted_python", "env", "compose_list"],
)
def test_default_pair_between_literals_is_still_found(text):
    """The positive control of RVF12-2-02: the distinction must not lose the literal."""
    password = "pass" + "word"
    findings = secrets_review.detect(text.format(u="u" + "ser", s=password, S=password.upper()))
    assert [f.value for f in findings] == ["reader"]
