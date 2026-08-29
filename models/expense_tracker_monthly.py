# -*- coding: utf-8 -*-
import calendar

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

MONTH_SELECTION = [
    ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
    ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
    ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December'),
]


class ExpenseTrackerMonthly(models.Model):
    _name = 'expense.tracker.monthly'
    _description = 'Monthly Income & Expense'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'year desc, month desc, id desc'
    _rec_name = 'name'

    name = fields.Char(compute='_compute_name', store=True)

    city_id = fields.Many2one(
        'expense.tracker.city', string='City', required=True, tracking=True,
        ondelete='restrict', index=True,
        default=lambda self: self._default_city_id())
    manager_id = fields.Many2one(
        related='city_id.manager_id', string='Manager', store=True, readonly=True, index=True)

    month = fields.Selection(
        MONTH_SELECTION, required=True, tracking=True,
        default=lambda self: str(fields.Date.context_today(self).month))
    year = fields.Integer(
        required=True, tracking=True,
        default=lambda self: fields.Date.context_today(self).year)

    line_ids = fields.One2many('expense.tracker.line', 'monthly_id', string='Entries', copy=True)

    total_income = fields.Monetary(compute='_compute_totals', store=True, string='Total Income')
    total_expense = fields.Monetary(compute='_compute_totals', store=True, string='Total Expense')
    net_income = fields.Monetary(compute='_compute_totals', store=True, string='Net Income')

    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    _city_month_year_uniq = models.Constraint(
        'unique(city_id, month, year, company_id)',
        'A monthly record for this City and Month already exists!',
    )

    @api.constrains('month', 'year')
    def _check_lines_still_within_month(self):
        # Mirror of expense.tracker.line's own date-boundary check, but
        # from the other direction: don't let someone change a record's
        # Month/Year out from under entries that were dated for the old one.
        month_labels = dict(MONTH_SELECTION)
        for rec in self:
            mismatched = rec.line_ids.filtered(
                lambda l: l.date and (l.date.year != rec.year or str(l.date.month) != rec.month))
            if mismatched:
                raise ValidationError(_(
                    "Can't change this record to %(period)s: %(count)d entr%(plural)s "
                    "still dated outside that month. Fix or remove those entries first."
                ) % {
                    'period': '%s %s' % (month_labels.get(rec.month), rec.year),
                    'count': len(mismatched),
                    'plural': 'y' if len(mismatched) == 1 else 'ies',
                })

    def _default_city_id(self):
        cities = self.env['expense.tracker.city'].search([('user_ids', 'in', self.env.user.id)], limit=2)
        return cities.id if len(cities) == 1 else False

    @api.depends('city_id', 'month', 'year')
    def _compute_name(self):
        month_labels = dict(MONTH_SELECTION)
        for rec in self:
            if rec.city_id and rec.month and rec.year:
                rec.name = f"{rec.city_id.name} - {month_labels.get(rec.month)} {rec.year}"
            else:
                rec.name = _('New')

    @api.depends('line_ids.amount', 'line_ids.line_type')
    def _compute_totals(self):
        for rec in self:
            total_income = sum(rec.line_ids.filtered(lambda l: l.line_type == 'income').mapped('amount'))
            total_expense = sum(rec.line_ids.filtered(lambda l: l.line_type == 'expense').mapped('amount'))
            rec.total_income = total_income
            rec.total_expense = total_expense
            rec.net_income = total_income - total_expense

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.line_ids:
                rec._add_default_lines()
        return records

    def _default_date_in_period(self):
        """A date guaranteed to fall inside THIS record's own Month/Year -
        today's real date if it happens to match, otherwise the last day of
        that month. Used both for the auto-created starter lines and for
        the 'Add Entry' popup, so neither ever produces a date that trips
        the boundary validation on expense.tracker.line."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        year = self.year
        month = int(self.month)
        last_day = calendar.monthrange(year, month)[1]
        day = min(today.day, last_day) if today.year == year and today.month == month else last_day
        return today.replace(year=year, month=month, day=day)

    def _add_default_lines(self):
        self.ensure_one()
        Category = self.env['expense.tracker.category']
        default_categories = Category.search([('is_default', '=', True)])
        default_date = self._default_date_in_period()
        for cat in default_categories:
            self.env['expense.tracker.line'].create({
                'monthly_id': self.id,
                'category_id': cat.id,
                'line_type': cat.type,
                'amount': 0.0,
                'date': default_date,
            })

    def action_add_line(self):
        """Open the entry popup (Type/Category/Date/Description/Amount) - the
        single 'Add Entry' button below Year replaces the default 'Add a
        line' link on the Entries list. Defaults the Date to a day inside
        THIS record's own Month/Year (not today's real-world date), so
        entries can't accidentally end up dated outside the sheet they're
        being added to."""
        self.ensure_one()
        default_date = fields.Date.to_string(self._default_date_in_period())
        return {
            'type': 'ir.actions.act_window',
            'name': _('Add Entry'),
            'res_model': 'expense.tracker.line',
            'view_mode': 'form',
            'views': [(self.env.ref('expense_tracker.view_expense_tracker_line_form').id, 'form')],
            'target': 'new',
            'context': {'default_monthly_id': self.id, 'default_date': default_date},
        }
