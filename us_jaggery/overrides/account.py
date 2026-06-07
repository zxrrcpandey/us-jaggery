"""Auto-numbering for the Account doctype (the client's 'Account ID').

ERPNext's native ``account_number`` field IS the Account ID. This module only
fills it in automatically for NEW accounts that are created without a number,
using the next value within the same parent group. Existing/imported accounts
already carry their client IDs, so this never overwrites them.

Wired via hooks.py:
    doc_events = {"Account": {"before_insert": "...overrides.account.autoset_account_number"}}

``before_insert`` runs *before* autoname (verified: frappe inserts run
before_insert -> set_new_name), so the number we set here flows into the
account name "<number> - <name> - <abbr>" automatically.
"""

import frappe
from frappe.utils import cint


def autoset_account_number(doc, method=None):
	"""Assign the next account_number within the account's group, if blank."""
	if doc.account_number or doc.is_group or not doc.company:
		return  # keep client/manually-entered IDs untouched; never number group accounts

	next_no = (
		_next_in_group(doc)
		or _seed_from_parent(doc)
		or _next_in_root_type(doc)
	)
	if next_no:
		doc.account_number = str(next_no)


def _numeric(values):
	"""Return the integer values of purely-numeric account numbers."""
	return [cint(v) for v in values if v and str(v).strip().isdigit()]


def _max_account_number(filters):
	nums = _numeric(frappe.get_all("Account", filters=filters, pluck="account_number"))
	return max(nums) if nums else None


def _next_in_group(doc):
	"""max(numeric sibling numbers under the same parent) + 1 — the chosen scheme."""
	if not doc.parent_account:
		return None
	mx = _max_account_number({"company": doc.company, "parent_account": doc.parent_account})
	return mx + 1 if mx is not None else None


def _seed_from_parent(doc):
	"""First child of a group: seed from the parent's own number + 1."""
	if not doc.parent_account:
		return None
	parent_no = frappe.db.get_value("Account", doc.parent_account, "account_number")
	return cint(parent_no) + 1 if parent_no and str(parent_no).strip().isdigit() else None


def _next_in_root_type(doc):
	"""Last-resort fallback: next number anywhere within the same root type."""
	root_type = doc.root_type or (
		frappe.db.get_value("Account", doc.parent_account, "root_type")
		if doc.parent_account
		else None
	)
	if not root_type:
		return None
	mx = _max_account_number({"company": doc.company, "root_type": root_type})
	return mx + 1 if mx is not None else None
