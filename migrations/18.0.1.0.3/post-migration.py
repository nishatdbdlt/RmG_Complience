import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE rmg_cmp_audit_line AS audit_line
           SET template_item_id = template_item.id,
               name = template_item.name
          FROM rmg_cmp_audit AS audit,
               rmg_cmp_template_item AS template_item
         WHERE (audit_line.name IS NULL OR audit_line.name IN ('', 'Checklist Item'))
           AND audit_line.template_item_id IS NULL
           AND audit.id = audit_line.audit_id
           AND template_item.template_id = audit.template_id
           AND template_item.sequence = audit_line.sequence
           AND COALESCE(template_item.section, '') = COALESCE(audit_line.section, '')
           AND template_item.name IS NOT NULL
           AND template_item.name != ''
           AND (
                SELECT COUNT(*)
                  FROM rmg_cmp_template_item AS candidate
                 WHERE candidate.template_id = audit.template_id
                   AND candidate.sequence = audit_line.sequence
                   AND COALESCE(candidate.section, '') = COALESCE(audit_line.section, '')
                   AND candidate.name IS NOT NULL
                   AND candidate.name != ''
           ) = 1
    """)
    _logger.info("Restored %s saved audit requirement names from their checklist templates", cr.rowcount)
