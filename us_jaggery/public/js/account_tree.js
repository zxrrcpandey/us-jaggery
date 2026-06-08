// Show the custom Auto-ID next to each account in the Chart of Accounts tree.
// Patches frappe.treeview_settings["Account"] (defined by erpnext/.../account_tree.js):
//  - get_tree_nodes -> our provider that also returns custom_auto_id
//  - get_label      -> renders "<account name> [Auto-ID]" for ledger accounts
frappe.provide("frappe.treeview_settings");

window.us_jaggery_patch_account_tree = function () {
	const s = frappe.treeview_settings && frappe.treeview_settings["Account"];
	if (!s || s.__us_jaggery_patched) return;

	s.get_tree_nodes = "us_jaggery.overrides.account_tree.get_children";

	s.get_label = function (node) {
		const data = (node && node.data) || {};
		const label = frappe.utils.escape_html(data.value || node.label || "");
		const id = data.custom_auto_id;
		if (id) {
			return (
				label +
				' <span class="text-muted" style="font-weight:600">[' +
				frappe.utils.escape_html(id) +
				"]</span>"
			);
		}
		return label;
	};

	s.__us_jaggery_patched = true;
};

us_jaggery_patch_account_tree();
$(document).on("page-change", us_jaggery_patch_account_tree);
