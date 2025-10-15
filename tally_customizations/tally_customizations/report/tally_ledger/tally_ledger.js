// Copyright (c) 2024, Your Company and contributors
// For license information, please see license.txt

frappe.query_reports["Tally Ledger"] = {
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
			"label": __("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"get_query": function() {
				let company = frappe.query_report.get_filter_value('company');
				return {
					"filters": {
						"company": company,
						"is_group": 0
					}
				};
			}
		},
		{
			"fieldname": "party_type",
			"label": __("Party Type"),
			"fieldtype": "Autocomplete",
			"options": ["Customer", "Supplier"],
			"on_change": function() {
				frappe.query_report.set_filter_value('party', []);
			}
		},
		{
			"fieldname": "party",
			"label": __("Party"),
			"fieldtype": "MultiSelectList",
			"get_data": function(txt) {
				if (!frappe.query_report.filters) return;

				let party_type = frappe.query_report.get_filter_value('party_type');
				if (!party_type) return;

				return frappe.db.get_link_options(party_type, txt);
			}
		}
	],

	"formatter": function(value, row, column, data, default_formatter) {
		// Use default formatter first
		value = default_formatter(value, row, column, data);

		// Check for special rows using underscore properties
		if (data && data._is_opening) {
			// Opening balance row - make bold
			return `<span style="font-weight: bold;">${value}</span>`;
		}

		if (data && data._is_closing) {
			// Closing balance row - make bold with indent for particulars
			if (column.fieldname === "particulars") {
				return `<span style="font-weight: bold; padding-left: 80px;">${value}</span>`;
			}
			return `<span style="font-weight: bold;">${value}</span>`;
		}

		if (data && data._is_total) {
			// Total row - make bold with top border
			return `<span style="font-weight: bold; border-top: 2px solid #000; display: inline-block; padding-top: 3px;">${value}</span>`;
		}

		return value;
	},

	"onload": function(report) {
		// Add custom Print button with Tally styling
		report.page.add_inner_button(__("Tally Print"), function() {
			let filters = frappe.query_report.get_filter_values();
			let data = frappe.query_report.data;

			if (!data || data.length === 0) {
				frappe.msgprint(__("No data to print. Please run the report first."));
				return;
			}

			// Get account name for display
			let account_name = filters.account;

			// Handle party filter (which is now an array from MultiSelectList)
			if (filters.party && Array.isArray(filters.party) && filters.party.length > 0) {
				account_name = filters.party.join(", ");
			} else if (filters.party && typeof filters.party === 'string') {
				account_name = filters.party;
			}

			if (!account_name) {
				account_name = "All Accounts";
			}

			let ledger_type = "Ledger Account";

			if (filters.party_type === "Customer") {
				ledger_type = "Customer Ledger";
			} else if (filters.party_type === "Supplier") {
				ledger_type = "Supplier Ledger";
			} else if (filters.account) {
				ledger_type = "Account Ledger";
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

						// Call server-side method to render template
						frappe.call({
							method: "tally_customizations.tally_customizations.report.tally_ledger.tally_ledger.get_print_html",
							args: {
								filters: filters,
								data: data,
								company: company,
								company_address: company_address,
								account_name: account_name,
								ledger_type: ledger_type
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