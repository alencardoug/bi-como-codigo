"""Coherence of the documents, by tool — a step of `make check`.

The documentation of this repository is a map of links: each subject has one
owning document, and the others point at it instead of repeating it. That only
works while the pointers point somewhere. A renamed heading breaks anchors
silently, and the reader lands at the top of the file thinking they read what
they were looking for.

What is checked:

* relative link → the file exists;
* anchor → a heading in the target file generates that slug;
* `ADR-nnnn` cited in the text → `docs/adr/nnnn-*.md` exists;
* link into mvp_eng_dados_1 → pinned to a commit, and the file and the anchor
  exist **at that commit**, read from a local checkout named by
  `ENG_DADOS_DIR`. Facts of that project are cited by pinned link, never copied,
  so these links carry most of the plan's weight. Without the variable they are
  listed as not verified — skipped is not verified —, and the check still fails
  on a link that is not pinned, since that one needs no checkout to be wrong.

**Ported from mvp_eng_dados_1** (`src/mvp_ed1/docs_check.py` at `26b58b3`);
the pinned-link check is new here. The RVF12 codes are findings of that
project's stage-12 final review, kept because they say why each rule is so.

**Declared limit: this checks paths, not prose.** A link that points at the
right file and describes the wrong thing passes here, and should: pretending
otherwise would be worse than not measuring.

**The slug rule is GitHub's**, because that is where these documents are read:
lowercase, punctuation removed, spaces become hyphens, accents **kept**, and
repeated headings get `-1`, `-2`. Headings inside code blocks do not count —
they are examples, not structure.
"""

from __future__ import annotations

import os
import pathlib
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from urllib.parse import unquote

#: Code fence: three or more backticks or tildes, with or without a language.
#: The indentation is measured apart, against that of the list item it is in.
FENCE = re.compile(r"^(?P<indent> *)(?P<fence>`{3,}|~{3,})(?P<rest>.*)$")

#: List item — `-`, `*`, `+`, `1.` or `1)` followed by a space or the end of the
#: line. Its content starts at the column after the marker and the spaces.
LIST_ITEM = re.compile(r"^(?P<marker> *(?:[-*+]|\d{1,9}[.)]))(?= |$)")

#: ATX heading. Setext (`====` underneath) is not used in this repository.
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

#: Inline link: `[text](target)`. The target stops at the first space or `)`.
LINK = re.compile(r"\[(?P<text>[^\]]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")

#: Reference link definition: `[label]: target`.
DEFINITION = re.compile(r"^\s{0,3}\[(?P<label>[^\]]+)\]:\s*(?P<target>\S+)")

#: Reference link use: `[text][label]`, or `[label][]`.
REFERENCE_USE = re.compile(r"\[(?P<text>[^\]]*)\]\[(?P<label>[^\]]*)\]")

#: ADR citation in the body of the text.
ADR_CITATION = re.compile(r"\bADR-(?P<number>\d{4})\b")

#: Schemes that do not resolve on disk.
EXTERNAL = ("http://", "https://", "mailto:", "ftp://")

#: A link into mvp_eng_dados_1. `ref` must be a commit, so that the fact it cites
#: cannot move under the link; `path` may be empty for the root of the tree.
ENG_DADOS_LINK = re.compile(
    r"^https://github\.com/alencardoug/mvp_eng_dados_1/(?P<kind>blob|tree)/(?P<ref>[^/#]+)/?(?P<path>[^#]*)(?:#(?P<fragment>.*))?$"
)

#: Documents whose bare `ADR-nnnn` are upstream's. `REVIEW.md` records the
#: review of this plan against mvp_eng_dados_1, and its reviewers cite that
#: project's ADRs by number, as recorded; the record is not rewritten to suit
#: the check. Its links are still checked.
UPSTREAM_ADR_DOCUMENTS = {"REVIEW.md"}

#: A commit, abbreviated or full. A branch or tag name is not a pin.
COMMIT = re.compile(r"^[0-9a-f]{7,40}$")

#: Inline markup GitHub removes before generating the slug. The slug comes from
#: the **rendered** text, so backtick, asterisk and tilde always go.
EMPHASIS = re.compile(r"[`*~]")

