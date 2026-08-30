# -*- coding: utf-8 -*-
import calendar
from datetime import date

from odoo import api, fields, models

from .expense_tracker_monthly import MONTH_SELECTION


class ExpenseTrackerBalanceReportLine(models.TransientModel):
    """One row of the Director's category balance report - not a real
    ledger entry, just a computed snapshot recreated every time the
    parent's filters change."""
    _name = 'expense.tracker.balance.report.line'
    _description = 'Category Balance Report Line'
    _order = 'sequence, id'

    report_id = fields.Many2one('expense.tracker.balance.report', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one('expense.tracker.category', string='Category', readonly=True)
    opening_balance = fields.Monetary(readonly=True)
    income = fields.Monetary(readonly=True)
    expense = fields.Monetary(readonly=True)
    closing_balance = fields.Monetary(readonly=True)
    currency_id = fields.Many2one(related='report_id.currency_id', readonly=True)


class ExpenseTrackerBalanceReport(models.TransientModel):
    """Director-only: pick Year (required) / Month (optional = whole year) /
    City (optional = every city), and see each income category's
    Opening -> Income -> Expense -> Closing balance for that period.

    Opening Balance = every SUBMITTED entry dated strictly before the
    period (all history, not just this year), so it's a genuine running
    balance, not just a per-period snapshot. Draft records are never
    counted, anywhere in this report."""
    _name = 'expense.tracker.balance.report'
    _description = 'Category Balance Report (Director)'
    _rec_name = 'name'

    name = fields.Char(default='Category Balance Report')

    def _selection_year(self):
        years = set(self.env['expense.tracker.monthly'].sudo().search([]).mapped('year'))
        years.add(fields.Date.context_today(self).year)
        return [(str(y), str(y)) for y in sorted(years, reverse=True)]

    year = fields.Selection(
        selection='_selection_year', string='Year', required=True,
        default=lambda self: str(fields.Date.context_today(self).year))
    month = fields.Selection(MONTH_SELECTION, string='Month')
    city_id = fields.Many2one('expense.tracker.city', string='City')

    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    line_ids = fields.One2many('expense.tracker.balance.report.line', 'report_id', string='Balances')

    def _get_period_bounds(self):
        self.ensure_one()
        year = int(self.year)
        if self.month:
            month = int(self.month)
            start = date(year, month, 1)
            end = date(year, month, calendar.monthrange(year, month)[1])
        else:
            start = date(year, 1, 1)
            end = date(year, 12, 31)
        return start, end

    @api.onchange('year', 'month', 'city_id')
    def _onchange_filters(self):
        self._refresh_lines()

    def _refresh_lines(self):
        self.ensure_one()
        Line = self.env['expense.tracker.line']
        Category = self.env['expense.tracker.category']
        start, end = self._get_period_bounds()

        base_domain = [('monthly_id.state', '=', 'submitted')]
        if self.city_id:
            base_domain.append(('monthly_id.city_id', '=', self.city_id.id))

        categories = Category.search([('type', '=', 'income')], order='sequence, name')

        commands = [(5, 0, 0)]
        for cat in categories:
            opening_income = sum(Line.search(base_domain + [
                ('line_type', '=', 'income'), ('category_id', '=', cat.id), ('date', '<', start),
            ]).mapped('amount'))
            opening_expense = sum(Line.search(base_domain + [
                ('line_type', '=', 'expense'), ('income_account_id', '=', cat.id), ('date', '<', start),
            ]).mapped('amount'))
            opening = opening_income - opening_expense

            period_income = sum(Line.search(base_domain + [
                ('line_type', '=', 'income'), ('category_id', '=', cat.id),
                ('date', '>=', start), ('date', '<=', end),
            ]).mapped('amount'))
            period_expense = sum(Line.search(base_domain + [
                ('line_type', '=', 'expense'), ('income_account_id', '=', cat.id),
                ('date', '>=', start), ('date', '<=', end),
            ]).mapped('amount'))

            commands.append((0, 0, {
                'category_id': cat.id,
                'opening_balance': opening,
                'income': period_income,
                'expense': period_expense,
                'closing_balance': opening + period_income - period_expense,
            }))
        self.line_ids = commands

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            rec._refresh_lines()
        return records
