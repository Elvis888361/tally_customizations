# Copyright (c) 2024, Tally Customizations and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, formatdate, getdate


def execute(filters=None):
	if not filters:
		return [], []

	validate_filters(filters)
	columns = get_columns()
	data = get_data(filters)

	return columns, data


def validate_filters(filters):
	"""Validate required filters"""
	if not filters.get("company"):
		frappe.throw(_("Please select a Company"))

	if not filters.get("customer"):
		frappe.throw(_("Please select a Customer"))

	if not filters.get("from_date"):
		frappe.throw(_("Please select From Date"))

	if not filters.get("to_date"):
		frappe.throw(_("Please select To Date"))


def get_columns():
	return [
		{
			"label": _("Date"),
			"fieldname": "posting_date",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Ref No"),
			"fieldname": "ref_no",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Type"),
			"fieldname": "type",
			"fieldtype": "Data",
			"width": 100
		},
		{
			"label": _("Location"),
			"fieldname": "location",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Payment Status"),
			"fieldname": "payment_status",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Debit"),
			"fieldname": "debit",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Credit"),
			"fieldname": "credit",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Balance"),
			"fieldname": "balance",
			"fieldtype": "Currency",
			"width": 120
		},
		{
			"label": _("Payment Method"),
			"fieldname": "payment_method",
			"fieldtype": "Data",
			"width": 120
		},
		{
			"label": _("Notes"),
			"fieldname": "notes",
			"fieldtype": "Data",
			"width": 150
		}
	]


def get_data(filters):
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	customer = filters.get("customer")
	company = filters.get("company")

	data = []
	balance = 0

	# Get opening balance
	opening_balance = get_opening_balance(customer, from_date, company)
	balance = opening_balance

	# Get currency
	currency = frappe.db.get_value("Customer", customer, "default_currency") or \
		frappe.db.get_value("Company", company, "default_currency") or "UGX"

	# Add opening balance row
	data.append({
		"posting_date": formatdate(from_date, "dd/MM/yyyy"),
		"ref_no": "",
		"type": "Opening Balance",
		"location": "",
		"payment_status": "",
		"debit": opening_balance if opening_balance > 0 else 0,
		"credit": abs(opening_balance) if opening_balance < 0 else 0,
		"balance": abs(balance),
		"balance_type": "DR" if balance >= 0 else "CR",
		"payment_method": "",
		"notes": "",
		"currency": currency,
		"_is_opening": True
	})

	# Get GL entries grouped by voucher so each Payment Entry / Sales Invoice
	# appears exactly once with its total debit and credit amounts.
	gl_entries = frappe.db.sql("""
		SELECT
			posting_date,
			voucher_type,
			voucher_no,
			SUM(debit) as debit,
			SUM(credit) as credit
		FROM `tabGL Entry`
		WHERE
			party_type = 'Customer'
			AND party = %(customer)s
			AND company = %(company)s
			AND posting_date BETWEEN %(from_date)s AND %(to_date)s
			AND is_cancelled = 0
		GROUP BY voucher_type, voucher_no, posting_date
		ORDER BY posting_date, MIN(creation)
	""", {
		"customer": customer,
		"company": company,
		"from_date": from_date,
		"to_date": to_date
	}, as_dict=1)

	# Process GL entries
	for gle in gl_entries:
		debit_amt = flt(gle.debit)
		credit_amt = flt(gle.credit)
		balance += debit_amt - credit_amt

		row_type = ""
		location = ""
		payment_status = ""
		payment_method = ""
		notes = ""
		items = []

		# Get voucher details
		if gle.voucher_type == "Sales Invoice":
			invoice = frappe.get_doc("Sales Invoice", gle.voucher_no)
			row_type = "Invoice"
			location = invoice.set_warehouse or ""
			payment_status = "Paid" if invoice.status == "Paid" else "NOT PAID"
			notes = "NOT PAID" if invoice.status != "Paid" else ""

			# Get invoice items
			items = frappe.get_all(
				"Sales Invoice Item",
				filters={"parent": gle.voucher_no},
				fields=["item_code", "item_name", "qty", "rate", "amount", "discount_amount", "uom"],
				order_by="idx"
			)

		elif gle.voucher_type == "Payment Entry":
			payment = frappe.db.get_value(
				"Payment Entry", gle.voucher_no,
				["mode_of_payment", "reference_no", "remarks"],
				as_dict=1
			)
			row_type = "Payment"
			payment_method = (payment.mode_of_payment or "Bank Transfer") if payment else "Bank Transfer"
			notes = (payment.reference_no or "Payment received") if payment else "Payment received"

		else:
			row_type = gle.voucher_type

		data.append({
			"posting_date": formatdate(gle.posting_date, "dd/MM/yyyy"),
			"ref_no": gle.voucher_no,
			"type": row_type,
			"location": location,
			"payment_status": payment_status,
			"debit": debit_amt,
			"credit": credit_amt,
			"balance": abs(balance),
			"balance_type": "DR" if balance >= 0 else "CR",
			"payment_method": payment_method,
			"notes": notes,
			"currency": currency,
			"items": items,
			"voucher_type": gle.voucher_type,
			"voucher_no": gle.voucher_no
		})

	return data


def get_opening_balance(customer, from_date, company):
	"""Get the opening balance for the customer before the from_date"""
	opening = frappe.db.sql("""
		SELECT
			SUM(debit) - SUM(credit) as balance
		FROM `tabGL Entry`
		WHERE
			party_type = 'Customer'
			AND party = %(customer)s
			AND company = %(company)s
			AND posting_date < %(from_date)s
			AND is_cancelled = 0
	""", {
		"customer": customer,
		"company": company,
		"from_date": from_date
	}, as_dict=1)

	return flt(opening[0].balance) if opening and opening[0].balance else 0.0


@frappe.whitelist()
def get_print_html(filters, data):
	"""Generate HTML for printing the customer detailed ledger"""
	import json

	# Parse filters and data if they're strings
	if isinstance(filters, str):
		filters = json.loads(filters)
	if isinstance(data, str):
		data = json.loads(data)

	# Get the HTML template
	template_path = frappe.get_app_path(
		"tally_customizations",
		"tally_customizations",
		"report",
		"customer_detailed_ledger",
		"customer_detailed_ledger.html"
	)

	with open(template_path, "r") as f:
		template_content = f.read()

	# Render the template with data
	from jinja2 import Template
	template = Template(template_content)

	# Get company info
	company = filters.get("company")
	customer = filters.get("customer")

	html = template.render(
		filters=filters,
		data=data,
		company=company,
		frappe=frappe
	)

	return html
