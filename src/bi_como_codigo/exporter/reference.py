"""§6, §7 and §8: the checks on every view, the frozen reference with its grain
keys, the canonical comparator of the round trip, and the control totals
computed from the reference — never from the Parquet.

Canonical values (§7): decimals as the exact fixed-point string at the column's
scale, integers as integers, booleans as booleans, text as text, instants as
integer microseconds in UTC, null as null.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, Inexact, localcontext
from types import MappingProxyType
from typing import Mapping

from .. import contract as c
from . import (
    DECIMAL_REFUSED,
    GRAIN_REPEATED,
    INSTANT_REFUSED,
    NULL_REFUSED,
    ROUND_TRIP,
    TEXT_REFUSED,
    VALUE_TYPE,
    Refused,
)
from .source import UNREPRESENTABLE
from .views import View, ViewColumn, fit

EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)
MICROSECOND = dt.timedelta(microseconds=1)
INTEGER_BOUNDS = {"integer": (-(2**31), 2**31 - 1), "bigint": (-(2**63), 2**63 - 1)}
CONTEXT_DIGITS = 200  # §4.3, §8: never the default of 28


@dataclass(frozen=True)
class Frozen:
    """The reference of one view: its canonical rows in read order, the map
    from grain key to row, and the digest of §7. Immutable: the writer gets a
    copy of the rows."""

    view: View
    rows: tuple[tuple, ...]
    by_key: Mapping[tuple, tuple]
    digest: str


def instant_us(value: object, view: str | None = None) -> int:
    """§4.3: an aware `datetime` as integer microseconds since the epoch, UTC.
    A naive one, PostgreSQL's `infinity` or a date the client cannot hold refuses."""
    if value is UNREPRESENTABLE or not isinstance(value, dt.datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise Refused(INSTANT_REFUSED, view, "instants")
    return (value - EPOCH) // MICROSECOND


def _integer(value: object, col: ViewColumn, view: str) -> int:
    low, high = INTEGER_BOUNDS[col.source_type]
    if type(value) is not int or not low <= value <= high:
        raise Refused(VALUE_TYPE, view, "types")
    return value


def _checked_text(value: object, col: ViewColumn, view: str) -> str:
    if type(value) is not str:
        raise Refused(VALUE_TYPE, view, "types")
    return value


def freeze(view: View, rows: list[tuple]) -> Frozen:
    """§6 on the raw result, check by check over every row, then the frozen
    reference by the validated positions (§7). Each refusal names the view and
    the check, never a value."""
    width = len(view.columns)
    if any(not isinstance(r, tuple) or len(r) != width for r in rows):
        raise Refused(VALUE_TYPE, view.view, "types")
    columns = list(enumerate(view.columns))
    # §6.3: nulls, grain columns included — never nullable.
    for row in rows:
        for i, col in columns:
            if row[i] is None and not col.nullable:
                raise Refused(NULL_REFUSED, view.view, "nulls")
    canonical = [list(row) for row in rows]
    # §6.4: decimals, finite and fitting exactly.
    with localcontext() as ctx:
        ctx.prec = CONTEXT_DIGITS
        for out, row in zip(canonical, rows):
            for i, col in columns:
                if col.is_decimal and row[i] is not None:
                    out[i] = fit(row[i], col.precision, col.scale, view.view)
    # §6.5: instants, aware and within the client's range.
    for out, row in zip(canonical, rows):
        for i, col in columns:
            if col.is_instant and row[i] is not None:
                out[i] = instant_us(row[i], view.view)
    # The other types are what the contract says, before the grain uses them.
    for out, row in zip(canonical, rows):
        for i, col in columns:
            if row[i] is None:
                continue
            if col.is_integer:
                out[i] = _integer(row[i], col, view.view)
            elif col.source_type == "boolean" and type(row[i]) is not bool:
                raise Refused(VALUE_TYPE, view.view, "types")
            elif col.is_text:
                out[i] = _checked_text(row[i], col, view.view)
    frozen_rows = tuple(tuple(r) for r in canonical)
    # §6.6: the grain, by the canonical key.
    positions = [view.names.index(g) for g in view.grain]
    by_key: dict[tuple, tuple] = {}
    for row in frozen_rows:
        key = tuple(row[p] for p in positions)
        if key in by_key:
            raise Refused(GRAIN_REPEATED, view.view, "grain")
        by_key[key] = row
    # §6.7: text — no NUL, at most `max_length` characters.
    for row in frozen_rows:
        for i, col in columns:
            if col.is_text and row[i] is not None and ("\x00" in row[i] or len(row[i]) > col.max_length):
                raise Refused(TEXT_REFUSED, view.view, "text")
    return Frozen(view, frozen_rows, MappingProxyType(by_key), digest(by_key))


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def digest(by_key: Mapping[tuple, tuple]) -> str:
    """§7: SHA-256 over the rows' canonical JSON, sorted by the key's."""
    ordered = sorted(by_key.items(), key=lambda kv: _canonical_json(list(kv[0])))
    text = "\n".join(_canonical_json(list(row)) for _key, row in ordered)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compare(reference: Frozen, back: list[tuple]) -> None:
    """§7: the read-back against the reference — the same count, the same set
    of keys, each once on each side, and every cell equal. No ordering."""
    view = reference.view
    if len(back) != len(reference.rows):
        raise Refused(ROUND_TRIP, view.view, "round_trip")
    positions = [view.names.index(g) for g in view.grain]
    seen: dict[tuple, tuple] = {}
    for row in back:
        key = tuple(row[p] for p in positions)
        if key in seen:
            raise Refused(ROUND_TRIP, view.view, "round_trip")
        seen[key] = row
    if set(seen) != set(reference.by_key):
        raise Refused(ROUND_TRIP, view.view, "round_trip")
    for key, row in seen.items():
        if not _equal(reference.by_key[key], row):
            raise Refused(ROUND_TRIP, view.view, "round_trip")


def _equal(left: tuple, right: tuple) -> bool:
    """Cell by cell, by type as well as value: `1 == True` and `0 == False` in
    Python, and a swap between an integer and a boolean must not pass."""
    return len(left) == len(right) and all(type(a) is type(b) and a == b for a, b in zip(left, right))


# --- §8: the control totals ---------------------------------------------------------------


def _at_scale(total: Decimal, scale: int) -> str:
    if total == 0:
        return "0" + ("." + "0" * scale if scale else "")
    text = f"{total.quantize(Decimal(1).scaleb(-scale)):f}" if scale else str(int(total))
    return text


def totals(contract: c.Contract, report: c.Report, reference: Frozen) -> bytes:
    """N78's format, from the frozen reference, in exact `Decimal` arithmetic
    under 200 digits; nulls skipped; an empty or all-null column is zero at its
    scale; no sign on zero."""
    names = list(reference.view.names)
    sums = {}
    with localcontext() as ctx:
        ctx.prec = CONTEXT_DIGITS
        ctx.traps[Inexact] = True  # exact, or refused
        for name in report.sums:
            i = names.index(name)
            scale = report.column(name).scale
            total = Decimal(0)
            for row in reference.rows:
                if row[i] is not None:
                    total += Decimal(row[i])
            text = _at_scale(total, scale)
            if not c.canonical_ok(text, scale):
                raise Refused(DECIMAL_REFUSED, reference.view.view, "totals")
            sums[name] = text
    return c.totals_object(contract, report, len(reference.rows), sums)
