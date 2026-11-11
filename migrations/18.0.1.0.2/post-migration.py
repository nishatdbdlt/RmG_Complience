def migrate(cr, version):
    cr.execute("""
        UPDATE rmg_cmp_audit
           SET grade = CASE
               WHEN score >= 90 THEN 'a'
               WHEN score >= 75 THEN 'b'
               WHEN score >= 60 THEN 'c'
               WHEN ok_count + nc_count > 0 THEN 'd'
               ELSE NULL
           END
         WHERE result_type = 'grade'
    """)
    cr.execute("""
        UPDATE rmg_cmp_audit
           SET result = CASE grade
               WHEN 'a' THEN 'A'
               WHEN 'b' THEN 'B'
               WHEN 'c' THEN 'C'
               WHEN 'd' THEN 'D'
               ELSE NULL
           END
         WHERE result_type = 'grade'
    """)
