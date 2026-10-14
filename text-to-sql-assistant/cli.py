#!/usr/bin/env python3
"""
Interactive CLI for the Text-to-SQL Query Assistant.

Usage:
    python cli.py [path-to-sqlite-db]

Defaults to db/shop.db. Run `python db/seed.py` first if it doesn't exist.
"""
import sys
from pathlib import Path

from dotenv import load_dotenv
from tabulate import tabulate

from texttosql.engine import TextToSQLEngine

load_dotenv()


def print_result(result) -> None:
    print(f"  SQL ({result.source}): {result.sql}")
    if not result.ok:
        print(f"  \u2717 {result.error}")
        return
    if not result.rows:
        print("  (no rows)")
        return
    print(tabulate(result.rows, headers="keys", tablefmt="simple"))
    print(f"  [{len(result.rows)} row(s) in {result.elapsed_seconds:.3f}s]")


def main() -> None:
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "db" / "shop.db")
    if not Path(db_path).exists():
        print(f"Database not found at {db_path}. Run `python db/seed.py` first.")
        sys.exit(1)

    engine = TextToSQLEngine(db_path)
    print(f"Connected to {db_path}")
    print(f"Tables: {', '.join(engine.schema.keys())}")
    print("Type a question in plain English, or 'quit' to exit.\n")

    try:
        while True:
            try:
                question = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not question:
                continue
            if question.lower() in {"quit", "exit"}:
                break
            result = engine.ask(question)
            print_result(result)
            print()
    finally:
        engine.close()


if __name__ == "__main__":
    main()
