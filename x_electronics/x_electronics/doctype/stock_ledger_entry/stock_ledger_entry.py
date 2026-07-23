# Copyright (c) 2026, William Ndoni and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class StockLedgerEntry(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		actual_qty: DF.Float
		incoming_rate: DF.Currency
		item: DF.Link
		posting_datetime: DF.Datetime
		voucher_no: DF.Data
		voucher_type: DF.Data
		warehouse: DF.Link
	# end: auto-generated types

	_DOCTYPE_NAME = "Stock Ledger Entry"
