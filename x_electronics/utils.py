# Copyright (c) 2026, William Ndoni and contributors
# For license information, please see license.txt

import frappe

VALUATION_METHODS = ("Moving Average", "FIFO", "LIFO")
DEFAULT_METHOD = "Moving Average"

# A "layer" is [qty, rate]: a slice of stock received at one cost.
# Receipts push layers; consumption removes from them per the method.
# Moving Average removes proportionally from every layer (equivalent to
# the pooled average, but keeps layer structure intact so FIFO/LIFO
# rows can follow in the same history).


def consume_from_layers(layers: list, qty: float, method: str) -> float:
	"""Remove qty from layers in place per the valuation method.

	Returns the value removed. This function is the single home of all
	three valuation rules.
	"""
	if method == "Moving Average":
		total_qty = sum(q for q, _r in layers)
		total_value = sum(q * r for q, r in layers)
		avg = (total_value / total_qty) if total_qty else 0
		if total_qty:
			factor = max(0.0, (total_qty - qty) / total_qty)
			layers[:] = [[q * factor, r] for q, r in layers if q * factor > 1e-9]
		return qty * avg

	index = 0 if method == "FIFO" else -1  # LIFO pops from the back
	removed_value = 0.0
	remaining = qty
	while remaining > 1e-9 and layers:
		layer_qty, rate = layers[index]
		take = min(layer_qty, remaining)
		removed_value += take * rate
		remaining -= take
		if take >= layer_qty - 1e-9:
			layers.pop(index)
		else:
			layers[index][0] = layer_qty - take
	return removed_value


def apply_row(layers: list, actual_qty: float, incoming_rate: float | None, method: str | None = None) -> float:
	"""Apply one ledger row to the layers. Returns the value change (+/-)."""
	if actual_qty >= 0:
		layers.append([actual_qty, incoming_rate or 0])
		return actual_qty * (incoming_rate or 0)
	return -consume_from_layers(layers, -actual_qty, method or DEFAULT_METHOD)


def layer_totals(layers: list) -> tuple[float, float]:
	qty = sum(q for q, _r in layers)
	value = sum(q * r for q, r in layers)
	return qty, value


def get_layers(item: str, warehouse: str, as_of=None, exclude_voucher: str | None = None) -> list:
	"""Rebuild the cost layers for an item in a warehouse from the ledger."""
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
		SELECT actual_qty, incoming_rate, valuation_method
		FROM `tabStock Ledger Entry`
		WHERE item = %(item)s AND warehouse = %(warehouse)s {conditions}
		ORDER BY posting_datetime, name
		""",
		values,
		as_dict=True,
	)

	layers: list = []
	for row in rows:
		apply_row(layers, row.actual_qty, row.incoming_rate, row.valuation_method)
	return layers


def get_stock_state(item: str, warehouse: str, as_of=None, exclude_voucher: str | None = None) -> tuple[float, float]:
	return layer_totals(get_layers(item, warehouse, as_of, exclude_voucher))


def get_valuation_rate(item: str, warehouse: str, as_of=None) -> float:
	qty, value = get_stock_state(item, warehouse, as_of=as_of)
	return (value / qty) if qty else 0


def get_outgoing_rate(item: str, warehouse: str, qty: float, method: str, as_of=None) -> float:
	"""Per-unit value that WOULD leave if qty were consumed now under method.

	Used by transfers to stamp the incoming leg's rate."""
	layers = get_layers(item, warehouse, as_of)
	value = consume_from_layers(layers, qty, method or DEFAULT_METHOD)
	return (value / qty) if qty else 0