"""
Orchestrates the full pipeline: schema introspection -> prompt -> generation
-> validation -> execution.
"""
import sqlite3
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .schema import SchemaIntrospector
from .prompt import build_prompt
from .llm_client import generate_sql, GenerationError
from .validator import validate_sql, SQLValidationError


@dataclass
class QueryResult:
    question: str
    sql: str
    source: str  # "openai" or "rule_based"
    rows: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0
    error: str = ""

    @property
    def ok(self) -> bool:
        return not self.error


class TextToSQLEngine:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.introspector = SchemaIntrospector(self.conn)
        self.schema = self.introspector.get_schema()
        self.schema_text = self.introspector.format_for_prompt(self.schema)

    def refresh_schema(self) -> None:
        self.schema = self.introspector.get_schema()
        self.schema_text = self.introspector.format_for_prompt(self.schema)

    def ask(self, question: str) -> QueryResult:
        start = time.time()
        prompt = build_prompt(self.schema_text, question)

        try:
            raw_sql, source = generate_sql(prompt, question, self.schema)
        except GenerationError as exc:
            return QueryResult(question=question, sql="", source="none",
                                error=f"generation failed: {exc}",
                                elapsed_seconds=time.time() - start)

        try:
            safe_sql = validate_sql(raw_sql, self.schema)
        except SQLValidationError as exc:
            return QueryResult(question=question, sql=raw_sql, source=source,
                                error=f"rejected: {exc}",
                                elapsed_seconds=time.time() - start)

        try:
            cursor = self.conn.execute(safe_sql)
            rows = [dict(row) for row in cursor.fetchall()]
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
        except sqlite3.Error as exc:
            return QueryResult(question=question, sql=safe_sql, source=source,
                                error=f"execution failed: {exc}",
                                elapsed_seconds=time.time() - start)

        return QueryResult(
            question=question,
            sql=safe_sql,
            source=source,
            rows=rows,
            columns=columns,
            elapsed_seconds=time.time() - start,
        )

    def close(self) -> None:
        self.conn.close()
