from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class RmgCmpLicense(models.Model):
    _name = 'rmg.cmp.license'
    _description = 'License / Certificate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'type_id'
    _order = 'expiry_date, id'

    active = fields.Boolean(default=True)
    type_id = fields.Many2one('rmg.cmp.license.type', string='License / Certificate', required=True)
    category = fields.Selection(related='type_id.category', store=True)
    authority = fields.Char(related='type_id.authority')
    number = fields.Char(string='Number')
    issue_date = fields.Date(string='Issued / Renewed On')
    expiry_date = fields.Date(string='Valid Until', compute='_compute_expiry', store=True,
                              readonly=False, tracking=True)
    attachment = fields.Binary(string='Copy (scan)', attachment=True)
    attachment_name = fields.Char()
    user_id = fields.Many2one('res.users', string='Responsible')
    state = fields.Selection([
        ('missing', 'Missing'), ('valid', 'Valid'),
        ('expiring', 'Expiring Soon'), ('expired', 'Expired'),
    ], compute='_compute_state', store=True, default='missing')
    days_left = fields.Integer(compute='_compute_days_left')
    note = fields.Char()

    @api.depends('issue_date', 'type_id.validity_months')
    def _compute_expiry(self):
        for rec in self:
            months = rec.type_id.validity_months
            if rec.issue_date and months:
                rec.expiry_date = rec.issue_date + relativedelta(months=months)
            else:
                rec.expiry_date = rec.expiry_date

    def _get_state(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        if not self.expiry_date:
            no_expiry = self.type_id and not self.type_id.validity_months
            return 'valid' if (no_expiry and (self.issue_date or self.number)) else 'missing'
        if self.expiry_date < today:
            return 'expired'
        if (self.expiry_date - today).days <= (self.type_id.alert_days or 60):
            return 'expiring'
        return 'valid'

    @api.depends('expiry_date', 'issue_date', 'number', 'type_id.alert_days', 'type_id.validity_months')
    def _compute_state(self):
        for rec in self:
            rec.state = rec._get_state()

    @api.depends('expiry_date')
    def _compute_days_left(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.days_left = (rec.expiry_date - today).days if rec.expiry_date else 0

    @api.model
    def _cron_check_licenses(self):
        admin = self.env.ref('base.user_admin')
        for rec in self.search([]):
            new_state = rec._get_state()
            if new_state != rec.state:
                rec.state = new_state
            if new_state in ('expiring', 'expired') and not rec.activity_ids:
                rec.activity_schedule(
                    'mail.mail_activity_data_todo',
                    summary=_('Renew: %s', rec.type_id.name),
                    user_id=(rec.user_id or admin).id)
