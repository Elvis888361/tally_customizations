"""
Installation script for Detailed Invoice Print format
"""
import frappe
import os


def install_print_format():
	"""Install or update the Detailed Invoice Print format"""

	# Path to HTML template
	html_path = os.path.join(
		os.path.dirname(__file__),
		"tally_customizations",
		"print_format",
		"detailed_invoice_print",
		"detailed_invoice_print.html"
	)

	# Read HTML content
	with open(html_path, "r") as f:
		html_content = f.read()

	# Check if print format exists
	if frappe.db.exists("Print Format", "Detailed Invoice Print"):
		# Update existing
		print_format = frappe.get_doc("Print Format", "Detailed Invoice Print")
		print_format.html = html_content
		print_format.save()
		print("✓ Updated Detailed Invoice Print format")
	else:
		# Create new
		print_format = frappe.get_doc({
			"doctype": "Print Format",
			"name": "Detailed Invoice Print",
			"doc_type": "Sales Invoice",
			"module": "Tally Customizations",
			"standard": "No",
			"custom_format": 1,
			"html": html_content,
			"print_format_type": "Jinja",
			"font_size": 9,
			"margin_top": 10,
			"margin_bottom": 10,
			"margin_left": 10,
			"margin_right": 10,
			"page_number": "Hide",
			"disabled": 0
		})
		print_format.insert()
		print("✓ Created Detailed Invoice Print format")

	frappe.db.commit()
	return print_format.name


if __name__ == "__main__":
	frappe.connect(site='local.net')
	install_print_format()
	print("\nDetaile Invoice Print format installed successfully!")
	print("You can now use it from any Sales Invoice by selecting it in the Print dropdown.")
