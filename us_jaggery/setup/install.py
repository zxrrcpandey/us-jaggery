import json
import os

import frappe


def get_coa_path():
	"""Absolute path to the US Jaggery chart-of-accounts JSON shipped with this app."""
	return os.path.join(
		os.path.dirname(__file__), "chart_of_accounts", "us_jaggery_coa.json"
	)


def load_coa():
	with open(get_coa_path()) as f:
		return json.load(f)


@frappe.whitelist()
def import_coa(company, replace_existing=False):
	"""Apply the US Jaggery custom Chart of Accounts (with account numbers) to ``company``.

	Each account's ``account_number`` in the JSON is its ID. Run after the company
	exists, e.g.::

	    bench --site us_jaggery.local execute us_jaggery.setup.install.import_coa \
	        --kwargs "{'company': 'US Jaggery', 'replace_existing': True}"

	Args:
	    company: name of an existing Company.
	    replace_existing: if truthy, delete the company's current (transaction-free)
	        accounts before importing, so the custom tree fully replaces the default CoA.
	"""
	from erpnext.accounts.doctype.account.chart_of_accounts.chart_of_accounts import (
		create_charts,
	)

	if isinstance(replace_existing, str):
		replace_existing = replace_existing.strip().lower() in ("1", "true", "yes", "y")

	if not frappe.db.exists("Company", company):
		frappe.throw(f"Company {company!r} does not exist.")

	coa = load_coa()
	tree = coa.get("tree") or coa  # support {name, tree, ...} or a bare tree dict

	if replace_existing:
		_delete_company_accounts(company)

	create_charts(company, custom_chart=tree)
	frappe.db.commit()

	created = frappe.db.count("Account", {"company": company})
	return f"Imported '{coa.get('name', 'US Jaggery CoA')}' into {company} ({created} accounts)."


def _delete_company_accounts(company):
	"""Delete all Accounts for a company, leaf-first. Refuses if any GL Entry exists."""
	if frappe.db.exists("GL Entry", {"company": company}):
		frappe.throw(
			f"Refusing to delete accounts for {company}: GL Entries already exist."
		)

	# Nested-set: deleting in descending lft order removes children before parents.
	accounts = frappe.get_all(
		"Account", filters={"company": company}, order_by="lft desc", pluck="name"
	)
	for name in accounts:
		frappe.delete_doc("Account", name, force=True, ignore_permissions=True)
