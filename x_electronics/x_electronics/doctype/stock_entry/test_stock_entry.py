# Copyright (c) 2026, William Ndoni and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from x_electronics.utils import get_stock_state, get_valuation_rate


class IntegrationTestStockEntry(IntegrationTestCase):
	def setUp(self):
		suffix = frappe.generate_hash(length=8)
		self.item = create_item(f"_TEST-PHONE-{suffix}")
		self.wh_source = create_warehouse(f"_Test Floor A {suffix}")
		self.wh_target = create_warehouse(f"_Test Floor B {suffix}")

	def make_entry(self, entry_type, qty, rate=None, source=None, target=None, submit=True):
		entry = frappe.get_doc({
			"doctype": "Stock Entry",
			"entry_type": entry_type,
			"posting_datetime": frappe.utils.now_datetime(),
			"items": [{
				"item": self.item,
				"qty": qty,
				"rate": rate,
				"source_warehouse": source,
				"target_warehouse": target,
			}],
		})
		entry.insert()
		if submit:
			entry.submit()
		return entry

	# Testing creation of Stock Ledger Entry

	def test_receipt_creates_positive_sle(self):
		entry = self.make_entry("Receipt", qty=100, rate=500, target=self.wh_target)
		sles = get_sles(entry.name)
		self.assertEqual(len(sles), 1)
		self.assertEqual(sles[0].actual_qty, 100)
		self.assertEqual(sles[0].incoming_rate, 500)
		self.assertEqual(sles[0].warehouse, self.wh_target)

	def test_consume_creates_negative_sle(self):
		self.make_entry("Receipt", qty=100, rate=500, target=self.wh_source)
		entry = self.make_entry("Consume", qty=30, source=self.wh_source)
		sles = get_sles(entry.name)
		self.assertEqual(len(sles), 1)
		self.assertEqual(sles[0].actual_qty, -30)

	def test_transfer_creates_two_sles(self):
		self.make_entry("Receipt", qty=100, rate=500, target=self.wh_source)
		entry = self.make_entry("Transfer", qty=20, source=self.wh_source, target=self.wh_target)
		sles = sorted(get_sles(entry.name), key=lambda s: s.actual_qty)
		self.assertEqual(len(sles), 2)
		self.assertEqual((sles[0].actual_qty, sles[0].warehouse), (-20, self.wh_source))
		self.assertEqual((sles[1].actual_qty, sles[1].warehouse), (20, self.wh_target))

	def test_cancel_removes_sles(self):
		entry = self.make_entry("Receipt", qty=100, rate=500, target=self.wh_target)
		self.assertEqual(len(get_sles(entry.name)), 1)
		entry.cancel()
		self.assertEqual(len(get_sles(entry.name)), 0)

	# Testing validation

	def test_receipt_requires_target_and_rate(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_entry("Receipt", qty=10, rate=500, source=self.wh_source, target=self.wh_target)
		with self.assertRaises(frappe.ValidationError):
			self.make_entry("Receipt", qty=10, target=self.wh_target)  # no rate

	def test_cannot_overconsume(self):
		self.make_entry("Receipt", qty=50, rate=500, target=self.wh_source)
		with self.assertRaises(frappe.ValidationError):
			self.make_entry("Consume", qty=60, source=self.wh_source)

	def test_qty_must_be_positive(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_entry("Receipt", qty=0, rate=500, target=self.wh_target)

	def test_cannot_use_group_warehouse(self):
		group = create_warehouse(f"_Test Group {frappe.generate_hash(length=8)}", is_group=1)
		with self.assertRaises(frappe.ValidationError):
			self.make_entry("Receipt", qty=10, rate=500, target=group)

	def test_disabled_item_rejected(self):
		frappe.db.set_value("Item", self.item, "disabled", 1)
		with self.assertRaises(frappe.ValidationError):
			self.make_entry("Receipt", qty=10, rate=500, target=self.wh_target)
		frappe.db.set_value("Item", self.item, "disabled", 0)

	# Testing valuation rate (moving average)

	def test_moving_average_stable_through_consumption(self):
		self.make_entry("Receipt", qty=100, rate=500, target=self.wh_source)
		self.make_entry("Consume", qty=30, source=self.wh_source)
		# Confirming valuation rate is 500, the current moving average at consumption time
		self.assertAlmostEqual(get_valuation_rate(self.item, self.wh_source), 500)

	def test_transfer_conserves_value(self):
		self.make_entry("Receipt", qty=100, rate=500, target=self.wh_source)
		self.make_entry("Consume", qty=30, source=self.wh_source)
		self.make_entry("Transfer", qty=20, source=self.wh_source, target=self.wh_target)

		src_qty, src_value = get_stock_state(self.item, self.wh_source)
		tgt_qty, tgt_value = get_stock_state(self.item, self.wh_target)
		self.assertAlmostEqual(src_qty, 50)
		self.assertAlmostEqual(tgt_qty, 20)
		self.assertAlmostEqual(src_value + tgt_value, 35000)
		self.assertAlmostEqual(get_valuation_rate(self.item, self.wh_target), 500)

	def test_moving_average_updates_on_new_receipt(self):
		self.make_entry("Receipt", qty=100, rate=500, target=self.wh_source)
		self.make_entry("Consume", qty=30, source=self.wh_source)
		self.make_entry("Receipt", qty=50, rate=520, target=self.wh_source)
		# Testing the above, this should be (70*500 + 50*520) / 120 =  508.333...
		self.assertAlmostEqual(get_valuation_rate(self.item, self.wh_source), 508.3333, places=3)


# Helper functions

def get_sles(voucher_no):
	return frappe.get_all(
		"Stock Ledger Entry",
		filters={"voucher_no": voucher_no},
		fields=["actual_qty", "incoming_rate", "warehouse"],
	)


def create_item(code):
	frappe.get_doc({"doctype": "Item", "item_code": code, "item_name": code}).insert()
	return code


def create_warehouse(name, is_group=0):
	frappe.get_doc({"doctype": "Warehouse", "warehouse_name": name, "is_group": is_group}).insert()
	return name