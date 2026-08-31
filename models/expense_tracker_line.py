# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from markupsafe import Markup


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
    income_account_id = fields.Many2one(
        'expense.tracker.category', string='Income Account',
        domain=[('type', '=', 'income')],
        help="Which income category (Contribution, Donation, Zakat, etc.) this "
             "expense is being paid out of. Only set on Expense entries - each "
             "income category acts as its own account/budget, and every expense "
             "must be charged against one of them so income vs. expense can be "
             "tracked per category, not just in aggregate.")
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    description = fields.Char(string='Description')
    amount = fields.Monetary(string='Amount', required=True, default=0.0)

    currency_id = fields.Many2one(related='monthly_id.currency_id', store=True, readonly=True)
    city_id = fields.Many2one(related='monthly_id.city_id', store=True, readonly=True, string='City')

    valid_period_label = fields.Char(compute='_compute_valid_period_label')

    @api.depends('monthly_id.month', 'monthly_id.year')
    def _compute_valid_period_label(self):
        month_labels = dict(self.env['expense.tracker.monthly']._fields['month'].selection)
        for line in self:
            if line.monthly_id.month and line.monthly_id.year:
                line.valid_period_label = '%s %s' % (
                    month_labels.get(line.monthly_id.month), line.monthly_id.year)
            else:
                line.valid_period_label = False

    @api.onchange('line_type')
    def _onchange_line_type(self):
        # Category belongs to a specific type, so clear it when the type
        # changes to avoid an Income entry pointing at an Expense category
        # (or vice versa).
        if self.category_id and self.category_id.type != self.line_type:
            self.category_id = False
        # Income Account only applies to Expense entries - an Income entry
        # IS an account (its own category), it doesn't draw from one.
        if self.line_type == 'income' and self.income_account_id:
            self.income_account_id = False

    @api.constrains('line_type', 'income_account_id')
    def _check_income_account_required(self):
        for line in self:
            if line.line_type == 'expense' and not line.income_account_id:
                raise ValidationError(_(
                    "Please select which Income Account (Contribution, Donation, "
                    "Zakat, etc.) this expense is being paid out of."
                ))
            if line.line_type == 'income' and line.income_account_id:
                raise ValidationError(_(
                    "Income Account only applies to Expense entries - an Income "
                    "entry is itself an account, so it can't also draw from one."
                ))

    @api.onchange('date', 'monthly_id')
    def _onchange_date_boundary(self):
        # Immediate feedback the moment the user picks a date, rather than
        # only finding out after they hit Save (the hard constraint below
        # still blocks the save regardless of whether this warning fires).
        if self.date and self.monthly_id and self.monthly_id.month and self.monthly_id.year:
            if self.date.year != self.monthly_id.year or str(self.date.month) != self.monthly_id.month:
                return {'warning': {
                    'title': _('Date outside this record\'s month'),
                    'message': _(
                        'This entry is for %(period)s, but the date you picked '
                        'falls outside that month. It will be rejected on save.'
                    ) % {'period': self.valid_period_label},
                }}

    @api.constrains('date', 'monthly_id')
    def _check_date_within_month(self):
        for line in self:
            if line.monthly_id and line.date:
                if line.date.year != line.monthly_id.year or str(line.date.month) != line.monthly_id.month:
                    raise ValidationError(_(
                        "Entry date %(date)s is outside %(record)s. "
                        "An entry's date must fall within its record's own Month and Year."
                    ) % {'date': line.date, 'record': line.monthly_id.name})

    # ------------------------------------------------------------------
    # Audit log: every add / edit / delete is posted to the parent Monthly
    # record's chatter, so anyone opening that record can see who changed
    # what and when (chatter shows the acting user and timestamp
    # automatically). Logged for every user/role - nothing is skipped.
    # ------------------------------------------------------------------
    TRACKED_FIELDS = ('line_type', 'category_id', 'income_account_id', 'date', 'description', 'amount')

    def _log_format_value(self, field_name, value):
        if field_name in ('category_id', 'income_account_id'):
            return value.display_name if value else '—'
        if field_name == 'line_type':
            return dict(self._fields['line_type'].selection).get(value, value)
        if field_name == 'amount':
            symbol = self.currency_id.symbol or ''
            return f"{symbol}{(value or 0.0):,.2f}"
        if field_name == 'date':
            return fields.Date.to_string(value) if value else '—'
        return value or '—'

    def _log_summary(self):
        self.ensure_one()
        type_label = dict(self._fields['line_type'].selection).get(self.line_type)
        category_label = self.category_id.display_name if self.category_id else '—'
        amount_label = self._log_format_value('amount', self.amount)
        date_label = self._log_format_value('date', self.date)
        summary = Markup(
            '<b>%(category)s</b> <span class="text-muted">(%(type)s)</span> '
            '— %(amount)s on %(date)s'
        ) % {
            'category': category_label,
            'type': type_label,
            'amount': amount_label,
            'date': date_label,
        }
        if self.line_type == 'expense' and self.income_account_id:
            summary += Markup(' <span class="text-muted">from %s</span>') % self.income_account_id.display_name
        if self.description:
            summary += Markup(' — <i>%s</i>') % self.description
        return summary

    @api.model_create_multi
    def create(self, vals_list):
        monthly_ids = {v.get('monthly_id') for v in vals_list if v.get('monthly_id')}
        if monthly_ids:
            submitted = self.env['expense.tracker.monthly'].browse(monthly_ids).filtered(
                lambda m: m.state == 'submitted')
            if submitted:
                raise ValidationError(_(
                    "Can't add entries to a Submitted record (%s). "
                    "A Director needs to reset it to Draft first."
                ) % ', '.join(submitted.mapped('name')))
        lines = super().create(vals_list)
        for line in lines:
            if line.monthly_id:
                line.monthly_id.message_post(
                    body=Markup('<b>Entry added:</b> %s') % line._log_summary(),
                    subtype_xmlid='mail.mt_note')
        return lines

    def write(self, vals):
        if any(line.monthly_id.state == 'submitted' for line in self):
            raise ValidationError(_(
                "Can't edit entries on a Submitted record. "
                "A Director needs to reset it to Draft first."
            ))
        changed_fields = [f for f in self.TRACKED_FIELDS if f in vals]
        old_data = {}
        if changed_fields:
            for line in self:
                old_data[line.id] = {f: line[f] for f in changed_fields}

        result = super().write(vals)

        if changed_fields:
            for line in self:
                old = old_data.get(line.id)
                if not old:
                    continue
                diff_items = []
                for f in changed_fields:
                    old_label = self._log_format_value(f, old[f])
                    new_label = self._log_format_value(f, line[f])
                    if old_label != new_label:
                        diff_items.append(Markup('<li>%s: %s → <b>%s</b></li>') % (
                            line._fields[f].string, old_label, new_label))
                if diff_items and line.monthly_id:
                    body = Markup('<b>Entry updated:</b> %s<ul class="mb-0 ps-3">%s</ul>') % (
                        line._log_summary(), Markup('').join(diff_items))
                    line.monthly_id.message_post(body=body, subtype_xmlid='mail.mt_note')
        return result

    def unlink(self):
        if any(line.monthly_id.state == 'submitted' for line in self):
            raise ValidationError(_(
                "Can't delete entries on a Submitted record. "
                "A Director needs to reset it to Draft first."
            ))
        summaries = [(line.monthly_id, line._log_summary()) for line in self if line.monthly_id]
        result = super().unlink()
        for monthly, summary in summaries:
            monthly.message_post(body=Markup('<b>Entry removed:</b> %s') % summary, subtype_xmlid='mail.mt_note')
        return result
