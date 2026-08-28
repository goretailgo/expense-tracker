# -*- coding: utf-8 -*-
from odoo import fields, models


class ExpenseTrackerCategory(models.Model):
    _name = 'expense.tracker.category'
    _description = 'Expense Tracker Income/Expense Category'
    _order = 'type, sequence, name'

    name = fields.Char(required=True)
    type = fields.Selection(
        [('income', 'Income'), ('expense', 'Expense')],
        required=True, default='expense')
    sequence = fields.Integer(default=10)
    is_default = fields.Boolean(
        string='Add by Default', default=False,
        help="If checked, this line is automatically added to every new monthly "
             "record of the matching type (Income/Expense).")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    _name_type_company_uniq = models.Constraint(
        'unique(name, type, company_id)',
        'A category with this name and type already exists!',
    )
