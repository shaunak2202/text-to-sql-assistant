"""
Schema introspection for SQLite databases.

Turns a live database connection into a structured description (tables,
columns, types, foreign keys) and a compact text rendering suitable for
embedding in an LLM prompt. This is what keeps the generator grounded in the
actual database instead of a hand-written, possibly stale, schema string.
"""
import sqlite3
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ColumnInfo:
    name: str
    type: str
    is_primary_key: bool = False


@dataclass
class TableInfo:
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    foreign_keys: List[str] = field(default_factory=list)  # human-readable strings

    def column_names(self) -> List[str]:
        return [c.name for c in self.columns]


class SchemaIntrospector:
    """Reads table/column/foreign-key metadata from a sqlite3 connection."""

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def _list_tables(self) -> List[str]:
        cur = self.conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in cur.fetchall()]

    def get_schema(self) -> Dict[str, TableInfo]:
        schema: Dict[str, TableInfo] = {}
        for table_name in self._list_tables():
            columns = []
            for row in self.conn.execute(f"PRAGMA table_info({table_name})"):
                # row: cid, name, type, notnull, dflt_value, pk
                columns.append(ColumnInfo(name=row[1], type=row[2] or "TEXT", is_primary_key=bool(row[5])))

            fks = []
            for row in self.conn.execute(f"PRAGMA foreign_key_list({table_name})"):
                # row: id, seq, table, from, to, on_update, on_delete, match
                fks.append(f"{table_name}.{row[3]} -> {row[2]}.{row[4]}")

            schema[table_name] = TableInfo(name=table_name, columns=columns, foreign_keys=fks)
        return schema

    def format_for_prompt(self, schema: Dict[str, TableInfo] = None) -> str:
        """Render the schema as CREATE TABLE-ish text for the LLM prompt."""
        schema = schema or self.get_schema()
        lines = []
        for table in schema.values():
            col_strs = [f"{c.name} {c.type}{' PRIMARY KEY' if c.is_primary_key else ''}" for c in table.columns]
            lines.append(f"CREATE TABLE {table.name} (")
            lines.append("    " + ",\n    ".join(col_strs))
            lines.append(");")
            for fk in table.foreign_keys:
                lines.append(f"-- foreign key: {fk}")
            lines.append("")
        return "\n".join(lines).strip()
