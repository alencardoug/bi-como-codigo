"""The carrier inspection of stage 2.3 (docs/framework_prototype.md §2.5.2).

Reads a set of files — a builder output, an artifact, or what the browser
diagnostic collects — and names the carrier of any fixture value it finds,
with the decoding path and never the value. Numbers are compared by role:
code-bearing files are searched for texts and amounts, and for the counts
only inside a structured carrier found in them; data-bearing carriers for
everything, the counts in any spelling.

What no layer reads is inconclusive, never clean. The draw of §2.1 calls the
same dispatch (`inspect_items`), so that what it calibrates is exactly what is
later inspected; `gate_hits` is the gate's own substring search, every hit
listed instead of the first.
"""

from __future__ import annotations

import base64
import binascii
import dataclasses
import gzip
import hashlib
import html
import io
import json
import pathlib
import re
import struct
import sys
import urllib.parse
import zlib
from decimal import Decimal, InvalidOperation

import fixture as fx_mod
from bi_como_codigo import contract as c, envelope as e

INSPECT_TEXT = "INSPECT_TEXT"
INSPECT_NUMBER = "INSPECT_NUMBER"
INSPECT_CALENDAR = "INSPECT_CALENDAR"
INSPECT_ARROW = "INSPECT_ARROW"
INSPECT_PARQUET = "INSPECT_PARQUET"
INSPECT_BINARY = "INSPECT_BINARY"

DEPTH = 3
CODE = "code"
DATA = "data"
COLLECTED = "collected"  # a data-bearing carrier of the browser diagnostic: the calendar too

#: What is served as the page itself (§2.5.2); anything else is data-bearing.
CODE_SUFFIXES = frozenset({
    ".html", ".htm", ".js", ".mjs", ".cjs", ".css", ".wasm", ".woff", ".woff2", ".ttf", ".otf",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp", ".avif",
})


# --- the needles ------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Needles:
    texts: frozenset[str]
    amounts: frozenset[Decimal]
    counts: frozenset[int]
    window: frozenset[tuple[int, int]]
    gate: tuple[tuple[str, bytes], ...] = ()  # `contract.needles` of the opened payload, for the manifest's labels

    @classmethod
    def from_fixture(cls, fx: fx_mod.Fixture, *, gate: bool = True) -> "Needles":
        """The fixture's values and the results of the page's queries — every
        summary cell under every filter — since a cache of a query holds results,
        not rows. Small integers are never integer needles (FPROTO-4-03)."""
        texts: set[str] = set()
        for row in fx.rows():
            texts |= {v for v in row if isinstance(v, str) and len(v) >= 3}
        amounts: set[Decimal] = set()
        counts: set[int] = {len(fx.cells)}
        for m in fx.cells.values():
            amounts |= {m.gross, m.discount, m.net}
            counts |= {m.order_count, m.unit_count}
        for net, units in fx_mod.summary(fx).values():
            amounts.add(net)
            counts.add(units)
        amounts |= {sum((m.gross for m in fx.cells.values()), fx_mod.ZERO),
                    sum((m.discount for m in fx.cells.values()), fx_mod.ZERO),
                    sum((m.net for m in fx.cells.values()), fx_mod.ZERO)}
        counts.add(sum(m.unit_count for m in fx.cells.values()))
        amounts.discard(fx_mod.ZERO)
        counts = {n for n in counts if n >= 10_000}
        window = {fx.month(i) for i in range(fx_mod.MONTHS)}
        gate_needles: tuple = ()
        if gate:
            contract = fx_mod.contract()
            values = c.check_payload(contract, contract.reports[fx_mod.REPORT], *fx_mod.payload(fx))
            public = c.load_public_values((fx_mod.HERE / "release" / "public_values.json").read_bytes())
            gate_needles = tuple(c.needles([values], public))
        return cls(frozenset(texts), frozenset(amounts), frozenset(counts), frozenset(window), gate_needles)

    def canonical(self, value) -> str:
        return str(value)


# --- the report --------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Finding:
    code: str
    file: str
    path: str
    value: str | None = dataclasses.field(default=None, repr=False, compare=False)  # for the draw only, never recorded

    def record(self) -> dict:
        return {"code": self.code, "file": self.file, "path": self.path}


@dataclasses.dataclass(frozen=True)
class Note:
    file: str
    path: str
    reason: str

    def record(self) -> dict:
        return dataclasses.asdict(self)


@dataclasses.dataclass
class Report:
    findings: list[Finding] = dataclasses.field(default_factory=list)
    inconclusive: list[Note] = dataclasses.field(default_factory=list)
    recorded: list[Note] = dataclasses.field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.findings and not self.inconclusive

    def codes(self) -> set[str]:
        return {f.code for f in self.findings}

    def record(self) -> dict:
        unique = list({(f.code, f.file, f.path): f for f in self.findings}.values())
        return {"findings": [f.record() for f in unique], "inconclusive": [n.record() for n in self.inconclusive],
                "recorded": [n.record() for n in self.recorded]}


@dataclasses.dataclass(frozen=True)
class Item:
    """One carrier: a file of an output, or a value the browser collected."""

    name: str
    data: bytes
    role: str | None = None  # None: by the name's suffix
    url: str | None = None  # a body fetched from this URL


# --- the inspection ---------------------------------------------------------------------


@dataclasses.dataclass
class Context:
    needles: Needles
    validated: dict[str, str]  # path → SHA-256 of the validated package's files
    cdn: dict[str, str]  # URL → SHA-256 of the pinned third-party bodies
    dependencies: frozenset[str]  # SHA-256 of every file of the locked dependency tree
    report: Report
    _binary: dict | None = None
    #: Each JSON script read whole, as each flat decoder turns it, keyed by the file, the text it was
    #: read in and its attributes: a script that breaks on a flat layer is explained only when it is
    #: one of these — the same script of the same file, reached from that text by flat layers alone,
    #: with the same attributes (CMP-1-06, CMP-2-03).
    read_scripts: set = dataclasses.field(default_factory=set)

    def find(self, code, file, path, value=None):
        self.report.findings.append(Finding(code, file, path, None if value is None else str(value)))


