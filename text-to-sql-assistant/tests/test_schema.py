import sqlite3

import pytest

from texttosql.schema import SchemaIntrospector
from db.seed import seed


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    seed(connection)
    yield connection
    connection.close()


def test_lists_expected_tables(conn):
    introspector = SchemaIntrospector(conn)
    schema = introspector.get_schema()
    assert set(schema.keys()) == {"customers", "products", "orders", "order_items"}


def test_customers_columns(conn):
    introspector = SchemaIntrospector(conn)
    schema = introspector.get_schema()
    cols = schema["customers"].column_names()
    assert "customer_id" in cols
    assert "email" in cols
    assert "state" in cols


def test_foreign_keys_detected(conn):
    introspector = SchemaIntrospector(conn)
    schema = introspector.get_schema()
    assert any("customer_id" in fk for fk in schema["orders"].foreign_keys)


def test_format_for_prompt_contains_create_table(conn):
    introspector = SchemaIntrospector(conn)
    text = introspector.format_for_prompt()
    assert "CREATE TABLE customers" in text
    assert "CREATE TABLE orders" in text
