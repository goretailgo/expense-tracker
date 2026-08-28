# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

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

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('returned', 'Returned'),
    ], default='draft', required=True, tracking=True, index=True)

    income_line_ids = fields.One2many('expense.tracker.income.line', 'monthly_id', string='Income Lines', copy=True)
    expense_line_ids = fields.One2many('expense.tracker.expense.line', 'monthly_id', string='Expense Lines', copy=True)

    total_income = fields.Monetary(compute='_compute_totals', store=True, string='Total Income')
    total_expense = fields.Monetary(compute='_compute_totals', store=True, string='Total Expense')
    net_income = fields.Monetary(compute='_compute_totals', store=True, string='Net Income')

    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    submitted_by = fields.Many2one('res.users', string='Submitted By', readonly=True, copy=False)
    submitted_date = fields.Datetime(string='Submitted On', readonly=True, copy=False)
    approved_by = fields.Many2one('res.users', string='Approved By', readonly=True, copy=False)
    approved_date = fields.Datetime(string='Approved On', readonly=True, copy=False)
    return_reason = fields.Text(string='Return Reason', readonly=True, copy=False)

    _city_month_year_uniq = models.Constraint(
        'unique(city_id, month, year, company_id)',
        'A monthly record for this City and Month already exists!',
    )

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

    @api.depends('income_line_ids.amount', 'expense_line_ids.amount')
    def _compute_totals(self):
        for rec in self:
            total_income = sum(rec.income_line_ids.mapped('amount'))
            total_expense = sum(rec.expense_line_ids.mapped('amount'))
            rec.total_income = total_income
            rec.total_expense = total_expense
            rec.net_income = total_income - total_expense

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.income_line_ids and not rec.expense_line_ids:
                rec._add_default_lines()
        return records

    def _add_default_lines(self):
        self.ensure_one()
        Category = self.env['expense.tracker.category']
        income_categories = Category.search([('type', '=', 'income'), ('is_default', '=', True)])
        expense_categories = Category.search([('type', '=', 'expense'), ('is_default', '=', True)])
        for cat in income_categories:
            self.env['expense.tracker.income.line'].create(
                {'monthly_id': self.id, 'category_id': cat.id, 'amount': 0.0})
        for cat in expense_categories:
            self.env['expense.tracker.expense.line'].create(
                {'monthly_id': self.id, 'category_id': cat.id, 'amount': 0.0})

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------
    def action_submit(self):
        for rec in self:
            if rec.state not in ('draft', 'returned'):
                raise UserError(_('Only Draft or Returned records can be submitted.'))
            rec.with_context(expense_tracker_workflow=True).write({
                'state': 'submitted',
                'submitted_by': self.env.user.id,
                'submitted_date': fields.Datetime.now(),
            })

    def action_approve(self):
        for rec in self:
            if rec.state != 'submitted':
                raise UserError(_('Only Submitted records can be approved.'))
            rec.with_context(expense_tracker_workflow=True).write({
                'state': 'approved',
                'approved_by': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            })

    def action_open_return_wizard(self):
        self.ensure_one()
        if self.state != 'submitted':
            raise UserError(_('Only Submitted records can be returned for correction.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return for Correction'),
            'res_model': 'expense.tracker.return.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_monthly_id': self.id},
        }

    def action_reset_to_draft(self):
        if not self.env.user.has_group('expense_tracker.group_expense_director'):
            raise UserError(_('Only a Director can reopen an Approved record.'))
        for rec in self:
            rec.with_context(expense_tracker_workflow=True).write({'state': 'draft'})

    # ------------------------------------------------------------------
    # Guards
    # ------------------------------------------------------------------
    def write(self, vals):
        # Internal workflow transitions (submit/approve/return/reset) are always
        # allowed to update status/audit fields regardless of the record's
        # current state; only *content* edits by non-Directors are restricted.
        if not self.env.context.get('expense_tracker_workflow'):
            is_director = self.env.user.has_group('expense_tracker.group_expense_director')
            if not is_director:
                ignored_keys = {'message_follower_ids', 'message_ids', 'activity_ids'}
                protected_vals = set(vals.keys()) - ignored_keys
                for rec in self:
                    if rec.state in ('submitted', 'approved') and protected_vals:
                        raise UserError(_(
                            'This record is %s and cannot be edited. Ask a Manager to '
                            'Return it, or a Director to reopen it.') % rec.state.capitalize())
        return super().write(vals)

    def unlink(self):
        if not self.env.user.has_group('expense_tracker.group_expense_director'):
            raise UserError(_('Only a Director can delete a monthly record.'))
        for rec in self:
            if rec.state == 'approved':
                raise UserError(_('Approved records cannot be deleted.'))
        return super().unlink()