def inspect_dir(root: pathlib.Path, needles: Needles, *, validated: dict[str, str] | None = None,
                cdn: dict[str, str] | None = None, dependencies: frozenset[str] = frozenset()) -> Report:
    import trees

    items = [Item(rel, data) for rel, data in sorted(trees.files(root).items())]  # checked root, no link followed, a walk never incomplete
    return inspect_items(items, needles, validated=validated, cdn=cdn, dependencies=dependencies)


def inspect_items(items: list[Item], needles: Needles, *, validated: dict[str, str] | None = None,
                  cdn: dict[str, str] | None = None, dependencies: frozenset[str] = frozenset()) -> Report:
    ctx = Context(needles, validated or {}, cdn or {}, dependencies, Report())
    for item in items:
        _item(ctx, item)
    return ctx.report


def _role_of(name: str) -> str:
    return CODE if pathlib.PurePosixPath(name).suffix.lower() in CODE_SUFFIXES else DATA


def _item(ctx: Context, item: Item) -> None:
    digest = hashlib.sha256(item.data).hexdigest()
    if item.url is not None and item.url in ctx.cdn:
        if ctx.cdn[item.url] == digest:
            ctx.report.recorded.append(Note(item.name, item.url, "pinned third-party body"))
        else:
            ctx.report.inconclusive.append(Note(item.name, item.url, "a body at a declared URL with another digest"))
        return
    if item.name.startswith("package/") and ctx.validated.get(item.name[len("package/"):]) == digest:
        if item.name == "package/manifest.json":
            labels = c.manifest_labels(e.validate_manifest(item.data))
            for code, needle in ctx.needles.gate:  # the gate's own search, as N83 has it, behind any form refusal
                if needle in labels:
                    ctx.find(INSPECT_TEXT, item.name, "manifest labels > the gate's needles", needle.decode("utf-8", "replace"))
            _blob(ctx, labels, item.name, "manifest labels", DATA, 0, speculative=False)
            ctx.report.recorded.append(Note(item.name, "", "validated manifest: labels searched, typed fields validated"))
        else:
            ctx.report.recorded.append(Note(item.name, "", "validated envelope"))
        return
    _blob(ctx, item.data, item.name, item.name, item.role or _role_of(item.name), 0, speculative=False, digest=digest)


def _is_text(data: bytes) -> str | None:
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None


def _blob(ctx: Context, data: bytes, file: str, path: str, role: str, depth: int, *, speculative: bool,
          digest: str | None = None, flat: bool = False) -> None:
    if data[:4] == b"PAR1" and data[-4:] == b"PAR1" and len(data) >= 12:
        if _parquet(ctx, data, file, path, depth):
            return
    if data[:6] == b"ARROW1" or data[:4] == b"\xff\xff\xff\xff":
        if _arrow(ctx, data, file, path, depth):
            return
    decompressed = _decompress_by_magic(data)
    if decompressed is not None:
        # The compressed bytes keep what their format stores in the clear — a
        # gzip header's file name, comment and extra field — and are searched
        # as bytes beside what they decode to (PROTO-5-08).
        for needle in ctx.needles.texts:
            if needle.encode("utf-8") in data:
                ctx.find(INSPECT_TEXT, file, f"{path} > compressed bytes", needle)
        for name, out in decompressed:
            if "incomplete" in name:
                ctx.report.inconclusive.append(Note(file, f"{path} > {name}", "a compressed frame that ends before its end"))
            if out:
                _descend(ctx, out, file, f"{path} > {name}", role, depth, speculative=False)
        return
    # The byte checks run on every blob, binary included, before any exemption (PROTO-1-05).
    for needle in ctx.needles.texts:
        if needle.encode("utf-8") in data:
            ctx.find(INSPECT_TEXT, file, path, needle)
    _binary_numbers(ctx, data, file, path)
    text = _is_text(data)
    if text is not None:
        _text(ctx, text, file, path, role, depth, flat=flat)
        return
    _numbers_in_text(ctx, data.decode("latin-1"), file, path, role)
    for name, attempt in (("brotli", _brotli), ("deflate", _raw_deflate)):
        out = attempt(data)
        if out is not None:
            _descend(ctx, out, file, f"{path} > {name}", role, depth, speculative=speculative)
            return
    if _arrow(ctx, data, file, path, depth):  # a stream with no continuation marker, speculative or not (PROTO-2-05)
        return
    if speculative:
        return  # a speculative decoding no layer reads: an identifier, not a carrier
    if (digest or hashlib.sha256(data).hexdigest()) in ctx.dependencies:
        ctx.report.recorded.append(Note(file, path, "binary identical to a file of the locked dependency tree"))
    else:
        ctx.report.inconclusive.append(Note(file, path, "a binary no layer decodes"))


def _looks_like_carrier(data: bytes) -> bool:
    """What a layer would read, at the depth where none may run any more: a
    magic, a layer with no magic, a JSON document — whole or embedded in other
    text, as the dispatcher reads it —, or an encoded run whose decoding is
    itself readable (PROTO-2-05, PROTO-4-05). A base64-shaped identifier that
    decodes to bytes nothing reads is no layer."""
    if _decompress_by_magic(data) is not None or data[:4] in (b"PAR1", b"\xff\xff\xff\xff") or data[:6] == b"ARROW1":
        return True
    text = _is_text(data)
    if text is None:  # the layers with no magic, too (PROTO-2-05)
        return _brotli(data) is not None or _raw_deflate(data) is not None or _arrow_opens(data)
    stripped = text.strip()
    if stripped[:1] in "{[":
        try:
            json.loads(stripped)
            return True
        except ValueError:
            pass
    if _has_embedded_json(text):
        return True
    # Every encoded run the dispatcher would decode, wherever it sits in the
    # text — a body inside a bundle too (PROTO-5-06) —, counts when what it
    # decodes to is itself readable; an identifier decoding to bytes nothing
    # reads does not (PROTO-4-05).
    for name, out in _text_decoders(text):
        if name.startswith(("base64", "hex")) and _readable(out):
            return True
    return False


