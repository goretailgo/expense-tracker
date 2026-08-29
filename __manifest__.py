{
    'name': 'Expense Tracker',
    'version': '19.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Multi-city monthly income & expense tracking with a City -> Manager -> Director hierarchy',
    'description': """
Expense Tracker
================
Single-window monthly Income & Expense data entry and reporting for
multi-city businesses.

Features
--------
* One Income & Expense form per City per Month (duplicates prevented).
* Predefined default Income / Expense lines, plus "+ Add Income" / "+ Add
  Expense" to add more, and line removal.
* Automatic Total Income, Total Expense and Net Income calculation.
* Every Income / Expense entry is added through its own quick-entry form
  (category, date, description, amount) - no inline grid editing.
* Anyone with access to a city can create, edit, and delete that city's
  records at any time - no approval workflow or locking.
* City -> Manager -> Director security hierarchy enforced with Odoo
  security groups and record rules (server-side, not just UI-level).
* City Statement report with drill-down: Manager -> City -> Month ->
  Statement -> individual Income/Expense lines.
* List, Pivot and Graph views with filters for Month, Year, Manager,
  City, Category and Status.
* No attachments / files / images / receipts required anywhere.
""",
    'author': 'GoRetailGo',
    'website': 'https://goretailgo.shop',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/expense_tracker_security.xml',
        'security/ir.model.access.csv',
        'data/expense_tracker_data.xml',
        'views/expense_tracker_city_views.xml',
        'views/expense_tracker_category_views.xml',
        'views/expense_tracker_monthly_views.xml',
        'views/expense_tracker_line_report_views.xml',
        'report/expense_tracker_statement_report.xml',
        'report/expense_tracker_statement_templates.xml',
        'views/expense_tracker_res_users_views.xml',
        'views/expense_tracker_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'expense_tracker/static/src/js/income_dollar_toggle_field.js',
            'expense_tracker/static/src/xml/income_dollar_toggle_templates.xml',
            'expense_tracker/static/src/css/income_dollar_toggle.css',
        ],
    },
    'images': ['static/description/icon.png'],
    'application': True,
    'installable': True,
    'auto_install': False,
}
