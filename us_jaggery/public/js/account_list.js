// Account list view: Auto-ID is the first (title) column; hide the docname column.
frappe.listview_settings["Account"] = Object.assign(
	frappe.listview_settings["Account"] || {},
	{
		hide_name_column: true,
		add_fields: ["custom_auto_id", "account_name"],
		// Accounts WITH an Auto-ID first (numeric order); empty (—) ones last.
		order_by: 'cast(ifnull(nullif(custom_auto_id,""),"999999999") as unsigned) asc, account_name asc',
		formatters: {
			// First column = Auto-ID; show an em-dash for accounts without an Auto-ID
			// yet (instead of the docname/name), so the column never shows account names.
			custom_auto_id: function (value, df, doc) {
				return value || "—";
			},
		},
	}
);
