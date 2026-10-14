# Text-to-SQL Query Assistant

A schema-aware natural language to SQL engine. Point it at a SQLite database,
ask a question in plain English, and it generates, **validates**, and executes
a safe `SELECT` statement against your schema — returning real rows, not a
guess at what the data might look like.

This is an NLP/LLM engineering project, not a toy wrapper around an API call:
most of the work is in (1) turning a live DB schema into a prompt the model
can actually use, and (2) a validation layer that refuses to run anything
that isn't a safe, single, read-only query against known tables/columns.

## Why this exists

"Chat with your database" demos usually skip two things that matter in a
real system: grounding the model in the *actual* schema (not a hand-written
one that drifts from reality), and treating LLM output as untrusted input
before it touches a database connection. This project tries to do both
honestly, including an offline fallback mode so the core pipeline is
demonstrable without an API key.

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
├── cli.py                    # interactive REPL
└── tests/
    ├── test_validator.py
    └── test_schema.py
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

The CLI (and `engine.py`) will automatically use OpenAI when the key is
present and silently fall back to the rule-based generator otherwise, so the
project is fully runnable with zero API keys.

## Example session

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

## Sample database

`db/seed.py` creates a small e-commerce schema: `customers`, `products`,
`orders`, `order_items`, with foreign keys between them and a handful of
rows — enough to exercise joins, aggregates, and filtering in the generated
SQL.

## Tests

```bash
pytest
```

Covers the validator (rejects destructive SQL, multi-statement injection,
unknown tables) and the schema introspector (correctly reads the seeded DB).

## Status / roadmap

This is the first milestone. Working now: schema introspection, prompt
construction, rule-based + OpenAI generation, SQL safety validation, CLI.

Planned next:
- FastAPI backend exposing `/ask` so this can sit behind a small React
  front end instead of just the CLI.
- A lightweight eval set (question → expected SQL/result) to track
  generation accuracy across prompt changes, similar in spirit to a
  regression test suite.
- Conversation memory so follow-up questions ("now just the ones from
  Illinois") can refine the previous query.

## Honesty note

The rule-based fallback is deliberately simple and is there so the
validation/execution pipeline can be demoed and tested without any external
API dependency — it is not presented as a substitute for an actual language
model, and the README/code say so explicitly.
