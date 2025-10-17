// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Banking"] = {
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
			"fieldname": "account",
			"label": __("Bank Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				let company = frappe.query_report.get_filter_value('company');
				return {
					"filters": {
						"company": company,
						"account_type": "Bank",
						"is_group": 0
					}
				};
			}
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		// Use default formatter first
		value = default_formatter(value, row, column, data);

		// Make voucher number clickable
		if (column.fieldname === "vch_no" && data && data.voucher_type && data.voucher_no) {
			// Create a clickable link to the voucher
			return `<a href="/app/${frappe.router.slug(data.voucher_type)}/${encodeURIComponent(data.voucher_no)}"
				style="color: #2490ef; text-decoration: underline; cursor: pointer;"
				onclick="event.preventDefault(); frappe.set_route('Form', '${data.voucher_type}', '${data.voucher_no}');">
				${value}
			</a>`;
		}

		// Check for special rows using underscore properties
		if (data && data._is_opening) {
			// Opening balance row - make bold
			return `<span style="font-weight: bold;">${value}</span>`;
		}

		if (data && data._is_subtotal) {
			// Subtotal row - add border on top
			return `<span style="border-top: 1px solid #000; display: inline-block; padding-top: 3px;">${value}</span>`;
		}

		if (data && data._is_closing) {
			// Closing balance row - make bold
			if (column.fieldname === "particulars") {
				return `<span style="font-weight: bold; padding-left: 40px;">${value}</span>`;
			}
			return `<span style="font-weight: bold;">${value}</span>`;
		}

		if (data && data._is_total) {
			// Total row - make bold with bottom border
			return `<span style="font-weight: bold; border-bottom: 2px double #000; display: inline-block; padding-bottom: 3px;">${value}</span>`;
		}

		return value;
	},

	"onload": function(report) {
		// Add custom Print button
		report.page.add_inner_button(__("Print Banking"), function() {
			let filters = frappe.query_report.get_filter_values();
			let data = frappe.query_report.data;

			if (!data || data.length === 0) {
				frappe.msgprint(__("No data to print. Please run the report first."));
				return;
			}

			// Get company details
			frappe.call({
				method: "frappe.client.get",
				args: {
					doctype: "Company",
					name: filters.company
				},
				callback: function(r) {
					if (r.message) {
						let company = r.message.company_name || r.message.name;
						let company_address = r.message.address || "";

						// Get company contact info (phone numbers)
						let company_contact = "";
						if (r.message.phone_no) {
							company_contact = "Tel " + r.message.phone_no;
						}
						if (r.message.mobile_no) {
							if (company_contact) {
								company_contact += ", " + r.message.mobile_no;
							} else {
								company_contact = "Tel " + r.message.mobile_no;
							}
						}

						// Call server-side method to render template
						frappe.call({
							method: "tally_customizations.tally_customizations.report.banking.banking.get_print_html",
							args: {
								filters: filters,
								data: data,
								company: company,
								company_address: company_address,
								company_contact: company_contact
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
					}
				}
			});
		});
	}
};
