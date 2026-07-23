# Copyright (c) 2026, William Ndoni and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Item(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		disabled: DF.Check
		item_code: DF.Data
		item_name: DF.Data
		unit_of_measure: DF.Literal["Kg", "Litre", "Box", "Nos"]
	# end: auto-generated types

	_DOCTYPE_NAME = "Item"
