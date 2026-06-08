// Account list view: hide the name (ID) column and surface the custom Auto-ID.
frappe.listview_settings["Account"] = Object.assign(
	frappe.listview_settings["Account"] || {},
	{
		hide_name_column: true,
		add_fields: ["custom_auto_id"],
	}
);
