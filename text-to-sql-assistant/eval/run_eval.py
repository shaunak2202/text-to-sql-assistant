"""
Runs the evaluation set against a seeded database and reports how many
generated queries return results matching a hand-written reference query.

This measures result correctness, not SQL text similarity: two
syntactically different queries that return the same rows both count as a
pass. It's a deliberately small, honest eval set (not a benchmark claim)
meant to catch regressions when the prompt or fallback logic changes, and to
make the fallback's known limitations explicit rather than discovered by
accident.

Usage:
    python -m eval.run_eval [path-to-db]
"""
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, List

from texttosql.engine import TextToSQLEngine
from .eval_set import EVAL_SET


def _normalize(rows: List[Any]) -> list:
    """Row-order and column-name agnostic view of a result set, so two
    queries that return the same data in a different shape/order still
    compare equal."""
    normalized = []
    for row in rows:
        values = tuple(row.values()) if isinstance(row, dict) else tuple(row)
        normalized.append(values)
    return sorted(normalized, key=lambda t: [str(v) for v in t])


def run_eval(db_path: str) -> dict:
    engine = TextToSQLEngine(db_path)
    ref_conn = sqlite3.connect(db_path)
    ref_conn.row_factory = sqlite3.Row

    results = []
    passed = 0
    try:
        for case in EVAL_SET:
            result = engine.ask(case.question)

            try:
                ref_rows = [dict(r) for r in ref_conn.execute(case.reference_sql).fetchall()]
                ref_ok = True
            except sqlite3.Error as exc:
                ref_rows, ref_ok = [], False
                result = result  # keep generated result as-is for reporting

            match = bool(result.ok and ref_ok and _normalize(result.rows) == _normalize(ref_rows))
            if match:
                passed += 1

            results.append({
                "question": case.question,
                "note": case.note,
                "generated_sql": result.sql,
                "source": result.source,
                "generated_ok": result.ok,
                "generated_error": result.error,
                "reference_sql": case.reference_sql,
                "match": match,
            })
    finally:
        engine.close()
        ref_conn.close()

    total = len(EVAL_SET)
    accuracy = passed / total if total else 0.0
    return {"accuracy": accuracy, "passed": passed, "total": total, "results": results}


def main() -> None:
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(
        Path(__file__).parent.parent / "db" / "shop.db"
    )
    if not Path(db_path).exists():
        print(f"Database not found at {db_path}. Run `python db/seed.py` first.")
        sys.exit(1)

    report = run_eval(db_path)
    for r in report["results"]:
        status = "PASS" if r["match"] else "FAIL"
        print(f"[{status}] ({r['source']}) {r['question']}")
        print(f"       generated: {r['generated_sql']}")
        print(f"       reference: {r['reference_sql']}")
        if r["note"]:
            print(f"       note: {r['note']}")
        if not r["match"] and r["generated_error"]:
            print(f"       error: {r['generated_error']}")
        print()

    print(f"Accuracy: {report['passed']}/{report['total']} "
          f"({report['accuracy'] * 100:.1f}%)")

    out_path = Path(__file__).parent / "report.json"
    out_path.write_text(json.dumps(report, indent=2, default=str))
    print(f"Full report written to {out_path}")


if __name__ == "__main__":
    main()
