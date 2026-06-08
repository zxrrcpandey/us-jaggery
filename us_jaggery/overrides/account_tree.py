"""Chart of Accounts tree node provider that also returns the custom Auto-ID.

Wraps ERPNext's get_children so each node carries ``custom_auto_id``; the tree's
client-side get_label (public/js/account_tree.js) renders it next to the account.
Wired by setting frappe.treeview_settings["Account"].get_tree_nodes to this path.
"""

import frappe


@frappe.whitelist()
def get_children(doctype, parent=None, company=None, is_root=False):
	from erpnext.accounts.utils import get_children as erpnext_get_children

	nodes = erpnext_get_children(doctype, parent, company, is_root)
	if doctype == "Account" and nodes:
		names = [n.get("value") for n in nodes]
		id_map = dict(
			frappe.get_all(
				"Account", filters={"name": ["in", names]},
				fields=["name", "custom_auto_id"], as_list=True
			)
		)
		for n in nodes:
			n["custom_auto_id"] = id_map.get(n.get("value")) or ""
	return nodes
