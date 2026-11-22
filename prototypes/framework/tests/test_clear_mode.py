"""The clear mode's A1 inventory (§3, §7 step 2): a query result Evidence
prerendered is found wherever under the outputs it lies — its SvelteKit
project lives in `.evidence/template/` —, and a binary byte-identical to a
file of the kept install is recorded, not inconclusive (§2.5.2)."""

from __future__ import annotations

import hashlib
import io

import pyarrow as pa
import pyarrow.ipc as ipc

import clear_mode as cm
import fixture as f


def _arrow(table: pa.Table) -> bytes:
    out = io.BytesIO()
    with ipc.new_file(out, table.schema) as writer:
        writer.write_table(table)
    return out.getvalue()


def test_a_nested_prerendered_result_and_a_dependency_binary(tmp_path):
    fx, _ = f.generate(cm.CLEAR_SEED)
    channel = fx.rows()[0][4]
    font = b"wOF2\0\x01opaque font bytes of a dependency"
    nested = tmp_path / ".evidence" / "template" / "build" / "api" / "prerendered_queries"
    nested.mkdir(parents=True)
    (nested / "q.arrow").write_bytes(_arrow(pa.table({"sales_channel_name": [channel]})))
    assets = tmp_path / "build" / "_app"
    assets.mkdir(parents=True)
    (assets / "Inter.woff2").write_bytes(font)
    (assets / "other.woff2").write_bytes(font + b"x")

    a1 = cm.inventory(tmp_path, [".evidence", "build"], fx, frozenset({hashlib.sha256(font).hexdigest()}))
    assert a1["queries_at_build_time"] is True
    assert a1["prerendered_query_files_with_rows"] == [".evidence/template/build/api/prerendered_queries/q.arrow"]
    build = a1["carriers"]["build"]
    assert build["recorded"] == 1
    assert [n["file"] for n in build["inconclusive"]] == ["build/_app/other.woff2"]


def test_no_prerendered_result_with_rows_is_no_query_at_build_time(tmp_path):
    fx, _ = f.generate(cm.CLEAR_SEED)
    nested = tmp_path / "build" / "api" / "prerendered_queries"
    nested.mkdir(parents=True)
    (nested / "q.arrow").write_bytes(_arrow(pa.table({"x": ["not a fixture value"]})))
    a1 = cm.inventory(tmp_path, ["build"], fx, frozenset())
    assert a1["queries_at_build_time"] is False
    assert a1["prerendered_query_files_with_rows"] == []
