import frappe
import os

def create_tally_invoice_print():
	"""Create Tally Invoice Print format"""

	# Delete if already exists to update with new settings
	if frappe.db.exists("Print Format", "Tally Invoice Print"):
		frappe.delete_doc("Print Format", "Tally Invoice Print", force=True)
		frappe.db.commit()

	# Read the HTML template
	html_path = os.path.join(
		frappe.get_app_path("tally_customizations"),
		"tally_customizations",
		"print_format",
		"tally_invoice_print",
		"tally_invoice_print.html"
	)

	with open(html_path, "r") as f:
		html_content = f.read()

	# Create Print Format with reduced margins for single-page printing
	print_format = frappe.get_doc({
		"doctype": "Print Format",
		"name": "Tally Invoice Print",
		"doc_type": "Sales Invoice",
		"module": "Tally Customizations",
		"standard": "No",
		"custom_format": 1,
		"print_format_type": "Jinja",
		"html": html_content,
		"default_print_language": "en",
		"disabled": 0,
		"margin_top": 5,
		"margin_bottom": 5,
		"margin_left": 5,
		"margin_right": 5
	})

	print_format.insert(ignore_permissions=True)
	frappe.db.commit()

	print("Tally Invoice Print format created successfully")

if __name__ == "__main__":
	create_tally_invoice_print()
