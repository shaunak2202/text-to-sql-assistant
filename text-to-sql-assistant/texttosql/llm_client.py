"""
Generates SQL from a prompt/question.

Tries OpenAI first (if OPENAI_API_KEY is set and the call succeeds), and
falls back to a small rule-based generator otherwise. The fallback exists so
the rest of the pipeline (prompting, validation, execution) is demonstrable
and testable without any external API — it is a deliberately simple
pattern-matcher, not a language model, and should not be described as one.
"""
import os
import re
from typing import Dict, Optional

from .schema import TableInfo


class GenerationError(Exception):
    pass


def _call_openai(prompt: str) -> Optional[str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    try:
        client = OpenAI(api_key=api_key)
        model = os.environ.get("TEXT2SQL_MODEL", "gpt-4o-mini")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a careful SQL generation assistant. Reply "
                        "with ONLY a single SQL SELECT statement — no "
                        "commentary, no markdown fences."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        content = response.choices[0].message.content
        return content.strip() if content else None
    except Exception:
        # Any API/network error falls back to the rule-based generator
        # rather than crashing the whole pipeline.
        return None


def _best_table_match(question: str, schema: Dict[str, TableInfo]) -> Optional[str]:
    question_lower = question.lower()
    # exact / substring match on table name (singular or plural)
    for table_name in schema:
        singular = table_name[:-1] if table_name.endswith("s") else table_name
        if table_name in question_lower or singular in question_lower:
            return table_name
    return None


def _best_column_match(question: str, table: TableInfo) -> Optional[str]:
    question_lower = question.lower()
    for col in table.columns:
        if col.name.lower() in question_lower:
            return col.name
    return None


def _rule_based_generate(question: str, schema: Dict[str, TableInfo]) -> str:
    """A small, honest, pattern-matching fallback — not an ML model."""
    q = question.strip().lower()
    table_name = _best_table_match(q, schema)

    if table_name is None:
        # Default to the first table alphabetically as a last resort so the
        # pipeline still produces *something* syntactically valid.
        table_name = sorted(schema.keys())[0]

    table = schema[table_name]

    count_match = re.search(r"how many", q)
    if count_match:
        return f"SELECT COUNT(*) FROM {table_name};"

    top_n_match = re.search(r"top\s+(\d+)", q)
    if top_n_match:
        n = top_n_match.group(1)
        order_col = _best_column_match(q, table) or (
            table.columns[0].name if table.columns else "rowid"
        )
        return f"SELECT * FROM {table_name} ORDER BY {order_col} DESC LIMIT {n};"

    avg_match = re.search(r"average\s+(\w+)", q)
    if avg_match:
        col_hint = avg_match.group(1)
        col = _best_column_match(col_hint, table) or (
            table.columns[0].name if table.columns else None
        )
        if col:
            return f"SELECT AVG({col}) FROM {table_name};"

    if "list" in q or "show" in q or "all" in q:
        return f"SELECT * FROM {table_name} LIMIT 20;"

    # Generic fallback: just return a bounded sample of the best-matched table.
    return f"SELECT * FROM {table_name} LIMIT 10;"


def generate_sql(prompt: str, question: str, schema: Dict[str, TableInfo]) -> str:
    """
    Returns a raw SQL string (not yet validated). Tries OpenAI, falls back
    to the rule-based generator. Raises GenerationError only if both paths
    somehow fail to produce anything.
    """
    sql = _call_openai(prompt)
    source = "openai"
    if sql is None:
        sql = _rule_based_generate(question, schema)
        source = "rule_based"

    if not sql:
        raise GenerationError("no SQL could be generated")

    # strip accidental markdown fences from LLM output
    sql = re.sub(r"^```(?:sql)?\s*|\s*```$", "", sql.strip(), flags=re.IGNORECASE)
    return sql, source
