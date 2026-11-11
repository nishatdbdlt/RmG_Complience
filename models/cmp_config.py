from odoo import fields, models


class RmgCmpLicenseType(models.Model):
    _name = 'rmg.cmp.license.type'
    _description = 'License / Certificate Type'
    _order = 'category, name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    category = fields.Selection([
        ('statutory', 'Statutory'),
        ('safety', 'Safety'),
        ('trade', 'Trade and Customs'),
        ('cert', 'Customer / Social Certificate'),
    ], required=True, default='statutory')
    authority = fields.Char(string='Issuing Authority')
    validity_months = fields.Integer(string='Validity (months)', default=12, help='0 = no expiry')
    alert_days = fields.Integer(string='Alert before (days)', default=60)
    mandatory = fields.Boolean(string='Required for audit')


class RmgCmpTemplate(models.Model):
    _name = 'rmg.cmp.template'
    _description = 'Audit Checklist'
    _order = 'name'

    name = fields.Char(string='Audit Type', required=True)
    active = fields.Boolean(default=True)
    standard = fields.Char(string='Standard / Law')
    interval_months = fields.Integer(string='Repeat every (months)', default=0, help='0 = on demand only')
    result_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('grade', 'A / B / C / D Grade'),
        ('pass_fail', 'Pass / Fail'),
        ('status', 'Complete / Non Complete'),
    ], string='Final Result Type', default='percentage', required=True,
       help='How the audit result will be calculated for this checklist.')
    item_ids = fields.One2many('rmg.cmp.template.item', 'template_id', string='Check Items')


class RmgCmpTemplateItem(models.Model):
    _name = 'rmg.cmp.template.item'
    _description = 'Audit Checklist Item'
    _order = 'sequence, id'

    template_id = fields.Many2one('rmg.cmp.template', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    section = fields.Char()
    name = fields.Char(string='Requirement', required=True)
    critical = fields.Boolean(string='Critical')
