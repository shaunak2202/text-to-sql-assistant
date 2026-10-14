"""
Creates a small sample e-commerce SQLite database used for demos and tests.

Run directly:
    python db/seed.py [path]

If no path is given, defaults to db/shop.db relative to this file.
"""
import sqlite3
import sys
from pathlib import Path

SCHEMA_SQL = """
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    state TEXT NOT NULL,
    signup_date TEXT NOT NULL
);

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price REAL NOT NULL
);

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);
"""

STATES = ["IL", "CA", "NY", "TX", "WA", "MA", "OH", "FL"]
CATEGORIES = ["Electronics", "Books", "Home", "Toys", "Sports"]


def seed(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    cur = conn.cursor()

    customers = [
        (i, f"Customer {i}", f"customer{i}@example.com",
         STATES[i % len(STATES)], f"2023-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}")
        for i in range(1, 26)
    ]
    cur.executemany(
        "INSERT INTO customers (customer_id, name, email, state, signup_date) "
        "VALUES (?, ?, ?, ?, ?)",
        customers,
    )

    products = [
        (1, "Wireless Mouse", "Electronics", 19.99),
        (2, "Mechanical Keyboard", "Electronics", 89.99),
        (3, "Python Crash Course", "Books", 34.99),
        (4, "Clean Code", "Books", 29.99),
        (5, "Desk Lamp", "Home", 24.50),
        (6, "Standing Desk", "Home", 249.00),
        (7, "Soccer Ball", "Sports", 15.00),
        (8, "Yoga Mat", "Sports", 22.00),
        (9, "Building Blocks Set", "Toys", 40.00),
        (10, "RC Car", "Toys", 55.00),
    ]
    cur.executemany(
        "INSERT INTO products (product_id, name, category, price) VALUES (?, ?, ?, ?)",
        products,
    )

    orders = []
    order_items = []
    order_id = 1
    item_id = 1
    statuses = ["completed", "pending", "cancelled"]
    for customer_id in range(1, 26):
        num_orders = (customer_id % 3) + 1
        for o in range(num_orders):
            orders.append((
                order_id,
                customer_id,
                f"2023-{((customer_id + o) % 12) + 1:02d}-{((customer_id + o) % 27) + 1:02d}",
                statuses[(customer_id + o) % len(statuses)],
            ))
            num_items = (o % 2) + 1
            for n in range(num_items):
                product_id = ((customer_id + o + n) % 10) + 1
                price = products[product_id - 1][3]
                order_items.append((
                    item_id, order_id, product_id, (n % 3) + 1, price,
                ))
                item_id += 1
            order_id += 1

    cur.executemany(
        "INSERT INTO orders (order_id, customer_id, order_date, status) VALUES (?, ?, ?, ?)",
        orders,
    )
    cur.executemany(
        "INSERT INTO order_items (order_item_id, order_id, product_id, quantity, unit_price) "
        "VALUES (?, ?, ?, ?, ?)",
        order_items,
    )
    conn.commit()


def main() -> None:
    default_path = Path(__file__).parent / "shop.db"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        seed(conn)
        print(f"Seeded sample database at {path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
