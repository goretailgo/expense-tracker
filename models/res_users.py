# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    expense_tracker_city_ids = fields.Many2many(
        'expense.tracker.city', 'expense_tracker_city_user_rel', 'user_id', 'city_id',
        string='Assigned Cities (Expense Tracker)',
        help="Cities this person is allowed to create and view monthly Income & "
             "Expense records for, as a City User. Not needed for Managers/"
             "Directors, whose access is derived from the city's Manager field.")

    managed_city_ids = fields.One2many(
        'expense.tracker.city', 'manager_id', string='Managed Cities (Expense Tracker)')

    expense_tracker_managed_city_count = fields.Integer(
        compute='_compute_expense_tracker_managed_city_count')

    def _compute_expense_tracker_managed_city_count(self):
        for user in self:
            user.expense_tracker_managed_city_count = len(user.managed_city_ids)
