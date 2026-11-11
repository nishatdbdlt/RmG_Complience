from datetime import timedelta

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, Command, _
from odoo.exceptions import UserError


class RmgCmpAudit(models.Model):
    _name = 'rmg.cmp.audit'
    _description = 'Compliance Audit'
    _inherit = ['mail.thread']
    _order = 'date desc, id desc'

    name = fields.Char(default='New', readonly=True, copy=False)
    date = fields.Date(default=fields.Date.context_today, required=True)
    template_id = fields.Many2one('rmg.cmp.template', string='Audit Type', required=True)
    result_type = fields.Selection(related='template_id.result_type', store=True, readonly=True)
    standard = fields.Char(related='template_id.standard')
    user_id = fields.Many2one('res.users', string='Auditor', default=lambda self: self.env.user)
    grade = fields.Selection([
        ('a', 'A'),
        ('b', 'B'),
        ('c', 'C'),
        ('d', 'D'),
    ], string='Final Grade', compute='_compute_grade', store=True, readonly=True)
    state = fields.Selection([('draft', 'To Do'), ('done', 'Done')], default='draft', tracking=True)
    line_ids = fields.One2many('rmg.cmp.audit.line', 'audit_id', string='Checklist')
    note = fields.Text(string='Remarks')
    ok_count = fields.Integer(compute='_compute_stats', store=True)
    nc_count = fields.Integer(string='Non-Compliant', compute='_compute_stats', store=True)
    score = fields.Float(string='Score %', compute='_compute_stats', store=True, aggregator='avg')
    result = fields.Char(string='Final Result', compute='_compute_final_result', store=True)

    @api.depends('line_ids.result')
    def _compute_stats(self):
        for rec in self:
            ok = len(rec.line_ids.filtered(lambda l: l.result == 'yes'))
            nc = len(rec.line_ids.filtered(lambda l: l.result == 'no'))
            rec.ok_count = ok
            rec.nc_count = nc
            rec.score = (ok * 100.0 / (ok + nc)) if (ok + nc) else 0.0

    @api.depends('line_ids.result', 'result_type')
    def _compute_grade(self):
        for rec in self:
            ok = len(rec.line_ids.filtered(lambda line: line.result == 'yes'))
            nc = len(rec.line_ids.filtered(lambda line: line.result == 'no'))
            total = ok + nc
            score = (ok * 100.0 / total) if total else 0.0
            if rec.result_type == 'grade' and total:
                if score >= 90:
                    rec.grade = 'a'
                elif score >= 75:
                    rec.grade = 'b'
                elif score >= 60:
                    rec.grade = 'c'
                else:
                    rec.grade = 'd'
            else:
                rec.grade = False

    @api.depends('line_ids.result', 'result_type', 'grade')
    def _compute_final_result(self):
        for rec in self:
            ok = len(rec.line_ids.filtered(lambda l: l.result == 'yes'))
            nc = len(rec.line_ids.filtered(lambda l: l.result == 'no'))
            total = ok + nc
            score = (ok * 100.0 / total) if total else 0.0

            if rec.result_type == 'percentage':
                rec.result = f'{score:.0f}%' if total else False
            elif rec.result_type == 'grade':
                rec.result = dict(rec._fields['grade'].selection).get(rec.grade) or False
            elif rec.result_type == 'pass_fail':
                all_answered = all(line.result for line in rec.line_ids)
                if not all_answered:
                    rec.result = _('Pending')
                else:
                    rec.result = _('Pass') if total and not nc else _('Fail')
            else:
                rec.result = 'Complete' if total and nc == 0 else 'Non Complete'

    @api.model
    def _template_cmds(self, template):
        return [Command.create({
            'template_item_id': item.id,
            'name': item.name,
            'section': item.section,
            'critical': item.critical,
            'sequence': item.sequence,
        }) for item in template.item_ids]

    @api.onchange('template_id')
    def _onchange_template_id(self):
        tmpl = self.template_id
        self.line_ids = [Command.clear()] + (self._template_cmds(tmpl) if tmpl else [])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('rmg.cmp.audit') or 'New'
        records = super().create(vals_list)
        for rec in records:
            if rec.template_id and not rec.line_ids:
                rec.line_ids = self._template_cmds(rec.template_id)
        return records

    def action_all_yes(self):
        self.line_ids.filtered(lambda l: not l.result).write({'result': 'yes'})

    def action_done(self):
        today = fields.Date.context_today(self)
        for rec in self.filtered(lambda r: r.state == 'draft'):
            if any(not l.result for l in rec.line_ids):
                raise UserError(_("Some items are not checked. Tap 'All Compliant' first, then mark only the problems."))
            for line in rec.line_ids.filtered(lambda l: l.result == 'no'):
                self.env['rmg.cmp.finding'].create({
                    'name': line.name,
                    'section': line.section,
                    'note': line.remark,
                    'correction_plan': line.remark or _('Prepare a corrective action plan for %s.', line.name),
                    'audit_id': rec.id,
                    'critical': line.critical,
                    'due_date': today + timedelta(days=7 if line.critical else 30),
                })
            rec.state = 'done'

    @api.model
    def _cron_generate_audits(self):
        today = fields.Date.context_today(self)
        admin = self.env.ref('base.user_admin')
        for tmpl in self.env['rmg.cmp.template'].search([('interval_months', '>', 0)]):
            if self.search_count([('template_id', '=', tmpl.id), ('state', '=', 'draft')]):
                continue
            last = self.search([('template_id', '=', tmpl.id)], order='date desc', limit=1)
            if not last or last.date + relativedelta(months=tmpl.interval_months) <= today:
                self.create({'template_id': tmpl.id, 'date': today, 'user_id': admin.id})


class RmgCmpAuditLine(models.Model):
    _name = 'rmg.cmp.audit.line'
    _description = 'Compliance Audit Line'
    _order = 'sequence, id'

    audit_id = fields.Many2one('rmg.cmp.audit', required=True, ondelete='cascade')
    template_item_id = fields.Many2one('rmg.cmp.template.item', ondelete='set null', copy=False)
    sequence = fields.Integer(default=10)
    section = fields.Char()
    name = fields.Char(string='Requirement', required=True)
    critical = fields.Boolean(string='Critical')
    result = fields.Selection([('yes', 'Compliant'), ('no', 'Non-Compliant'), ('na', 'N/A')])
    remark = fields.Char()
    state = fields.Selection(related='audit_id.state')

    @api.model_create_multi
    def create(self, vals_list):
        template_item_ids = [
            vals.get('template_item_id')
            for vals in vals_list
            if vals.get('template_item_id')
        ]
        template_items = {
            item.id: item
            for item in self.env['rmg.cmp.template.item'].browse(template_item_ids).exists()
        }
        for vals in vals_list:
            item = template_items.get(vals.get('template_item_id'))
            if item:
                vals.update({
                    'name': item.name,
                    'section': item.section,
                    'critical': item.critical,
                    'sequence': item.sequence,
                })
        return super().create(vals_list)

    def action_yes(self):
        self.write({'result': 'yes'})

    def action_no(self):
        self.write({'result': 'no'})

    def action_na(self):
        self.write({'result': 'na'})
