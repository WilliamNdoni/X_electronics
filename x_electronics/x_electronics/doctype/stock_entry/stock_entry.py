# Copyright (c) 2026, William Ndoni and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from x_electronics.utils import get_outgoing_rate

class StockEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF
		from x_electronics.x_electronics.doctype.stock_entry_item.stock_entry_item import StockEntryItem

		amended_from: DF.Link | None
		entry_type: DF.Literal["Receipt", "Consume", "Transfer"]
		items: DF.Table[StockEntryItem]
		posting_datetime: DF.Datetime
		remarks: DF.SmallText | None
		valuation_method: DF.Literal["Moving Average", "FIFO", "LIFO"]
	# end: auto-generated types

	def validate(self):
		self._validate_items_present()
		for row in self.items:
			self._validate_row_warehouses(row)
			self._validate_row_qty_and_rate(row)
			self._validate_active(row)
			self._validate_sufficient_stock(row)
	
	def _validate_items_present(self):
		if not self.items:
			frappe.throw(_("Add at least one item!"))
	
	def _validate_row_warehouses(self, row):
		if self.entry_type == "Receipt":
			if not row.target_warehouse:
				frappe.throw(_("Row {0}: Target Warehouse is required for a Receipt.").format(row.idx))
			if row.source_warehouse:
				frappe.throw(_("Row {0}: Source Warehouse must be empty for a Receipt.").format(row.idx))

		elif self.entry_type == "Consume":
			if not row.source_warehouse:
				frappe.throw(_("Row {0}: Source Warehouse is required for a Consume.").format(row.idx))
			if row.target_warehouse:
				frappe.throw(_("Row {0}: Target Warehouse must be empty for a Consume.").format(row.idx))

		elif self.entry_type == "Transfer":
			if not (row.source_warehouse and row.target_warehouse):
				frappe.throw(_("Row {0}: Transfer needs both Source and Target Warehouse.").format(row.idx))
			if row.source_warehouse == row.target_warehouse:
				frappe.throw(_("Row {0}: Source and Target cannot be the same warehouse.").format(row.idx))

		for warehouse in (row.source_warehouse, row.target_warehouse):
			if warehouse and frappe.db.get_value("Warehouse", warehouse, "is_group"):
				frappe.throw(_("Row {0}: {1} is a group warehouse; stock can only be held in leaf warehouses.").format(row.idx, warehouse))
	
	def _validate_row_qty_and_rate(self, row):
		if row.qty is None or row.qty <= 0:
			frappe.throw(_("Row {0}: Qty must be greater than zero.").format(row.idx))

		if self.entry_type == "Receipt":
			if not row.rate or row.rate <= 0:
				frappe.throw(_("Row {0}: Rate is required for a Receipt.").format(row.idx))
		else:
			row.rate = None
	
	def _validate_active(self, row):
		if frappe.db.get_value("Item", row.item, "disabled"):
			frappe.throw(_("Row {0}: Item {1} is disabled.").format(row.idx, row.item))

		for warehouse in (row.source_warehouse, row.target_warehouse):
			if warehouse and frappe.db.get_value("Warehouse", warehouse, "disabled"):
				frappe.throw(_("Row {0}: Warehouse {1} is disabled.").format(row.idx, warehouse))
	
	def _get_balance(self, item, warehouse, posting_datetime, exclude_voucher=None):
		"""Balance of an item in a warehouse as of a moment, by summing the ledger."""
		conditions = ""
		values = {
			"item": item,
			"warehouse": warehouse,
			"posting_datetime": posting_datetime,
		}
		if exclude_voucher:
			conditions = "AND voucher_no != %(exclude_voucher)s"
			values["exclude_voucher"] = exclude_voucher

		result = frappe.db.sql(
			f"""
			SELECT COALESCE(SUM(actual_qty), 0)
			FROM `tabStock Ledger Entry`
			WHERE item = %(item)s
			  AND warehouse = %(warehouse)s
			  AND posting_datetime <= %(posting_datetime)s
			  {conditions}
			""",
			values,
		)[0][0]
		return result

	def _validate_sufficient_stock(self, row):
		if self.entry_type not in ("Consume", "Transfer"):
			return

		balance = self._get_balance(
			row.item, row.source_warehouse, self.posting_datetime, exclude_voucher=self.name
		)
		if balance < row.qty:
			frappe.throw(
				_("Row {0}: Insufficient stock of {1} in {2}. Available: {3}, requested: {4}.").format(
					row.idx, row.item, row.source_warehouse, balance, row.qty
				)
			)
	
	def on_submit(self):
		self._create_stock_ledger_entries()
	
	def on_cancel(self):
		self._delete_stock_ledger_entries()
	
	def _create_stock_ledger_entries(self):
		for row in self.items:
			if self.entry_type == "Receipt":
				self._make_sle(row.item, row.target_warehouse, row.qty, row.rate)
			elif self.entry_type == "Consume":
				self._make_sle(row.item, row.source_warehouse, -row.qty, None)
			elif self.entry_type == "Transfer":
				outgoing_rate = get_outgoing_rate(row.item, row.source_warehouse, row.qty, self.valuation_method, as_of=self.posting_datetime,)
				self._make_sle(row.item, row.source_warehouse, -row.qty, None)
				self._make_sle(row.item, row.target_warehouse, row.qty, outgoing_rate)
	
	def _make_sle(self, item, warehouse, actual_qty, incoming_rate):
		frappe.get_doc({
			"doctype": "Stock Ledger Entry",
			"posting_datetime": self.posting_datetime,
			"item": item,
			"warehouse": warehouse,
			"actual_qty": actual_qty,
			"incoming_rate": incoming_rate,
			"voucher_type": self._DOCTYPE_NAME,
			"voucher_no": self.name,
			"valuation_method": self.valuation_method or "Moving Average"
		}).insert()
	
	def _delete_stock_ledger_entries(self):
		frappe.db.delete(
			"Stock Ledger Entry",
			{"voucher_type": self._DOCTYPE_NAME, "voucher_no": self.name},
		)



	_DOCTYPE_NAME = "Stock Entry"
