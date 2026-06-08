app_name = "us_jaggery"
app_title = "US Jaggery"
app_publisher = "Trustbit Software"
app_description = "Custom app for US Jaggery — Chart of Accounts customizations and ERPNext tailoring"
app_email = "ra.pandey008@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "us_jaggery",
# 		"logo": "/assets/us_jaggery/logo.png",
# 		"title": "US Jaggery",
# 		"route": "/us_jaggery",
# 		"has_permission": "us_jaggery.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/us_jaggery/css/us_jaggery.css"
# app_include_js = "/assets/us_jaggery/js/us_jaggery.js"

# include js, css files in header of web template
# web_include_css = "/assets/us_jaggery/css/us_jaggery.css"
# web_include_js = "/assets/us_jaggery/js/us_jaggery.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "us_jaggery/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
doctype_list_js = {"Account": "public/js/account_list.js"}
doctype_tree_js = {"Account": "public/js/account_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "us_jaggery/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "us_jaggery.utils.jinja_methods",
# 	"filters": "us_jaggery.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "us_jaggery.install.before_install"
# after_install = "us_jaggery.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "us_jaggery.uninstall.before_uninstall"
# after_uninstall = "us_jaggery.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "us_jaggery.utils.before_app_install"
# after_app_install = "us_jaggery.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "us_jaggery.utils.before_app_uninstall"
# after_app_uninstall = "us_jaggery.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "us_jaggery.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

doc_events = {
	"Account": {
		# Auto-assign the next account_number (Account ID) within the group for
		# new accounts left blank. Runs before autoname so it lands in the name.
		"before_insert": "us_jaggery.overrides.account.autoset_account_number",
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"us_jaggery.tasks.all"
# 	],
# 	"daily": [
# 		"us_jaggery.tasks.daily"
# 	],
# 	"hourly": [
# 		"us_jaggery.tasks.hourly"
# 	],
# 	"weekly": [
# 		"us_jaggery.tasks.weekly"
# 	],
# 	"monthly": [
# 		"us_jaggery.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "us_jaggery.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "us_jaggery.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "us_jaggery.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["us_jaggery.utils.before_request"]
# after_request = ["us_jaggery.utils.after_request"]

# Job Events
# ----------
# before_job = ["us_jaggery.utils.before_job"]
# after_job = ["us_jaggery.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"us_jaggery.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

