"""
app.py — Flask web UI for the NL-to-SQL BI demo.

Wires together the parser (nl2sql/parser.py) and the database layer
(nl2sql/db.py): a user types a plain-English business question, the app
translates it into SQL, runs it against a small synthetic SQLite
database, and shows both the generated SQL and the resulting table.

Run:
    python app.py
Then open http://127.0.0.1:5000
"""

from flask import Flask, jsonify, render_template, request

from nl2sql import db
from nl2sql.parser import EXAMPLE_QUESTIONS, UnrecognizedQuestion, translate

app = Flask(__name__)


@app.route("/")
def index():
    return render_template(
        "index.html",
        schema=db.schema_description(),
        examples=EXAMPLE_QUESTIONS,
    )


@app.route("/query", methods=["POST"])
def query():
    payload = request.get_json(force=True, silent=True) or {}
    question = payload.get("question", "")

    try:
        sql, params, caption = translate(question)
    except UnrecognizedQuestion as exc:
        return jsonify({"error": str(exc)}), 400

    conn = db.get_connection()
    try:
        cursor = conn.execute(sql, params)
        columns = [c[0] for c in cursor.description]
        rows = [list(r) for r in cursor.fetchall()]
    except Exception as exc:  # surfaces SQL errors instead of crashing the app
        return jsonify({"error": f"Query failed: {exc}", "sql": sql}), 500
    finally:
        conn.close()

    return jsonify(
        {
            "caption": caption,
            "sql": sql,
            "params": params,
            "columns": columns,
            "rows": rows,
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    db.build_database()  # ensure the DB exists before serving requests
    app.run(debug=True)
