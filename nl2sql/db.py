"""
db.py — schema definition and sample-data loader for the NL-to-SQL demo.

Builds a small SQLite "business" database (customers, products, orders)
from the CSV files in sample_data/, or from scratch if the CSVs are
missing. Kept separate from the web app and the parser so each piece
can be tested/reused independently.
"""

import csv
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    region  TEXT NOT NULL,
    segment TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    category TEXT NOT NULL,
    price    REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    product_id  INTEGER NOT NULL REFERENCES products(id),
    quantity    INTEGER NOT NULL,
    order_date  TEXT NOT NULL
);
"""

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "data", "business.db")


def _load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def build_database(db_path=DEFAULT_DB_PATH, sample_dir=SAMPLE_DATA_DIR, force=False):
    """Create (or reuse) the SQLite database and seed it from the CSVs."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    if force and os.path.exists(db_path):
        os.remove(db_path)

    is_new = not os.path.exists(db_path)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)

    if is_new:
        cur = conn.cursor()

        customers = _load_csv(os.path.join(sample_dir, "customers.csv"))
        cur.executemany(
            "INSERT INTO customers (id, name, region, segment) VALUES (:id, :name, :region, :segment)",
            customers,
        )

        products = _load_csv(os.path.join(sample_dir, "products.csv"))
        cur.executemany(
            "INSERT INTO products (id, name, category, price) VALUES (:id, :name, :category, :price)",
            products,
        )

        orders = _load_csv(os.path.join(sample_dir, "orders.csv"))
        cur.executemany(
            "INSERT INTO orders (id, customer_id, product_id, quantity, order_date) "
            "VALUES (:id, :customer_id, :product_id, :quantity, :order_date)",
            orders,
        )

        conn.commit()

    return conn


def get_connection(db_path=DEFAULT_DB_PATH):
    """Return a connection to an already-built database, building it if needed."""
    if not os.path.exists(db_path):
        return build_database(db_path)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def schema_description():
    """Human-readable schema summary, shown in the UI so users know what they can ask."""
    return (
        "customers(id, name, region, segment)\n"
        "products(id, name, category, price)\n"
        "orders(id, customer_id, product_id, quantity, order_date)"
    )


if __name__ == "__main__":
    conn = build_database(force=True)
    print(f"Database built at {DEFAULT_DB_PATH}")
    for table in ("customers", "products", "orders"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")
