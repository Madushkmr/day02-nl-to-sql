# BI Natural-Language-to-SQL

Day 2 of a daily AI-app build series, focused on Business Intelligence use cases.

A small web app that lets you ask business questions in plain English ("top 5 products by revenue", "revenue by region", "average order value for Enterprise customers") and get back the generated SQL plus the answer, run against a synthetic sales database. No external LLM API key required — the translation is done by a compact rule-based parser.

## Why this is useful for BI work

Most BI stakeholders don't write SQL. A common first ask from analytics teams is "can I just ask a question and get an answer?" This project is a minimal, self-contained demonstration of that pattern: a fixed schema, a library of recognized question shapes, and a web UI that shows both the generated query and the result — so it's transparent about what it's doing, not a black box.

It intentionally avoids depending on an external LLM API so it can run fully offline and be reviewed/audited query-pattern by query-pattern, which matters in BI contexts where query correctness has to be trustworthy.

## Architecture

```
day02-nl-to-sql/
  app.py                 Flask web app (routes: / and /query)
  nl2sql/
    __init__.py
    parser.py             Rule-based NL -> SQL translator (regex/keyword recognizers)
    db.py                  Schema definition + CSV-seeded SQLite database builder
  templates/
    index.html             Single-page UI (textarea, example chips, results table)
  sample_data/
    customers.csv, products.csv, orders.csv   Synthetic seed data (10 customers, 8 products, ~120 orders over 6 months)
  tests/
    test_parser.py         Unit tests covering every recognized question pattern + error cases
  requirements.txt
```

Data flow: `app.py` receives a question via POST `/query` -> `nl2sql/parser.py` matches it against a list of recognizers (each a pattern + SQL builder) -> the resulting parameterized SQL runs against the SQLite DB built by `nl2sql/db.py` from the CSVs in `sample_data/` -> the JSON response (caption, SQL, columns, rows) is rendered as a table in the browser.

### Recognized question types
- Total revenue (overall or by month, e.g. "total revenue in March")
- Top N products by revenue
- Revenue by region / by month / by category
- Orders by region
- Average order value (overall or filtered by customer segment)
- Top N customers by orders or revenue
- Customer counts (overall or by segment)

Unrecognized questions return a 400 with example questions instead of crashing or guessing.

## How to run

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 and click one of the example questions, or type your own.

The SQLite database is built automatically on first run (`data/business.db`, not checked into git) from the CSVs in `sample_data/`.

## Tests

```bash
python -m pytest tests/ -v
```

Covers every recognizer pattern plus the unrecognized-question and empty-question error paths.

## Next in this series

Day 1 was a single-script IsolationForest anomaly detector. This adds a Flask web UI, a modular parser/db split, seeded sample data, and a test suite — more moving parts, still runnable in one command. Future days will keep escalating: persistent storage, multi-stage pipelines, dashboards, and eventually agentic multi-step workflows.