def _readable(out: bytes) -> bool:
    """Bytes a layer of the dispatcher would open, or text."""
    if _decompress_by_magic(out) is not None or out[:4] == b"PAR1" or out[:6] == b"ARROW1" or out[:4] == b"\xff\xff\xff\xff":
        return True
    text = _is_text(out)
    if text is None:  # Brotli has no magic: it counts only when it opens to text
        opened = _brotli(out) if len(out) >= 16 else None
        return opened is not None and _is_text(opened) is not None and len(opened) >= 16
    printable = sum(ch.isprintable() or ch in "\n\r\t" for ch in text)
    return len(text) >= 16 and printable >= 0.95 * len(text)


def _has_embedded_json(text: str) -> bool:
    decoder = json.JSONDecoder()
    for tries, m in enumerate(_EMBEDDED.finditer(text)):
        if tries >= 1000:
            return True  # as the dispatcher: more openings than it reads is no clean result
        try:
            parsed, _ = decoder.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(parsed, (dict, list)) and parsed:
            return True
    return False


def _search_only(ctx: Context, data: bytes, file: str, path: str, role: str) -> None:
    """The byte and number searches of a blob, with no layer opened."""
    for needle in ctx.needles.texts:
        if needle.encode("utf-8") in data:
            ctx.find(INSPECT_TEXT, file, path, needle)
    _binary_numbers(ctx, data, file, path)
    text = _is_text(data)
    _numbers_in_text(ctx, text if text is not None else data.decode("latin-1"), file, path, role)


def _flat_text_decoders(text: str):
    """The decoders of `_text_decoders` whose output is the same text unescaped."""
    for name, out in _text_decoders(text):
        if name in ("percent", "escapes", "entities") and out != text.encode("utf-8", "surrogatepass"):
            yield name, out


def _descend(ctx: Context, data: bytes, file: str, path: str, role: str, depth: int, *, speculative: bool,
             flat: bool = False) -> None:
    if depth + 1 > DEPTH:
        # Past the depth, the bytes are still searched; only no further layer is opened.
        _search_only(ctx, data, file, path, role)
        text = _is_text(data)
        unread = not speculative or _looks_like_carrier(data)
        if text is not None:
            # The text decoders that open no further layer — percent, escapes,
            # entities — are read here, searched only; one whose output would
            # itself open is a layer unread (PROTO-3-06).
            for name, out in _flat_text_decoders(text):
                _search_only(ctx, out, file, f"{path} > {name}", role)
                unread = unread or _looks_like_carrier(out)
        if unread:
            ctx.report.inconclusive.append(Note(file, path, f"deeper than {DEPTH} layers"))
        return
    _blob(ctx, data, file, path, role, depth + 1, speculative=speculative, flat=flat)


# --- decoders ---------------------------------------------------------------------------


def _skippable(data: bytes) -> int | None:
    """The length of a zstd skippable frame at the start of `data` — magic
    0x184D2A50 to 0x184D2A5F, a 4-byte size, that many bytes —, or None."""
    if len(data) < 8 or data[1:4] != b"\x2a\x4d\x18" or data[0] & 0xF0 != 0x50:
        return None
    size = int.from_bytes(data[4:8], "little")
    return 8 + size if 8 + size <= len(data) else None


def _decompress_by_magic(data: bytes) -> list[tuple[str, bytes]] | None:
    """Every frame of a zstd stream, every member of a gzip file, and what
    follows a zlib stream, read as its own blob (PROTO-1-05)."""
    try:
        if data[:2] == b"\x1f\x8b":
            # Member by member; a member that ends before its end gives what it
            # holds and is said so — the encoding is established by its header
            # (PROTO-5-08).
            outs, rest = [], data
            while rest[:2] == b"\x1f\x8b":
                d = zlib.decompressobj(31)
                outs.append(d.decompress(rest))
                if not d.eof:
                    return [("gzip, incomplete member", b"".join(outs))]
                rest = d.unused_data
            return [("gzip", b"".join(outs))] + ([("after gzip", rest)] if rest else [])
        if len(data) >= 2 and data[0] == 0x78 and (data[0] * 256 + data[1]) % 31 == 0:
            d = zlib.decompressobj()
            out = d.decompress(data) + d.flush()
            if not d.eof:
                return None
            return [("zlib", out)] + ([("after zlib", d.unused_data)] if d.unused_data else [])
        if data[:4] == b"\x28\xb5\x2f\xfd" or _skippable(data) is not None:
            import zstandard

            # Frame by frame, so that a frame not read to its end is said so
            # (PROTO-2-05); the frames are one byte stream (RFC 8878 §3.1), read
            # as one blob, so that a value split across two frames is found
            # (PROTO-3-05).
            outs, remaining, complete, skipped = [], data, True, []
            while remaining[:4] == b"\x28\xb5\x2f\xfd" or _skippable(remaining) is not None:
                skip = _skippable(remaining)
                if skip is not None:  # no stream data (RFC 8878 §3.1.2; PROTO-4-08), but bytes it keeps (PROTO-5-08)
                    skipped.append(remaining[8:skip])
                    remaining = remaining[skip:]
                    continue
                obj = zstandard.ZstdDecompressor().decompressobj()
                outs.append(obj.decompress(remaining))
                if not obj.eof:
                    complete, remaining = False, b""
                    break
                remaining = obj.unused_data
            parts = [("zstd" if complete else "zstd, incomplete frame", b"".join(outs))]
            parts += [(f"zstd skippable#{i}", payload) for i, payload in enumerate(skipped) if payload]
            return parts + ([("after zstd", remaining)] if remaining else [])
    except Exception:  # noqa: BLE001 — a magic that does not decode is no carrier
        return None
    return None


def _brotli(data: bytes) -> bytes | None:
    import brotli

    try:
        out = brotli.decompress(data)
    except Exception:  # noqa: BLE001
        return None
    return out or None


def _raw_deflate(data: bytes) -> bytes | None:
    try:
        d = zlib.decompressobj(-15)
        out = d.decompress(data) + d.flush()
    except zlib.error:
        return None
    return out if d.eof and not d.unused_data and out else None


