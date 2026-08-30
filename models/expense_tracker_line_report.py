# -*- coding: utf-8 -*-
from odoo import fields, models, tools


class ExpenseTrackerLineReport(models.Model):
    """Read-only Statement model: a UNION of all income and expense lines,
    used for drill-down reporting (Manager -> City -> Month -> Statement ->
    individual Income/Expense lines) via list, pivot and graph views.
    """
    _name = 'expense.tracker.line.report'
    _description = 'Expense Tracker Statement (Income & Expense Lines)'
    _auto = False
    _order = 'year desc, month desc, city_id, line_type'
    _rec_name = 'description'

    monthly_id = fields.Many2one('expense.tracker.monthly', string='Monthly Record', readonly=True)
    city_id = fields.Many2one('expense.tracker.city', string='City', readonly=True)
    manager_id = fields.Many2one('res.users', string='Manager', readonly=True)
    month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
    ], readonly=True)
    year = fields.Integer(readonly=True)
    category_id = fields.Many2one('expense.tracker.category', string='Category', readonly=True)
    income_account_id = fields.Many2one(
        'expense.tracker.category', string='Income Account', readonly=True,
        help="For Expense lines: the income category this expense was charged "
             "against. Empty for Income lines.")
    line_type = fields.Selection(
        [('income', 'Income'), ('expense', 'Expense')], string='Type', readonly=True)
    date = fields.Date(readonly=True)
    description = fields.Char(readonly=True)
    amount = fields.Monetary(readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    company_id = fields.Many2one('res.company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW expense_tracker_line_report AS (
                SELECT
                    l.id AS id,
                    l.monthly_id AS monthly_id,
                    m.city_id AS city_id,
                    c.manager_id AS manager_id,
                    m.month AS month,
                    m.year AS year,
                    l.category_id AS category_id,
                    l.income_account_id AS income_account_id,
                    l.line_type AS line_type,
                    l.date AS date,
                    l.description AS description,
                    l.amount AS amount,
                    m.currency_id AS currency_id,
                    m.company_id AS company_id
                FROM expense_tracker_line l
                JOIN expense_tracker_monthly m ON m.id = l.monthly_id
                JOIN expense_tracker_city c ON c.id = m.city_id
            )
        """)
