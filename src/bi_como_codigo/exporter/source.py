"""§3: the read — the environment, the connection with explicit parameters only,
the facts checked before any row, in their order, and the rows of each view.

The reader works over `Source`, a small connection interface: execute, the
result's fields, fetch, commit and close. psycopg implements it in production
(`PsycopgSource`); the tests implement it with a fake fed by a committed
fixture (§12). Every statement goes through it, in one transaction, once.
"""

from __future__ import annotations

import datetime as dt
import os
import pathlib
from dataclasses import dataclass, field
from typing import Callable, Protocol

from . import (
    COMMIT_FAILED,
    CONNECT_FAILED,
    ENVIRONMENT_INVALID,
    FACT_ACCESS,
    FACT_INVENTORY,
    FACT_LOGIN,
    FACT_POLICY,
    FACT_PROVENANCE,
    FACT_ROLES,
    FACT_SCHEMA,
    FACT_TRANSACTION,
    RESULT_SCHEMA,
    SIZE_EMPTY,
    SIZE_OVER,
    STATEMENT_FAILED,
    TLS_ROOT_REQUIRED,
    WITNESS_MISMATCH,
    Refused,
)
from .views import COLLATION_KEYS, POLICY_KEYS, Build, View, ViewContract

SCHEMA = "consumption"
APPLICATION_NAME = "bi-como-codigo-exporter"
SSLMODES = ("disable", "allow", "prefer", "require", "verify-ca", "verify-full")
VERIFYING = ("verify-ca", "verify-full")
CONNECT_TIMEOUT = "10"


# --- the environment ------------------------------------------------------------------------


@dataclass(frozen=True)
class Settings:
    host: str
    port: str
    dbname: str
    user: str
    password: str = field(repr=False)
    sslmode: str
    sslrootcert: str | None
    sslcrl: str | None

    def __repr__(self) -> str:  # the password is never printed
        return f"Settings(host={self.host!r}, port={self.port!r}, dbname={self.dbname!r}, user={self.user!r}, sslmode={self.sslmode!r})"


def settings(environ: dict[str, str]) -> Settings:
    """The warehouse's variables (§3). A missing or empty one refuses, and so
    does a verifying `sslmode` with no root certificate — before connecting."""
    def need(name: str) -> str:
        value = environ.get(name, "")
        if not value:
            raise Refused(ENVIRONMENT_INVALID, check=name)
        return value

    found = Settings(
        host=need("BICE_WAREHOUSE_HOST"),
        port=need("BICE_WAREHOUSE_PORT"),
        dbname=need("BICE_WAREHOUSE_DB"),
        user=need("BICE_WAREHOUSE_USER"),
        password=need("BICE_WAREHOUSE_PASSWORD"),
        sslmode=need("BICE_WAREHOUSE_SSLMODE"),
        sslrootcert=_tls_path(environ.get("BICE_WAREHOUSE_SSLROOTCERT"), allow_system=True),
        sslcrl=_tls_path(environ.get("BICE_WAREHOUSE_SSLCRL")),
    )
    if not found.port.isdigit() or found.sslmode not in SSLMODES:
        raise Refused(ENVIRONMENT_INVALID, check="BICE_WAREHOUSE_PORT" if not found.port.isdigit() else "BICE_WAREHOUSE_SSLMODE")
    if found.sslmode in VERIFYING and not found.sslrootcert:
        raise Refused(TLS_ROOT_REQUIRED)
    return found


def _tls_path(value: str | None, allow_system: bool = False) -> str | None:
    """A TLS file the Owner names, resolved where it was named: the run changes
    its working directory before libpq opens it (XIMPL-1-10). libpq's special
    root `system` stays as it is."""
    if not value:
        return None
    if allow_system and value == "system":
        return value
    return os.path.abspath(value)


def scrub_environment(environ) -> list[str]:
    """§3: every variable whose name starts with `PG` is removed before
    connecting, so libpq takes only the explicit parameters. Returns the names
    removed — names, never values."""
    removed = sorted(name for name in environ if name.startswith("PG"))
    for name in removed:
        del environ[name]
    return removed


