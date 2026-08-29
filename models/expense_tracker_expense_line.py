# -*- coding: utf-8 -*-
from odoo import fields, models


class ExpenseTrackerExpenseLine(models.Model):
    _name = 'expense.tracker.expense.line'
    _description = 'Expense Tracker Expense Line'
    _order = 'date desc, sequence, id'

    monthly_id = fields.Many2one(
        'expense.tracker.monthly', string='Monthly Record', required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(default=10)
    category_id = fields.Many2one(
        'expense.tracker.category', string='Expense Category', required=True,
        domain=[('type', '=', 'expense')])
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    description = fields.Char(string='Description')
    amount = fields.Monetary(string='Amount', required=True, default=0.0)

    currency_id = fields.Many2one(related='monthly_id.currency_id', store=True, readonly=True)
    city_id = fields.Many2one(related='monthly_id.city_id', store=True, readonly=True, string='City')
