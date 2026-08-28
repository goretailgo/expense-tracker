# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ExpenseTrackerCity(models.Model):
    _name = 'expense.tracker.city'
    _description = 'Expense Tracker City'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True, help="Short code, e.g. HYD, MUM, DEL")
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)

    manager_id = fields.Many2one(
        'res.users', string='Manager', required=True, tracking=True,
        domain=lambda self: [
            ('groups_id', 'in', self.env.ref('expense_tracker.group_expense_manager').ids)
        ],
        help="A manager can be assigned to more than one city.")

    user_ids = fields.Many2many(
        'res.users', 'expense_tracker_city_user_rel', 'city_id', 'user_id',
        string='City Users', tracking=True,
        domain=lambda self: [
            ('groups_id', 'in', self.env.ref('expense_tracker.group_expense_city_user').ids)
        ],
        help="Users who can create and view monthly records for this city.")

    monthly_ids = fields.One2many('expense.tracker.monthly', 'city_id', string='Monthly Records')
    monthly_count = fields.Integer(compute='_compute_monthly_count')

    _sql_constraints = [
        ('code_company_uniq', 'unique(code, company_id)', 'City code must be unique per company!'),
    ]

    @api.depends('monthly_ids')
    def _compute_monthly_count(self):
        for rec in self:
            rec.monthly_count = len(rec.monthly_ids)

    def action_view_monthly_records(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'expense_tracker.action_expense_tracker_monthly')
        action['domain'] = [('city_id', '=', self.id)]
        action['context'] = {'default_city_id': self.id}
        return action

    def name_get(self):
        result = []
        for rec in self:
            name = f"[{rec.code}] {rec.name}" if rec.code else rec.name
            result.append((rec.id, name))
        return result
