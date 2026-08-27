import frappe
from frappe import _
from x_electronics.utils import apply_row, layer_totals


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Posting Datetime"), "fieldname": "posting_datetime", "fieldtype": "Datetime", "width": 165},
		{"label": _("Item"), "fieldname": "item", "fieldtype": "Link", "options": "Item", "width": 120},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 130},
		{"label": _("Qty Change"), "fieldname": "actual_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Balance Qty"), "fieldname": "balance_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Incoming Rate"), "fieldname": "incoming_rate", "fieldtype": "Currency", "width": 110},
		{"label": _("Valuation Rate"), "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 110},
		{"label": _("Stock Value"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 120},
		{"label": _("Voucher No"), "fieldname": "voucher_no", "fieldtype": "Data", "width": 130},
		{"label": _("Method"), "fieldname": "valuation_method", "fieldtype": "Data", "width": 110},
	]


def get_data(filters):
	conditions = ""
	if filters.get("item"):
		conditions += " AND item = %(item)s"
	if filters.get("warehouse"):
		conditions += " AND warehouse = %(warehouse)s"

	rows = frappe.db.sql(
		f"""
		SELECT posting_datetime, item, warehouse, actual_qty, incoming_rate,
		       voucher_type, voucher_no, valuation_method
		FROM `tabStock Ledger Entry`
		WHERE 1=1 {conditions}
		ORDER BY item, warehouse, posting_datetime, name
		""",
		filters,
		as_dict=True,
	)

	# Reading the ledger from top to bottom (walk the ledger) using the chosen valuation_method
	state = {}
	for row in rows:
		key = (row.item, row.warehouse)
		layers = state.setdefault(key, [])
		apply_row(layers, row.actual_qty, row.incoming_rate, row.valuation_method)
		qty, value = layer_totals(layers)

		row.balance_qty = qty
		row.valuation_rate = value / qty if qty else 0
		row.stock_value = value

	# Applying date filters after the walk
	if filters.get("from_date"):
		rows = [r for r in rows if str(r.posting_datetime) >= str(filters.from_date)]
	if filters.get("to_date"):
		rows = [r for r in rows if str(r.posting_datetime) <= str(filters.to_date)]

	return rows