_B64 = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")
_B64URL = re.compile(r"[A-Za-z0-9_-]{16,}={0,2}")
_HEX = re.compile(r"(?:[0-9a-fA-F]{2}){16,}")
_PERCENT = re.compile(r"%[0-9A-Fa-f]{2}")
_ESCAPE = re.compile(r"\\(u[0-9a-fA-F]{4}|u\{[0-9a-fA-F]+\}|x[0-9a-fA-F]{2}|[nrt\"'\\/])")
_ENTITY = re.compile(r"&(#[0-9]+|#[xX][0-9a-fA-F]+|[A-Za-z]+);")


def _b64(run: str, alphabet: str) -> bytes | None:
    body = run.rstrip("=")
    if len(body) % 4 == 1:
        return None
    padded = body + "=" * (-len(body) % 4)
    try:
        return base64.b64decode(padded, altchars=b"-_" if alphabet == "url" else None, validate=True)
    except (binascii.Error, ValueError):
        return None


def _unescape(text: str) -> str:
    simple = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "'": "'", "\\": "\\", "/": "/"}

    def one(m: re.Match) -> str:
        s = m[1]
        if s.startswith("u{"):
            return chr(int(s[2:-1], 16))
        if s[0] in "ux":
            return chr(int(s[1:], 16))
        return simple[s]

    return _ESCAPE.sub(one, text)


def _text_decoders(text: str):
    seen: set[str] = set()
    for alphabet, pattern in (("std", _B64), ("url", _B64URL)):
        for m in pattern.finditer(text):
            if m[0] in seen:
                continue
            seen.add(m[0])
            out = _b64(m[0], alphabet)
            if out:
                yield f"base64{'url' if alphabet == 'url' else ''}@{m.start()}", out
    for m in _HEX.finditer(text):
        yield f"hex@{m.start()}", bytes.fromhex(m[0])
    if _PERCENT.search(text):
        yield "percent", urllib.parse.unquote_to_bytes(text)
    if _ESCAPE.search(text):
        try:
            yield "escapes", _unescape(text).encode("utf-8", "surrogatepass")
        except (ValueError, OverflowError):
            pass
    if _ENTITY.search(text):
        yield "entities", html.unescape(text).encode("utf-8", "surrogatepass")


# --- text and numbers -----------------------------------------------------------------


_SEPARATORS = ".,\u00a0\u202f\u2009"
_RUN = re.compile(r"[0-9](?:[0-9.,\u00a0\u202f\u2009]*[0-9])?")
_EXPONENT = re.compile(r"(?<![0-9A-Za-z_.])([-\u2212]?)((?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)[eE][+-]?[0-9]+)(?![0-9])")  # `.2e5`, `20000.e-5` (PROTO-4-07)
_PLAIN = re.compile(r"[0-9]+")
_DOTTED = re.compile(r"[0-9]+\.[0-9]+")
_PT_GROUPED = re.compile(r"[0-9]{1,3}(?:\.[0-9]{3})+")
_PT_DECIMAL = re.compile(r"[0-9]{1,3}(?:\.[0-9]{3})*,[0-9]+")
_COMMA_DECIMAL = re.compile(r"[0-9]+,[0-9]+")
_EN_GROUPED = re.compile(r"[0-9]{1,3}(?:,[0-9]{3})+(?:\.[0-9]+)?")
_SPACE_GROUPED = re.compile(r"[0-9]{1,3}(?:[\u00a0\u202f\u2009][0-9]{3})+(?:[.,][0-9]+)?")
WINDOW = 4  # separators a token may span inside one run of digits and separators
_SPACED = re.compile(r"(?<![0-9])[0-9]+(?: [0-9]+)+(?:[.,][0-9]+)?(?![0-9])")  # digit groups an ordinary space apart


def _space_groupings(run: str) -> list[tuple[str, int]]:
    """The groupings inside digit groups an ordinary space apart, read from the
    left and each as long as it goes: a group of one to three digits followed
    by groups of exactly three. `2 20 000` holds `20 000`; `1 220 000` holds
    only `1 220 000` (PROTO-4-07). A decimal part after a comma stays with the
    last group."""
    mark = next((c for c in run if c in ".,"), ",")
    body, _, decimals = run.partition(mark)
    groups = body.split(" ")
    offsets, at = [], 0
    for g in groups:
        offsets.append(at)
        at += len(g) + 1
    out, i = [], 0
    while i < len(groups) - 1:
        if 1 <= len(groups[i]) <= 3 and len(groups[i + 1]) == 3:
            j = i + 1
            while j + 1 < len(groups) and len(groups[j + 1]) == 3:
                j += 1
            literal = " ".join(groups[i:j + 1]) + ("," + decimals if decimals and j == len(groups) - 1 else "")  # one decimal mark, read as a comma below
            out.append((literal, offsets[i]))
            i = j + 1
        else:
            i += 1
    return out


def _readings(token: str):
    """(value, how): `gate` when the token is a spelling of `contract.spellings`
    for an amount, `js` when it is only a shorter JavaScript spelling, `int`
    for an integer in any spelling."""
    out = []
    if _PLAIN.fullmatch(token):
        out.append((Decimal(token), "int"))
    if _DOTTED.fullmatch(token):
        out.append((Decimal(token), "gate" if len(token.split(".")[1]) == 2 else "js"))
    if _PT_GROUPED.fullmatch(token):
        out.append((Decimal(token.replace(".", "")), "int"))
    if _PT_DECIMAL.fullmatch(token):
        out.append((Decimal(token.replace(".", "").replace(",", ".")), "gate" if len(token.split(",")[1]) == 2 else "js"))
    if _COMMA_DECIMAL.fullmatch(token):
        out.append((Decimal(token.replace(",", ".")), "gate" if len(token.split(",")[1]) == 2 else "js"))
    if _EN_GROUPED.fullmatch(token):
        out.append((Decimal(token.replace(",", "")), "int"))
    if _SPACE_GROUPED.fullmatch(token):
        plain = re.sub("[\u00a0\u202f\u2009]", "", token).replace(",", ".")
        out.append((Decimal(plain), "int" if "." not in plain else "js"))
    return out


