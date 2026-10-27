import sqlite3

import pytest
from fastapi.testclient import TestClient

from db.seed import seed
from api import create_app


@pytest.fixture
def client(tmp_path):
    db_path = tmp_path / "test_shop.db"
    conn = sqlite3.connect(db_path)
    seed(conn)
    conn.close()

    app = create_app(str(db_path))
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_schema_endpoint(client):
    resp = client.get("/schema")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["tables"]) == {"customers", "products", "orders", "order_items"}
    assert "CREATE TABLE customers" in data["schema_text"]


def test_ask_count_customers(client):
    resp = client.post("/ask", json={"question": "how many customers are there"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "SELECT COUNT(*)" in data["sql"].upper()
    assert data["rows"][0]["COUNT(*)"] == 25


def test_ask_list_products_returns_rows(client):
    resp = client.post("/ask", json={"question": "list all products"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert len(data["rows"]) == 10
    assert "price" in data["columns"]


def test_ask_rejects_blank_question(client):
    resp = client.post("/ask", json={"question": ""})
    assert resp.status_code == 422


def test_ask_rejects_missing_question_field(client):
    resp = client.post("/ask", json={})
    assert resp.status_code == 422


def test_startup_fails_on_missing_db(tmp_path):
    missing_path = tmp_path / "does_not_exist.db"
    app = create_app(str(missing_path))
    with pytest.raises(RuntimeError):
        with TestClient(app):
            pass


def test_cors_headers_present_for_frontend_origin(client):
    # The React dev server runs on localhost:5173; make sure the permissive
    # CORS config actually lets a browser call this API from there.
    resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"


def test_cors_preflight_for_ask(client):
    resp = client.options(
        "/ask",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "*"
