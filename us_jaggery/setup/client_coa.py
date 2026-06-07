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


def _ensure_subgroup(company, sub_name, parent_group):
	existing = _group(company, sub_name)
	if existing:
		return existing
	parent = _group(company, parent_group)
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
	created, skipped, banks, errors = 0, 0, [], []

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

			parent = _ensure_subgroup(company, subgroup, parent_group) if subgroup else _group(company, parent_group)
			if not parent:
				errors.append((acc["id"], f"parent group {parent_group!r} not found"))
				continue

			doc = frappe.new_doc("Account")
			doc.update({
				"account_name": acc["name"],
				"account_number": acc["id"],
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
	return {"created": created, "skipped": skipped, "banks": banks, "errors": errors}


SUBGROUPS = ["Other Current Assets", "Other Current Liabilities", "Long Term Liabilities", "Cost of Sales"]


def cleanup(company=COMPANY):
	"""Remove the imported client accounts + the sub-groups we created (leaves first)."""
	ids = [a["id"] for a in _load()]
	deleted = 0
	for name in frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 0, "account_number": ["in", ids]},
		pluck="name",
		order_by="lft desc",
	):
		frappe.delete_doc("Account", name, force=True, ignore_permissions=True)
		deleted += 1
	for sub in SUBGROUPS:
		nm = _group(company, sub)
		if nm and not frappe.get_all("Account", filters={"parent_account": nm}, limit=1):
			frappe.delete_doc("Account", nm, force=True, ignore_permissions=True)
			deleted += 1
	frappe.db.commit()
	return deleted


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
		"Account", {"company": company, "is_group": 0, "account_number": ["!=", ""]}
	)
	out["sample_1010"] = frappe.db.get_value(
		"Account", {"company": company, "account_number": "1010"}, ["name", "account_type"], as_dict=True
	)
	out["banks"] = frappe.get_all(
		"Account", filters={"company": company, "account_type": "Bank"}, fields=["account_number", "account_name"]
	)
	out["dup_pair_10205_203"] = frappe.get_all(
		"Account", filters={"company": company, "account_number": ["in", ["10205", "203"]]},
		fields=["account_number", "account_name", "root_type"],
	)
	out["subgroup_numbers"] = frappe.get_all(
		"Account", filters={"company": company, "account_name": ["in", SUBGROUPS], "is_group": 1},
		fields=["account_name", "account_number"],
	)

	# Live auto-increment test: a new ledger under Indirect Expenses should get max-sibling+1
	ie = _group(company, "Indirect Expenses")
	test = frappe.new_doc("Account")
	test.update({"account_name": "ZZ Autonumber Test", "parent_account": ie, "company": company, "is_group": 0})
	test.flags.ignore_permissions = True
	test.insert()
	out["autonumber_test"] = {"assigned_id": test.account_number, "name": test.name}
	frappe.delete_doc("Account", test.name, force=True, ignore_permissions=True)
	frappe.db.commit()

	# ID-search test (what the Journal Entry account field does when you type an ID)
	try:
		from frappe.desk.search import search_link

		frappe.response["results"] = []
		search_link("Account", "10120", filters={"company": company, "is_group": 0}, page_length=5)
		out["search_id_10120"] = [r.get("value") for r in frappe.response.get("results", [])][:5]
	except Exception as e:
		out["search_id_10120"] = f"{type(e).__name__}: {e}"

	return out


def run(company=COMPANY):
	"""Create the company (if needed) and import the client chart. Idempotent."""
	create_company(company)
	result = import_accounts(company)
	result["company"] = company
	result["total_accounts"] = frappe.db.count("Account", {"company": company})
	return result
