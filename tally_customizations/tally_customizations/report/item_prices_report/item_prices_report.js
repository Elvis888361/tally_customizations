// Copyright (c) 2024, Tally Customizations and contributors
// For license information, please see license.txt

frappe.query_reports["Item Prices Report"] = {
	"filters": [
		{
			"fieldname": "item_code",
			"label": __("Item"),
			"fieldtype": "Link",
			"options": "Item",
			"width": 100
		},
		{
			"fieldname": "item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group",
			"width": 100
		},
		{
			"fieldname": "brand",
			"label": __("Brand"),
			"fieldtype": "Link",
			"options": "Brand",
			"width": 100
		},
		{
			"fieldname": "buying_price_list",
			"label": __("Buying Price List"),
			"fieldtype": "MultiSelectList",
			"get_data": function(txt) {
				return frappe.db.get_link_options("Price List", txt, {
					buying: 1,
					enabled: 1
				});
			}
		},
		{
			"fieldname": "selling_price_list",
			"label": __("Selling Price List"),
			"fieldtype": "MultiSelectList",
			"get_data": function(txt) {
				return frappe.db.get_link_options("Price List", txt, {
					selling: 1,
					enabled: 1
				});
			}
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Make item code clickable
		if (column.fieldname === "item_code" && data && data.item_code) {
			return `<a href="/app/item/${encodeURIComponent(data.item_code)}"
				style="color: #2490ef; text-decoration: underline; cursor: pointer;"
				onclick="event.preventDefault(); frappe.set_route('Form', 'Item', '${data.item_code}');">
				${value}
			</a>`;
		}

		// Format currency columns
		if (column.fieldtype === "Currency" && value) {
			let num_value = parseFloat(value.replace(/[^0-9.-]/g, ''));
			if (num_value > 0) {
				return `<span style="color: #333;">${value}</span>`;
			}
		}

		return value;
	},

	"onload": function(report) {
		// Add Export to Excel button
		report.page.add_inner_button(__("Export to Excel"), function() {
			let filters = frappe.query_report.get_filter_values();
			let data = frappe.query_report.data;

			if (!data || data.length === 0) {
				frappe.msgprint(__("No data to export. Please run the report first."));
				return;
			}

			// Use built-in export functionality
			frappe.query_report.export_report();
		});
	}
};
