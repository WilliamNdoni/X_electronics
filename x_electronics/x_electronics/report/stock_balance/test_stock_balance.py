# Copyright (c) 2026, William Ndoni and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from x_electronics.x_electronics.report.stock_balance.stock_balance import execute
from x_electronics.x_electronics.doctype.stock_entry.test_stock_entry import (
	create_item,
	create_warehouse,
)


class IntegrationTestStockBalance(IntegrationTestCase):
	def setUp(self):
		suffix = frappe.generate_hash(length=8)
		self.item = create_item(f"_TEST-BAL-{suffix}")
		self.parent = create_warehouse(f"_Test Region {suffix}", is_group=1)
		self.wh_a = create_warehouse(f"_Test Shop A {suffix}", parent_warehouse=self.parent)
		self.wh_b = create_warehouse(f"_Test Shop B {suffix}", parent_warehouse=self.parent)
		self.wh_outside = create_warehouse(f"_Test Outside {suffix}")

		receive(self.item, self.wh_a, qty=100, rate=500)
		receive(self.item, self.wh_b, qty=50, rate=520)
		receive(self.item, self.wh_outside, qty=10, rate=500)

	def run_report(self, **filters):
		filters.setdefault("as_on_date", today())
		_columns, data = execute(filters)
		return [r for r in data if r["item"] == self.item]

	def test_balance_per_warehouse(self):
		rows = {r["warehouse"]: r for r in self.run_report()}
		self.assertEqual(rows[self.wh_a]["balance_qty"], 100)
		self.assertEqual(rows[self.wh_a]["stock_value"], 50000)
		self.assertEqual(rows[self.wh_b]["balance_qty"], 50)

	def test_group_warehouse_consolidates_children(self):
		rows = self.run_report(warehouse=self.parent)
		warehouses = {r["warehouse"] for r in rows}
		self.assertEqual(warehouses, {self.wh_a, self.wh_b})  

	def test_leaf_warehouse_filter(self):
		rows = self.run_report(warehouse=self.wh_a)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["balance_qty"], 100)

	def test_as_on_date_excludes_future(self):
		rows = self.run_report(as_on_date=add_days(today(), -1))
		self.assertEqual(rows, [])  # everything was received today


def receive(item, warehouse, qty, rate):
	frappe.get_doc({
		"doctype": "Stock Entry",
		"entry_type": "Receipt",
		"posting_datetime": frappe.utils.now_datetime(),
		"items": [{"item": item, "qty": qty, "rate": rate, "target_warehouse": warehouse}],
	}).insert().submit()