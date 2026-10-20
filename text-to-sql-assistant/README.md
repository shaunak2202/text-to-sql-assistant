# Text-to-SQL Query Assistant

A schema-aware natural language to SQL engine. Point it at a SQLite database,
ask a question in plain English, and it generates, **validates**, and executes
a safe `SELECT` statement against your schema — returning real rows, not a
guess at what the data might look like.

This is an NLP/LLM engineering project, not a toy wrapper around an API call:
most of the work is in (1) turning a live DB schema into a prompt the model
can actually use, (2) a validation layer that refuses to run anything that
isn't a safe, single, read-only query against known tables/columns, and
(3) an eval harness that measures whether the generated SQL actually returns
the right rows.

## Why this exists

"Chat with your database" demos usually skip three things that matter in a
real system: grounding the model in the *actual* schema (not a hand-written
one that drifts from reality), treating LLM output as untrusted input before
it touches a database connection, and having any way to tell whether
generation quality improved or regressed after a prompt change. This project
tries to do all three honestly, including an offline fallback mode so the
core pipeline is demonstrable without an API key.

## How it works

```
question ──▶ SchemaIntrospector ──▶ prompt.build_prompt ──▶ llm_client.generate_sql
                                                                   │
                                                                   ▼
                                                           validator.validate_sql
                                                                   │
                                                                   ▼
                                                        sqlite3 execution (read-only)
                                                                   │
                                                                   ▼
                                                             rows + timing
```

exposed over two interfaces — a CLI and a FastAPI HTTP API — that both sit
on top of the same `TextToSQLEngine`.

1. **`texttosql/schema.py`** — introspects the live SQLite DB (tables,
   columns, types, foreign keys) and renders it as compact `CREATE TABLE`-like
   text for the prompt. No hard-coded schema anywhere.
2. **`texttosql/prompt.py`** — builds the final prompt: schema + a few
   few-shot examples + the user's question.
3. **`texttosql/llm_client.py`** — calls an OpenAI chat model if
   `OPENAI_API_KEY` is set. If it isn't (or the call fails), it falls back to
   a small **rule-based generator** that pattern-matches common question
   shapes ("how many X", "list all X", "top N X by Y", "average Y of X")
   against the real schema. This fallback is intentionally simple — it's a
   demo/offline mode, not a claim that regex is a language model.
4. **`texttosql/validator.py`** — parses the generated SQL with `sqlparse`
   and rejects anything that:
   - isn't exactly one statement,
   - isn't a `SELECT`,
   - references a table not present in the introspected schema,
   - contains write/DDL/pragma/attach keywords.
5. **`texttosql/engine.py`** — wires the above together and executes the
   validated query against the DB.
6. **`api.py`** — a thin FastAPI layer exposing the same engine over HTTP
   (`/ask`, `/schema`, `/health`), so a front end (or `curl`) can use this
   without going through the CLI.
7. **`eval/`** — a small hand-labeled set of (question, reference SQL) pairs
   used to measure whether generated queries return *correct results*, not
   just plausible-looking SQL.

## Project layout

```
text-to-sql-assistant/
├── db/
│   └── seed.py              # builds a small sample e-commerce SQLite DB
├── texttosql/
│   ├── schema.py             # schema introspection
│   ├── prompt.py              # prompt construction
│   ├── llm_client.py          # OpenAI call + rule-based fallback
│   ├── validator.py           # SQL safety validation
│   └── engine.py               # orchestration
├── eval/
│   ├── eval_set.py            # hand-labeled question -> reference SQL cases
│   └── run_eval.py             # runs the eval set, reports accuracy
├── cli.py                    # interactive REPL
├── api.py                    # FastAPI HTTP server (/ask, /schema, /health)
└── tests/
    ├── test_validator.py
    ├── test_schema.py
    ├── test_api.py
    └── test_eval.py
```

## Setup

```bash
pip install -r requirements.txt
python db/seed.py                 # creates db/shop.db with sample data
python cli.py                     # interactive REPL
```

To use real LLM generation instead of the rule-based fallback:

```bash
cp .env.example .env
# edit .env and set OPENAI_API_KEY=sk-...
```

