import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("""
        UPDATE rmg_cmp_audit_line AS audit_line
           SET name = template_item.name
          FROM rmg_cmp_audit AS audit
          JOIN rmg_cmp_template_item AS template_item
            ON template_item.template_id = audit.template_id
         WHERE audit_line.audit_id = audit.id
           AND audit_line.name IN ('', 'Checklist Item')
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
    repaired_lines = cr.rowcount

    cr.execute("""
        UPDATE rmg_cmp_audit
           SET grade = CASE
               WHEN score >= 90 THEN 'a'
               WHEN score >= 75 THEN 'b'
               WHEN score >= 60 THEN 'c'
               ELSE 'd'
           END
         WHERE result_type = 'grade'
           AND state = 'done'
           AND (grade IS NULL OR grade = '')
    """)
    preserved_grades = cr.rowcount

    cr.execute("""
        UPDATE rmg_cmp_audit
           SET result = UPPER(grade)
         WHERE result_type = 'grade'
           AND grade IS NOT NULL
    """)
    _logger.info(
        "RMG Compliance upgrade repaired %s audit requirements and preserved %s completed grades",
        repaired_lines,
        preserved_grades,
    )
