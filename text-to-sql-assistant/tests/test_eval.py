import sqlite3

import pytest

from db.seed import seed
from eval.run_eval import run_eval


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "eval_shop.db"
    conn = sqlite3.connect(path)
    seed(conn)
    conn.close()
    return str(path)


def test_rule_based_eval_known_cases_pass(db_path, monkeypatch):
    # Force the rule-based fallback regardless of whether OPENAI_API_KEY
    # happens to be set in the environment running the tests, so this test
    # is deterministic.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    report = run_eval(db_path)
    assert report["total"] == len(report["results"])

    by_question = {r["question"]: r for r in report["results"]}

    # solvable by the simple rule-based generator
    assert by_question["how many customers are there"]["match"] is True
    assert by_question["how many orders are there"]["match"] is True
    assert by_question["list all products"]["match"] is True
    assert by_question["top 3 products by price"]["match"] is True
    assert by_question["average price of products"]["match"] is True

    # documented, known limitations of the rule-based fallback
    assert by_question["total revenue per product category"]["match"] is False


def test_accuracy_is_reasonable_without_llm(db_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = run_eval(db_path)
    # the rule-based fallback should handle the easy majority of cases
    assert report["accuracy"] >= 0.6


def test_report_contains_sql_for_every_case(db_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    report = run_eval(db_path)
    for r in report["results"]:
        assert r["generated_sql"], f"no SQL generated for: {r['question']}"
        assert r["source"] in {"openai", "rule_based"}
