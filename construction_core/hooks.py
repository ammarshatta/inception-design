app_name = "construction_core"
app_title = "Construction Core"
app_publisher = "Inceptiondesign"
app_description = "Construction and finishing project platform: stages, portals, catalog"
app_email = "ammar.shata@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "construction_core",
# 		"logo": "/assets/construction_core/logo.png",
# 		"title": "Construction Core",
# 		"route": "/construction_core",
# 		"has_permission": "construction_core.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `construction_core/dock/construction_core/construction_core.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/construction_core/css/construction_core.css"
# app_include_js = "/assets/construction_core/js/construction_core.js"

# include js, css files in header of web template
# web_include_css = "/assets/construction_core/css/construction_core.css"
# web_include_js = "/assets/construction_core/js/construction_core.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "construction_core/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "construction_core/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "construction_core.utils.jinja_methods",
# 	"filters": "construction_core.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "construction_core.install.before_install"
# after_install = "construction_core.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "construction_core.uninstall.before_uninstall"
# after_uninstall = "construction_core.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "construction_core.utils.before_app_install"
# after_app_install = "construction_core.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "construction_core.utils.before_app_uninstall"
# after_app_uninstall = "construction_core.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "construction_core.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "construction_core.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "construction_core.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["construction_core.search.awesomebar_results"]

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

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"construction_core.tasks.all"
# 	],
# 	"daily": [
# 		"construction_core.tasks.daily"
# 	],
# 	"hourly": [
# 		"construction_core.tasks.hourly"
# 	],
# 	"weekly": [
# 		"construction_core.tasks.weekly"
# 	],
# 	"monthly": [
# 		"construction_core.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "construction_core.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "construction_core.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "construction_core.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "construction_core.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["construction_core.utils.before_request"]
# after_request = ["construction_core.utils.after_request"]

# Job Events
# ----------
# before_job = ["construction_core.utils.before_job"]
# after_job = ["construction_core.utils.after_job"]

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
# 	"construction_core.auth.validate"
# ]

# on_social_login = "construction_core.auth.on_social_login"

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []


# ---------------------------------------------------------------------------
# Inceptiondesign configuration (everything above is the bench boilerplate)
# ---------------------------------------------------------------------------

required_apps = ["erpnext"]

after_install = "construction_core.setup.install.after_install"
after_migrate = "construction_core.setup.install.after_migrate"
before_tests = "construction_core.setup.install.before_tests"

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["Construction Admin", "Construction Engineer", "Construction Client"]]],
	},
	{"dt": "Custom Field", "filters": [["module", "=", "Construction Core"]]},
	{"dt": "Property Setter", "filters": [["module", "=", "Construction Core"]]},
]

_SCOPED = ("Project", "Project Stage", "Stage Update", "Payment Milestone", "Project Message")

has_permission = {dt: "construction_core.permissions.has_permission" for dt in _SCOPED}

permission_query_conditions = {
	dt: "construction_core.permissions.get_permission_query_conditions" for dt in _SCOPED
}

doc_events = {
	"Project": {
		"before_validate": "construction_core.overrides.project.before_validate",
		"after_insert": "construction_core.overrides.project.after_insert",
	},
	"File": {"before_insert": "construction_core.overrides.file.before_insert"},
	"User": {"before_insert": "construction_core.auth.user_before_insert"},
}

doctype_js = {
	"Project": "public/js/project.js",
	"Phase Template": "public/js/phase_template.js",
}

# Temporary passwords: nothing but the change-password page until it is changed
before_request = ["construction_core.auth.force_password_change"]

override_whitelisted_methods = {
	"frappe.core.doctype.user.user.update_password": "construction_core.auth.update_password",
	"frappe.integrations.oauth2_logins.login_via_google": "construction_core.auth.login_via_google",
	"frappe.integrations.oauth2_logins.login_via_facebook": "construction_core.auth.login_via_facebook",
}

jinja = {
	"methods": [
		"construction_core.branding.get_branding",
	],
}

# The Vue portal: /portal and every route under it render www/portal.html
website_route_rules = [
	{"from_route": "/portal/<path:app_path>", "to_route": "portal"},
	{"from_route": "/p/<project>", "to_route": "public_project"},
]
