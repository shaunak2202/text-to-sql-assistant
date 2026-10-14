"""
Validates LLM-generated SQL before it ever touches a database connection.

This is the safety boundary of the project: we treat anything the model
produces as untrusted input. The validator rejects:
  - more than one statement (prevents stacked-query injection),
  - anything that isn't a SELECT,
  - any write/DDL/pragma/attach keyword appearing anywhere in the statement,
  - references to tables not present in the introspected schema.

It intentionally does NOT try to be a full SQL parser/analyzer — it's a
pragmatic guardrail, not a formal verifier, and the README says so.
"""
import re
from typing import Dict, Iterable

import sqlparse

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH",
    "DETACH", "PRAGMA", "REPLACE", "TRUNCATE", "VACUUM", "REINDEX",
    "GRANT", "REVOKE",
}

TABLE_REF_RE = re.compile(
    r"\b(?:FROM|JOIN)\s+([`\"\[]?)([A-Za-z_][A-Za-z0-9_]*)\1", re.IGNORECASE
)


class SQLValidationError(Exception):
    pass


def _strip_trailing_semicolon(sql: str) -> str:
    sql = sql.strip()
    if sql.endswith(";"):
        sql = sql[:-1]
    return sql.strip()


def _extract_statements(sql: str):
    return [s for s in sqlparse.split(sql) if s.strip()]


def _extract_table_refs(sql: str) -> Iterable[str]:
    return {m.group(2).lower() for m in TABLE_REF_RE.finditer(sql)}


def validate_sql(sql: str, schema: Dict) -> str:
    """
    Validates `sql` against `schema` (a dict of table_name -> TableInfo, as
    produced by SchemaIntrospector.get_schema()).

    Returns the cleaned single statement on success, raises
    SQLValidationError on any violation.
    """
    if not sql or not sql.strip():
        raise SQLValidationError("empty SQL generated")

    statements = _extract_statements(sql)
    if len(statements) != 1:
        raise SQLValidationError(
            f"expected exactly one statement, found {len(statements)}"
        )

    statement = statements[0]
    cleaned = _strip_trailing_semicolon(statement)

    upper = cleaned.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", upper):
            raise SQLValidationError(
                f"only SELECT statements are allowed (found keyword: {keyword})"
            )

    parsed = sqlparse.parse(cleaned)
    if not parsed:
        raise SQLValidationError("could not parse SQL")

    stmt_type = parsed[0].get_type()
    if stmt_type != "SELECT":
        raise SQLValidationError(
            f"only SELECT statements are allowed (found: {stmt_type})"
        )

    referenced_tables = _extract_table_refs(cleaned)
    known_tables = {name.lower() for name in schema.keys()}
    unknown = referenced_tables - known_tables
    if unknown:
        raise SQLValidationError(
            f"query references unknown table(s): {', '.join(sorted(unknown))}"
        )

    return cleaned + ";"
