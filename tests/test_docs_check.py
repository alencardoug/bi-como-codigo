"""Oracles of `docs_check`: the link check that used to be done by eye.

A renamed heading breaks anchors silently. Each GitHub slug rule this repository
depends on has its counter-proof here, because getting one wrong produces the
worst possible result: a tool that says "nothing broken" about a broken map.

Ported from mvp_eng_dados_1 (`tests/test_docs_check.py` at `26b58b3`); the
tests of links into mvp_eng_dados_1 are new here.
"""

from __future__ import annotations

import os
import pathlib
import subprocess

import pytest

from bi_como_codigo import docs_check

UPSTREAM = "https://github.com/alencardoug/mvp_eng_dados_1"


def _git(root: pathlib.Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _init(root: pathlib.Path) -> None:
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.local")
    _git(root, "config", "user.name", "test")


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "repo"
    root.mkdir()
    _init(root)
    (root / "docs" / "adr").mkdir(parents=True)
    (root / "docs" / "adr" / "0007-a-decision.md").write_text("# ADR-0007\n", encoding="utf-8")
    return root


@pytest.fixture
def upstream(tmp_path: pathlib.Path) -> tuple[docs_check.EngDados, str]:
    """A stand-in for mvp_eng_dados_1 with one commit, and that commit."""
    root = tmp_path / "upstream"
    (root / "docs").mkdir(parents=True)
    _init(root)
    (root / "docs" / "gov.md").write_text("# Governança\n\n## 7. Regras de acesso\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "lineage.py").write_text("", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return docs_check.EngDados(root), _git(root, "rev-parse", "--short", "HEAD")


def _write(root: pathlib.Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    _git(root, "add", relative)


def _broken(root: pathlib.Path, eng_dados: docs_check.EngDados | None = None) -> list[docs_check.Broken]:
    return docs_check.check(root, eng_dados)[0]


# ── The slug rule, which is where mistakes come from ───────────────────────


@pytest.mark.parametrize(
    "heading, expected",
    [
        ("## 8. Retenção", "8-retenção"),
        ("## 3. Modelo dimensional — 25 tabelas em `analytics`", "3-modelo-dimensional--25-tabelas-em-analytics"),
        ("### D35 — decidida em 07/09/2026", "d35--decidida-em-07092026"),
        ("## O que **não** entra", "o-que-não-entra"),
        ("## Ver o [Termo](abertura.md)", "ver-o-termo"),
        ("## snake_case e kebab-case", "snake_case-e-kebab-case"),
    ],
)
def test_the_slug_is_githubs(heading, expected):
    """Accents stay; punctuation goes; the em dash becomes two hyphens."""
    assert docs_check.slug(heading.lstrip("# ")) == expected


def test_good_link_passes(repo):
    _write(repo, "docs/target.md", "# Target\n\n## A section\n")
    _write(repo, "README.md", "See [the target](docs/target.md#a-section).\n")

    broken, counts, _ = docs_check.check(repo)

    assert broken == []
    assert counts["links"] == 1 and counts["anchors"] == 1


def test_missing_file_and_missing_anchor_are_flagged(repo):
    _write(repo, "docs/target.md", "# Target\n\n## A section\n")
    _write(repo, "README.md", "[gone](docs/gone.md)\n\n[wrong](docs/target.md#another-section)\n")

    reasons = {b.target: b.reason for b in _broken(repo)}

    assert reasons["docs/gone.md"] == "file does not exist"
    assert reasons["docs/target.md#another-section"] == "heading does not exist in docs/target.md"


def test_accented_anchor_and_encoded_fragment(repo):
    """`%C3%A7` is what the browser copies from the address bar."""
    _write(repo, "docs/gov.md", "# Governança\n\n## 8. Retenção\n")
    _write(repo, "README.md", "[raw](docs/gov.md#8-retenção)\n\n[encoded](docs/gov.md#8-reten%C3%A7%C3%A3o)\n")

    broken, counts, _ = docs_check.check(repo)

    assert broken == [], broken
    assert counts["anchors"] == 2


def test_repeated_heading_gets_a_suffix(repo):
    _write(repo, "docs/adr/0007-a-decision.md", "# ADR-0007\n\n## Context\n\n## Context\n")
    _write(
        repo,
        "README.md",
        "[first](docs/adr/0007-a-decision.md#context)\n\n"
        "[second](docs/adr/0007-a-decision.md#context-1)\n\n"
        "[third](docs/adr/0007-a-decision.md#context-2)\n",
    )

    assert [b.target for b in _broken(repo)] == ["docs/adr/0007-a-decision.md#context-2"]


def test_suffix_does_not_repeat_an_emitted_anchor(repo):
    """RVF12-05: `X`, `X`, `X-1` give `x`, `x-1` and `x-1-1`, as `github-slugger` does."""
    _write(repo, "README.md", "# X\n\n# X\n\n# X-1\n\n[1](#x) [2](#x-1) [3](#x-1-1) [4](#x-2)\n")

    broken, counts, _ = docs_check.check(repo)

    assert counts["anchors"] == 4
    assert [b.target for b in broken] == ["#x-2"]


def test_heading_inside_a_code_block_does_not_count(repo):
    _write(repo, "docs/target.md", "# Target\n\n```bash\n# A comment\n```\n")
    _write(repo, "README.md", "[false](docs/target.md#a-comment)\n")

    broken = _broken(repo)

    assert len(broken) == 1
    assert broken[0].reason == "heading does not exist in docs/target.md"


@pytest.mark.parametrize(
    "block",
    [
        pytest.param("````markdown\n```python\n# False\n```\n````\n", id="four-backticks-with-three-inside"),
        pytest.param("~~~markdown\n```\n# False\n```\n~~~\n", id="tildes-with-backticks-inside"),
        pytest.param("```\n# False\n``` text\n```\n", id="fence-with-text-does-not-close"),
    ],
)
def test_fence_closes_only_on_the_same_character_and_length(repo, block):
    """RVF12-06: inside four backticks, three backticks are content."""
    _write(repo, "README.md", block + "\n# Real\n\n[false](#false) [real](#real)\n")

    assert [b.target for b in _broken(repo)] == ["#false"]


@pytest.mark.parametrize(
    "block",
    [
        pytest.param("```text\n    ```\n# False\n```\n", id="four-spaces-are-content"),
        pytest.param("   ```\n     ```\n# False\n   ```\n", id="opens-with-three-content-with-five"),
        pytest.param("1. Step:\n\n   ```bash\n   # False\n   ```\n", id="list-item"),
        pytest.param("16. Step:\n    ```\n    # False\n    ```\n", id="two-digit-item"),
        pytest.param("- Step:\n\n  ```\n  # False\n", id="the-end-of-the-item-closes-the-block"),
        pytest.param("    ```\n", id="four-spaces-outside-a-list-do-not-open"),
    ],
)
def test_fence_indentation_counts_against_the_list_item(repo, block):
    """RVF12-2-06: a fence opens and closes with up to three spaces beyond the item."""
    _write(repo, "README.md", block + "\n# Real\n\n[false](#false) [real](#real)\n")

    assert [b.target for b in _broken(repo)] == ["#false"]


def test_backtick_on_the_line_does_not_open_a_fence(repo):
    _write(repo, "README.md", "``` `x` ```\n\n# Real\n\n[real](#real)\n")

    assert _broken(repo) == []


def test_link_inside_a_code_block_is_not_checked(repo):
    _write(repo, "README.md", "```markdown\n[example](does/not/exist.md)\n```\n")

    broken, counts, _ = docs_check.check(repo)

    assert broken == []
    assert counts["links"] == 0


def test_reference_link_is_resolved(repo):
    _write(repo, "docs/target.md", "# Target\n\n## A section\n")
    _write(repo, "README.md", "See [the target][t] and [the lost][lost].\n\n[t]: docs/target.md#a-section\n")

    assert [(b.target, b.reason) for b in _broken(repo)] == [("[lost]", "reference with no definition")]


def test_cited_adr_must_exist(repo):
    _write(repo, "README.md", "See ADR-0007 and also ADR-0099.\n")

    broken, counts, _ = docs_check.check(repo)

    assert counts["adrs"] == 2
    assert [(b.target, b.reason) for b in broken] == [("ADR-0099", "does not exist in docs/adr/")]


def test_adr_cited_as_the_text_of_an_upstream_link_is_upstreams(repo):
    """`[ADR-0018](…/mvp_eng_dados_1/…)` is checked as a link, not as a local ADR."""
    _write(repo, "README.md", f"[ADR-0018]({UPSTREAM}/blob/26b58b3/docs/adr/0018-x.md) and ADR-0099.\n")

    broken, counts, _ = docs_check.check(repo)

    assert counts["adrs"] == 1
    assert [b.target for b in broken] == ["ADR-0099"]


def test_bare_adr_in_the_review_record_is_upstreams(repo):
    """The review record cites mvp_eng_dados_1's ADRs by number, as recorded."""
    _write(repo, "REVIEW.md", "N16 correctly reads ADR-0008 and ADR-0018.\n")
    _write(repo, "README.md", "ADR-0099 is ours, and missing.\n")

    assert [(b.file, b.target) for b in _broken(repo)] == [("README.md", "ADR-0099")]


def test_link_and_adr_in_a_heading_are_checked(repo):
    """RVF12-04: the heading generates an anchor **and** is text."""
    _write(repo, "README.md", "# See the [target](gone.md)\n\n## According to ADR-0099\n")

    broken, counts, _ = docs_check.check(repo)

    assert [(b.line, b.target, b.reason) for b in broken] == [
        (1, "gone.md", "file does not exist"),
        (3, "ADR-0099", "does not exist in docs/adr/"),
    ]
    assert (counts["links"], counts["adrs"]) == (1, 1)


def test_link_inside_inline_code_is_not_checked(repo):
    """RVF12-2-05 and RVF12-3-02: in GFM inline code takes precedence over links."""
    _write(
        repo,
        "README.md",
        "# How to write `[lost](gone.md)`\n\n"
        "With a backtick inside: `` `[lost](gone.md)` `` and `[x][y]`.\n\n"
        "Link with code as text: [`gone.md`](also-gone.md).\n\n"
        "Escaped backtick: \\`[escaped](escaped.md)\\`.\n\n"
        "Code between the parts: [lost]`text`(gone.md).\n\n"
        "Escaped backslash: \\\\`[lost](gone.md)`.\n\n"
        "Backslash inside code: `a\\`[inside](inside.md).\n",
    )

    broken, counts, _ = docs_check.check(repo)

    assert [(b.line, b.target) for b in broken] == [
        (5, "also-gone.md"),
        (7, "escaped.md"),
        (13, "inside.md"),
    ]
    assert counts["links"] == 3


def test_external_link_is_not_checked(repo):
    _write(repo, "README.md", "[out](https://example.invalid/page)\n")

    broken, counts, _ = docs_check.check(repo)

    assert broken == []
    assert counts["links"] == 0


# ── Links into mvp_eng_dados_1 (new in this port) ───────────────────────────


def test_pinned_upstream_links_are_checked_at_their_commit(repo, upstream):
    eng_dados, ref = upstream
    _write(
        repo,
        "README.md",
        f"[gov]({UPSTREAM}/blob/{ref}/docs/gov.md#7-regras-de-acesso)\n\n"
        f"[code]({UPSTREAM}/blob/{ref}/src/lineage.py)\n\n"
        f"[tree]({UPSTREAM}/tree/{ref}/docs)\n\n"
        f"[anchor]({UPSTREAM}/blob/{ref}/docs/gov.md#8-retenção)\n\n"
        f"[file]({UPSTREAM}/blob/{ref}/docs/gone.md)\n",
    )

    broken, counts, unverified = docs_check.check(repo, eng_dados)

    assert counts["eng_dados"] == 5 and unverified == []
    assert [(b.line, b.reason) for b in broken] == [
        (7, f"heading does not exist in docs/gov.md at {ref}"),
        (9, f"does not exist in mvp_eng_dados_1 at {ref}"),
    ]


def test_unpinned_upstream_link_is_broken_even_without_a_checkout(repo):
    """A branch name lets the cited fact move under the link."""
    _write(repo, "README.md", f"[gov]({UPSTREAM}/blob/main/docs/gov.md)\n\n[ok]({UPSTREAM}/blob/26b58b3/x.md)\n")

    broken, _, unverified = docs_check.check(repo)

    assert [b.reason for b in broken] == ["not pinned: `main` is not a commit, so the fact it cites can move"]
    assert [u.line for u in unverified] == [3]


def test_without_a_checkout_the_upstream_links_are_listed_not_passed(repo, capsys, monkeypatch):
    """Skipped is not verified: each link is named, and the summary says so."""
    monkeypatch.delenv("ENG_DADOS_DIR", raising=False)
    _write(repo, "README.md", f"[gov]({UPSTREAM}/blob/26b58b3/docs/gov.md)\n")

    assert docs_check.main([str(repo)]) == 0
    output = capsys.readouterr()
    assert f"README.md:1: {UPSTREAM}/blob/26b58b3/docs/gov.md" in output.err
    assert "1 not verified" in output.out


def test_the_documentation_of_this_repository_passes():
    """The check holds for the real repository, not only for the throwaway one.

    The links into mvp_eng_dados_1 are verified when `ENG_DADOS_DIR` names a
    checkout of it; `make check` requires it.
    """
    root = pathlib.Path(__file__).resolve().parent.parent
    checkout = os.environ.get("ENG_DADOS_DIR")
    broken, counts, unverified = docs_check.check(
        root, docs_check.EngDados(pathlib.Path(checkout)) if checkout else None
    )

    assert broken == [], "\n".join(str(b) for b in broken)
    assert counts["eng_dados"] > 0
    if checkout:
        assert unverified == []