def connection_parameters(found: Settings, absent: pathlib.Path) -> dict[str, str]:
    """§3, TLS: the parameters libpq gets, all explicit. `absent` is a path
    inside the run directory that does not exist: the TLS files not given point
    there, so no file of the home directory is read. No client certificate is
    ever sent (`sslcertmode=disable`), the password file and GSS are off, and
    the client encoding is UTF-8, which check 8 reads back."""
    if absent.exists():
        raise Refused(ENVIRONMENT_INVALID, check="absent")
    nothing = str(absent)
    return {
        "host": found.host,
        "port": found.port,
        "dbname": found.dbname,
        "user": found.user,
        "password": found.password,
        "sslmode": found.sslmode,
        "sslcertmode": "disable",
        "sslcert": nothing,
        "sslkey": nothing,
        "sslrootcert": found.sslrootcert or nothing,
        "sslcrl": found.sslcrl or nothing,
        "passfile": nothing,
        "gssencmode": "disable",
        "options": "",
        "application_name": APPLICATION_NAME,
        "client_encoding": "UTF8",
        "connect_timeout": CONNECT_TIMEOUT,
    }


# --- the connection interface ---------------------------------------------------------------


class Source(Protocol):
    def execute(self, sql: str, params: tuple = ()) -> None: ...

    def fields(self) -> list[tuple[str, int, int]]:
        """The last result's columns: name, type OID and modifier, by position."""
        ...

    def fetchall(self) -> list[tuple]: ...

    def commit(self) -> None: ...

    def close(self) -> None: ...


#: What the psycopg adapter returns for an instant the client cannot hold —
#: PostgreSQL's `infinity`, or a year past 9999. The check of §6.5 refuses it.
UNREPRESENTABLE = object()


class PsycopgSource:
    """psycopg 3 (N105): one connection, `autocommit` off, REPEATABLE READ and
    READ ONLY, its first statement starting the transaction. No retry."""

    def __init__(self, parameters: dict[str, str]):
        import psycopg
        from psycopg.types.datetime import TimestamptzLoader

        class _Instant(TimestamptzLoader):
            def load(self, data):
                try:
                    return super().load(data)
                except psycopg.DataError:
                    return UNREPRESENTABLE

        self._conn = psycopg.connect(**parameters, autocommit=False, prepare_threshold=None)
        self._conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        self._conn.read_only = True
        self._conn.adapters.register_loader("timestamptz", _Instant)
        self._conn.add_notice_handler(lambda _diagnostic: None)  # a server notice is never printed
        self._cur = self._conn.cursor()

    def execute(self, sql: str, params: tuple = ()) -> None:
        self._cur.execute(sql, params or None)

    def fields(self) -> list[tuple[str, int, int]]:
        return result_fields(self._cur.pgresult)

    def fetchall(self) -> list[tuple]:
        return self._cur.fetchall()

    def commit(self) -> None:
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()


def result_fields(pgresult) -> list[tuple[str, int, int]]:
    """§3, the rows: psycopg's public result object, by position — `fname`,
    `ftype` and `fmod`. `cursor.description` does not expose the raw modifier
    (EXP-3-02)."""
    if pgresult is None:
        return []
    return [(pgresult.fname(i).decode("utf-8"), pgresult.ftype(i), pgresult.fmod(i)) for i in range(pgresult.nfields)]


# --- the statements -------------------------------------------------------------------------

