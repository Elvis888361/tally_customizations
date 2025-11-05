// Copyright (c) 2024, Tally Customizations and contributors
// For license information, please see license.txt

frappe.query_reports["Customer Detailed Ledger"] = {
	"filters": [
		{
			"fieldname": "company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"default": frappe.defaults.get_user_default("Company"),
			"reqd": 1
		},
		{
			"fieldname": "from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"reqd": 1
		},
		{
			"fieldname": "to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"reqd": 1
		},
		{
			"fieldname": "customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			"get_query": function() {
				let company = frappe.query_report.get_filter_value('company');
				return {
					"filters": {
						"disabled": 0
					}
				};
			},
			"reqd": 1
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);

		// Make voucher number clickable
		if (column.fieldname === "ref_no" && data && data.voucher_type && data.voucher_no) {
			return `<a href="/app/${frappe.router.slug(data.voucher_type)}/${encodeURIComponent(data.voucher_no)}"
				style="color: #2490ef; text-decoration: underline; cursor: pointer;"
				onclick="event.preventDefault(); frappe.set_route('Form', '${data.voucher_type}', '${data.voucher_no}');">
				${value}
			</a>`;
		}

		// Highlight opening balance row
		if (data && data._is_opening) {
			return `<span style="font-weight: bold;">${value}</span>`;
		}

		// Color code balance
		if (column.fieldname === "balance" && data) {
			if (data.balance_type === "DR") {
				value = "<span style='color: red;'>" + value + "</span>";
			} else if (data.balance_type === "CR") {
				value = "<span style='color: green;'>" + value + "</span>";
			}
		}

		// Highlight invoice rows
		if (data && data.type === "Invoice") {
			value = "<span style='font-weight: 500;'>" + value + "</span>";
		}

		return value;
	},

	"onload": function(report) {
		// Add custom Print button
		report.page.add_inner_button(__("Print Statement"), function() {
			let filters = frappe.query_report.get_filter_values();
			let data = frappe.query_report.data;

			if (!data || data.length === 0) {
				frappe.msgprint(__("No data to print. Please run the report first."));
				return;
			}

			if (!filters.customer) {
				frappe.msgprint(__("Please select a customer"));
				return;
			}

			// Call server-side method to render template
			frappe.call({
				method: "tally_customizations.tally_customizations.report.customer_detailed_ledger.customer_detailed_ledger.get_print_html",
				args: {
					filters: filters,
					data: data
				},
				callback: function(response) {
					if (response.message) {
						// Build print window
						let print_window = window.open("", "_blank");
						print_window.document.write(response.message);
						print_window.document.close();

						// Auto print after a short delay
						setTimeout(function() {
							print_window.print();
						}, 500);
					}
				}
			});
		});
	}
};
