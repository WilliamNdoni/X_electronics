# Copyright (c) 2026, William Ndoni and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters: dict | None = None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns() -> list[dict]:
	return [
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 140},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 160},
		{"label": _("Balance Qty"), "fieldname": "balance_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 120},
		{"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters) -> list[dict]:
	conditions = ""
	values = {}

	if filters.get("as_on_date"):
		conditions += " AND posting_datetime < DATE_ADD(%(as_on_date)s, INTERVAL 1 DAY)"
		values["as_on_date"] = filters.as_on_date

	if filters.get("item"):
		conditions += " AND item = %(item)s"
		values["item"] = filters.item

	if filters.get("warehouse"):
		# Consolidation, using the nested-set range of the selected node.
		lft, rgt = frappe.db.get_value("Warehouse", filters.warehouse, ["lft", "rgt"])
		conditions += """ AND warehouse IN (
			SELECT name FROM `tabWarehouse`
			WHERE lft >= %(lft)s AND rgt <= %(rgt)s AND is_group = 0
		)"""
		values.update({"lft": lft, "rgt": rgt})

	rows = frappe.db.sql(
		f"""
		SELECT item, warehouse, actual_qty, incoming_rate
		FROM `tabStock Ledger Entry`
		WHERE 1=1 {conditions}
		ORDER BY item, warehouse, posting_datetime, name
		""",
		values,
		as_dict=True,
	)

	# Moving-average walk aggregated to one line per item+warehouse.
	state = {}
	for row in rows:
		key = (row.item, row.warehouse)
		qty, value = state.get(key, (0.0, 0.0))
		if row.actual_qty >= 0:
			value += row.actual_qty * (row.incoming_rate or 0)
		else:
			avg = value / qty if qty else 0
			value += row.actual_qty * avg
		qty += row.actual_qty
		state[key] = (qty, value)

	data = []
	for (item, warehouse), (qty, value) in sorted(state.items()):
		if qty == 0 and value == 0:
			continue  
		data.append({
			"item": item,
			"warehouse": warehouse,
			"balance_qty": qty,
			"valuation_rate": (value / qty) if qty else 0,
			"stock_value": value,
		})
	return data