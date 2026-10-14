import pytest

from texttosql.validator import validate_sql, SQLValidationError
from texttosql.schema import TableInfo, ColumnInfo

SCHEMA = {
    "customers": TableInfo(
        name="customers",
        columns=[ColumnInfo("customer_id", "INTEGER", True), ColumnInfo("name", "TEXT")],
    ),
    "orders": TableInfo(
        name="orders",
        columns=[ColumnInfo("order_id", "INTEGER", True), ColumnInfo("customer_id", "INTEGER")],
    ),
}


def test_accepts_simple_select():
    sql = "SELECT * FROM customers"
    cleaned = validate_sql(sql, SCHEMA)
    assert cleaned == "SELECT * FROM customers;"


def test_accepts_join_with_known_tables():
    sql = (
        "SELECT c.name FROM customers c "
        "JOIN orders o ON c.customer_id = o.customer_id"
    )
    cleaned = validate_sql(sql, SCHEMA)
    assert "JOIN" in cleaned


def test_rejects_drop_table():
    with pytest.raises(SQLValidationError):
        validate_sql("DROP TABLE customers", SCHEMA)


def test_rejects_delete():
    with pytest.raises(SQLValidationError):
        validate_sql("DELETE FROM customers WHERE customer_id = 1", SCHEMA)


def test_rejects_multiple_statements():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM customers; DROP TABLE customers;", SCHEMA)


def test_rejects_unknown_table():
    with pytest.raises(SQLValidationError):
        validate_sql("SELECT * FROM secret_table", SCHEMA)


def test_rejects_empty_sql():
    with pytest.raises(SQLValidationError):
        validate_sql("", SCHEMA)


def test_rejects_pragma():
    with pytest.raises(SQLValidationError):
        validate_sql("PRAGMA table_info(customers)", SCHEMA)
