// Copyright (c) 2026, William Ndoni and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Ledger"] = {
	filters: [
		{ fieldname: "item", label: __("Item"), fieldtype: "Link", options: "Item" },
		{ fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse" },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date" },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date" },
	],
};