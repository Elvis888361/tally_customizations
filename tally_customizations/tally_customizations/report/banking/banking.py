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
	"""Define columns for Banking"""
	columns = [
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
			"fieldname": "account",
			"label": _("Paid To/From"),
			"fieldtype": "Data",
			"width": 200
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
	]

	return columns


def get_data(filters):
	"""Fetch and format data for Banking"""
	data = []

	# Get opening balance
	opening_balance = get_opening_balance(filters)

	# Format from_date for display
	from_date_str = filters.get("from_date")
	if isinstance(from_date_str, str):
		from_date_obj = getdate(from_date_str)
	else:
		from_date_obj = from_date_str

	# Add opening balance row
	if opening_balance != 0:
		opening_row = _dict({
			"posting_date": from_date_obj.strftime("%-d-%-m-%Y"),
			"particulars": "By Opening Balance" if opening_balance > 0 else "To Opening Balance",
			"account": "",
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
		# Format particulars with Cr/Dr prefix (Banking style)
		particulars, contra_account = format_banking_particulars(gle)

		# Map voucher type to Tally-style names
		vch_type = map_voucher_type(gle.get("voucher_type", ""))

		# Format posting_date
		posting_date = gle.get("posting_date")
		if posting_date:
			if isinstance(posting_date, str):
				posting_date = getdate(posting_date)
			posting_date_str = posting_date.strftime("%-d-%-m-%Y")
		else:
			posting_date_str = ""

		# Get amounts
		debit_amt = flt(gle.get("debit", 0))
		credit_amt = flt(gle.get("credit", 0))

		# Create row as dict
		row = _dict({
			"posting_date": posting_date_str,
			"particulars": particulars,
			"account": contra_account,
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

	# Add subtotal row (without closing balance) if there are entries
	if data:
		subtotal_row = _dict({
			"posting_date": "",
			"particulars": "",
			"account": "",
			"vch_type": "",
			"vch_no": "",
			"debit": total_debit,
			"credit": total_credit,
			"_is_subtotal": True
		})
		data.append(subtotal_row)

	# Calculate closing balance
	closing_balance = total_debit - total_credit

	# Add closing balance row with appropriate Dr/Cr prefix
	if closing_balance > 0:
		closing_particulars = "Dr  Closing Balance"
	else:
		closing_particulars = "Cr  Closing Balance"

	closing_row = _dict({
		"posting_date": "",
		"particulars": closing_particulars,
		"account": "",
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
		"account": "",
		"vch_type": "",
		"vch_no": "",
		"debit": total_debit,
		"credit": total_credit,
		"_is_total": True
	})
	data.append(total_row)

	return data


def get_opening_balance(filters):
	"""Calculate opening balance before from_date for party"""
	conditions = []
	values = {
		"company": filters.get("company"),
		"from_date": filters.get("from_date")
	}

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
	"""Fetch GL entries for the selected period with party filters"""
	conditions = []
	values = dict(filters)

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


def format_banking_particulars(gle):
	"""Format particulars in Cash Book style with Cr/Dr prefix
	Returns: (particulars, contra_account)
	"""
	prefix = ""
	contra_account = gle.get("contra_account", "")
	party_name = ""

	if gle.get("debit") > 0:
		# Debit entry - money coming in (Credit to the contra account)
		prefix = "Cr"
		# Get party name or against field for particulars
		party_name = gle.get("against") or gle.get("party") or contra_account or "Sales"
		# Fallback if contra_account is empty
		if not contra_account:
			contra_account = "Sales"
	elif gle.get("credit") > 0:
		# Credit entry - money going out (Debit to the contra account)
		prefix = "Dr"
		# Get party name or against field for particulars
		party_name = gle.get("against") or gle.get("party") or contra_account or "Expenses"
		# Fallback if contra_account is empty
		if not contra_account:
			contra_account = "Expenses"

	# Clean up party name for particulars (handle multiple values)
	if party_name:
		if "," in party_name:
			party_name = party_name.split(",")[0].strip()
		party_name = party_name.strip()

	# Clean up contra account (remove any trailing/leading spaces)
	if contra_account:
		contra_account = contra_account.strip()

	particulars = f"{prefix}  {party_name}"
	return particulars, contra_account


def map_voucher_type(voucher_type):
	"""Map ERPNext voucher types to Tally-style names"""
	mapping = {
		"Sales Invoice": "Bank Sales",
		"Purchase Invoice": "Purchase",
		"Payment Entry": "Payment",
		"Journal Entry": "Receipt",
		"Credit Note": "Credit Note",
		"Debit Note": "Debit Note",
		"Stock Entry": "Stock Journal",
		"Delivery Note": "Delivery Note",
		"Purchase Receipt": "Receipt"
	}

	return mapping.get(voucher_type, voucher_type)


@frappe.whitelist()
def get_print_html(filters, data, company, company_address, company_contact, party_name=None, ledger_type=None):
	"""Generate HTML for printing the banking report"""
	import json

	# Parse JSON strings if needed
	if isinstance(filters, str):
		filters = json.loads(filters)
	if isinstance(data, str):
		data = json.loads(data)

	# Get the template path
	template_path = os.path.join(
		os.path.dirname(__file__),
		"banking_print.html"
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
	to_date = filters.get("to_date")
	if isinstance(to_date, str):
		to_date = getdate(to_date)

	# Use party_name if provided, otherwise use default
	title = f"{ledger_type or 'Banking'} - {party_name or company}"

	context = {
		"title": title,
		"company": company,
		"company_address": company_address,
		"company_contact": company_contact,
		"party_name": party_name or "All Parties",
		"ledger_type": ledger_type or "Banking",
		"from_date": getdate(filters.get("from_date")).strftime("%-d-%b-%Y"),
		"to_date": to_date.strftime("%-d-%b-%Y"),
		"report_date": to_date.strftime("%-d-%b-%Y"),
		"currency": company_currency,
		"data": data,
		"frappe": frappe
	}

	# Render and return HTML
	html = template.render(context)
	return html
