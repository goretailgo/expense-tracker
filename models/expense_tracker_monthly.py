# -*- coding: utf-8 -*-
import calendar

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError

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

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
    ], string='Status', default='draft', tracking=True, copy=False, index=True)

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
        required=True, tracking=True, aggregator=None,
        default=lambda self: fields.Date.context_today(self).year)

    line_ids = fields.One2many('expense.tracker.line', 'monthly_id', string='Entries', copy=True)

    total_income = fields.Monetary(compute='_compute_totals', store=True, string='Total Income')
    total_expense = fields.Monetary(compute='_compute_totals', store=True, string='Total Expense')
    net_income = fields.Monetary(compute='_compute_totals', store=True, string='Net Income')

    # Named income-category columns for the Monthly Records list view.
    # Matched by category name (not a fixed xmlid) since these were added
    # as regular data by the user, not seeded by the module.
    income_contribution = fields.Monetary(
        compute='_compute_totals', store=True, string='Contribution')
    income_zakat = fields.Monetary(
        compute='_compute_totals', store=True, string='Zakat')
    income_donation = fields.Monetary(
        compute='_compute_totals', store=True, string='Donation')

    # Matching expense-side columns: this month's expenses charged against
    # each income account (via expense.tracker.line.income_account_id).
    # Same aggregation style as the income columns above - no running
    # opening/closing balance, just this month's figure per account.
    expense_contribution = fields.Monetary(
        compute='_compute_totals', store=True, string='Exp. Contribution')
    expense_zakat = fields.Monetary(
        compute='_compute_totals', store=True, string='Exp. Zakat')
    expense_donation = fields.Monetary(
        compute='_compute_totals', store=True, string='Exp. Donation')

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

    @api.depends('line_ids.amount', 'line_ids.line_type', 'line_ids.category_id', 'line_ids.income_account_id')
    def _compute_totals(self):
        named_income_fields = {
            'Contribution': 'income_contribution',
            'Zakat': 'income_zakat',
            'Donation': 'income_donation',
        }
        named_expense_fields = {
            'Contribution': 'expense_contribution',
            'Zakat': 'expense_zakat',
            'Donation': 'expense_donation',
        }
        for rec in self:
            income_lines = rec.line_ids.filtered(lambda l: l.line_type == 'income')
            expense_lines = rec.line_ids.filtered(lambda l: l.line_type == 'expense')
            total_income = sum(income_lines.mapped('amount'))
            total_expense = sum(expense_lines.mapped('amount'))
            rec.total_income = total_income
            rec.total_expense = total_expense
            rec.net_income = total_income - total_expense
            for cat_name, field_name in named_income_fields.items():
                rec[field_name] = sum(
                    income_lines.filtered(lambda l: l.category_id.name == cat_name).mapped('amount'))
            for cat_name, field_name in named_expense_fields.items():
                rec[field_name] = sum(
                    expense_lines.filtered(lambda l: l.income_account_id.name == cat_name).mapped('amount'))

    @api.model_create_multi
    def create(self, vals_list):
        # New sheets start empty - entries are only added by hand via the
        # 'Add Entry' button, not auto-seeded from default categories.
        return super().create(vals_list)

    def unlink(self):
        # Draft only - once a sheet is Submitted, deleting it is blocked
        # for everyone (City User, Manager, Director alike), not just via
        # the form's Delete button but also list-view bulk delete/API.
        if any(rec.state == 'submitted' for rec in self):
            raise ValidationError(_(
                "Submitted records can't be deleted. Reset to Draft first "
                "(Director only) if this record needs to be removed."
            ))
        return super().unlink()

    def _default_date_in_period(self):
        """A date guaranteed to fall inside THIS record's own Month/Year -
        today's real date if it happens to match, otherwise the last day of
        that month. Used by the 'Add Entry' popup so it never suggests a
        date that trips the boundary validation on expense.tracker.line."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        year = self.year
        month = int(self.month)
        last_day = calendar.monthrange(year, month)[1]
        day = min(today.day, last_day) if today.year == year and today.month == month else last_day
        return today.replace(year=year, month=month, day=day)

    def action_delete_and_redirect(self):
        """Delete this record and go back to the list, instead of Odoo's
        default behaviour of jumping to the next/previous record in the
        current set. Pairs with delete="false" on the form view, which
        hides the generic gear-menu Delete (which doesn't redirect this
        way) so this button is the only way to delete from the form."""
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('expense_tracker.action_expense_tracker_monthly')
        self.unlink()
        action['view_mode'] = 'list,form'
        action.pop('res_id', None)
        return action

    def action_submit(self):
        """City User submits the sheet once it's ready - only then does it
        become visible to Manager/Director (see the record rules in
        expense_tracker_security.xml, which filter their access to
        state='submitted'). Submission is final for City User/Manager -
        only Director can reopen it (action_reset_to_draft, group-gated
        on the button in the form view)."""
        self.write({'state': 'submitted'})

    def action_reset_to_draft(self):
        """Director-only: pull a submitted sheet back to Draft for a
        correction. Enforced here (not just by hiding the button), so it
        can't be triggered by a non-Director via dev tools/API either."""
        if not self.env.user.has_group('expense_tracker.group_expense_director'):
            raise AccessError(_("Only a Director can reset a submitted record back to Draft."))
        self.write({'state': 'draft'})

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
