"""
A small hand-labeled evaluation set.

Each case pairs a plain-English question with a hand-written reference SQL
query that is known to answer it correctly against the seeded sample
database (db/seed.py). `run_eval.py` executes both the engine's generated
SQL and the reference SQL and compares the resulting rows.

This set is intentionally small and documents, rather than hides, the known
limitations of the rule-based fallback generator (filtering by a literal
value, and join + GROUP BY queries) — those cases are expected to fail
without a real LLM configured, and the `note` field says so.
"""
from typing import NamedTuple


class EvalCase(NamedTuple):
    question: str
    reference_sql: str
    note: str = ""


EVAL_SET = [
    EvalCase(
        "how many customers are there",
        "SELECT COUNT(*) FROM customers;",
    ),
    EvalCase(
        "how many orders are there",
        "SELECT COUNT(*) FROM orders;",
    ),
    EvalCase(
        "list all products",
        "SELECT * FROM products;",
    ),
    EvalCase(
        "top 3 products by price",
        "SELECT * FROM products ORDER BY price DESC LIMIT 3;",
    ),
    EvalCase(
        "average price of products",
        "SELECT AVG(price) FROM products;",
    ),
    EvalCase(
        "how many products are in the Electronics category",
        "SELECT COUNT(*) FROM products WHERE category = 'Electronics';",
        note=(
            "the rule-based fallback has no concept of filtering by a "
            "literal value from the question, so this is expected to fail "
            "without a real LLM configured."
        ),
    ),
    EvalCase(
        "total revenue per product category",
        "SELECT p.category, SUM(oi.quantity * oi.unit_price) AS revenue "
        "FROM order_items oi JOIN products p ON oi.product_id = p.product_id "
        "GROUP BY p.category ORDER BY revenue DESC;",
        note=(
            "requires a join plus GROUP BY, which the rule-based fallback "
            "cannot produce; expected to pass only with a real LLM "
            "configured."
        ),
    ),
]
