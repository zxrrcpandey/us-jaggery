"""Create the US Jaggery company and import the client's 185-account chart.

Strategy (see project notes): create the company on ERPNext's **Standard** chart
so ERPNext + India Compliance build all mandatory system + GST/TDS accounts under
the parent groups they expect, then **add** the client's accounts into the matching
standard groups, preserving each client Account ID in ``account_number``.

Run end-to-end:
    bench --site us_jaggery.local execute us_jaggery.setup.client_coa.run
"""

import json
import os

import frappe

COMPANY = "US Jaggery"
ABBR = "USJ"

# Sage account-type  ->  (standard ERPNext parent group, optional sub-group to create, leaf account_type)
MAPPING = {
	"Cash":                     ("Cash In Hand",                 None,                        "Cash"),
	"Other Current Assets":     ("Current Assets",               "Other Current Assets",      ""),
	"Accounts Receivable":      ("Accounts Receivable",          None,                        ""),   # plain ledger (not Receivable -> no forced party)
	"Inventory":                ("Stock Assets",                 None,                        "Stock"),
	"Fixed Assets":             ("Fixed Assets",                 None,                        "Fixed Asset"),
	"Accumulated Depreciation": ("Fixed Assets",                 None,                        "Accumulated Depreciation"),
	"Accounts Payable":         ("Accounts Payable",             None,                        ""),   # plain ledger (Creditors stays the Payable control)
	"Other Current Liabilities":("Current Liabilities",          "Other Current Liabilities", ""),
	"Long Term Liabilities":    ("Source of Funds (Liabilities)","Long Term Liabilities",     ""),
	# India CoA has no separate Equity root: capital/reserves sit under "Capital Account" (Liability / Sources of Funds)
	"Equity-Retained Earnings": ("Capital Account",              None,                        ""),
	"Equity-gets closed":       ("Capital Account",              None,                        ""),
	"Equity-doesn't close":     ("Capital Account",              None,                        ""),
	"Income":                   ("Indirect Income",              None,                        "Income Account"),
	"Cost of Sales":            ("Direct Expenses",              "Cost of Sales",             "Cost of Goods Sold"),
	"Expenses":                 ("Indirect Expenses",            None,                        "Expense Account"),
}


def _data_path():
	return os.path.join(os.path.dirname(__file__), "data", "client_accounts.json")


def _load():
	with open(_data_path()) as f:
		return json.load(f)


def _is_bank(name, sage_type):
	"""Real operating bank accounts only (exclude FDRs / sweep / deposits)."""
	if sage_type != "Other Current Assets":
		return False
	u = name.upper()
	return "BANK" in u and not any(x in u for x in ("FDR", "SWEEP", "DEP", "FCNR", "RENT"))


def _group(company, account_name):
	return frappe.db.get_value(
		"Account", {"account_name": account_name, "company": company, "is_group": 1}, "name"
	)


# Some erpnext versions build the India chart (equity under "Capital Account"), others the
# generic Standard chart (equity under the "Equity" root). Resolve with a fallback.
GROUP_FALLBACKS = {"Capital Account": "Equity"}


def _resolve_group(company, account_name):
	nm = _group(company, account_name)
	if not nm and account_name in GROUP_FALLBACKS:
		nm = _group(company, GROUP_FALLBACKS[account_name])
	return nm


def _ensure_subgroup(company, sub_name, parent_group):
	existing = _group(company, sub_name)
	if existing:
		return existing
	parent = _resolve_group(company, parent_group)
	if not parent:
		frappe.throw(f"Parent group {parent_group!r} not found for company {company}")
	doc = frappe.new_doc("Account")
	doc.update({"account_name": sub_name, "parent_account": parent, "company": company, "is_group": 1})
	doc.flags.ignore_permissions = True
	doc.insert()
	return doc.name


# ---------------------------------------------------------------------------


def create_company(company=COMPANY, abbr=ABBR, currency="INR", country="India"):
	if frappe.db.exists("Company", company):
		return company
	doc = frappe.new_doc("Company")
	doc.update({
		"company_name": company,
		"abbr": abbr,
		"default_currency": currency,
		"country": country,
		"create_chart_of_accounts_based_on": "Standard Template",
		"chart_of_accounts": "Standard",
	})
	doc.flags.ignore_permissions = True
	doc.insert()
	frappe.db.commit()
	return doc.name


