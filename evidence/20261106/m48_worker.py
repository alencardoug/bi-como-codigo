"""M48's Python worker: the dedicated cases of one predicate against a mutant.

Called by `m48_counter_proof.py` as `m48_worker.py <mutant src> <predicate>`;
prints a JSON list of {case, killed, end}.
"""

from __future__ import annotations

import json
import pathlib
import sys

MUTANT, PID = sys.argv[1], sys.argv[2]
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, MUTANT)
sys.path.insert(1, str(ROOT / "tests"))

from bi_como_codigo import envelope as e  # noqa: E402  - the mutant

assert pathlib.Path(e.__file__).is_relative_to(MUTANT), e.__file__
import envelope_fixtures as fx  # noqa: E402
import test_envelope as t  # noqa: E402

assert t.e is e


def end_of(thunk) -> str:
    try:
        thunk()
    except e.Refused as refusal:
        return f"{refusal.code}/{refusal.predicate_id}"
    except Exception as error:  # a broken parse counts as killed (§6.5)
        return f"error {type(error).__name__}"
    return "opened"


results = []
cases = json.loads((ROOT / "tests" / "vectors" / "envelope_v1" / "cases.json").read_text(encoding="utf-8"))["cases"]
for c in cases:
    if c["predicate"] != PID:
        continue

    def thunk(c=c):
        out = t.run(c["manifest"], bytes.fromhex(c["envelope"]), c["report"], c["profile"], c["typed"])
        if isinstance(out, e.Refused):
            raise out

    end = end_of(thunk)
    results.append({"case": c["id"], "killed": end != f"{c['code']}/{PID}", "end": end})

if PID == "ciphertext_len_range":
    manifest_text, data = t._range_max_case()

    def big():
        out = t.run(manifest_text, data, "P01", "diretoria", fx.TYPED["diretoria"])
        if isinstance(out, e.Refused):
            raise out

    end = end_of(big)
    results.append({"case": "header_ciphertext_range__above", "killed": end != "header_malformed/ciphertext_len_range", "end": end})

package = {
    "dek_unique": ("reuse_dek_only", True, False, False, "dek_reused"),
    "iv_unique": ("reuse_iv_only", False, True, False, "iv_reused"),
    "matrix_closed": ("matrix_same_key", False, False, True, "unentitled_opens"),
}
if PID in package:
    name, same_dek, same_iv, same_key, code = package[PID]
    deks, ivs = t._fresh(name)
    if same_dek:
        deks["P02"] = deks["P01"]
    if same_iv:
        ivs["P02"] = ivs["P01"]
    manifest, files, typed = t._package(deks, ivs, same_key=same_key)
    end = end_of(lambda: e.check_package(manifest, files, typed))
    results.append({"case": name, "killed": end != f"{code}/{PID}", "end": end})

print(json.dumps(results))