def _tokens(text: str):
    """Every window of a run of digits and separators that starts and ends on a
    digit and spans at most `WINDOW` separators — so that `1.234,50` is read
    inside `1.234,50,7` (PROTO-1-06) —, with whether a minus sign precedes it."""
    exponents = [(m.start(2), m.end(2)) for m in _EXPONENT.finditer(text)]
    for m in _RUN.finditer(text):
        # A scientific literal is read as one number below (PROTO-2-06); only
        # its own span leaves the run — `20000,2e-1` still reads 20000
        # (PROTO-3-08).
        pieces, cursor = [], m.start()
        for a, b in exponents:
            if b <= cursor or a >= m.end():
                continue
            pieces.append((cursor, max(cursor, a)))
            cursor = max(cursor, b)
        pieces.append((cursor, m.end()))
        for lo, hi in pieces:
            sub = _RUN.search(text, lo, hi)
            while sub is not None and sub.end() <= hi:
                yield from _windows(text, sub[0], sub.start())
                sub = _RUN.search(text, sub.end(), hi)


def _windows(text: str, run: str, start: int):
    """The windows of one run of digits and separators, with whether a minus
    sign precedes the run."""
    negative = start > 0 and text[start - 1] in "-\u2212" and not (start > 1 and text[start - 2].isalnum())
    seps = [i for i, ch in enumerate(run) if ch in _SEPARATORS]
    starts = [0] + [i + 1 for i in seps]
    ends = seps + [len(run)]
    for a, s0 in enumerate(starts):
        if a > 0 and _continues_grouping(run, starts, ends, a):
            continue
        for b in range(a, min(len(ends), a + WINDOW + 1)):
            token = run[s0:ends[b]]
            if token and token[0].isdigit() and token[-1].isdigit() and not _stops_short(run, starts, ends, a, b):
                yield token, negative and s0 == 0


def _stops_short(run: str, starts: list[int], ends: list[int], a: int, b: int) -> bool:
    """A window ending at group *b* stops short of its number when what
    follows completes it (PROTO-5-07): the next group continues a grouping —
    three digits after the same separator the window already groups with
    (`20 000 123` never holds `20 000`) —, or the window holds no decimal part
    and the next group, one or two digits after `.` or `,`, is one
    (`20000.50` never holds `20000`; `1.234,50,7` still holds `1.234,50`)."""
    if b + 1 >= len(starts):
        return False
    sep = run[ends[b]]
    following = run[starts[b + 1]:ends[b + 1]]
    if not following.isdigit():
        return False
    inner = [run[ends[k]] for k in range(a, b)]
    if len(following) == 3 and inner and sep == inner[-1]:
        return True
    decimal = bool(inner) and inner[-1] in ".," and len(run[starts[b]:ends[b]]) != 3  # `1.234,50` has one; `1.234` does not
    return sep in ".," and 1 <= len(following) <= 2 and not decimal


def _continues_grouping(run: str, starts: list[int], ends: list[int], a: int) -> bool:
    """A window starting at group *a* is no number of its own when that group is
    the continuation of a grouping: three digits, after a group of one to three
    digits, with the same separator before it and after it — `1 020 000` never
    holds `020 000`, `1.220.000` never `220.000`; `5,200.000` still holds
    `200.000` (PROTO-4-07)."""
    group = run[starts[a]:ends[a]]
    previous = run[starts[a - 1]:ends[a - 1]]
    if len(group) != 3 or not group.isdigit() or not (1 <= len(previous) <= 3 and previous.isdigit()):
        return False
    before = run[starts[a] - 1]
    after = run[ends[a]] if ends[a] < len(run) else None
    return after == before


def _numbers_in_text(ctx: Context, text: str, file: str, path: str, role: str) -> None:
    n = ctx.needles
    for token, negative in _tokens(text):
        if negative:
            continue  # every needle is positive: -20000 is not 20000
        for value, how in _readings(token):
            _match(ctx, value, how, file, path, role)
    for m in _EXPONENT.finditer(text):
        if not m[1]:
            try:
                value = Decimal(m[2])
            except InvalidOperation:
                continue
            if value.is_finite() and abs(value.adjusted()) <= 30:  # an exponent never becomes a huge integer
                _match(ctx, value, "exponent", file, path, role)
    for m in _SPACED.finditer(text):  # "20 000": grouping by an ordinary space (PROTO-2-06)
        for literal, at in _space_groupings(m[0]):
            start = m.start() + at
            if not (start > 0 and text[start - 1] in "-\u2212"):
                _match(ctx, Decimal(literal.replace(" ", "").replace(",", ".")), "int" if "," not in literal else "js", file, path, role)


def _match(ctx: Context, value: Decimal, how: str, file: str, path: str, role: str) -> None:
    n = ctx.needles
    if value in n.amounts:
        ctx.find(INSPECT_TEXT if how == "gate" else INSPECT_NUMBER, file, path, _canonical_amount(n, value))
    if how in ("int", "exponent") and role != CODE and value == value.to_integral_value() and int(value) in n.counts:
        ctx.find(INSPECT_NUMBER, file, path, int(value))


_EMBEDDED = re.compile(r'\{\s*"|\[\s*[-0-9"\[{]')
EMBEDDED_MAX = 100_000


def _embedded_json(ctx: Context, text: str, file: str, path: str, depth: int) -> None:
    """A strict JSON document inside other text — an object in a bundle —,
    parsed and walked as a structured carrier, counts included (PROTO-1-06)."""
    decoder = json.JSONDecoder()
    end_of_last = -1
    for tries, m in enumerate(_EMBEDDED.finditer(text)):
        if tries >= EMBEDDED_MAX:
            ctx.report.inconclusive.append(Note(file, path, f"more than {EMBEDDED_MAX} JSON-like openings"))
            return
        if m.start() < end_of_last:
            continue
        try:
            parsed, end = decoder.raw_decode(text, m.start())
        except ValueError:
            continue
        if isinstance(parsed, (dict, list)) and parsed:
            _structured(ctx, parsed, file, f"{path} > embedded json@{m.start()}", DATA, depth)
            end_of_last = end


