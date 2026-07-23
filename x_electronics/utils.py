# Copyright (c) 2026, William Ndoni and contributors
# For license information, please see license.txt

import frappe


def get_stock_state(item: str, warehouse: str, as_of=None, exclude_voucher: str | None = None) -> tuple[float, float]:
	"""Return (qty, value) for an item in a warehouse by walking the ledger.

	Receipts add value at their incoming rate; consumption removes value at
	the moving average prevailing at that point. 
	"""
	conditions = ""
	values = {"item": item, "warehouse": warehouse}

	if as_of:
		conditions += " AND posting_datetime <= %(as_of)s"
		values["as_of"] = as_of
	if exclude_voucher:
		conditions += " AND voucher_no != %(exclude_voucher)s"
		values["exclude_voucher"] = exclude_voucher

	rows = frappe.db.sql(
		f"""
		SELECT actual_qty, incoming_rate
		FROM `tabStock Ledger Entry`
		WHERE item = %(item)s AND warehouse = %(warehouse)s {conditions}
		ORDER BY posting_datetime, name
		""",
		values,
		as_dict=True,
	)

	qty, value = 0.0, 0.0
	for row in rows:
		if row.actual_qty >= 0:
			value += row.actual_qty * (row.incoming_rate or 0)
		else:
			avg = value / qty if qty else 0
			value += row.actual_qty * avg
		qty += row.actual_qty

	return qty, value


def get_valuation_rate(item: str, warehouse: str, as_of=None) -> float:
	qty, value = get_stock_state(item, warehouse, as_of=as_of)
	return (value / qty) if qty else 0