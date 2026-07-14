"""
parser.py — a small, dependency-free natural-language-to-SQL translator.

This is deliberately rule-based (regex + keyword matching) rather than
calling an external LLM API, so the whole app runs offline with no API
key required. It recognizes a family of common BI questions ("total
revenue in March", "top 5 products by revenue", "orders by region",
"average order value for Enterprise customers", ...) and turns them
into parameterized SQL against the customers/products/orders schema.

Each recognizer is a (pattern, builder) pair. `translate()` tries them
in order and returns the first match. If nothing matches, it raises
UnrecognizedQuestion with a helpful message and example questions.
"""

import re

MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}

REVENUE_EXPR = "SUM(o.quantity * p.price)"


class UnrecognizedQuestion(Exception):
    pass


def _find_month(text):
    for name, num in MONTHS.items():
        if name in text:
            return name.capitalize(), num
    return None, None


def _base_join():
    return (
        "FROM orders o "
        "JOIN customers c ON o.customer_id = c.id "
        "JOIN products p ON o.product_id = p.id"
    )


# --- individual recognizers -------------------------------------------------

def _try_total_revenue(text):
    if not re.search(r"\btotal (revenue|sales)\b", text):
        return None
    month_name, month_num = _find_month(text)
    sql = f"SELECT {REVENUE_EXPR} AS total_revenue {_base_join()}"
    params = []
    caption = "Total revenue across all orders."
    if month_num:
        sql += " WHERE strftime('%m', o.order_date) = ?"
        params.append(month_num)
        caption = f"Total revenue in {month_name}."
    return sql, params, caption


def _try_top_products(text):
    m = re.search(r"top (\d+) products?( by (revenue|sales))?", text)
    if not m:
        return None
    n = int(m.group(1))
    sql = (
        f"SELECT p.name AS product, {REVENUE_EXPR} AS revenue "
        f"{_base_join()} GROUP BY p.id ORDER BY revenue DESC LIMIT ?"
    )
    return sql, [n], f"Top {n} products by revenue."


def _try_revenue_by_region(text):
    if not re.search(r"revenue by region|sales by region", text):
        return None
    sql = (
        f"SELECT c.region AS region, {REVENUE_EXPR} AS revenue "
        f"{_base_join()} GROUP BY c.region ORDER BY revenue DESC"
    )
    return sql, [], "Revenue broken down by customer region."


def _try_revenue_by_month(text):
    if not re.search(r"revenue by month|monthly revenue|sales by month", text):
        return None
    sql = (
        f"SELECT strftime('%Y-%m', o.order_date) AS month, {REVENUE_EXPR} AS revenue "
        f"{_base_join()} GROUP BY month ORDER BY month"
    )
    return sql, [], "Revenue broken down by month."


def _try_orders_by_region(text):
    if not re.search(r"orders by region", text):
        return None
    sql = (
        f"SELECT c.region AS region, COUNT(*) AS order_count "
        f"{_base_join()} GROUP BY c.region ORDER BY order_count DESC"
    )
    return sql, [], "Number of orders per customer region."


def _try_average_order_value(text):
    if not re.search(r"average order value|avg order value", text):
        return None
    segment = None
    seg_match = re.search(r"for (\w+) customers", text)
    if seg_match:
        segment = seg_match.group(1).capitalize()

    # Average order value needs a per-order total subquery, not a global SUM.
    sql = (
        "SELECT AVG(order_total) AS average_order_value FROM ("
        "SELECT o.id AS order_id, (o.quantity * p.price) AS order_total "
        f"{_base_join()}"
    )
    params = []
    if segment:
        sql += " WHERE c.segment = ?"
        params.append(segment)
    sql += ")"
    caption = "Average order value" + (f" for {segment} customers." if segment else ".")
    return sql, params, caption


def _try_top_customers(text):
    m = re.search(r"top (\d+) customers?( by (orders|revenue))?", text)
    if not m:
        return None
    n = int(m.group(1))
    metric = m.group(3) or "orders"
    if metric == "revenue":
        sql = (
            f"SELECT c.name AS customer, {REVENUE_EXPR} AS revenue "
            f"{_base_join()} GROUP BY c.id ORDER BY revenue DESC LIMIT ?"
        )
        caption = f"Top {n} customers by revenue."
    else:
        sql = (
            f"SELECT c.name AS customer, COUNT(*) AS order_count "
            f"{_base_join()} GROUP BY c.id ORDER BY order_count DESC LIMIT ?"
        )
        caption = f"Top {n} customers by order count."
    return sql, [n], caption


def _try_revenue_by_category(text):
    if not re.search(r"revenue by category|sales by category", text):
        return None
    sql = (
        f"SELECT p.category AS category, {REVENUE_EXPR} AS revenue "
        f"{_base_join()} GROUP BY p.category ORDER BY revenue DESC"
    )
    return sql, [], "Revenue broken down by product category."


def _try_customer_count(text):
    if not re.search(r"how many customers|number of customers|total customers", text):
        return None
    segment = None
    seg_match = re.search(r"in (\w+) segment|(\w+) segment customers", text)
    sql = "SELECT COUNT(*) AS customer_count FROM customers"
    params = []
    caption = "Total number of customers."
    if seg_match:
        segment = (seg_match.group(1) or seg_match.group(2)).capitalize()
        sql += " WHERE segment = ?"
        params.append(segment)
        caption = f"Total number of customers in the {segment} segment."
    return sql, params, caption


RECOGNIZERS = [
    _try_total_revenue,
    _try_top_products,
    _try_revenue_by_region,
    _try_revenue_by_month,
    _try_orders_by_region,
    _try_average_order_value,
    _try_top_customers,
    _try_revenue_by_category,
    _try_customer_count,
]

EXAMPLE_QUESTIONS = [
    "total revenue",
    "total revenue in March",
    "top 5 products by revenue",
    "revenue by region",
    "revenue by month",
    "orders by region",
    "average order value",
    "average order value for Enterprise customers",
    "top 3 customers by revenue",
    "revenue by category",
    "how many customers",
    "how many customers in Enterprise segment",
]


def translate(question):
    """Translate a natural-language question into (sql, params, caption).

    Raises UnrecognizedQuestion if no recognizer matches.
    """
    text = question.strip().lower()
    if not text:
        raise UnrecognizedQuestion("Please enter a question.")

    for recognizer in RECOGNIZERS:
        result = recognizer(text)
        if result:
            return result

    raise UnrecognizedQuestion(
        "I couldn't match that to a known question pattern. Try one of the "
        "example questions, e.g.: " + "; ".join(EXAMPLE_QUESTIONS[:4])
    )