def import_accounts(company=COMPANY):
	data = _load()
	abbr = frappe.get_cached_value("Company", company, "abbr")
	created, skipped, banks, errors, suffixed = 0, 0, [], [], []

	for acc in data:
		try:
			if frappe.db.exists("Account", {"company": company, "account_number": acc["id"]}):
				skipped += 1
				continue

			sage = acc["sage_type"]
			mapping = MAPPING.get(sage)
			if not mapping:
				errors.append((acc["id"], f"no mapping for sage type {sage!r}"))
				continue
			parent_group, subgroup, acct_type = mapping

			if _is_bank(acc["name"], sage):
				parent_group, subgroup, acct_type = "Bank Accounts", None, "Bank"
				banks.append(f'{acc["id"]} {acc["name"]}')

			parent = _ensure_subgroup(company, subgroup, parent_group) if subgroup else _resolve_group(company, parent_group)
			if not parent:
				errors.append((acc["id"], f"parent group {parent_group!r} not found"))
				continue

			# ERPNext account names must be unique; without the ID in the name, the
			# client's duplicate names (and names matching standard/group accounts)
			# would collide. Disambiguate ONLY those by appending the Auto-ID.
			acct_name = acc["name"]
			if frappe.db.exists("Account", f"{acct_name} - {abbr}"):
				acct_name = f'{acc["name"]} ({acc["id"]})'
				suffixed.append(f'{acc["id"]} {acc["name"]}')

			doc = frappe.new_doc("Account")
			doc.update({
				"account_name": acct_name,
				"custom_auto_id": acc["id"],   # client ID -> custom Auto-ID field (account_number left blank)
				"parent_account": parent,
				"company": company,
				"is_group": 0,
				"account_type": acct_type or None,
				"disabled": 0 if acc.get("active", True) else 1,
			})
			doc.flags.ignore_permissions = True
			doc.insert()
			created += 1
		except Exception as e:
			errors.append((acc["id"], f"{type(e).__name__}: {e}"))

	frappe.db.commit()
	return {"created": created, "skipped": skipped, "banks": banks, "suffixed": suffixed, "errors": errors}


SUBGROUPS = ["Other Current Assets", "Other Current Liabilities", "Long Term Liabilities", "Cost of Sales"]


def cleanup(company=COMPANY):
	"""Remove previously-imported client accounts (matched on either the old
	account_number OR the new custom_auto_id), the stray 'Test Bank', and the
	sub-groups we created (leaves first)."""
	ids = [a["id"] for a in _load()]
	names = set()
	for field in ("account_number", "custom_auto_id"):
		if not frappe.db.has_column("Account", field):
			continue
		names.update(frappe.get_all(
			"Account", filters={"company": company, "is_group": 0, field: ["in", ids]}, pluck="name"
		))
	# stray manual test account(s)
	names.update(frappe.get_all(
		"Account", filters={"company": company, "is_group": 0, "account_name": ["like", "%Test Bank%"]}, pluck="name"
	))

	deleted = 0
	for name in frappe.get_all("Account", filters={"name": ["in", list(names)]}, pluck="name", order_by="lft desc"):
		frappe.delete_doc("Account", name, force=True, ignore_permissions=True)
		deleted += 1
	for sub in SUBGROUPS:
		nm = _group(company, sub)
		if nm and not frappe.get_all("Account", filters={"parent_account": nm}, limit=1):
			frappe.delete_doc("Account", nm, force=True, ignore_permissions=True)
			deleted += 1
	frappe.db.commit()
	return deleted


def setup_auto_id_field():
	"""Create the custom 'Auto-ID' field on Account and make it searchable in link
	fields (so typing an Auto-ID in Journal Entry resolves the account). Idempotent."""
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	create_custom_fields(
		{
			"Account": [
				{
					"fieldname": "custom_auto_id",
					"label": "Auto-ID",
					"fieldtype": "Data",
					"insert_after": "account_name",
					"translatable": 0,
					"in_list_view": 1,
					"in_standard_filter": 1,
					"columns": 2,
					"description": "Auto-incrementing account ID. Leave blank on a new account to auto-assign.",
				},
				{
					"fieldname": "custom_description",
					"label": "Description",
					"fieldtype": "Small Text",
					"insert_after": "account_type",
					"translatable": 0,
					"in_list_view": 1,
					"columns": 3,
				},
			],
			# Auto-ID column on the Journal Entry grid, before the Account column
			# (insert_after "" => first). Two-way fill is handled by public/js/journal_entry.js.
			"Journal Entry Account": [
				{
					"fieldname": "custom_auto_id",
					"label": "Auto-ID",
					"fieldtype": "Data",
					"insert_after": "",
					"in_list_view": 1,
					"columns": 1,
					"translatable": 0,
				}
			],
		},
		ignore_validate=True,
	)
	# add custom_auto_id to the Account doctype's link search fields (Journal Entry resolves by Auto-ID)
	make_property_setter(
		"Account", None, "search_fields", "account_number,custom_auto_id", "Data",
		for_doctype=True, validate_fields_for_doctype=False,
	)
	# hide the now-unused native Account Number column from the list view
	make_property_setter(
		"Account", "account_number", "in_list_view", "0", "Check",
		validate_fields_for_doctype=False,
	)
	# make Auto-ID the title field -> it becomes the first (leftmost) list column and
	# removes the docname 'ID' column (with hide_name_column in account_list.js).
	# Accounts without an Auto-ID fall back to the account name for the clickable label.
	make_property_setter(
		"Account", None, "title_field", "custom_auto_id", "Data",
		for_doctype=True, validate_fields_for_doctype=False,
	)

	# List view column order: Auto-ID (title, fixed first) | Description | Account Name | Status
	lvs_fields = json.dumps([
		{"fieldname": "custom_description", "label": "Description"},
		{"fieldname": "account_name", "label": "Account Name"},
		{"fieldname": "status_field", "label": "Status"},
	])
	if frappe.db.exists("List View Settings", "Account"):
		lvs = frappe.get_doc("List View Settings", "Account")
	else:
		lvs = frappe.new_doc("List View Settings")
		lvs.name = "Account"
		lvs.__newname = "Account"
	lvs.fields = lvs_fields
	lvs.total_fields = 6
	lvs.flags.ignore_permissions = True
	lvs.save()

	frappe.clear_cache(doctype="Account")
	frappe.db.commit()


