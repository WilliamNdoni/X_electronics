// Copyright (c) 2026, William Ndoni and contributors
// For license information, please see license.txt

frappe.query_reports["Stock Balance"] = {
	filters: [
		{
			fieldname: "as_on_date",
			label: __("As On Date"),
			fieldtype: "Date",
			default: frappe.datetime.get_today(),
			reqd: 1,
		},
		{ fieldname: "item", label: __("Item"), fieldtype: "Link", options: "Item" },
		{ fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse" },
	],
};
