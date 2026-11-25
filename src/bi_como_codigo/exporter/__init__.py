"""The exporter of stage 2.4 (docs/exporter.md): the source-to-package gate, run
on the Owner's machine. Section numbers (§n) are that document's.

    views       §4    the view contract, its strict loader, the exact fit, the
                      generated report contract
    source      §3    the connection, the facts checked before any row, the read
    reference   §6–§8 the checks on every view, the frozen reference, the totals
    writer      §7    the Parquet written by DuckDB and read back
    metadata    §5    the governance metadata, bound to the pin
    paths       §10   where clear data may be written
    receipt     §9    the receipt, read back strictly
    cli         §10   the commands, and what a refusal prints

Every refusal is a `Refused` with a fixed code, and at most the view and the
check it belongs to — names of the contract, never a value (§10).
"""

from __future__ import annotations


class Refused(Exception):
    """A refusal of the exporter: a fixed code, and at most a view and a check.
    It carries no message of a driver nor any value, so printing it is safe."""

    def __init__(self, code: str, view: str | None = None, check: str | None = None, cause: str | None = None):
        self.code, self.view, self.check = code, view, check
        self.cause = cause  # the class name of the exception refused, never its message
        detail = ", ".join(f"{k} {v}" for k, v in (("view", view), ("check", check)) if v)
        super().__init__(code + (f" ({detail})" if detail else ""))


def strict_json(raw: object) -> tuple[bool, object]:
    """The envelope's strict JSON — UTF-8, one value, no repeated key, no NaN
    or Infinity — as (parsed, value). A repeated key is a failed parse here."""
    from .. import envelope as e

    if not isinstance(raw, bytes):
        return False, None
    try:
        return e._strict_json(raw)
    except e.Refused:
        return False, None


# --- the codes ------------------------------------------------------------------------

#: §4: the declarations.
VIEWS_INVALID = "views_invalid"
CONTRACT_STALE = "contract_stale"
CATALOGUE_INVALID = "catalogue_invalid"

#: §3: the environment and the connection.
ENVIRONMENT_INVALID = "environment_invalid"
TLS_ROOT_REQUIRED = "tls_root_required"
CONNECT_FAILED = "connect_failed"
STATEMENT_FAILED = "statement_failed"
COMMIT_FAILED = "commit_failed"
SEQUENCE_BROKEN = "sequence_broken"

#: §3: the facts, in their order.
FACT_TRANSACTION = "fact_transaction"
FACT_PROVENANCE = "fact_provenance"
FACT_LOGIN = "fact_login"
FACT_ROLES = "fact_roles"
FACT_INVENTORY = "fact_inventory"
FACT_ACCESS = "fact_access"
FACT_SCHEMA = "fact_schema"
FACT_POLICY = "fact_policy"
WITNESS_MISMATCH = "witness_mismatch"

#: §3, the rows, and §6: the checks on every view.
RESULT_SCHEMA = "result_schema"
SIZE_OVER = "size_over"
SIZE_EMPTY = "size_empty"
NULL_REFUSED = "null_refused"
DECIMAL_REFUSED = "decimal_refused"
INSTANT_REFUSED = "instant_refused"
GRAIN_REPEATED = "grain_repeated"
TEXT_REFUSED = "text_refused"
VALUE_TYPE = "value_type"

#: §7: the round trip.
ROUND_TRIP = "round_trip"
READBACK_TAMPERED = "readback_tampered"
SEAL_TAMPERED = "seal_tampered"
WRITE_FAILED = "write_failed"

#: §5: the metadata.
METADATA_PIN = "metadata_pin"
METADATA_BLOB = "metadata_blob"
METADATA_FORMAT = "metadata_format"
METADATA_MAPPING = "metadata_mapping"
METADATA_COLUMNS = "metadata_columns"
METADATA_GRAIN = "metadata_grain"

#: §10: the paths and the run directory.
PATH_REFUSED = "path_refused"
PATH_EXISTS = "path_exists"
RUN_LEFTOVER = "run_leftover"
RUN_LOCKED = "run_locked"
INTERRUPTED = "interrupted"

#: §9 and §10: the receipt, the candidate, and anything else.
RECEIPT_INVALID = "receipt_invalid"
CANDIDATE_REFUSED = "candidate_refused"
UNEXPECTED = "unexpected"
USAGE_INVALID = "usage_invalid"
CLEANUP_FAILED = "cleanup_failed"