Q_TRANSACTION = (
    "SELECT current_setting('transaction_isolation'), current_setting('transaction_read_only'), now()"
)
Q_PROVENANCE = (
    "SELECT status, invocation_id::text, built_from_commit, sequence::bigint FROM governance.warehouse_provenance"
)
Q_LOGIN = "SELECT session_user::text, current_user::text"
_REACHED = (
    "WITH RECURSIVE reached(oid) AS ("
    " SELECT oid FROM pg_roles WHERE rolname = session_user"
    " UNION SELECT m.roleid FROM pg_auth_members m JOIN reached r ON m.member = r.oid) "
)
Q_MEMBERSHIPS = (
    _REACHED + "SELECT mem.rolname::text, rol.rolname::text, m.admin_option, m.inherit_option, m.set_option"
    " FROM pg_auth_members m JOIN reached r ON m.member = r.oid"
    " JOIN pg_roles mem ON mem.oid = m.member JOIN pg_roles rol ON rol.oid = m.roleid"
    " ORDER BY 1, 2"
)
Q_ROLE_ATTRIBUTES = (
    _REACHED + "SELECT r.rolname::text, r.rolsuper, r.rolcreaterole, r.rolcreatedb, r.rolreplication, r.rolbypassrls, r.rolcanlogin"
    " FROM pg_roles r JOIN reached USING (oid) ORDER BY 1"
)
Q_INVENTORY = (
    "SELECT c.oid::bigint, c.relname::text, c.relkind::text FROM pg_class c"
    " JOIN pg_namespace n ON n.oid = c.relnamespace WHERE n.nspname = %s ORDER BY 2"
)
TABLE_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")
COLUMN_PRIVILEGES = ("INSERT", "UPDATE")
Q_ACCESS = (
    "SELECT c.oid::bigint, "
    + ", ".join(f"has_table_privilege(session_user, c.oid, '{p}')" for p in TABLE_PRIVILEGES)
    + ", "
    + ", ".join(f"has_any_column_privilege(session_user, c.oid, '{p}')" for p in COLUMN_PRIVILEGES)
    + ", pg_has_role(session_user, c.relowner, 'MEMBER')"
    " FROM pg_class c WHERE c.oid = ANY(%s::oid[]) ORDER BY 1"
)
Q_SCHEMA_ACCESS = "SELECT has_schema_privilege(session_user, %s, 'USAGE'), has_schema_privilege(session_user, %s, 'CREATE')"
Q_ATTRIBUTES = (
    "SELECT a.attrelid::bigint, a.attname::text, a.atttypid::bigint, a.atttypmod FROM pg_attribute a"
    " WHERE a.attrelid = ANY(%s::oid[]) AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attrelid, a.attnum"
)
Q_SET_POLICY = "SELECT set_config(%s, %s, true)"
Q_POLICY = (
    "SELECT " + ", ".join(f"current_setting('{k}')" for k in POLICY_KEYS)
    + ", current_setting('server_encoding'), current_setting('client_encoding')"
)
Q_COLLATION = (
    "SELECT datlocprovider::text, datcollate::text, datctype::text, daticulocale::text, daticurules::text,"
    " datcollversion::text, pg_database_collation_actual_version(oid)::text"
    " FROM pg_database WHERE datname = current_database()"
)


def _ident(name: str) -> str:
    return '"' + name + '"'  # names come from the strict contract, `[a-z][a-z0-9_]*`


def q_count(view: str) -> str:
    return f"SELECT count(*) FROM {SCHEMA}.{_ident(view)}"


#: The column the rows statement adds: M55's fingerprint over the same rows.
FINGERPRINT_COLUMN = ("bice_fingerprint", 25, -1)  # text, no modifier
EMPTY_FINGERPRINT = "d41d8cd98f00b204e9800998ecf8427e"  # md5(''): M55's expression over no row


def m55_expression(alias: str) -> str:
    """M55's exact expression (§3, the witness), over a row alias."""
    return f"md5(coalesce(string_agg({alias}::text, E'\\n' ORDER BY {alias}::text), ''))"


def q_rows(view: View) -> str:
    """N112: one statement materializes the view once and returns its rows, in
    the contract's column order, with M55's fingerprint computed over those same
    rows — so the witness attests exactly what is frozen. The contract's columns
    are every column of the view (check 7), so each row's record text is the
    view's own."""
    columns = ", ".join(_ident(n) for n in view.names)
    return (
        f"WITH t AS MATERIALIZED (SELECT {columns} FROM {SCHEMA}.{_ident(view.view)}) "
        f"SELECT {columns}, (SELECT {m55_expression('w')} FROM t AS w) AS {FINGERPRINT_COLUMN[0]} FROM t"
    )


def q_fingerprint(view: str) -> str:
    """M55's statement as M59 ran it, over the view itself: the probe compares it
    with the fingerprint of `q_rows`, never the exporter."""
    return f"SELECT count(*), {m55_expression('t')} FROM {SCHEMA}.{_ident(view)} t"


# --- the read ---------------------------------------------------------------------------------


@dataclass
class Fact:
    code: str
    passed: bool
    compared: dict


@dataclass
class ViewRead:
    view: View
    rows: int
    fingerprint: str
    witness_equal: bool
    frozen: object  # reference.Frozen


@dataclass
class Read:
    read_at: dt.datetime
    provenance: dict
    build: Build
    policy: dict
    collation: dict
    facts: list[Fact]
    views: dict[str, ViewRead]
    timings: dict[str, float] = field(default_factory=dict)