The CLI, API, and `engine.py` all automatically use OpenAI when the key is
present and silently fall back to the rule-based generator otherwise, so the
project is fully runnable with zero API keys.

## Example CLI session

```
$ python cli.py
Connected to db/shop.db
Tables: customers, products, orders, order_items

> how many customers are there
  SQL: SELECT COUNT(*) FROM customers;
  ┌──────────┐
  │ COUNT(*) │
  ├──────────┤
  │ 25       │
  └──────────┘

> list all products
  SQL: SELECT * FROM products LIMIT 20;
  ...

> drop table customers
  ✗ Rejected: only SELECT statements are allowed (found: DROP)
```

## HTTP API

```bash
python db/seed.py
uvicorn api:app --reload
```

- `GET /health` — liveness check.
- `GET /schema` — returns the introspected tables and a prompt-ready schema
  rendering.
- `POST /ask` — body `{"question": "how many customers are there"}`, returns
  the generated SQL, its source (`openai` or `rule_based`), the result rows,
  and whether it succeeded.

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "top 3 products by price"}'
```

```json
{
  "question": "top 3 products by price",
  "sql": "SELECT * FROM products ORDER BY price DESC LIMIT 3;",
  "source": "rule_based",
  "ok": true,
  "rows": [
    {"product_id": 6, "name": "Standing Desk", "category": "Home", "price": 249.0},
    {"product_id": 2, "name": "Mechanical Keyboard", "category": "Electronics", "price": 89.99},
    {"product_id": 10, "name": "RC Car", "category": "Toys", "price": 55.0}
  ],
  "columns": ["product_id", "name", "category", "price"],
  "elapsed_seconds": 0.0012,
  "error": ""
}
```

By default the API loads `db/shop.db`; point it elsewhere with
`TEXT2SQL_DB_PATH=/path/to/your.db`.

## Sample database

`db/seed.py` creates a small e-commerce schema: `customers`, `products`,
`orders`, `order_items`, with foreign keys between them and a handful of
rows — enough to exercise joins, aggregates, and filtering in the generated
SQL.

## Evaluation harness

Running `pytest` and manually trying questions tells you the pipeline
*works*; it doesn't tell you whether generation quality got better or worse
after changing the prompt or the fallback rules. `eval/` is a small,
explicit answer to that:

```bash
python db/seed.py
python -m eval.run_eval
```

Each case in `eval/eval_set.py` is a plain-English question paired with a
hand-written reference SQL query. `run_eval.py` executes **both** the
engine's generated SQL and the reference SQL against the same database and
compares the *result rows* — not the SQL text — so two differently-written
but equivalent queries both count as correct. It prints a pass/fail line per
case plus overall accuracy, and writes `eval/report.json` with the full
detail.

Running it with no `OPENAI_API_KEY` set (pure rule-based fallback) currently
scores correctly on straightforward count/list/top-n/average questions, and
honestly fails on the two cases that require filtering by a literal value or
a join + `GROUP BY` — those are exactly the cases the README already says
the rule-based fallback can't handle. The eval set documents that limitation
instead of hiding it, and gives a concrete way to check whether plugging in
a real LLM (or improving the fallback) actually fixes it.

## Tests

```bash
pytest
```

Covers the validator (rejects destructive SQL, multi-statement injection,
unknown tables), the schema introspector (correctly reads the seeded DB),
the FastAPI endpoints, and the eval harness's expected pass/fail cases on
the rule-based fallback.

## Status / roadmap

Working now: schema introspection, prompt construction, rule-based +
OpenAI generation, SQL safety validation, CLI, FastAPI backend, and a
result-based accuracy eval harness.

Planned next:
- A minimal React/Next.js front end that talks to the `/ask` endpoint,
  so this is demoable as a full web app, not just a CLI or `curl`.
- Conversation memory so follow-up questions ("now just the ones from
  Illinois") can refine the previous query instead of starting over.

## Honesty note

The rule-based fallback is deliberately simple and is there so the
validation/execution pipeline can be demoed and tested without any external
API dependency — it is not presented as a substitute for an actual language
model, and the README, code comments, and eval harness all say so
explicitly, including the specific question types it gets wrong.