#: The underscore is another case: `_emphasis_` goes because it is markup, but
#: that of `snake_case` **stays** — inside a word it is no emphasis at all.
#: Removing both would generate an anchor GitHub does not generate.
EMPHASIS_UNDERSCORE = re.compile(r"(?<!\w)_|_(?!\w)")
LINK_IN_HEADING = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def slug(heading: str) -> str:
    """The identifier GitHub generates for a heading.

    Accents stay: `## 8. Retenção` becomes `8-retenção`.
    """
    text = LINK_IN_HEADING.sub(r"\1", heading)
    text = EMPHASIS_UNDERSCORE.sub("", EMPHASIS.sub("", text)).strip().lower()
    # Normalise composition, so that `ç` written as `c` + cedilla and a
    # precomposed `ç` give the same slug — both exist in files edited by
    # different tools.
    text = unicodedata.normalize("NFC", text)
    text = "".join(c for c in text if c.isalnum() or c in " -_")
    return text.replace(" ", "-")


@dataclass(frozen=True)
class Broken:
    file: str
    line: int
    target: str
    reason: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line}: {self.target} — {self.reason}"


@dataclass
class Document:
    path: pathlib.Path
    relative: str
    #: the anchors its headings generate, with the suffix of repeated ones
    anchors: set[str]
    #: reference label → target
    definitions: dict[str, str]
    #: (line, target) of each link
    links: list[tuple[int, str]]
    #: (line, number) of each ADR cited
    adrs: list[tuple[int, str]]


def _outside_code(text: str):
    """Yields `(number, line)`, skipping what is inside a code fence.

    The GFM rule: a block closes only on a fence of the **same** character, of
    equal or greater length, with nothing after it. Inside a four-backtick fence,
    three backticks are content (RVF12-06). A backtick on the opening line of a
    backtick fence is inline code, not a fence.

    **Indentation counts, against the column of the list item** (RVF12-2-06).
    The fence opens and closes with up to three spaces beyond the column where
    the item's content starts — zero outside a list. A line indented less than
    the item ends the item, and the block with it. **Declared limits:** tabs,
    block quotes (`>`), an item that opens with the fence itself and indented
    blocks with no fence are not read; the error there is flagging an example,
    not hiding one.
    """
    widths: list[int] = []  # the content column of each open list item
    open_fence: tuple[str, int] | None = None  # the fence and the item column it opened at
    for number, line in enumerate(text.splitlines(), start=1):
        indent = len(line) - len(line.lstrip(" "))
        if open_fence is not None:
            fence_open, base = open_fence
            if not line.strip():
                continue
            if indent >= base:
                fence = FENCE.match(line)
                if (
                    fence
                    and indent - base <= 3
                    and fence["fence"][0] == fence_open[0]
                    and len(fence["fence"]) >= len(fence_open)
                    and not fence["rest"].strip()
                ):
                    open_fence = None
                continue
            open_fence = None
        if line.strip():
            while widths and indent < widths[-1]:
                widths.pop()
        base = widths[-1] if widths else 0
        fence = FENCE.match(line)
        if (
            fence
            and indent - base <= 3
            and not (fence["fence"][0] == "`" and "`" in fence["rest"])
        ):
            open_fence = (fence["fence"], base)
            continue
        item = LIST_ITEM.match(line)
        if item:
            after = line[item.end():]
            spaces = len(after) - len(after.lstrip(" "))
            widths.append(item.end() + (spaces if after.strip() and spaces <= 4 else 1))
        yield number, line


def _without_inline_code(line: str) -> str:
    """The line with each inline code span replaced by a space.

    In GFM inline code takes precedence over links — `` `[x](y.md)` `` shows the
    syntax, it points at nothing (RVF12-2-05). A link whose text is code is still
    a link.

    Reading goes left to right, as in GFM (RVF12-3-02). Outside code, a
    backslash escapes the next character. A run of backticks closes only on
    another of the **same** length, and inside code the backslash is literal.
    The code becomes a space, not nothing: deleting it would join `[x]`, the
    code and `(y.md)` into a link that did not exist.
    """
    parts: list[str] = []
    i = 0
    while i < len(line):
        if line[i] == "\\":
            parts.append(line[i : i + 2])
            i += 2
        elif line[i] == "`":
            end = i
            while end < len(line) and line[end] == "`":
                end += 1
            closing = re.compile(rf"(?<!`){'`' * (end - i)}(?!`)").search(line, end)
            if closing:
                parts.append(" ")
                i = closing.end()
            else:
                parts.append(line[i:end])
                i = end
        else:
            parts.append(line[i])
            i += 1
    return "".join(parts)


