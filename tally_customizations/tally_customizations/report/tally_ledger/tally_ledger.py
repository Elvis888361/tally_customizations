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
	if not filters.get("account") and not (filters.get("party_type") and filters.get("party")):
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
			"fieldtype": "Data",
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

	# Check if specific account or party is selected
	if filters.get("account") or (filters.get("party_type") and filters.get("party")):
		# Single account/party view with opening/closing balance
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

	# Format from_date for display
	from_date_str = filters.get("from_date")
	if isinstance(from_date_str, str):
		from_date_obj = getdate(from_date_str)
	else:
		from_date_obj = from_date_str

	# Add opening balance row - only add to data list for printing, not for display
	opening_row = _dict({
		"posting_date": frappe.utils.formatdate(from_date_obj, "d-M-yyyy"),
		"particulars": "By Opening Balance",
		"vch_type": "",
		"vch_no": "",
		"debit": opening_balance if opening_balance > 0 else 0,
		"credit": abs(opening_balance) if opening_balance < 0 else 0,
		"_is_opening": True
	})
	data.append(opening_row)

	# Get GL entries for the period
	gl_entries = get_gl_entries(filters)

	# Track running totals
	total_debit = opening_balance if opening_balance > 0 else 0.0
	total_credit = abs(opening_balance) if opening_balance < 0 else 0.0

	# Process each GL entry
	for gle in gl_entries:
		# Format particulars with To/By prefix (Tally style)
		particulars = format_particulars(gle)

		# Map voucher type to Tally-style names
		vch_type = map_voucher_type(gle.get("voucher_type", ""))

		# Format posting_date
		posting_date = gle.get("posting_date")
		if posting_date:
			posting_date_str = frappe.utils.formatdate(posting_date, "d-M-yyyy")
		else:
			posting_date_str = ""

		# Get amounts
		debit_amt = flt(gle.get("debit", 0))
		credit_amt = flt(gle.get("credit", 0))

		# Create row as dict
		row = _dict({
			"posting_date": posting_date_str,
			"particulars": particulars,
			"vch_type": vch_type,
			"vch_no": gle.get("voucher_no") or "",
			"debit": debit_amt,
			"credit": credit_amt,
			"voucher_type": gle.get("voucher_type", ""),  # Original voucher type for linking
			"voucher_no": gle.get("voucher_no") or ""  # Voucher number for linking
		})

		data.append(row)

		# Update totals
		total_debit += debit_amt
		total_credit += credit_amt

	# Calculate closing balance
	closing_balance = total_debit - total_credit

	# Add closing balance row
	closing_row = _dict({
		"posting_date": "",
		"particulars": "To Closing Balance",
		"vch_type": "",
		"vch_no": "",
		"debit": closing_balance if closing_balance > 0 else 0,
		"credit": abs(closing_balance) if closing_balance < 0 else 0,
		"_is_closing": True
	})
	data.append(closing_row)

	# Update totals to balance
	if closing_balance < 0:
		total_debit += abs(closing_balance)
	else:
		total_credit += closing_balance

	# Add final total row
	total_row = _dict({
		"posting_date": "",
		"particulars": "",
		"vch_type": "",
		"vch_no": "",
		"debit": total_debit,
		"credit": total_credit,
		"_is_total": True
	})
	data.append(total_row)

	return data


def get_all_accounts_data(filters):
	"""Get data for all accounts - just transactions and total"""
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

		# Format posting_date
		posting_date = gle.get("posting_date")
		if posting_date:
			posting_date_str = frappe.utils.formatdate(posting_date, "d-M-yyyy")
		else:
			posting_date_str = ""

		# Get amounts
		debit_amt = flt(gle.get("debit", 0))
		credit_amt = flt(gle.get("credit", 0))

		# Create row as dict
		row = _dict({
			"account": gle.get("account") or "",
			"posting_date": posting_date_str,
			"particulars": particulars or "",
			"vch_type": vch_type or "",
			"vch_no": gle.get("voucher_no") or "",
			"debit": debit_amt,
			"credit": credit_amt,
			"voucher_type": gle.get("voucher_type", ""),  # Original voucher type for linking
			"voucher_no": gle.get("voucher_no") or ""  # Voucher number for linking
		})

		data.append(row)

		# Update totals
		total_debit += debit_amt
		total_credit += credit_amt

	# Add total row - just totals, no closing balance for all accounts view
	if data:
		total_row = _dict({
			"account": "",
			"posting_date": "",
			"particulars": "Total",
			"vch_type": "",
			"vch_no": "",
			"debit": total_debit,
			"credit": total_credit,
			"_is_total": True
		})
		data.append(total_row)

	return data


def get_opening_balance(filters):
	"""Calculate opening balance before from_date"""
	conditions = []
	values = {
		"company": filters.get("company"),
		"from_date": filters.get("from_date")
	}

	# Add account condition if specified
	if filters.get("account"):
		conditions.append("account = %(account)s")
		values["account"] = filters.get("account")

	# Add party filters
	if filters.get("party_type") and filters.get("party"):
		party = filters.get("party")
		if isinstance(party, (list, tuple)) and len(party) > 0:
			# For multiple parties, calculate combined opening balance
			party_placeholders = ', '.join([f"%(party_{idx})s" for idx in range(len(party))])
			conditions.append(f"party_type = %(party_type)s AND party IN ({party_placeholders})")
			values["party_type"] = filters.get("party_type")
			for idx, p in enumerate(party):
				values[f"party_{idx}"] = p
		else:
			# Single party
			if isinstance(party, list):
				party = party[0] if party else None
			if party:
				conditions.append("party_type = %(party_type)s AND party = %(party)s")
				values["party_type"] = filters.get("party_type")
				values["party"] = party

	if not conditions:
		return 0.0

	where_clause = " AND ".join(conditions)

	opening = frappe.db.sql(f"""
		SELECT
			SUM(debit) - SUM(credit) as balance
		FROM `tabGL Entry`
		WHERE
			{where_clause}
			AND company = %(company)s
			AND posting_date < %(from_date)s
			AND is_cancelled = 0
	""", values, as_dict=1)

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
			party_placeholders = ', '.join([f"%(party_{idx})s" for idx in range(len(party))])
			conditions.append(f"party_type = %(party_type)s AND party IN ({party_placeholders})")
			# Add party values to SQL parameters
			for idx, p in enumerate(party):
				values[f"party_{idx}"] = p
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
	prefix = ""
	contra_account = ""

	if gle.get("debit") > 0:
		# Debit entry - money coming to this account
		prefix = "By"
		contra_account = gle.get("against") or gle.get("party") or "Various"
	elif gle.get("credit") > 0:
		# Credit entry - money going from this account
		prefix = "To"
		contra_account = gle.get("against") or gle.get("party") or "Various"

	# Clean up contra account
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
		"Payment Entry": "Receipt",
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
		"from_date": frappe.utils.formatdate(filters.get("from_date"), "d-MMM-yyyy"),
		"to_date": frappe.utils.formatdate(filters.get("to_date"), "d-MMM-yyyy"),
		"currency": company_currency,
		"data": data,
		"frappe": frappe
	}

	# Render and return HTML
	html = template.render(context)
	return html