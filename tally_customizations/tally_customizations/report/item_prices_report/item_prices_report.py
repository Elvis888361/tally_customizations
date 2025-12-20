# Copyright (c) 2024, Tally Customizations and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	if not filters:
		return [], []

	columns = get_columns(filters)
	data = get_data(filters)

	return columns, data


def get_columns(filters):
	"""Build columns dynamically based on selected price lists"""
	columns = [
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 150
		},
		{
			"label": _("Item Name"),
			"fieldname": "item_name",
			"fieldtype": "Data",
			"width": 200
		},
		{
			"label": _("UOM"),
			"fieldname": "uom",
			"fieldtype": "Link",
			"options": "UOM",
			"width": 80
		}
	]

	# Get buying price lists
	buying_price_lists = get_buying_price_lists(filters)
	for pl in buying_price_lists:
		currency = get_price_list_currency(pl)
		fieldname = frappe.scrub(pl)
		columns.append({
			"label": f"{pl} ({currency})",
			"fieldname": f"buying_{fieldname}",
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		})

	# Get selling price lists
	selling_price_lists = get_selling_price_lists(filters)
	for pl in selling_price_lists:
		currency = get_price_list_currency(pl)
		fieldname = frappe.scrub(pl)
		columns.append({
			"label": f"{pl} ({currency})",
			"fieldname": f"selling_{fieldname}",
			"fieldtype": "Float",
			"precision": 2,
			"width": 150
		})

	return columns


def get_price_list_currency(price_list):
	"""Get the currency of a price list"""
	currency = frappe.db.get_value("Price List", price_list, "currency")
	return currency or frappe.db.get_default("currency") or "UGX"


def get_buying_price_lists(filters):
	"""Get buying price lists"""
	if filters.get("buying_price_list"):
		pl = filters.get("buying_price_list")
		return [pl] if isinstance(pl, str) else list(pl)

	# Get all price lists marked for buying
	return frappe.get_all(
		"Price List",
		filters={"buying": 1, "enabled": 1},
		pluck="name",
		order_by="name"
	)


def get_selling_price_lists(filters):
	"""Get selling price lists"""
	if filters.get("selling_price_list"):
		pl = filters.get("selling_price_list")
		return [pl] if isinstance(pl, str) else list(pl)

	# Get all price lists marked for selling
	return frappe.get_all(
		"Price List",
		filters={"selling": 1, "enabled": 1},
		pluck="name",
		order_by="name"
	)


def get_data(filters):
	"""Fetch items and their prices from different price lists"""
	data = []

	# Build item filters
	item_filters = {"disabled": 0}

	if filters.get("item_group"):
		item_filters["item_group"] = filters.get("item_group")

	if filters.get("item_code"):
		item_filters["name"] = filters.get("item_code")

	if filters.get("brand"):
		item_filters["brand"] = filters.get("brand")

	# Get items
	items = frappe.get_all(
		"Item",
		filters=item_filters,
		fields=["name", "item_name", "stock_uom", "item_group", "brand"],
		order_by="name"
	)

	if not items:
		return data

	# Get price lists
	buying_price_lists = get_buying_price_lists(filters)
	selling_price_lists = get_selling_price_lists(filters)

	# Build a map of item prices for faster lookup
	all_price_lists = list(set(buying_price_lists + selling_price_lists))

	# Get item codes for filtering
	item_codes = [item.name for item in items]

	# Build price map
	price_map = build_price_map(all_price_lists, item_codes)

	for item in items:
		row = {
			"item_code": item.name,
			"item_name": item.item_name,
			"uom": item.stock_uom,
		}

		# Add buying rates
		for pl in buying_price_lists:
			fieldname = frappe.scrub(pl)
			rate = get_item_price(price_map, item.name, pl, item.stock_uom)
			row[f"buying_{fieldname}"] = rate

		# Add selling rates
		for pl in selling_price_lists:
			fieldname = frappe.scrub(pl)
			rate = get_item_price(price_map, item.name, pl, item.stock_uom)
			row[f"selling_{fieldname}"] = rate

		data.append(row)

	return data


def build_price_map(price_lists, item_codes=None):
	"""Build a map of item prices for quick lookup"""
	if not price_lists:
		return {}

	# Build filters
	filters = {"price_list": ["in", price_lists]}

	# Optionally filter by items for better performance
	if item_codes:
		filters["item_code"] = ["in", item_codes]

	# Get all item prices for these price lists
	item_prices = frappe.get_all(
		"Item Price",
		filters=filters,
		fields=["item_code", "price_list", "price_list_rate", "uom"]
	)

	# Build map: {(item_code, price_list): rate}
	price_map = {}
	for ip in item_prices:
		# Store with UOM
		key_with_uom = (ip.item_code, ip.price_list, ip.uom)
		price_map[key_with_uom] = flt(ip.price_list_rate)

		# Store without UOM (for fallback)
		key_no_uom = (ip.item_code, ip.price_list)
		if key_no_uom not in price_map:
			price_map[key_no_uom] = flt(ip.price_list_rate)

	return price_map


def get_item_price(price_map, item_code, price_list, uom):
	"""Get item price from price map"""
	# Try with UOM first
	if uom:
		key = (item_code, price_list, uom)
		if key in price_map:
			return price_map[key]

	# Try without UOM
	key_no_uom = (item_code, price_list)
	if key_no_uom in price_map:
		return price_map[key_no_uom]

	return 0.0