def read_text(text: str, path: pathlib.Path, relative: str) -> Document:
    #: anchor already emitted → last suffix used from it
    seen: dict[str, int] = {}
    anchors: set[str] = set()
    definitions: dict[str, str] = {}
    links: list[tuple[int, str]] = []
    adrs: list[tuple[int, str]] = []

    for number, line in _outside_code(text):
        heading = HEADING.match(line)
        if heading:
            # The `github-slugger` algorithm: every emitted anchor stays
            # reserved, suffixed ones included. `X`, `X`, `X-1` give `x`, `x-1`
            # and `x-1-1` (RVF12-05). The heading is also text: links and ADR
            # citations in it count as on any line (RVF12-04).
            base = slug(heading.group(2))
            anchor = base
            while anchor in seen:
                seen[base] += 1
                anchor = f"{base}-{seen[base]}"
            seen[anchor] = 0
            anchors.add(anchor)

        definition = DEFINITION.match(line)
        if definition:
            definitions[definition.group("label").lower()] = definition.group("target")
            continue

        without_code = _without_inline_code(line)
        for match in LINK.finditer(without_code):
            links.append((number, match.group("target")))
        for match in REFERENCE_USE.finditer(without_code):
            label = (match.group("label") or match.group("text")).lower()
            links.append((number, f"[[ref:{label}]]"))
        # An ADR cited as the text of an external link is that link's ADR —
        # `[ADR-0018](https://…/mvp_eng_dados_1/…)` is upstream's, and the link
        # check verifies it. Only the others must exist in `docs/adr/` here.
        local = LINK.sub(
            lambda m: " " if m["target"].startswith(EXTERNAL) else m[0], line
        )
        for match in ADR_CITATION.finditer(local):
            adrs.append((number, match.group("number")))

    return Document(path, relative, anchors, definitions, links, adrs)


def read(path: pathlib.Path, relative: str) -> Document:
    return read_text(path.read_text(encoding="utf-8"), path, relative)


def _documents(root: pathlib.Path) -> dict[str, Document]:
    output = subprocess.run(
        ["git", "ls-files", "-z", "*.md"], cwd=root, capture_output=True, text=True, check=True
    ).stdout
    relatives = [c for c in output.split("\0") if c]
    return {r: read(root / r, r) for r in relatives if (root / r).is_file()}


class EngDados:
    """Files of mvp_eng_dados_1 at a commit, read from a local checkout.

    `git cat-file` reads the object database, so the checkout's working tree and
    current branch do not matter — only that it has fetched the commit.
    """

    def __init__(self, checkout: pathlib.Path) -> None:
        self.checkout = checkout
        self._documents: dict[tuple[str, str], Document | None] = {}

    def _git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.checkout), *args], capture_output=True, text=True
        )

    def kind(self, ref: str, path: str) -> str | None:
        """`blob`, `tree`, or `None` when the path does not exist at that commit."""
        result = self._git("cat-file", "-t", f"{ref}:{path}")
        return result.stdout.strip() if result.returncode == 0 else None

    def document(self, ref: str, path: str) -> Document | None:
        if (ref, path) not in self._documents:
            result = self._git("show", f"{ref}:{path}")
            self._documents[(ref, path)] = (
                read_text(result.stdout, pathlib.Path(path), path) if result.returncode == 0 else None
            )
        return self._documents[(ref, path)]


def _check_eng_dados(
    match: re.Match[str], eng_dados: EngDados | None
) -> str | None:
    """Why a link into mvp_eng_dados_1 is broken, `""` when not verified, `None` when good."""
    ref, path = match["ref"], unquote(match["path"]).rstrip("/")
    fragment = unquote(match["fragment"] or "")
    if not COMMIT.match(ref):
        return f"not pinned: `{ref}` is not a commit, so the fact it cites can move"
    if eng_dados is None:
        return ""
    kind = eng_dados.kind(ref, path) if path else eng_dados.kind(ref, "")
    if kind is None:
        return f"does not exist in mvp_eng_dados_1 at {ref}"
    if fragment and path.lower().endswith(".md"):
        document = eng_dados.document(ref, path)
        if document is None or fragment not in document.anchors:
            return f"heading does not exist in {path} at {ref}"
    return None


