"""待结构化简历清单查询服务。"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

PENDING_RESUMES_SQL = """
SELECT source_type,
       source_id,
       resume_created_time,
       filekey
FROM (
         SELECT 'employee'     AS source_type,
                eb.employee_id AS source_id,
                eb.gmt_create  AS resume_created_time,
                eb.file_key    AS filekey
         FROM (SELECT DISTINCT ei.id,
                               ei.employee_id,
                               ei.employee_name,
                               ei.is_deleted,
                               ei.is_effective,
                               ei.dimission,
                               cr.resume_attach,
                               os.file_name,
                               os.file_key,
                               os.gmt_create
               FROM employee_info ei
                        LEFT JOIN (SELECT employee_id,
                                          SUBSTRING_INDEX(resume_attach, ',', -1) AS resume_attach
                                   FROM certificate_resources
                                   WHERE is_deleted = 0) cr ON cr.employee_id = ei.employee_id
                        LEFT JOIN obs_file os ON os.file_id = cr.resume_attach
                        LEFT JOIN (SELECT ds.employee_id,
                                          ds.client_organization_id,
                                          ds.client_id,
                                          ds.after_client_post_id,
                                          ds.after_client_post_level_id,
                                          fso.org_id,
                                          fso.org_name,
                                          ds.work_province_code,
                                          ds.work_city_code,
                                          ds.work_area_code
                                   FROM dispatched_staff ds
                                            JOIN (SELECT MAX(planned_admission_date) AS date, employee_id
                                                  FROM dispatched_staff
                                                  GROUP BY employee_id) ost1
                                                 ON ost1.employee_id = ds.employee_id
                                                     AND ost1.date = ds.planned_admission_date
                                            LEFT JOIN client ct ON ds.client_id = ct.client_id
                                            LEFT JOIN sys_organization fso
                                                      ON fso.org_id = ct.first_org_id AND fso.is_deleted = 0) a
                                  ON a.employee_id = ei.employee_id
                        LEFT JOIN (SELECT bpr.employee_id,
                                          bpr.client_organization_id,
                                          bpr.client_id,
                                          bpr.client_post_id,
                                          bpr.client_post_level_id,
                                          bpr.admission_date,
                                          fso.org_id,
                                          fso.org_name,
                                          bpr.work_province_code,
                                          bpr.work_city_code,
                                          bpr.work_area_code
                                   FROM biz_presence_record bpr
                                            JOIN (SELECT MAX(admission_date) AS date, employee_id
                                                  FROM biz_presence_record
                                                  WHERE is_deleted = 0
                                                    AND audit_status = 1
                                                  GROUP BY employee_id) ost1
                                                 ON ost1.employee_id = bpr.employee_id
                                                     AND ost1.date = bpr.admission_date
                                            LEFT JOIN client ct ON bpr.client_id = ct.client_id
                                            LEFT JOIN sys_organization fso
                                                      ON fso.org_id = ct.first_org_id AND fso.is_deleted = 0
                                   WHERE bpr.is_deleted = 0
                                     AND bpr.audit_status = 1) b ON b.employee_id = ei.employee_id
                        LEFT JOIN (SELECT et.employee_id,
                                          et.client_organization_id,
                                          et.client_id,
                                          et.post_id,
                                          et.post_level_id,
                                          et.unit_price_start_date,
                                          fso.org_id,
                                          fso.org_name
                                   FROM entrant et
                                            LEFT JOIN client ct ON et.client_id = ct.client_id
                                            LEFT JOIN sys_organization fso
                                                      ON fso.org_id = ct.first_org_id AND fso.is_deleted = 0) c
                                  ON c.employee_id = ei.employee_id) eb
         WHERE eb.is_effective = 1
           AND eb.is_deleted = 0
           AND eb.dimission = 0
           AND eb.resume_attach IS NOT NULL

         UNION

         SELECT 'submit_candidate' AS source_type,
                sc.candidate_id    AS source_id,
                os.gmt_create      AS resume_created_time,
                os.file_key        AS filekey
         FROM submit_claim sc
                  LEFT JOIN obs_file os ON os.file_id = sc.attachments
         WHERE sc.is_deleted = 0
           AND sc.attachments != ''
           AND sc.attachments IS NOT NULL
           AND DATE_FORMAT(sc.gmt_create, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
           AND sc.status = 10
     ) pending_resumes
WHERE source_type = :source_type
  AND (:cursor IS NULL OR source_id > :cursor)
ORDER BY source_id ASC
LIMIT :fetch_limit
"""


class PendingResumeService:
    """统一查询待结构化简历清单。"""

    def __init__(self, db: Session):
        self.db = db

    def list_pending_resumes(
        self,
        source_type: str,
        cursor: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """按来源类型分页返回待结构化简历。"""
        if source_type == "entrant":
            return {"items": [], "next_cursor": None}

        fetch_limit = limit + 1
        rows = (
            self.db.execute(
                text(PENDING_RESUMES_SQL),
                {
                    "source_type": source_type,
                    "cursor": cursor,
                    "fetch_limit": fetch_limit,
                },
            )
            .mappings()
            .all()
        )

        items = [
            {
                "source_type": row["source_type"],
                "source_id": str(row["source_id"]),
                "resume_created_time": str(row["resume_created_time"]),
                "filekey": row["filekey"],
            }
            for row in rows[:limit]
        ]

        next_cursor = items[-1]["source_id"] if len(rows) > limit and items else None
        return {
            "items": items,
            "next_cursor": next_cursor,
        }
