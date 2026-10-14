"""
Prompt construction for SQL generation.

Keeps the prompt-building logic isolated so it can be iterated on and
tested independently of whichever model/backend ends up calling it.
"""
from typing import List, Tuple

FEW_SHOT_EXAMPLES: List[Tuple[str, str]] = [
    (
        "how many customers signed up from Illinois",
        "SELECT COUNT(*) FROM customers WHERE state = 'IL';",
    ),
    (
        "list the 5 most expensive products",
        "SELECT * FROM products ORDER BY price DESC LIMIT 5;",
    ),
    (
        "total revenue per product category",
        "SELECT p.category, SUM(oi.quantity * oi.unit_price) AS revenue "
        "FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
        "GROUP BY p.category ORDER BY revenue DESC;",
    ),
]

SYSTEM_PREAMBLE = (
    "You translate natural language questions into a single valid SQLite "
    "SELECT statement. Only use the tables and columns given in the schema. "
    "Never write INSERT, UPDATE, DELETE, DROP, ALTER, ATTACH, or PRAGMA "
    "statements. Return ONLY the SQL statement, with no explanation and no "
    "markdown code fences."
)


def build_prompt(schema_text: str, question: str, examples: List[Tuple[str, str]] = None) -> str:
    examples = examples if examples is not None else FEW_SHOT_EXAMPLES
    example_block = "\n\n".join(
        f"Question: {q}\nSQL: {sql}" for q, sql in examples
    )
    return (
        f"{SYSTEM_PREAMBLE}\n\n"
        f"Schema:\n{schema_text}\n\n"
        f"Examples:\n{example_block}\n\n"
        f"Question: {question}\nSQL:"
    )
