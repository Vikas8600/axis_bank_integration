from . import __version__ as app_version

app_name = "axis_bank_integration"
app_title = "Axis Bank Integration"
app_publisher = "Dexciss"
app_description = "Axis Bank Integration"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "skuthe@dexciss.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/axis_bank_integration/css/axis_bank_integration.css"
# app_include_js = "/assets/axis_bank_integration/js/axis_bank_integration.js"

# include js, css files in header of web template
# web_include_css = "/assets/axis_bank_integration/css/axis_bank_integration.css"
# web_include_js = "/assets/axis_bank_integration/js/axis_bank_integration.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "axis_bank_integration/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Customer" : "public/js/custom.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "axis_bank_integration.install.before_install"
# after_install = "axis_bank_integration.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "axis_bank_integration.uninstall.before_uninstall"
# after_uninstall = "axis_bank_integration.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "axis_bank_integration.notifications.get_notification_config"

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
#	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
# 	"all": [
# 		"axis_bank_integration.tasks.all"
# 	],
# 	"daily": [
# 		"axis_bank_integration.tasks.daily"
# 	],
	"hourly": [
		"axis_bank_integration.axis_bank_integration.doctype.bank_transaction_log.bank_transaction_log.create_payment_entry_background"
	],
# 	"weekly": [
# 		"axis_bank_integration.tasks.weekly"
# 	]
# 	"monthly": [
# 		"axis_bank_integration.tasks.monthly"
# 	]
}

# Fixtures
# -------

fixtures = [
	{
		"dt": "Property Setter",
		"filters": [
			[
				"name",
				"in",
				[
					"Journal Entry-user_remark-hidden",
					"Payment Entry-main-field_order",
				],
			]
		],
	}
]

# Testing
# -------

# before_tests = "axis_bank_integration.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "axis_bank_integration.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "axis_bank_integration.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"axis_bank_integration.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []
