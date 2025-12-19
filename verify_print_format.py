import frappe

def verify_print_format():
    """Verify that the Detailed Invoice Print format exists"""
    frappe.connect(site='local.net')

    if frappe.db.exists('Print Format', 'Detailed Invoice Print'):
        print("SUCCESS: Detailed Invoice Print format is installed!")

        # Get the print format doc
        pf = frappe.get_doc('Print Format', 'Detailed Invoice Print')
        print(f"Print Format Name: {pf.name}")
        print(f"Doc Type: {pf.doc_type}")
        print(f"Module: {pf.module}")
        print(f"Print Format Type: {pf.print_format_type}")
        return True
    else:
        print("ERROR: Detailed Invoice Print format not found!")
        return False

if __name__ == "__main__":
    verify_print_format()