class _Session:
    """Every statement through one place. A statement that fails refuses with
    `statement_failed` and the name of the statement, and the run issues
    nothing after it; a result of the wrong shape refuses with its fact's code."""

    def __init__(self, source: Source):
        self.source = source

    def query(self, sql: str, params: tuple = (), *, check: str, view: str | None = None) -> list[tuple]:
        try:
            self.source.execute(sql, params)
            return self.source.fetchall()
        except Refused:
            raise
        except Exception as exc:
            raise Refused(STATEMENT_FAILED, view, check, type(exc).__name__) from None

    def described(self, sql: str, view: str) -> list[tuple[str, int, int]]:
        try:
            self.source.execute(sql)
            return self.source.fields()
        except Refused:
            raise
        except Exception as exc:
            raise Refused(STATEMENT_FAILED, view, "rows", type(exc).__name__) from None

    def fetch(self, view: str) -> list[tuple]:
        try:
            return self.source.fetchall()
        except Refused:
            raise
        except Exception as exc:
            raise Refused(STATEMENT_FAILED, view, "rows", type(exc).__name__) from None


def _bools(row: tuple, start: int, code: str) -> None:
    if any(type(v) is not bool for v in row[start:]):
        raise Refused(code)  # a null or a non-boolean where a boolean is expected


def _one(rows: list[tuple], code: str) -> tuple:
    if len(rows) != 1:
        raise Refused(code)
    return rows[0]


def check_transaction(s: _Session) -> tuple[Fact, dt.datetime]:
    isolation, read_only, read_at = _one(s.query(Q_TRANSACTION, check="transaction"), FACT_TRANSACTION)
    if isolation != "repeatable read" or read_only != "on" or not isinstance(read_at, dt.datetime) or read_at.tzinfo is None:
        raise Refused(FACT_TRANSACTION)
    return Fact(FACT_TRANSACTION, True, {"isolation": isolation, "read_only": read_only}), read_at


def provenance_row(s: _Session) -> dict:
    """Exactly one row of `governance.warehouse_provenance`, `verified`."""
    status, invocation, commit, sequence = _one(s.query(Q_PROVENANCE, check="provenance"), FACT_PROVENANCE)
    if status != "verified" or not isinstance(invocation, str) or not isinstance(commit, str) or type(sequence) is not int:
        raise Refused(FACT_PROVENANCE)
    return {"status": status, "built_from_commit": commit, "invocation_id": invocation, "sequence": sequence}


def check_provenance(s: _Session, contract: ViewContract) -> tuple[Fact, Build, dict]:
    """§3 check 2: the row matches exactly one accepted build — whose witness
    and policy the rest of the run uses."""
    row = provenance_row(s)
    matching = [
        b for b in contract.builds
        if (b.provenance.built_from_commit, b.provenance.invocation_id, b.provenance.sequence)
        == (row["built_from_commit"], row["invocation_id"], row["sequence"])
    ]
    if len(matching) != 1:
        raise Refused(FACT_PROVENANCE)
    return Fact(FACT_PROVENANCE, True, row), matching[0], row


def check_login(s: _Session, login: str) -> Fact:
    session_user, current_user = _one(s.query(Q_LOGIN, check="login"), FACT_LOGIN)
    if session_user != login or current_user != login:
        raise Refused(FACT_LOGIN)
    return Fact(FACT_LOGIN, True, {"session_user": session_user, "current_user": current_user})


def measure_roles(s: _Session) -> tuple[list[tuple[str, str, bool, bool]], dict[str, bool]]:
    """The closure of the login's memberships, recursive over `pg_auth_members`,
    with each edge's options, and each role's `rolcanlogin`. An edge with
    `admin_option`, or a role with superuser, CREATEROLE, CREATEDB, REPLICATION
    or BYPASSRLS, refuses here, whatever the contract says."""
    edges = s.query(Q_MEMBERSHIPS, check="memberships")
    for row in edges:
        if len(row) != 5 or not all(isinstance(v, str) for v in row[:2]):
            raise Refused(FACT_ROLES)
        _bools(row, 2, FACT_ROLES)
        if row[2]:
            raise Refused(FACT_ROLES)  # admin_option is never true
    found = sorted((m, r, inherit, set_) for m, r, _admin, inherit, set_ in edges)
    attributes = s.query(Q_ROLE_ATTRIBUTES, check="role_attributes")
    can_login: dict[str, bool] = {}
    for row in attributes:
        if len(row) != 7 or not isinstance(row[0], str):
            raise Refused(FACT_ROLES)
        _bools(row, 1, FACT_ROLES)
        if any(row[1:6]):
            raise Refused(FACT_ROLES)  # superuser, CREATEROLE, CREATEDB, REPLICATION, BYPASSRLS
        if row[0] in can_login:
            raise Refused(FACT_ROLES)
        can_login[row[0]] = row[6]
    return found, can_login


