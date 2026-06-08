"""Auto-numbering for a SEPARATE custom 'Auto-ID' field on Account.

The client ID lives in a custom field ``custom_auto_id`` (label "Auto-ID"),
independent of ERPNext's native ``account_number`` (so account names stay clean).
This hook fills Auto-ID for NEW accounts left blank, using the next value within
the account's group; existing/imported accounts keep their client IDs.

Wired via hooks.py:
    doc_events = {"Account": {"before_insert": "...overrides.account.autoset_account_number"}}

It runs before naming (naming doesn't depend on Auto-ID). Account link fields
search Auto-ID because a Property Setter adds ``custom_auto_id`` to the Account
doctype's ``search_fields`` (so typing an Auto-ID in Journal Entry resolves the account).
"""

import frappe
from frappe.utils import cint

FIELD = "custom_auto_id"


def autoset_account_number(doc, method=None):
	"""Assign the next Auto-ID within the account's group, if blank. Never numbers groups."""
	if doc.get(FIELD) or doc.is_group or not doc.company:
		return

	base = _next_in_group(doc) or _seed_from_parent(doc) or _next_in_root_type(doc)
	if base:
		doc.set(FIELD, str(_next_free(doc.company, base)))


def _next_free(company, start):
	"""First number >= start not already used as an Auto-ID in this company."""
	n = int(start)
	while frappe.db.exists("Account", {"company": company, FIELD: str(n)}):
		n += 1
	return n


def _numeric(values):
	return [cint(v) for v in values if v and str(v).strip().isdigit()]


def _max_id(filters):
	nums = _numeric(frappe.get_all("Account", filters=filters, pluck=FIELD))
	return max(nums) if nums else None


def _next_in_group(doc):
	"""max(numeric sibling Auto-IDs under the same parent) + 1 — the chosen scheme."""
	if not doc.parent_account:
		return None
	mx = _max_id({"company": doc.company, "parent_account": doc.parent_account})
	return mx + 1 if mx is not None else None


def _seed_from_parent(doc):
	if not doc.parent_account:
		return None
	pid = frappe.db.get_value("Account", doc.parent_account, FIELD)
	return cint(pid) + 1 if pid and str(pid).strip().isdigit() else None


def _next_in_root_type(doc):
	root_type = doc.root_type or (
		frappe.db.get_value("Account", doc.parent_account, "root_type") if doc.parent_account else None
	)
	if not root_type:
		return None
	mx = _max_id({"company": doc.company, "root_type": root_type})
	return mx + 1 if mx is not None else None
