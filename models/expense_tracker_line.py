# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ExpenseTrackerLine(models.Model):
    """A single Income or Expense entry on a Monthly record. Income and
    Expense used to be two separate models; they are merged into one so
    both can be listed together (differentiated by ``line_type``) with a
    single toggle to filter by type."""
    _name = 'expense.tracker.line'
    _description = 'Expense Tracker Income/Expense Line'
    _order = 'date desc, sequence, id'

    monthly_id = fields.Many2one(
        'expense.tracker.monthly', string='Monthly Record', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    line_type = fields.Selection(
        [('income', 'Income'), ('expense', 'Expense')],
        string='Type', required=True, default='income', tracking=True)
    category_id = fields.Many2one(
        'expense.tracker.category', string='Category', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    description = fields.Char(string='Description')
    amount = fields.Monetary(string='Amount', required=True, default=0.0)

    currency_id = fields.Many2one(related='monthly_id.currency_id', store=True, readonly=True)
    city_id = fields.Many2one(related='monthly_id.city_id', store=True, readonly=True, string='City')

    @api.onchange('line_type')
    def _onchange_line_type(self):
        # Category belongs to a specific type, so clear it when the type
        # changes to avoid an Income entry pointing at an Expense category
        # (or vice versa).
        if self.category_id and self.category_id.type != self.line_type:
            self.category_id = False