def check(
    root: pathlib.Path, eng_dados: EngDados | None = None
) -> tuple[list[Broken], dict[str, int], list[Broken]]:
    """Checks every tracked `.md`. Returns broken, the counts and the links not verified."""
    documents = _documents(root)
    broken: list[Broken] = []
    unverified: list[Broken] = []
    counts = {"documents": len(documents), "links": 0, "anchors": 0, "adrs": 0, "eng_dados": 0}

    existing_adrs = {
        file.name[:4] for file in (root / "docs" / "adr").glob("[0-9][0-9][0-9][0-9]-*.md")
    }

    for relative, document in documents.items():
        folder = document.path.parent
        for number, target in document.links:
            if target.startswith("[[ref:"):
                label = target[len("[[ref:") : -2]
                if label not in document.definitions:
                    broken.append(Broken(relative, number, f"[{label}]", "reference with no definition"))
                    continue
                target = document.definitions[label]

            upstream = ENG_DADOS_LINK.match(target)
            if upstream:
                counts["eng_dados"] += 1
                reason = _check_eng_dados(upstream, eng_dados)
                if reason == "":
                    unverified.append(Broken(relative, number, target, "ENG_DADOS_DIR not set"))
                elif reason is not None:
                    broken.append(Broken(relative, number, target, reason))
                continue

            if target.startswith(EXTERNAL):
                continue

            path, _, fragment = target.partition("#")
            fragment = unquote(fragment)

            if not path:  # anchor in the same document
                counts["anchors"] += 1
                if fragment not in document.anchors:
                    broken.append(Broken(relative, number, f"#{fragment}", "heading does not exist in this file"))
                continue

            counts["links"] += 1
            destination = (folder / unquote(path)).resolve()
            try:
                key = str(destination.relative_to(root.resolve()))
            except ValueError:
                broken.append(Broken(relative, number, target, "points outside the repository"))
                continue

            if not destination.exists():
                broken.append(Broken(relative, number, target, "file does not exist"))
                continue

            if fragment:
                counts["anchors"] += 1
                target_document = documents.get(key)
                if target_document is None:
                    if destination.suffix.lower() == ".md":
                        broken.append(Broken(relative, number, target, "target is not a tracked document"))
                elif fragment not in target_document.anchors:
                    broken.append(Broken(relative, number, target, f"heading does not exist in {key}"))

        for number, adr_number in [] if relative in UPSTREAM_ADR_DOCUMENTS else document.adrs:
            counts["adrs"] += 1
            if adr_number not in existing_adrs:
                broken.append(Broken(relative, number, f"ADR-{adr_number}", "does not exist in docs/adr/"))

    return broken, counts, unverified


def main(argv: list[str] | None = None) -> int:
    root = pathlib.Path(argv[0]) if argv else pathlib.Path.cwd()
    checkout = os.environ.get("ENG_DADOS_DIR")
    eng_dados = EngDados(pathlib.Path(checkout)) if checkout else None
    broken, counts, unverified = check(root, eng_dados)

    summary = (
        f"{counts['documents']} documents, {counts['links']} file links, "
        f"{counts['anchors']} anchors, {counts['adrs']} ADR citations, "
        f"{counts['eng_dados']} links into mvp_eng_dados_1"
    )
    if unverified:
        print(
            f"not verified ({len(unverified)}) — set ENG_DADOS_DIR to a checkout of mvp_eng_dados_1:",
            file=sys.stderr,
        )
        for link in unverified:
            print(f"  {link.file}:{link.line}: {link.target}", file=sys.stderr)
    if broken:
        for link in broken:
            print(link, file=sys.stderr)
        print(f"\ndocs-check: {len(broken)} broken of {summary}", file=sys.stderr)
        return 1
    print(f"docs-check: {summary} — nothing broken" + (f", {len(unverified)} not verified" if unverified else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
