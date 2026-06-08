// Two-way Auto-ID <-> Account on the Journal Entry "Accounting Entries" grid:
//  - type an Auto-ID  -> set the matching Account
//  - pick an Account  -> fill its Auto-ID
// The value guards prevent an infinite set_value loop.
frappe.ui.form.on("Journal Entry Account", {
	custom_auto_id(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const val = (row.custom_auto_id || "").toString().trim();
		if (!val || !frm.doc.company) return;
		// Resolve the account by Auto-ID, account name, or docname (exact),
		// then fall back to a partial name/docname match.
		frappe.db
			.get_list("Account", {
				filters: { company: frm.doc.company, is_group: 0 },
				or_filters: { custom_auto_id: val, account_name: val, name: val },
				fields: ["name"],
				limit: 1,
			})
			.then((rows) => {
				if (rows && rows.length) return rows[0].name;
				return frappe.db
					.get_list("Account", {
						filters: { company: frm.doc.company, is_group: 0 },
						or_filters: [
							["account_name", "like", "%" + val + "%"],
							["name", "like", "%" + val + "%"],
						],
						fields: ["name"],
						order_by: "name asc",
						limit: 1,
					})
					.then((r2) => (r2 && r2.length ? r2[0].name : null));
			})
			.then((acc) => {
				if (acc && acc !== row.account) {
					frappe.model.set_value(cdt, cdn, "account", acc);
				}
			});
	},

	account(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.account) {
			if (row.custom_auto_id) frappe.model.set_value(cdt, cdn, "custom_auto_id", "");
			return;
		}
		frappe.db.get_value("Account", row.account, "custom_auto_id").then((r) => {
			const aid = (r.message && r.message.custom_auto_id) || "";
			if (aid !== (row.custom_auto_id || "")) {
				frappe.model.set_value(cdt, cdn, "custom_auto_id", aid);
			}
		});
	},
});
