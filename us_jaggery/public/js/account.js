// ERPNext hides the Account Name field on saved accounts (rename is done via the
// "Update Account Number / Name" dialog), relying on the page title to show the name.
// Since we set title_field = Auto-ID, the title shows the Auto-ID instead — so keep the
// Account Name visible (read-only) on saved accounts so it's never hidden.
frappe.ui.form.on("Account", {
	refresh(frm) {
		frm.toggle_display("account_name", true);
		if (!frm.is_new()) {
			frm.set_df_property("account_name", "read_only", 1);
			frm.set_df_property(
				"account_name",
				"description",
				__("To rename, use Actions / ⋯ → Update Account Number / Name."),
			);
		}
	},
});
