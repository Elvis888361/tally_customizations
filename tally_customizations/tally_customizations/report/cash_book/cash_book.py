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
	"""Define columns for Cash Book"""
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
	"""Fetch and format data for Cash Book"""
	data = []

	# Get cash accounts for the company
	cash_accounts = get_cash_accounts(filters.get("company"))

	if not cash_accounts:
		frappe.msgprint(_("No Cash accounts found for this company"))
		return data

	# If specific account is selected, use it; otherwise use all cash accounts
	if filters.get("account"):
		if filters.get("account") in cash_accounts:
			account_list = [filters.get("account")]
		else:
			frappe.msgprint(_("Selected account is not a Cash account"))
			return data
	else:
		account_list = cash_accounts

	# Get opening balance
	opening_balance = get_opening_balance(filters, account_list)

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
	gl_entries = get_gl_entries(filters, account_list)

	# Track running totals
	total_debit = opening_balance if opening_balance > 0 else 0.0
	total_credit = abs(opening_balance) if opening_balance < 0 else 0.0

	# Process each GL entry
	for gle in gl_entries:
		# Format particulars with Cr/Dr prefix (Cash Book style)
		particulars, contra_account = format_cash_book_particulars(gle)

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


def get_cash_accounts(company):
	"""Get all Cash accounts for the company"""
	cash_accounts = frappe.db.sql("""
		SELECT name
		FROM `tabAccount`
		WHERE company = %(company)s
			AND account_type = 'Cash'
			AND is_group = 0
			AND disabled = 0
		ORDER BY name
	""", {"company": company}, as_list=1)

	return [acc[0] for acc in cash_accounts] if cash_accounts else []


def get_opening_balance(filters, account_list):
	"""Calculate opening balance before from_date for cash accounts"""
	if not account_list:
		return 0.0

	# Create placeholders for accounts
	account_placeholders = ', '.join([f"%(account_{idx})s" for idx in range(len(account_list))])

	values = {
		"company": filters.get("company"),
		"from_date": filters.get("from_date")
	}

	# Add account values
	for idx, acc in enumerate(account_list):
		values[f"account_{idx}"] = acc

	opening = frappe.db.sql(f"""
		SELECT
			SUM(debit) - SUM(credit) as balance
		FROM `tabGL Entry`
		WHERE
			account IN ({account_placeholders})
			AND company = %(company)s
			AND posting_date < %(from_date)s
			AND is_cancelled = 0
	""", values, as_dict=1)

	return flt(opening[0].balance) if opening and opening[0].balance else 0.0


def get_gl_entries(filters, account_list):
	"""Fetch GL entries for cash accounts for the selected period with contra accounts"""
	if not account_list:
		return []

	# Create placeholders for accounts
	account_placeholders = ', '.join([f"%(account_{idx})s" for idx in range(len(account_list))])

	values = {
		"company": filters.get("company"),
		"from_date": filters.get("from_date"),
		"to_date": filters.get("to_date")
	}

	# Add account values
	for idx, acc in enumerate(account_list):
		values[f"account_{idx}"] = acc

	# First get all GL entries for cash accounts
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
			account IN ({account_placeholders})
			AND company = %(company)s
			AND posting_date >= %(from_date)s
			AND posting_date <= %(to_date)s
			AND is_cancelled = 0
		ORDER BY posting_date, account, creation
	""", values, as_dict=1)

	# Now get the actual contra accounts for each GL entry
	for gle in gl_entries:
		# Query the contra GL entries from the same voucher
		contra_entries = frappe.db.sql("""
			SELECT account
			FROM `tabGL Entry`
			WHERE voucher_type = %(voucher_type)s
				AND voucher_no = %(voucher_no)s
				AND account NOT IN %(cash_accounts)s
				AND is_cancelled = 0
			LIMIT 1
		""", {
			"voucher_type": gle.get("voucher_type"),
			"voucher_no": gle.get("voucher_no"),
			"cash_accounts": account_list
		}, as_dict=1)

		# Set the contra_account field
		if contra_entries and len(contra_entries) > 0:
			gle["contra_account"] = contra_entries[0].get("account")
		else:
			# Fallback to against field if no contra entry found
			against = gle.get("against", "")
			if against:
				# Clean up the against field (remove party names, take first account)
				if "," in against:
					against = against.split(",")[0].strip()
				gle["contra_account"] = against
			else:
				gle["contra_account"] = ""

	return gl_entries


def format_cash_book_particulars(gle):
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
		"Sales Invoice": "Cash Sales",
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
def get_print_html(filters, data, company, company_address, company_contact):
	"""Generate HTML for printing the cash book"""
	import json

	# Parse JSON strings if needed
	if isinstance(filters, str):
		filters = json.loads(filters)
	if isinstance(data, str):
		data = json.loads(data)

	# Get the template path
	template_path = os.path.join(
		os.path.dirname(__file__),
		"cash_book_print.html"
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

	context = {
		"title": f"Cash Book - {company}",
		"company": company,
		"company_address": company_address,
		"company_contact": company_contact,
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
