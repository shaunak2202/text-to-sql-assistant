#!/usr/bin/env python3
"""
FastAPI backend for the Text-to-SQL Query Assistant.

Exposes the same TextToSQLEngine used by the CLI over HTTP so a front end
(or curl, or a test suite) can use it without going through the REPL.

Run:
    python db/seed.py                 # if db/shop.db doesn't exist yet
    uvicorn api:app --reload

Endpoints:
    GET  /health   -> liveness check
    GET  /schema   -> introspected tables + prompt-ready schema text
    POST /ask      -> {"question": "..."} -> generated SQL + rows
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

from texttosql.engine import TextToSQLEngine

load_dotenv()

DEFAULT_DB_PATH = str(Path(__file__).parent / "db" / "shop.db")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=500)


class AskResponse(BaseModel):
    question: str
    sql: str
    source: str
    ok: bool
    rows: List[Dict[str, Any]] = []
    columns: List[str] = []
    elapsed_seconds: float = 0.0
    error: str = ""


class SchemaResponse(BaseModel):
    tables: List[str]
    schema_text: str


def create_app(db_path: Optional[str] = None) -> FastAPI:
    """
    Builds a FastAPI app bound to `db_path` (or $TEXT2SQL_DB_PATH, or the
    default sample DB). Factored out as a function rather than a bare
    module-level `app` so tests can spin up independent apps against
    isolated temp databases.
    """
    resolved_path = db_path or os.environ.get("TEXT2SQL_DB_PATH") or DEFAULT_DB_PATH

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if not Path(resolved_path).exists():
            raise RuntimeError(
                f"Database not found at {resolved_path}. "
                "Run `python db/seed.py` first, or set TEXT2SQL_DB_PATH."
            )
        app.state.engine = TextToSQLEngine(resolved_path)
        try:
            yield
        finally:
            app.state.engine.close()

    app = FastAPI(
        title="Text-to-SQL Query Assistant API",
        description=(
            "Schema-grounded natural language to SQL over a SQLite "
            "database, with a safety validator in front of execution."
        ),
        version="0.2.0",
        lifespan=lifespan,
    )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.get("/schema", response_model=SchemaResponse)
    def get_schema() -> SchemaResponse:
        engine: TextToSQLEngine = app.state.engine
        return SchemaResponse(
            tables=list(engine.schema.keys()),
            schema_text=engine.schema_text,
        )

    @app.post("/ask", response_model=AskResponse)
    def ask(request: AskRequest) -> AskResponse:
        engine: TextToSQLEngine = app.state.engine
        result = engine.ask(request.question)
        return AskResponse(
            question=result.question,
            sql=result.sql,
            source=result.source,
            ok=result.ok,
            rows=result.rows,
            columns=result.columns,
            elapsed_seconds=result.elapsed_seconds,
            error=result.error,
        )

    return app


# Module-level app for `uvicorn api:app`. The DB existence check happens at
# startup (lifespan), not at import time, so simply importing this module
# never fails even if the sample DB hasn't been seeded yet.
app = create_app()
