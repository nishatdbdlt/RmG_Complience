from odoo import _, fields, models
from odoo.exceptions import UserError


class RmgCmpFinding(models.Model):
    _name = 'rmg.cmp.finding'
    _description = 'Audit Finding / Corrective Action'
    _inherit = ['mail.thread']
    _order = 'critical desc, due_date, id'

    name = fields.Char(string='Finding', required=True)
    section = fields.Char()
    audit_id = fields.Many2one('rmg.cmp.audit', string='Audit', ondelete='set null')
    critical = fields.Boolean(string='Critical')
    user_id = fields.Many2one('res.users', string='Responsible', tracking=True)
    due_date = fields.Date(string='Due', tracking=True)
    state = fields.Selection([('open', 'Open'), ('closed', 'Closed')], default='open', tracking=True)
    closed_date = fields.Date(readonly=True)
    note = fields.Text(string='Remarks / Action taken')
    correction_plan = fields.Text(string='Correction Plan', required=True, tracking=True)

    def action_close(self):
        for rec in self:
            if not rec.correction_plan or not rec.correction_plan.strip():
                raise UserError(_("Correction plan is mandatory before closing this finding."))
        self.write({'state': 'closed', 'closed_date': fields.Date.context_today(self)})