def _roles_compared(found, can_login) -> dict:
    return {
        "memberships": [{"member": m, "role": r, "admin_option": False, "inherit_option": i, "set_option": so} for m, r, i, so in found],
        "can_login": dict(sorted(can_login.items())),
    }


def check_roles(s: _Session, contract: ViewContract) -> Fact:
    """§3 check 4: the closure and its options are exactly the contract's."""
    found, can_login = measure_roles(s)
    declared = sorted((m.member, m.role, m.inherit_option, m.set_option) for m in contract.memberships)
    if found != declared or can_login != contract.can_login:
        raise Refused(FACT_ROLES)
    return Fact(FACT_ROLES, True, _roles_compared(found, can_login))


def check_inventory(s: _Session, names: set[str]) -> tuple[Fact, dict[str, int]]:
    rows = s.query(Q_INVENTORY, (SCHEMA,), check="inventory")
    found: dict[str, tuple[int, str]] = {}
    for row in rows:
        if len(row) != 3 or type(row[0]) is not int or not isinstance(row[1], str) or not isinstance(row[2], str) or row[1] in found:
            raise Refused(FACT_INVENTORY)
        found[row[1]] = (row[0], row[2])
    if set(found) != names or any(kind != "v" for _oid, kind in found.values()):
        raise Refused(FACT_INVENTORY)  # missing, extra of any kind — granted or not — or not a view
    oids = {name: oid for name, (oid, _kind) in found.items()}
    return Fact(FACT_INVENTORY, True, {"views": [{"view": n, "kind": "v"} for n in sorted(found)]}), oids


def check_access(s: _Session, oids: dict[str, int]) -> Fact:
    rows = s.query(Q_ACCESS, (sorted(oids.values()),), check="access")
    by_oid = {}
    for row in rows:
        if len(row) != 1 + len(TABLE_PRIVILEGES) + len(COLUMN_PRIVILEGES) + 1 or type(row[0]) is not int or row[0] in by_oid:
            raise Refused(FACT_ACCESS)
        _bools(row, 1, FACT_ACCESS)
        by_oid[row[0]] = row[1:]
    if set(by_oid) != set(oids.values()):
        raise Refused(FACT_ACCESS)
    compared = {}
    for name, oid in sorted(oids.items()):
        flags = by_oid[oid]
        table = dict(zip(TABLE_PRIVILEGES, flags[: len(TABLE_PRIVILEGES)]))
        column = dict(zip(COLUMN_PRIVILEGES, flags[len(TABLE_PRIVILEGES) : -1]))
        owner_reachable = flags[-1]
        if not table["SELECT"] or any(table[p] for p in TABLE_PRIVILEGES[1:]) or any(column.values()) or owner_reachable:
            raise Refused(FACT_ACCESS, name)
        compared[name] = {"table": table, "any_column": column, "owner_reachable": owner_reachable}
    usage, create = _one(s.query(Q_SCHEMA_ACCESS, (SCHEMA, SCHEMA), check="schema_access"), FACT_ACCESS)
    if type(usage) is not bool or type(create) is not bool or not usage or create:
        raise Refused(FACT_ACCESS, check="schema")
    return Fact(FACT_ACCESS, True, {"views": compared, "schema": {"USAGE": usage, "CREATE": create}})


def read_attributes(s: _Session, oids: dict[str, int], code: str = FACT_SCHEMA) -> dict[str, list[tuple[str, int, int]]]:
    rows = s.query(Q_ATTRIBUTES, (sorted(oids.values()),), check="attributes")
    names = {oid: name for name, oid in oids.items()}
    found: dict[str, list[tuple[str, int, int]]] = {name: [] for name in oids}
    for row in rows:
        if len(row) != 4 or row[0] not in names or not isinstance(row[1], str) or type(row[2]) is not int or type(row[3]) is not int:
            raise Refused(code)
        found[names[row[0]]].append((row[1], row[2], row[3]))
    return found


