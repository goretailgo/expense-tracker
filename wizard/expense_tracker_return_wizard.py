# -*- coding: utf-8 -*-
from odoo import fields, models


class ExpenseTrackerReturnWizard(models.TransientModel):
    _name = 'expense.tracker.return.wizard'
    _description = 'Return Monthly Record for Correction'

    monthly_id = fields.Many2one('expense.tracker.monthly', required=True, readonly=True)
    reason = fields.Text(required=True, string='Reason for Return')

    def action_confirm(self):
        self.ensure_one()
        self.monthly_id.with_context(expense_tracker_workflow=True).write(
            {'state': 'returned', 'return_reason': self.reason})
        return {'type': 'ir.actions.act_window_close'}
