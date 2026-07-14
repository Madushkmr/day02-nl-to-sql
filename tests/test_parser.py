"""
Unit tests for nl2sql.parser — checks that known question patterns
translate to valid, executable SQL, and that unknown questions raise
a helpful error instead of silently failing.

Run: python -m pytest tests/ -v   (from the day02-nl-to-sql directory)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nl2sql import db
from nl2sql.parser import UnrecognizedQuestion, translate


class TestParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_path = os.path.join(os.path.dirname(__file__), "test_business.db")
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)
        cls.conn = db.build_database(db_path=cls.db_path, force=True)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def _run(self, question):
        sql, params, caption = translate(question)
        cursor = self.conn.execute(sql, params)
        rows = cursor.fetchall()
        return rows, caption

    def test_total_revenue(self):
        rows, caption = self._run("total revenue")
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(rows[0][0])
        self.assertIn("Total revenue", caption)

    def test_total_revenue_with_month(self):
        rows, caption = self._run("total revenue in March")
        self.assertEqual(len(rows), 1)
        self.assertIn("March", caption)

    def test_top_products(self):
        rows, caption = self._run("top 3 products by revenue")
        self.assertLessEqual(len(rows), 3)
        self.assertIn("Top 3 products", caption)

    def test_revenue_by_region(self):
        rows, _ = self._run("revenue by region")
        self.assertGreater(len(rows), 0)

    def test_revenue_by_month(self):
        rows, _ = self._run("revenue by month")
        self.assertGreater(len(rows), 0)

    def test_orders_by_region(self):
        rows, _ = self._run("orders by region")
        self.assertGreater(len(rows), 0)

    def test_average_order_value(self):
        rows, caption = self._run("average order value")
        self.assertEqual(len(rows), 1)
        self.assertIn("Average order value", caption)

    def test_average_order_value_segment(self):
        rows, caption = self._run("average order value for Enterprise customers")
        self.assertEqual(len(rows), 1)
        self.assertIn("Enterprise", caption)

    def test_top_customers(self):
        rows, caption = self._run("top 5 customers by revenue")
        self.assertLessEqual(len(rows), 5)
        self.assertIn("Top 5 customers", caption)

    def test_revenue_by_category(self):
        rows, _ = self._run("revenue by category")
        self.assertGreater(len(rows), 0)

    def test_customer_count(self):
        rows, caption = self._run("how many customers")
        self.assertEqual(rows[0][0], 10)

    def test_customer_count_segment(self):
        rows, caption = self._run("how many customers in Enterprise segment")
        self.assertGreater(rows[0][0], 0)
        self.assertIn("Enterprise", caption)

    def test_unrecognized_question_raises(self):
        with self.assertRaises(UnrecognizedQuestion):
            translate("what is the meaning of life")

    def test_empty_question_raises(self):
        with self.assertRaises(UnrecognizedQuestion):
            translate("   ")


if __name__ == "__main__":
    unittest.main()