def reimport_with_auto_id(company=COMPANY):
	"""Switch from native account_number to the custom Auto-ID field:
	add the field, wipe the old import + Test Bank, re-import clean (Auto-ID = client ID)."""
	setup_auto_id_field()
	cleaned = cleanup(company)
	result = import_accounts(company)
	result["cleaned"] = cleaned
	result["client_accounts_loaded"] = len(_load())
	result["total_company_accounts"] = frappe.db.count("Account", {"company": company})
	return result


def redo(company=COMPANY):
	"""Clean any prior import and re-import fresh (use after fixing the hook)."""
	cleaned = cleanup(company)
	result = import_accounts(company)
	result["cleaned"] = cleaned
	result["total_company_accounts"] = frappe.db.count("Account", {"company": company})
	result["client_accounts_loaded"] = len(_load())
	return result


def verify(company=COMPANY):
	"""Data + behaviour checks: counts, banks, a duplicate-name pair, sub-group numbers,
	a live auto-increment test, and an ID-search test (the Journal Entry behaviour)."""
	out = {}
	out["client_leaves"] = frappe.db.count(
		"Account", {"company": company, "is_group": 0, "custom_auto_id": ["!=", ""]}
	)
	out["sample_1010"] = frappe.db.get_value(
		"Account", {"company": company, "custom_auto_id": "1010"},
		["name", "account_number", "custom_auto_id", "account_type"], as_dict=True
	)
	out["banks"] = frappe.get_all(
		"Account", filters={"company": company, "account_type": "Bank", "custom_auto_id": ["!=", ""]},
		fields=["custom_auto_id", "account_name", "name"]
	)
	out["dup_pair_10205_203"] = frappe.get_all(
		"Account", filters={"company": company, "custom_auto_id": ["in", ["10205", "203"]]},
		fields=["custom_auto_id", "account_name", "name", "root_type"],
	)

	# Live auto-increment test: a new ledger under Indirect Expenses should get max-sibling+1
	ie = _group(company, "Indirect Expenses")
	test = frappe.new_doc("Account")
	test.update({"account_name": "ZZ Autonumber Test", "parent_account": ie, "company": company, "is_group": 0})
	test.flags.ignore_permissions = True
	test.insert()
	out["autonumber_test"] = {"assigned_auto_id": test.get("custom_auto_id"), "name": test.name}
	frappe.delete_doc("Account", test.name, force=True, ignore_permissions=True)
	frappe.db.commit()

	# Auto-ID search test (what the Journal Entry account field does when you type an Auto-ID)
	try:
		from frappe.desk.search import search_widget

		res = search_widget(doctype="Account", txt="10120", filters={"company": company, "is_group": 0})
		out["search_auto_id_10120"] = [r[0] for r in (res or [])][:5]
	except Exception as e:
		out["search_auto_id_10120"] = f"{type(e).__name__}: {e}"

	return out


def run(company=COMPANY):
	"""Create the company (if needed) and import the client chart. Idempotent."""
	create_company(company)
	result = import_accounts(company)
	result["company"] = company
	result["total_accounts"] = frappe.db.count("Account", {"company": company})
	return result


def _ensure_erpnext_fixtures():
	"""ERPNext master fixtures (UOMs, Warehouse Types incl. 'Transit', etc.) normally come
	from the setup wizard; ensure they exist before creating a company programmatically."""
	if frappe.db.exists("Warehouse Type", "Transit"):
		return
	from erpnext.setup.setup_wizard.operations.install_fixtures import install as install_fixtures

	install_fixtures("India")
	frappe.db.commit()


def provision(company=COMPANY, import_chart=True):
	"""Full first-time setup on a fresh site, in the correct order:
	erpnext fixtures -> Auto-ID field + view settings (must precede company creation, since
	the auto-number hook reads custom_auto_id) -> company (CoA + India Compliance GST/TDS)
	-> optionally the 185 client accounts. Idempotent / re-runnable.

	Pass import_chart=False to leave the Chart of Accounts for the client to build manually."""
	_ensure_erpnext_fixtures()
	setup_auto_id_field()
	create_company(company)
	result = {"company": company}
	if import_chart:
		result.update(import_accounts(company))
		result["client_accounts_loaded"] = len(_load())
	result["total_company_accounts"] = frappe.db.count("Account", {"company": company})
	return result
