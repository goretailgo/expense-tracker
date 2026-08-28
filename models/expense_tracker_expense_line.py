# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ExpenseTrackerExpenseLine(models.Model):
    _name = 'expense.tracker.expense.line'
    _description = 'Expense Tracker Expense Line'
    _order = 'sequence, id'

    monthly_id = fields.Many2one(
        'expense.tracker.monthly', string='Monthly Record', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one(
        'expense.tracker.category', string='Expense Category', required=True,
        domain=[('type', '=', 'expense')])
    description = fields.Char(string='Description')
    amount = fields.Monetary(string='Amount', required=True, default=0.0)

    currency_id = fields.Many2one(related='monthly_id.currency_id', store=True, readonly=True)
    city_id = fields.Many2one(related='monthly_id.city_id', store=True, readonly=True, string='City')
    monthly_state = fields.Selection(related='monthly_id.state', store=True, readonly=True, string='Status')

    def _check_editable(self):
        for line in self:
            if line.monthly_id.state in ('submitted', 'approved') and not self.env.user.has_group(
                    'expense_tracker.group_expense_director'):
                raise UserError(_(
                    'Cannot modify Expense lines of a %s record. '
                    'Ask a Manager to Return it, or a Director to reopen it.'
                ) % line.monthly_id.state.capitalize())

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._check_editable()
        return lines

    def write(self, vals):
        self._check_editable()
        return super().write(vals)

    def unlink(self):
        self._check_editable()
        return super().unlink()