def check_schema(s: _Session, contract: ViewContract, oids: dict[str, int]) -> Fact:
    found = read_attributes(s, oids)
    for v in contract.views:
        declared = [(col.name, col.source_oid, col.source_typmod) for col in v.columns]
        if found[v.view] != declared:
            raise Refused(FACT_SCHEMA, v.view)  # trailing, moved, retyped or a modifier changed
    return Fact(FACT_SCHEMA, True, {"views": {name: [list(c) for c in cols] for name, cols in sorted(found.items())}})


def collation_verdict(collation: dict, actual, build: Build) -> str:
    """N111: the build's collation exactly, and its version explicit — `verified`
    when the stored and the effective versions are present and equal, and
    `unavailable` when the build declares none and neither is reported. A
    version that appears where the build declares none, or a stored and an
    effective that differ, refuses."""
    if collation != build.collation:
        raise Refused(FACT_POLICY, check="collation")
    stored = collation["datcollversion"]
    if stored is None and actual is None:
        return "unavailable"
    if stored is not None and actual == stored:
        return "verified"
    raise Refused(FACT_POLICY, check="collation_version")  # drifted, or appeared under a build with none


def check_policy(s: _Session, build: Build) -> tuple[Fact, dict, dict]:
    for key in POLICY_KEYS:
        result = s.query(Q_SET_POLICY, (key, build.policy[key]), check="set_policy")
        if len(result) != 1 or len(result[0]) != 1 or not isinstance(result[0][0], str):
            raise Refused(FACT_POLICY, check="set_policy")  # missing, extra or null
    row = _one(s.query(Q_POLICY, check="policy"), FACT_POLICY)
    if len(row) != len(POLICY_KEYS) + 2 or any(not isinstance(v, str) for v in row):
        raise Refused(FACT_POLICY)
    policy = dict(zip(POLICY_KEYS, row[: len(POLICY_KEYS)]))
    server_encoding, client_encoding = row[len(POLICY_KEYS) :]
    if policy != build.policy or server_encoding != "UTF8" or client_encoding != "UTF8":
        raise Refused(FACT_POLICY, check="settings")
    collation_row = _one(s.query(Q_COLLATION, check="collation"), FACT_POLICY)
    if len(collation_row) != len(COLLATION_KEYS) + 1 or any(v is not None and not isinstance(v, str) for v in collation_row):
        raise Refused(FACT_POLICY)
    collation = dict(zip(COLLATION_KEYS, collation_row[: len(COLLATION_KEYS)]))
    actual = collation_row[-1]
    verdict = collation_verdict(collation, actual, build)
    read_back = {**policy, "server_encoding": server_encoding, "client_encoding": client_encoding}
    collation_read = {**collation, "actual_version": actual, "version": verdict}
    return Fact(FACT_POLICY, True, {"settings": read_back, "collation": collation_read}), read_back, collation_read


def facts(s: _Session, contract: ViewContract):
    """§3, checks 1 to 8, in their order."""
    f1, read_at = check_transaction(s)
    f2, build, provenance = check_provenance(s, contract)
    f3 = check_login(s, contract.login)
    f4 = check_roles(s, contract)
    f5, oids = check_inventory(s, {v.view for v in contract.views})
    f6 = check_access(s, oids)
    f7 = check_schema(s, contract, oids)
    f8, policy, collation = check_policy(s, build)
    return [f1, f2, f3, f4, f5, f6, f7, f8], read_at, build, provenance, policy, collation, oids


def read_view(s: _Session, view: View, build: Build, freeze: Callable) -> ViewRead:
    """§3, the rows, then §6 on the frozen reference, then the witness."""
    (count,) = _one(s.query(q_count(view.view), check="count", view=view.view), SIZE_OVER)
    if type(count) is not int:
        raise Refused(SIZE_OVER, view.view, "size")
    if count > view.max_rows:
        raise Refused(SIZE_OVER, view.view, "size")  # before any row is fetched
    if count == 0 and not view.may_be_empty:
        raise Refused(SIZE_EMPTY, view.view, "size")
    fields = s.described(q_rows(view), view.view)
    declared = [(col.name, col.source_oid, col.source_typmod) for col in view.columns]
    if fields != [*declared, FINGERPRINT_COLUMN]:
        raise Refused(RESULT_SCHEMA, view.view, "schema")  # before any row is read
    raw = s.fetch(view.view)
    if len(raw) != count:
        raise Refused(SIZE_OVER if len(raw) > count else SIZE_EMPTY, view.view, "size")
    width = len(view.columns)
    if any(not isinstance(r, tuple) or len(r) != width + 1 for r in raw):
        raise Refused(RESULT_SCHEMA, view.view, "schema")
    fingerprints = {r[width] for r in raw}
    if raw and (len(fingerprints) != 1 or not isinstance(next(iter(fingerprints)), str)):
        raise Refused(WITNESS_MISMATCH, view.view, "witness")
    got_md5 = next(iter(fingerprints)) if raw else EMPTY_FINGERPRINT
    frozen = freeze(view, [r[:width] for r in raw])
    witness_rows, witness_md5 = build.witness[view.view]
    if len(raw) != witness_rows or got_md5 != witness_md5:
        raise Refused(WITNESS_MISMATCH, view.view, "witness")  # after §6, so a row's own check comes first
    return ViewRead(view, len(raw), got_md5, True, frozen)


