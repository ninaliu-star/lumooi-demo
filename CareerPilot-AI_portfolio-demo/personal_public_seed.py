"""Detached public portfolio seed for Liu Zefei.

The bundled JSON is a one-time sanitized snapshot. This module never opens or
imports the private CareerPilot database.
"""

from __future__ import annotations

import json
from pathlib import Path

from demo_database import _upsert_asset, _upsert_experience, get_asset_by_code, get_connection, initialize_database


DATA_PATH = Path(__file__).with_name("public_profile_data.json")


def _clear(connection):
    for table in (
        "resume_import_records", "resume_prompts", "resume_versions", "interview_sessions",
        "job_stage_events", "jobs", "experience_rules", "experience_assets", "experiences",
    ):
        connection.execute(f"DELETE FROM {table}")


def seed_personal_public_demo():
    initialize_database()
    if get_asset_by_code("CP-01"):
        return

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    connection = get_connection()
    _clear(connection)
    connection.commit()
    connection.close()

    experience_ids = {}
    for experience in payload["experiences"]:
        experience_ids[experience["experience_code"]] = _upsert_experience(experience)
    for asset in payload["assets"]:
        record = dict(asset)
        code = record.pop("experience_code")
        _upsert_asset(experience_ids[code], record)
    for rule in payload["rules"]:
        connection = get_connection()
        connection.execute(
            "INSERT INTO experience_rules(experience_id,rule_type,rule_text) VALUES(?,?,?)",
            (experience_ids[rule["experience_code"]], rule["rule_type"], rule["rule_text"]),
        )
        connection.commit()
        connection.close()

    connection = get_connection()
    demo_stages = ["准备投递", "投递简历", "笔试测评", "群面", "初试", "复试", "业务面", "HR面", "已结束"]
    for index, job in enumerate(payload["jobs"]):
        status = demo_stages[index % len(demo_stages)]
        applied_date = "" if status == "准备投递" else f"2026-08-{18 + index:02d}"
        interview_date = f"2026-09-{3 + index:02d}" if status in {"群面", "初试", "复试", "业务面", "HR面"} else ""
        deadline = f"2026-09-{15 + index:02d}"
        cursor = connection.execute(
            "INSERT INTO jobs(company,position,location,application_url,job_description,target_direction,priority,status,current_stage_status,application_state,deadline,applied_date,interview_date,next_action,resume_status,interview_prep_status,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (job["company"], job["position"], "地点已隐藏", "", job["job_description"], job["target_direction"], "Demo", status, "虚构进度", "ended" if status == "已结束" else "scenario", deadline, applied_date, interview_date, "体验：使用JD筛选最匹配的经历资产", "Demo 模板", "Demo 模板", "公司名称、申请阶段与日期均为虚构；岗位名称与JD保留。"),
        )
        if status not in {"准备投递", "已结束"}:
            connection.execute(
                "INSERT INTO job_stage_events(job_id,stage,stage_status,event_date,notes) VALUES(?,?,?,?,?)",
                (cursor.lastrowid, status, "虚构进度", interview_date or applied_date, "Demo虚构流程节点"),
            )
    first_job = connection.execute("SELECT id FROM jobs ORDER BY id LIMIT 1").fetchone()[0]
    connection.execute(
        "INSERT INTO interview_sessions(job_id,round_name,interview_date,status,transcript,review_notes) VALUES(?,?,?,?,?,?)",
        (first_job, "STAR 匹配练习（假设）", "", "示例", "面试官：请举例说明你如何同时推进多个任务。\n刘泽菲：我会从多岗位招聘交付资产中选择案例，按背景、任务、行动和结果组织回答。", "演示用面试准备；不包含真实公司、面试时间或面试记录。"),
    )
    connection.commit()
    connection.close()
