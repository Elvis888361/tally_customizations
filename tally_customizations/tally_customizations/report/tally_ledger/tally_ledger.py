# Copyright (c) 2024, Your Company and contributors
# For license information, please see license.txt

import frappe
from frappe import _, _dict
from frappe.utils import flt, getdate, fmt_money, get_datetime_str
import os


def execute(filters=None):
	"""Main entry point for the report"""
	if not filters:
		return [], []

	validate_filters(filters)
	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data


def validate_filters(filters):
	"""Validate required filters"""
	if not filters.get("company"):
		frappe.throw(_("Please select a Company"))

	if not filters.get("from_date"):
		frappe.throw(_("Please select From Date"))

	if not filters.get("to_date"):
		frappe.throw(_("Please select To Date"))


def get_columns(filters):
	"""Define columns in Tally style"""
	columns = []

	# Add account column if showing all accounts
	if not filters.get("account"):
		columns.append({
			"fieldname": "account",
			"label": _("Account"),
			"fieldtype": "Link",
			"options": "Account",
			"width": 200
		})

	columns.extend([
		{
			"fieldname": "posting_date",
			"label": _("Date"),
			"fieldtype": "Date",
			"width": 100
		},
		{
			"fieldname": "particulars",
			"label": _("Particulars"),
			"fieldtype": "Data",
			"width": 250
		},
		{
			"fieldname": "vch_type",
			"label": _("Vch Type"),
			"fieldtype": "Data",
			"width": 120
		},
		{
			"fieldname": "vch_no",
			"label": _("Vch No /Excise Inv No"),
			"fieldtype": "Data",
			"width": 150
		},
		{
			"fieldname": "debit",
			"label": _("Debit"),
			"fieldtype": "Currency",
			"width": 130
		},
		{
			"fieldname": "credit",
			"label": _("Credit"),
			"fieldtype": "Currency",
			"width": 130
		}
	])

	return columns


def get_data(filters):
	"""Fetch and format data in Tally style"""
	data = []

	# Check if specific account is selected
	if filters.get("account"):
		# Single account view with opening/closing balance
		data = get_single_account_data(filters)
	else:
		# All accounts view
		data = get_all_accounts_data(filters)

	return data


def get_single_account_data(filters):
	"""Get data for a single account with opening and closing balance"""
	data = []

	# Get opening balance
	opening_balance = get_opening_balance(filters)

	# Add opening balance row
	opening_particulars = "By Opening Balance" if opening_balance > 0 else "To Opening Balance"
	data.append(_dict(
		posting_date="",
		particulars=opening_particulars,
		vch_type="",
		vch_no="",
		debit=flt(opening_balance) if opening_balance > 0 else 0.0,
		credit=flt(abs(opening_balance)) if opening_balance < 0 else 0.0
	))

	# Get GL entries for the period
	gl_entries = get_gl_entries(filters)

	# Track running totals
	total_debit = flt(opening_balance) if opening_balance > 0 else 0.0
	total_credit = flt(abs(opening_balance)) if opening_balance < 0 else 0.0

	# Process each GL entry
	for gle in gl_entries:
		# Format particulars with To/By prefix (Tally style)
		particulars = format_particulars(gle)

		# Map voucher type to Tally-style names
		vch_type = map_voucher_type(gle.get("voucher_type", ""))

		# Convert posting_date to string if it's a date object
		posting_date = gle.get("posting_date")
		if posting_date:
			posting_date = str(posting_date) if not isinstance(posting_date, str) else posting_date

		# Create row with only the required fields
		data.append(_dict(
			posting_date=posting_date,
			particulars=particulars,
			vch_type=vch_type,
			vch_no=gle.get("voucher_no"),
			debit=flt(gle.get("debit", 0)),
			credit=flt(gle.get("credit", 0))
		))

		# Update totals
		total_debit += flt(gle.get("debit", 0))
		total_credit += flt(gle.get("credit", 0))

	# Calculate closing balance
	closing_balance = total_debit - total_credit

	# Add closing balance row
	closing_particulars = "To Closing Balance" if closing_balance > 0 else "By Closing Balance"
	data.append(_dict(
		posting_date="",
		particulars=closing_particulars,
		vch_type="",
		vch_no="",
		debit=flt(abs(closing_balance)) if closing_balance < 0 else 0.0,
		credit=flt(closing_balance) if closing_balance > 0 else 0.0
	))

	# Update totals to balance
	if closing_balance < 0:
		total_debit += flt(abs(closing_balance))
	else:
		total_credit += flt(closing_balance)

	# Add total row
	data.append(_dict(
		posting_date="",
		particulars="",
		vch_type="",
		vch_no="",
		debit=flt(total_debit),
		credit=flt(total_credit)
	))

	return data


def get_all_accounts_data(filters):
	"""Get data for all accounts"""
	data = []

	# Get GL entries for all accounts
	gl_entries = get_gl_entries(filters)

	# Track totals
	total_debit = 0.0
	total_credit = 0.0

	# Process each GL entry
	for gle in gl_entries:
		# Format particulars with To/By prefix (Tally style)
		particulars = format_particulars(gle)

		# Map voucher type to Tally-style names
		vch_type = map_voucher_type(gle.get("voucher_type", ""))

		# Convert posting_date to string if it's a date object
		posting_date = gle.get("posting_date")
		if posting_date:
			posting_date = str(posting_date) if not isinstance(posting_date, str) else posting_date

		# Create row with only the required fields
		data.append(_dict(
			account=gle.get("account"),
			posting_date=posting_date,
			particulars=particulars,
			vch_type=vch_type,
			vch_no=gle.get("voucher_no"),
			debit=flt(gle.get("debit", 0)),
			credit=flt(gle.get("credit", 0))
		))

		# Update totals
		total_debit += flt(gle.get("debit", 0))
		total_credit += flt(gle.get("credit", 0))

	# Add total row with explicit string conversions
	if data:
		data.append(_dict(
			account="",
			posting_date="",
			particulars="Total",
			vch_type="",
			vch_no="",
			debit=flt(total_debit),
			credit=flt(total_credit)
		))

	return data