def _canonical_amount(n: Needles, value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'))}"


_DELIMITED = {".csv": ",", ".tsv": "\t"}


def _csv_fields(text: str, path: str) -> list[str] | None:
    """The fields of a file named as CSV or TSV, as the csv module reads them;
    None for any other text, or one that does not parse."""
    import csv
    import io as io_mod

    delimiter = next((d for ext, d in _DELIMITED.items() if path.lower().endswith(ext)), None)
    if delimiter is None:
        return None
    try:
        return [field for row in csv.reader(io_mod.StringIO(text), delimiter=delimiter) for field in row]
    except csv.Error:
        return None


#: The text decoders whose output is the same text unescaped (N99).
FLAT = ("percent", "escapes", "entities")


def _text(ctx: Context, text: str, file: str, path: str, role: str, depth: int, *, flat: bool = False) -> None:
    fields = _csv_fields(text, path)
    if fields is None:
        _numbers_in_text(ctx, text, file, path, role)
    else:  # a CSV gives its fields' boundaries: `20,000,123` is three numbers (PROTO-5-07)
        for n, field in enumerate(fields):
            _numbers_in_text(ctx, field, file, f"{path} > field#{n}", role)
    stripped = text.strip()
    parsed = None
    if stripped[:1] in "{[":
        try:
            parsed = json.loads(stripped)
        except ValueError:
            parsed = None
        if parsed is not None:
            _structured(ctx, parsed, file, f"{path} > json", role, depth)
    if parsed is None:
        _embedded_json(ctx, text, file, path, depth)
    if "<script" in text.lower():
        _scripts(ctx, text, file, path, role, depth, flat=flat)
    same = text.encode("utf-8", "surrogatepass")
    for name, out in _text_decoders(text):
        if out == same:
            continue  # a decoding that changes nothing is no layer: `&t;` is no entity (N99)
        _descend(ctx, out, file, f"{path} > {name}", role, depth, speculative=True, flat=name in FLAT)


_SCRIPT = re.compile(r"<script([^>]*)>(.*?)</script>", re.S | re.I)
_DEVALUE_NUMBER = re.compile(r"(?<=[:\[,(])\s*(-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?)(?=\s*[,\]})])")


def _scripts(ctx: Context, text: str, file: str, path: str, role: str, depth: int, *, flat: bool = False) -> None:
    """Inline scripts of an HTML page: SvelteKit's fetched-data scripts and JSON
    scripts parsed as JSON — with `data-b64`, their body base64 —; SvelteKit's
    devalue data read as JSON-like text, every number compared as a number.

    On a layer a flat decoder made (`flat`), a JSON script that does not parse
    is searched as a data-bearing carrier, every integer needle in any
    spelling. It is recorded, not inconclusive, only when it is a script the
    layer before read whole, as the unescaping turned it — `\\"` of a string
    turned into `"` (N99) —; one no layer read — a malformed script only an
    unescaping exposes — stays inconclusive (CMP-1-06)."""
    for n, m in enumerate(_SCRIPT.finditer(text)):
        attrs, body = m[1].lower(), m[2]
        where = f"{path} > script#{n}"
        if "data-sveltekit-fetched" in attrs or "application/json" in attrs:
            try:
                parsed = json.loads(body)
            except ValueError:
                if flat:
                    _numbers_in_text(ctx, body, file, f"{where} > as data", DATA)
                origin = _read_whole(ctx, file, path, attrs, body) if flat else None
                if origin is not None:
                    ctx.report.recorded.append(Note(file, where, "a JSON script an unescaping broke, searched as data"))
                    # unescaped again on the next flat layer, it is still the script read whole
                    _remember_script(ctx, file, origin, attrs, body)
                else:
                    ctx.report.inconclusive.append(Note(file, where, "a JSON script that does not parse"))
                continue
            _remember_script(ctx, file, path, attrs, body)
            if "data-b64" in attrs and not (isinstance(parsed, dict) and isinstance(parsed.get("body"), str)):
                ctx.report.inconclusive.append(Note(file, where, "a data-b64 script with no body to decode"))
            elif "data-b64" in attrs:
                raw = _b64(parsed["body"], "std")
                if raw is None:
                    ctx.report.inconclusive.append(Note(file, where, "a data-b64 body that does not decode"))
                else:
                    _descend(ctx, raw, file, f"{where} > base64", DATA, depth, speculative=False)
            _structured(ctx, parsed, file, f"{where} > json", DATA, depth)
        elif "__sveltekit" in body or "kit.start" in body:
            for num in _DEVALUE_NUMBER.finditer(body):
                _number(ctx, num[1], file, f"{where} > devalue", count_too=True)


def _flat_forms(text: str) -> dict[str, str]:
    """`text` as each flat decoder turns it; unchanged where a decoder does not apply."""
    forms = dict.fromkeys(FLAT, text)
    for name, out in _text_decoders(text):
        if name in FLAT:
            try:
                forms[name] = out.decode("utf-8", "surrogatepass")
            except UnicodeDecodeError:
                forms.pop(name)
    return forms


def _remember_script(ctx: Context, file: str, origin: str, attrs: str, body: str) -> None:
    """A JSON script read whole in the text at `origin`: what each flat layer makes of it."""
    a, b = _flat_forms(attrs), _flat_forms(body)
    for name in FLAT:
        if name in a and name in b:
            ctx.read_scripts.add((file, origin, a[name], b[name]))


def _read_whole(ctx: Context, file: str, path: str, attrs: str, body: str) -> str | None:
    """The text a broken script on the layer at `path` was read whole in, or None: the same
    file, the same attributes and body as that layer made them, and `path` that text's path
    followed by flat layers only (CMP-2-03)."""
    for f, origin, a, b in ctx.read_scripts:
        if f != file or a != attrs or b != body or not path.startswith(origin + " > "):
            continue
        if all(step in FLAT for step in path[len(origin) + 3:].split(" > ")):
            return origin
    return None


def _number(ctx: Context, literal, file: str, path: str, *, count_too: bool) -> None:
    try:
        value = literal if isinstance(literal, Decimal) else Decimal(str(literal))
    except InvalidOperation:
        return
    if not value.is_finite() or abs(value.adjusted()) > 30:  # 1e309, NaN: no needle (PROTO-2-06)
        return
    n = ctx.needles
    if value in n.amounts:
        ctx.find(INSPECT_NUMBER, file, path, _canonical_amount(n, value))
    if count_too and value == value.to_integral_value() and int(value) in n.counts:
        ctx.find(INSPECT_NUMBER, file, path, int(value))


def _structured(ctx: Context, value, file: str, path: str, role: str, depth: int) -> None:
    """A parsed JSON: every number compared as a number, every string searched
    and, when it is itself a document, inspected again."""
    stack = [value]
    while stack:
        v = stack.pop()
        if isinstance(v, bool) or v is None:
            continue
        if isinstance(v, (int, float)):
            _number(ctx, repr(v) if isinstance(v, float) else v, file, path, count_too=True)
        elif isinstance(v, str):
            raw = v.encode("utf-8", "surrogatepass")
            if len(v) >= 3:
                for needle in ctx.needles.texts:
                    if needle in v:
                        ctx.find(INSPECT_TEXT, file, path, needle)
                _numbers_in_text(ctx, v, file, path, DATA)
                if v.strip()[:1] in "{[" or len(v) >= 16:
                    _descend(ctx, raw, file, f"{path} > string", DATA, depth, speculative=True)
        elif isinstance(v, list):
            stack.extend(v)
        elif isinstance(v, dict):
            stack.extend(v.values())
            if role == COLLECTED:
                _calendar(ctx, v, file, path)


def _calendar(ctx: Context, record: dict, file: str, path: str) -> None:
    """Two integer fields of one record whose values are a year and a month of
    the window: a lead, not a proof (§2.5.2)."""
    ints = [v for v in record.values() if isinstance(v, int) and not isinstance(v, bool)]
    years = {y for y, _ in ctx.needles.window}
    for y in (v for v in ints if v in years):
        if any((y, m) in ctx.needles.window for m in ints if 1 <= m <= 12):
            ctx.find(INSPECT_CALENDAR, file, path, y)
            return


# --- Arrow and Parquet ------------------------------------------------------------------


def _stored(array):
    """The values an Arrow array stores, walked through its physical children:
    a dictionary's whole dictionary — values no row refers to included —, the
    whole child of a list, a list view or a fixed-size list, a struct's fields,
    a map's keys and items, a union's children, a run-end array's values, an
    extension array's storage (PROTO-3-07, PROTO-4-06, PROTO-5-04). A view
    array's data buffers keep bytes no row refers to: they are yielded whole,
    as one bytes value of the kind `("buffer", bytes)`. Yields Python values;
    what still comes back nested is walked to its leaves."""
    import pyarrow as pa
    import pyarrow.types as t

    stack = [array]
    while stack:
        a = stack.pop()
        if isinstance(a, pa.ChunkedArray):
            stack.extend(a.chunks)
            continue
        ty = a.type
        if isinstance(ty, pa.ExtensionType):
            stack.append(a.storage)
        elif t.is_dictionary(ty):
            stack.append(a.dictionary)
        elif t.is_map(ty):
            stack.extend((a.keys, a.items))
        elif t.is_list(ty) or t.is_large_list(ty) or t.is_fixed_size_list(ty) or t.is_list_view(ty) or t.is_large_list_view(ty):
            stack.append(a.values)
        elif t.is_struct(ty) or t.is_union(ty):
            stack.extend(a.field(i) for i in range(ty.num_fields))
        elif t.is_run_end_encoded(ty):
            stack.append(a.values)
        else:
            if t.is_string_view(ty) or t.is_binary_view(ty):
                for buffer in a.buffers()[2:]:  # the variadic data buffers, kept whole by a slice
                    if buffer is not None and buffer.size:
                        yield ("buffer", buffer.to_pybytes())
            for v in a.to_pylist():
                if v is not None:
                    yield from _leaves(v)


def _leaves(value):
    """The scalar leaves of a Python value: lists, tuples and dicts walked to
    the end."""
    stack = [value]
    while stack:
        v = stack.pop()
        if isinstance(v, dict):
            stack.extend(v.values())
        elif isinstance(v, (list, tuple)):
            stack.extend(v)
        elif v is not None:
            yield v


def _cells(ctx: Context, table, code: str, file: str, path: str, depth: int = 0) -> None:
    """Every stored value of a typed table: a text needle in a string, a count
    or an amount in a typed number. A string is also read as a data carrier's
    text — numbers, and the documents and encodings it may carry —, and a
    binary value as a blob of its own, one layer deeper, where bytes no layer
    reads are inconclusive (PROTO-4-06, PROTO-5-05)."""
    n = ctx.needles
    for column in table.columns:
        for v in _stored(column):
            if isinstance(v, tuple) and len(v) == 2 and v[0] == "buffer":
                _descend(ctx, v[1], file, f"{path} > view buffer", DATA, depth, speculative=True)
            elif isinstance(v, str):
                for t in sorted(t for t in n.texts if t in v):  # the matched needle, not the cell (PROTO-1-09)
                    ctx.find(code, file, path, t)
                _numbers_in_text(ctx, v, file, f"{path} > string", DATA)
                _string_layers(ctx, v, file, f"{path} > string", depth)
            elif isinstance(v, (bytes, bytearray)):
                _descend(ctx, bytes(v), file, f"{path} > binary cell", DATA, depth, speculative=False)
            elif isinstance(v, (int, float, Decimal)) and not isinstance(v, bool):
                d = Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
                if not d.is_finite():
                    continue
                if d in n.amounts:
                    ctx.find(code, file, path, _canonical_amount(n, d))  # the canonical value the draw can move (PROTO-2-08)
                if d == d.to_integral_value() and int(d) in n.counts:
                    ctx.find(code, file, path, int(d))


def _string_layers(ctx: Context, v: str, file: str, path: str, depth: int) -> None:
    """What a typed string cell carries beyond its own text, which `_cells`
    searched: a JSON document, parsed, and what the text decoders open — a
    data URL's base64, a percent or escape encoding —, each one layer deeper
    (PROTO-5-05)."""
    stripped = v.strip()
    if stripped[:1] in "{[":
        try:
            _structured(ctx, json.loads(stripped), file, f"{path} > json", DATA, depth + 1)
        except ValueError:
            pass
    for name, out in _text_decoders(v):
        _descend(ctx, out, file, f"{path} > {name}", DATA, depth, speculative=True)


def _parquet(ctx: Context, data: bytes, file: str, path: str, depth: int = 0) -> bool:
    """A Parquet read by PyArrow — or, when PyArrow refuses it and DuckDB reads
    it, by DuckDB, said so (PROTO-5-03) —, then its top-level string and binary
    columns read again as dictionaries, so that a dictionary page keeps values
    no row refers to even with no Arrow schema stored (PROTO-5-04)."""
    import pyarrow.parquet as pq
    import pyarrow.types as t

    try:
        table = pq.read_table(io.BytesIO(data))
    except Exception:  # noqa: BLE001
        table = _duckdb_parquet(data)
        if table is None:
            return False
        ctx.report.recorded.append(Note(file, path, "a Parquet PyArrow refuses, read by DuckDB"))
        _cells(ctx, table, INSPECT_PARQUET, file, path, depth)
        return True
    if table.num_rows == 0 and fx_mod.schema_only(data):
        ctx.report.recorded.append(Note(file, path, "Parquet with P01's schema and no row: schema only"))
        return True
    _cells(ctx, table, INSPECT_PARQUET, file, path, depth)
    names = [f.name for f in table.schema if t.is_string(f.type) or t.is_large_string(f.type) or t.is_binary(f.type)
             or t.is_large_binary(f.type)]
    if names:
        try:
            stored = pq.read_table(io.BytesIO(data), read_dictionary=names)
        except Exception:  # noqa: BLE001
            ctx.report.inconclusive.append(Note(file, path, "the dictionary pages could not be read as stored"))
            return True
        _cells(ctx, stored.select(names), INSPECT_PARQUET, file, f"{path} > dictionary pages", depth)
    return True


def _duckdb_parquet(data: bytes):
    """The table DuckDB reads from Parquet bytes, or None."""
    import tempfile

    import duckdb

    with tempfile.TemporaryDirectory() as tmp:
        target = pathlib.Path(tmp) / "f.parquet"
        target.write_bytes(data)
        try:
            con = duckdb.connect(":memory:")
            try:
                return con.execute("SELECT * FROM read_parquet(?)", [str(target)]).to_arrow_table()
            finally:
                con.close()
        except Exception:  # noqa: BLE001
            return None


def _arrow_opens(data: bytes) -> bool:
    import pyarrow.ipc as ipc

    for opener in (ipc.open_file, ipc.open_stream):
        try:
            opener(io.BytesIO(data)).read_all()
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


def _arrow(ctx: Context, data: bytes, file: str, path: str, depth: int = 0) -> bool:
    import pyarrow.ipc as ipc

    for opener in (ipc.open_file, ipc.open_stream):
        try:
            table = opener(io.BytesIO(data)).read_all()
        except Exception:  # noqa: BLE001
            continue
        _cells(ctx, table, INSPECT_ARROW, file, f"{path} > arrow", depth)
        return True
    return False


# --- binary numbers ---------------------------------------------------------------------


def _binary_table(n: Needles) -> dict[int, list[tuple[str, Decimal]]]:
    table: dict[int, list[tuple[str, Decimal]]] = {}
    for a in n.amounts:
        f = float(a)
        for kind, raw in (("double-le", struct.pack("<d", f)), ("double-be", struct.pack(">d", f))):
            table.setdefault(struct.unpack("<Q", raw)[0], []).append((kind, a))
        cents = int(a * 100)
        if 0 < cents < 2**63:
            table.setdefault(cents, []).append(("decimal128", a))
    return table


def _binary_numbers(ctx: Context, data: bytes, file: str, path: str) -> None:
    """Every amount as the 8 bytes of an IEEE 754 double, both byte orders, and
    as the 16 bytes of an Arrow decimal128 at scale 2 (§2.5.2): each of the 8
    alignments read as little-endian 64-bit words, intersected with the words
    of the needles."""
    if len(data) < 8:
        return
    if ctx._binary is None:
        table = _binary_table(ctx.needles)
        ctx._binary = {"table": table, "set": frozenset(table)}
    table, words = ctx._binary["table"], ctx._binary["set"]
    little = sys.byteorder == "little"
    for off in range(8):
        count = (len(data) - off) // 8
        if count <= 0:
            break
        view = memoryview(data[off: off + count * 8]).cast("Q")
        found = words.intersection(view) if little else words.intersection(struct.unpack(f"<{count}Q", view))
        if not found:
            continue
        for i, word in enumerate(view if little else struct.unpack(f"<{count}Q", view)):
            if word not in found:
                continue
            pos = off + 8 * i
            for kind, amount in table[word]:
                if kind == "decimal128" and data[pos + 8: pos + 16] != b"\x00" * 8:
                    continue
                ctx.find(INSPECT_BINARY, file, f"{path} > {kind}@{pos}", _canonical_amount(ctx.needles, amount))


# --- the gate's own search, every hit -------------------------------------------------


_NUMERIC_NEEDLE = re.compile(rb"[0-9.,-]+")


def gate_hits(haystacks: dict[str, bytes], needles: list[tuple[str, bytes]]) -> list[tuple[str, bytes, str]]:
    """`contract.inspect`'s search — substrings of `contract.needles(values,
    public)`, given — with every (code, needle, file) instead of the first
    refusal. A numeric needle lies within a maximal run of `[0-9.,-]`, so only
    those runs are scanned."""
    numeric = {n for code, n in needles if _NUMERIC_NEEDLE.fullmatch(n)}
    code_of = {n: code for code, n in needles}
    others = [(code, n) for code, n in needles if n not in numeric]
    lengths = sorted({len(n) for n in numeric})
    hits = []
    for rel in sorted(haystacks):
        data = haystacks[rel]
        for code, n in others:
            if n in data:
                hits.append((code, n, rel))
        found: set[bytes] = set()
        if lengths:
            for m in _NUMERIC_NEEDLE.finditer(data):
                run = m[0]
                if len(run) < lengths[0]:
                    continue
                for i in range(len(run)):
                    for size in lengths:
                        if i + size > len(run):
                            break
                        s = run[i: i + size]
                        if s in numeric:
                            found.add(s)
        hits += [(code_of[s], s, rel) for s in sorted(found)]
    return hits