def read(source: Source, contract: ViewContract, freeze: Callable, clock=None) -> Read:
    """The whole read, in one transaction: the facts, then each view in the
    contract's order, then COMMIT. Any failure refuses; nothing is retried."""
    clock = clock or _monotonic
    s = _Session(source)
    timings = {}
    t0 = clock()
    found, read_at, build, provenance, policy, collation, _oids = facts(s, contract)
    timings["facts"] = clock() - t0
    t0 = clock()
    views = {}
    for view in contract.views:
        views[view.view] = read_view(s, view, build, freeze)
    try:
        source.commit()
    except Exception as exc:
        raise Refused(COMMIT_FAILED, cause=type(exc).__name__) from None
    timings["read"] = clock() - t0
    return Read(read_at, provenance, build, policy, collation, found, views, timings)


def catalogue(source: Source, login: str, names: set[str], provenance: dict) -> dict:
    """§3 check 7's baseline, read and not inferred (EXP-3-02): checks 1 to 6 in
    the same kind of transaction — against the capture's login, views and
    provenance, since the contract does not exist yet, with the role closure
    measured — then `pg_attribute` for the views, the session's text-form
    settings and the database's collation as they are by default. No row."""
    s = _Session(source)
    check_transaction(s)
    row = provenance_row(s)
    if {k: row[k] for k in ("built_from_commit", "invocation_id", "sequence")} != provenance:
        raise Refused(FACT_PROVENANCE)
    check_login(s, login)
    memberships, can_login = measure_roles(s)
    _fact, oids = check_inventory(s, names)
    check_access(s, oids)
    attributes = read_attributes(s, oids)
    settings_row = _one(s.query(Q_POLICY, check="policy"), FACT_POLICY)
    if len(settings_row) != len(POLICY_KEYS) + 2 or any(not isinstance(v, str) for v in settings_row):
        raise Refused(FACT_POLICY)
    collation_row = _one(s.query(Q_COLLATION, check="collation"), FACT_POLICY)
    if len(collation_row) != len(COLLATION_KEYS) + 1:
        raise Refused(FACT_POLICY)
    try:
        source.commit()
    except Exception as exc:
        raise Refused(COMMIT_FAILED, cause=type(exc).__name__) from None
    return {
        "catalogue_version": 1,
        "login": login,
        "provenance": row,
        "memberships": [{"member": m, "role": r, "inherit_option": i, "set_option": so} for m, r, i, so in memberships],
        "can_login": [{"role": k, "rolcanlogin": v} for k, v in sorted(can_login.items())],
        "views": [
            {"view": name, "columns": [{"name": n, "oid": o, "typmod": m} for n, o, m in attributes[name]]}
            for name in sorted(attributes)
        ],
        "defaults": dict(zip(POLICY_KEYS, settings_row[: len(POLICY_KEYS)])),
        "encodings": {"server_encoding": settings_row[-2], "client_encoding": settings_row[-1]},
        "collation": dict(zip(COLLATION_KEYS, collation_row[: len(COLLATION_KEYS)])),
        "collation_actual_version": collation_row[-1],
    }


def _monotonic() -> float:
    import time

    return time.monotonic()


def connect(found: Settings, absent: pathlib.Path, environ=None) -> Source:
    """Scrubs the environment, then opens the one connection. A failure to
    connect refuses with its code and the exception's class only."""
    scrub_environment(os.environ if environ is None else environ)
    parameters = connection_parameters(found, absent)
    try:
        return PsycopgSource(parameters)
    except Exception as exc:
        raise Refused(CONNECT_FAILED, cause=type(exc).__name__) from None