def get_opening_balance(filters):
	"""Calculate opening balance before from_date"""
	if not filters.get("account"):
		return 0.0

	opening = frappe.db.sql("""
		SELECT
			SUM(debit) - SUM(credit) as balance
		FROM `tabGL Entry`
		WHERE
			account = %(account)s
			AND company = %(company)s
			AND posting_date < %(from_date)s
			AND is_cancelled = 0
	""", {
		"account": filters.get("account"),
		"company": filters.get("company"),
		"from_date": filters.get("from_date")
	}, as_dict=1)

	return flt(opening[0].balance) if opening and opening[0].balance else 0.0


def get_gl_entries(filters):
	"""Fetch GL entries for the selected period"""
	conditions = []
	values = dict(filters)

	# Add account condition if specified
	if filters.get("account"):
		conditions.append("account = %(account)s")

	# Add party filters
	if filters.get("party_type") and filters.get("party"):
		# Handle party as list (MultiSelectList) or single value
		party = filters.get("party")
		if isinstance(party, (list, tuple)) and len(party) > 0:
			# Use IN clause for multiple parties
			party_list = ', '.join(['%s'] * len(party))
			conditions.append(f"party_type = %(party_type)s AND party IN ({party_list})")
			# Add party values to SQL parameters
			for idx, p in enumerate(party):
				values[f"party_{idx}"] = p
			# Rebuild the query with named parameters
			party_placeholders = ', '.join([f"%(party_{idx})s" for idx in range(len(party))])
			conditions[-1] = f"party_type = %(party_type)s AND party IN ({party_placeholders})"
		else:
			# Single party or string
			if isinstance(party, list):
				party = party[0] if party else None
			if party:
				conditions.append("party_type = %(party_type)s AND party = %(party)s")
				values["party"] = party

	where_clause = ""
	if conditions:
		where_clause = " AND " + " AND ".join(conditions)

	gl_entries = frappe.db.sql(f"""
		SELECT
			posting_date,
			account,
			party_type,
			party,
			voucher_type,
			voucher_no,
			debit,
			credit,
			against,
			remarks
		FROM `tabGL Entry`
		WHERE
			company = %(company)s
			AND posting_date >= %(from_date)s
			AND posting_date <= %(to_date)s
			AND is_cancelled = 0
			{where_clause}
		ORDER BY posting_date, account, creation
	""", values, as_dict=1)

	return gl_entries


def format_particulars(gle):
	"""Format particulars in Tally style with To/By prefix"""
	# In Tally:
	# - "By" is used when money comes from an account (credit side / source)
	# - "To" is used when money goes to an account (debit side / destination)

	# For the selected account:
	# - If debit > 0, money is coming "To" this account, so show "By <contra account>"
	# - If credit > 0, money is going "From" this account, so show "To <contra account>"

	prefix = ""
	contra_account = ""

	if gle.get("debit") > 0:
		# Debit entry - money coming to this account, so it's "By <source>"
		prefix = "By"
		contra_account = gle.get("against") or gle.get("party") or "Various"
	elif gle.get("credit") > 0:
		# Credit entry - money going from this account, so it's "To <destination>"
		prefix = "To"
		contra_account = gle.get("against") or gle.get("party") or "Various"

	# Clean up contra account (remove extra characters)
	if contra_account:
		# Handle multiple accounts (comma-separated)
		if "," in contra_account:
			contra_account = contra_account.split(",")[0].strip()
		# Remove leading/trailing whitespace
		contra_account = contra_account.strip()

	return f"{prefix} {contra_account}"


def map_voucher_type(voucher_type):
	"""Map ERPNext voucher types to Tally-style names"""
	mapping = {
		"Sales Invoice": "Sales",
		"Purchase Invoice": "Purchase",
		"Payment Entry": "Payment",
		"Journal Entry": "Journal",
		"Credit Note": "Credit Note",
		"Debit Note": "Debit Note",
		"Stock Entry": "Stock Journal",
		"Delivery Note": "Delivery Note",
		"Purchase Receipt": "Receipt Note"
	}

	return mapping.get(voucher_type, voucher_type)


@frappe.whitelist()
def get_print_html(filters, data, company, company_address, account_name, ledger_type):
	"""Generate HTML for printing the ledger"""
	import json

	# Parse JSON strings if needed
	if isinstance(filters, str):
		filters = json.loads(filters)
	if isinstance(data, str):
		data = json.loads(data)

	# Get the template path
	template_path = os.path.join(
		os.path.dirname(__file__),
		"tally_ledger_print.html"
	)

	# Read template content
	with open(template_path, "r") as f:
		template_content = f.read()

	# Render template with Jinja
	from jinja2 import Template
	template = Template(template_content)

	# Get company currency
	company_currency = frappe.db.get_value("Company", filters.get("company"), "default_currency") or \
		frappe.defaults.get_global_default("currency") or "USD"

	# Prepare context
	context = {
		"title": f"Tally Ledger - {account_name}",
		"company": company,
		"company_address": company_address,
		"account_name": account_name,
		"ledger_type": ledger_type,
		"from_date": frappe.utils.formatdate(filters.get("from_date"), "dd-MM-yyyy"),
		"to_date": frappe.utils.formatdate(filters.get("to_date"), "dd-MM-yyyy"),
		"currency": company_currency,
		"data": data,
		"frappe": frappe
	}

	# Render and return HTML
	html = template.render(context)
	return html
