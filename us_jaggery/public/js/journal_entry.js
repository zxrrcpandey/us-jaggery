// Two-way Auto-ID <-> Account on the Journal Entry "Accounting Entries" grid:
//  - type an Auto-ID  -> set the matching Account
//  - pick an Account  -> fill its Auto-ID
// The value guards prevent an infinite set_value loop.
frappe.ui.form.on("Journal Entry Account", {
	custom_auto_id(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const aid = (row.custom_auto_id || "").toString().trim();
		if (!aid || !frm.doc.company) return;
		frappe.db
			.get_value("Account", { company: frm.doc.company, custom_auto_id: aid, is_group: 0 }, "name")
			.then((r) => {
				const acc = r.message && r.message.name;
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
