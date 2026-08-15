"""Synthetic-only data layer for the public portfolio demo.

This module intentionally contains no personal records and never opens the
private CareerPilot database.
"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from pathlib import Path


DATABASE_PATH = Path("data/portfolio_demo.db")
PIPELINE_STAGES = ["投递简历", "笔试测评", "群面", "初试", "复试", "业务面", "HR面", "谈薪", "Offer"]


def configure_session_database(session_token):
    """Isolate every external viewer in a disposable demo database."""
    global DATABASE_PATH
    safe_token = "".join(character for character in str(session_token) if character.isalnum())[:64]
    if not safe_token:
        raise ValueError("A valid showcase session token is required.")
    DATABASE_PATH = Path(tempfile.gettempdir()) / "lumooi_hr_sessions" / f"{safe_token}.db"

EXPERIENCE_FIELDS = [
    "experience_code", "organization", "alternate_name", "experience_type", "role", "role_en",
    "responsibility_direction", "location", "start_date", "end_date", "team", "summary_zh",
    "summary_en", "background", "description", "skills", "tools", "verification_status",
    "external_permission", "verified",
]

ASSET_FIELDS = [
    "experience_id", "asset_code", "title", "category", "asset_position", "role_in_asset",
    "participation_level", "fact_status", "overview_summary", "overview_strengths", "background",
    "objective", "actions", "decisions", "process_scope", "constraints", "results", "uncertainties",
    "metrics", "skills", "tools", "ai_usage", "reflection", "interview_memory_notes", "star_situation",
    "star_task", "star_action", "star_result", "star_uses", "star_b_situation", "star_b_task",
    "star_b_action", "star_b_result", "resume_bullets", "resume_strategy", "resume_roles",
    "resume_keywords", "interview_questions", "interview_followups", "interview_angles",
    "interview_risks", "design_decision", "lessons_learned", "differentiator", "evidence",
    "evidence_status", "contribution_boundary", "expression_limits", "external_permission",
    "include_in_resume", "include_in_interview",
]


def get_connection():
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            position TEXT NOT NULL,
            location TEXT, application_url TEXT, job_description TEXT,
            target_direction TEXT, details TEXT, priority TEXT, status TEXT,
            pipeline_stage TEXT, pipeline_state TEXT, current_stage_status TEXT DEFAULT '进行中',
            application_state TEXT DEFAULT 'active', ended_stage TEXT, termination_notes TEXT,
            deadline TEXT, applied_date TEXT, interview_date TEXT, next_action TEXT, notes TEXT,
            resume_status TEXT DEFAULT '尚未开始', interview_prep_status TEXT DEFAULT '尚未开始',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS job_stage_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL, stage TEXT NOT NULL, stage_status TEXT DEFAULT '准备中',
            event_date TEXT, notes TEXT, scheduled_at TEXT, status_changed_at TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(job_id, stage), FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS interview_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL, round_name TEXT NOT NULL, interview_date TEXT,
            status TEXT DEFAULT '准备中', audio_path TEXT, transcript TEXT,
            extraction_prompt TEXT, review_notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS experiences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experience_code TEXT UNIQUE, organization TEXT NOT NULL, alternate_name TEXT,
            experience_type TEXT, role TEXT NOT NULL, role_en TEXT, responsibility_direction TEXT,
            location TEXT, start_date TEXT, end_date TEXT, team TEXT, summary_zh TEXT,
            summary_en TEXT, background TEXT, description TEXT, skills TEXT, tools TEXT,
            verification_status TEXT, external_permission TEXT, verified INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS experience_assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            experience_id INTEGER NOT NULL, asset_code TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
            category TEXT, asset_position TEXT, role_in_asset TEXT, participation_level TEXT,
            fact_status TEXT, overview_summary TEXT, overview_strengths TEXT, background TEXT,
            objective TEXT, actions TEXT, decisions TEXT, process_scope TEXT, constraints TEXT,
            results TEXT, uncertainties TEXT, metrics TEXT, skills TEXT, tools TEXT, ai_usage TEXT,
            reflection TEXT, interview_memory_notes TEXT, star_situation TEXT, star_task TEXT,
            star_action TEXT, star_result TEXT, star_uses TEXT, star_b_situation TEXT,
            star_b_task TEXT, star_b_action TEXT, star_b_result TEXT, resume_bullets TEXT,
            resume_strategy TEXT, resume_roles TEXT, resume_keywords TEXT, interview_questions TEXT,
            interview_followups TEXT, interview_angles TEXT, interview_risks TEXT,
            design_decision TEXT, lessons_learned TEXT, differentiator TEXT, evidence TEXT,
            evidence_status TEXT, contribution_boundary TEXT, expression_limits TEXT,
            external_permission TEXT, include_in_resume INTEGER DEFAULT 1,
            include_in_interview INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(experience_id) REFERENCES experiences(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS experience_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT, experience_id INTEGER NOT NULL,
            rule_type TEXT NOT NULL, rule_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(experience_id) REFERENCES experiences(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS resume_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER, parent_version_id INTEGER,
            version_name TEXT NOT NULL, version_type TEXT DEFAULT 'manual', content_json TEXT NOT NULL,
            source_prompt TEXT, ai_raw_response TEXT, is_final INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS resume_prompts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, job_id INTEGER NOT NULL, resume_version_id INTEGER,
            prompt_type TEXT DEFAULT 'tailoring', prompt_text TEXT NOT NULL,
            selected_experience_ids TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS resume_import_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT, resume_version_id INTEGER,
            raw_response TEXT, parsed_json TEXT, import_status TEXT NOT NULL,
            error_message TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    connection.commit()
    connection.close()


def _rows(query, params=()):
    connection = get_connection()
    rows = [dict(row) for row in connection.execute(query, params).fetchall()]
    connection.close()
    return rows


def _upsert_experience(record):
    connection = get_connection()
    values = [record.get(field, 1 if field == "verified" else "") for field in EXPERIENCE_FIELDS]
    columns = ", ".join(EXPERIENCE_FIELDS)
    updates = ", ".join(f"{field}=excluded.{field}" for field in EXPERIENCE_FIELDS if field != "experience_code")
    connection.execute(
        f"INSERT INTO experiences ({columns}) VALUES ({','.join('?' for _ in values)}) "
        f"ON CONFLICT(experience_code) DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP",
        values,
    )
    row = connection.execute("SELECT id FROM experiences WHERE experience_code=?", (record["experience_code"],)).fetchone()
    connection.commit()
    connection.close()
    return row["id"]


def _upsert_asset(experience_id, record):
    payload = {**record, "experience_id": experience_id}
    values = [payload.get(field, 1 if field in {"include_in_resume", "include_in_interview"} else "") for field in ASSET_FIELDS]
    columns = ", ".join(ASSET_FIELDS)
    updates = ", ".join(f"{field}=excluded.{field}" for field in ASSET_FIELDS if field != "asset_code")
    connection = get_connection()
    connection.execute(
        f"INSERT INTO experience_assets ({columns}) VALUES ({','.join('?' for _ in values)}) "
        f"ON CONFLICT(asset_code) DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP",
        values,
    )
    connection.commit()
    connection.close()


def _asset(code, title, category, summary, result, metrics, skills):
    return {
        "asset_code": code, "title": title, "category": category,
        "asset_position": "可复用于简历、面试与作品集的核心案例",
        "role_in_asset": "独立负责核心执行，并与相关团队协作",
        "participation_level": "核心执行者", "fact_status": "虚构演示数据",
        "overview_summary": summary, "overview_strengths": skills,
        "background": "团队需要在有限时间内完成交付，同时保证候选人和业务方体验。",
        "objective": "建立清晰、可追踪且可以复用的工作流程。",
        "actions": "1. 明确问题和成功标准。\n2. 整理信息并建立工作看板。\n3. 与关键协作者校准节奏。\n4. 复盘数据并迭代流程。",
        "decisions": "优先解决高频且影响交付质量的问题，并保留人工复核节点。",
        "process_scope": "需求分析、信息整理、协作推进、结果复盘",
        "constraints": "时间有限，部分数据只能使用区间表达。", "results": result,
        "uncertainties": "对外展示不包含任何真实企业或个人资料。", "metrics": metrics,
        "skills": skills, "tools": "Excel, Notion, Python, Streamlit",
        "ai_usage": "",
        "reflection": "下一次会更早定义数据口径，并把复盘节点加入项目计划。",
        "interview_memory_notes": f"重点讲清楚个人贡献、协作边界与结果：{result}",
        "star_situation": "项目同时存在进度分散、协作成本高和信息口径不一致的问题。",
        "star_task": "在限定周期内建立可执行的流程并完成关键交付。",
        "star_action": "拆解目标、建立看板、同步利益相关者，并根据数据持续调整优先级。",
        "star_result": result, "star_uses": "行为面试、项目管理、流程优化",
        "resume_bullets": f"{summary}；{result}",
        "resume_strategy": "根据目标岗位强调项目推进、数据分析或跨团队协作。",
        "resume_roles": "People Operations, Talent Acquisition, HR Technology",
        "resume_keywords": skills,
        "interview_questions": "你如何确定优先级？\n你遇到的最大阻力是什么？\n如何衡量项目结果？",
        "interview_followups": "哪些工作由你独立完成？\n如何处理不完整信息？",
        "interview_angles": "突出结构化思考、执行和复盘能力。",
        "interview_risks": "不要把团队结果全部归为个人成果。",
        "design_decision": "采用可复用的数据结构，而不是一次性文档。",
        "lessons_learned": "事实边界和数据口径需要在项目早期确认。",
        "differentiator": "把业务执行经验转化为可追踪、可复用的职业资产。",
        "evidence": "本页面为作品集虚构示例，不对应真实企业文件。",
        "evidence_status": "Synthetic / Portfolio Demo",
        "contribution_boundary": "演示人物负责分析和执行；业务决策由虚构团队共同完成。",
        "expression_limits": "不得将虚构数据解释为真实客户、候选人或企业成果。",
        "external_permission": "可公开展示（虚构数据）",
    }


def seed_demo_data():
    from personal_public_seed import seed_personal_public_demo
    seed_personal_public_demo()
    return

    initialize_database()
    if get_asset_by_code("AUR-01"):
        return
    experiences = [
        ({"experience_code":"AUR","organization":"Aurora Consumer Tech","alternate_name":"Aurora","experience_type":"实习经历","role":"Talent Operations Intern","role_en":"Talent Operations Intern","responsibility_direction":"招聘运营、候选人体验、流程优化","location":"Shanghai","start_date":"2025-01","end_date":"2025-06","team":"People Team","summary_zh":"支持高速增长团队的招聘交付与运营优化。","summary_en":"Supported recruiting delivery and operations for a growing consumer technology team.","background":"虚构的消费科技公司招聘项目。","description":"负责招聘流程、数据跟踪与候选人沟通。","skills":"招聘运营, 数据分析, 项目管理","tools":"Excel, ATS, Notion","verification_status":"虚构演示数据","external_permission":"可公开展示","verified":1}, [
            _asset("AUR-01","多岗位招聘交付看板","招聘运营","建立统一看板管理多条招聘流程","将平均反馈周期缩短约25%","并行跟进10–12个岗位","项目管理, 招聘运营, 数据分析"),
            _asset("AUR-02","候选人体验触点优化","候选人体验","梳理从邀约到面试反馈的关键触点","候选人信息遗漏显著减少","覆盖5个关键触点","流程优化, 沟通, 用户体验"),
            _asset("AUR-03","校招内容运营实验","雇主品牌","设计面向毕业生的内容节奏和反馈机制","自然互动率提升约30%","完成8周内容实验","内容策略, 跨团队协作, 复盘"),
        ]),
        ({"experience_code":"BLU","organization":"BluePeak Media","alternate_name":"BluePeak","experience_type":"实习经历","role":"People Partner Intern","role_en":"People Partner Intern","responsibility_direction":"招聘支持、培训运营、员工体验","location":"Beijing","start_date":"2024-06","end_date":"2024-09","team":"People Experience","summary_zh":"支持业务团队招聘与新员工体验项目。","summary_en":"Supported recruiting and onboarding experience for a digital media team.","background":"虚构的数字媒体企业人力资源项目。","description":"连接业务需求、候选人沟通与培训执行。","skills":"HRBP, 培训运营, 沟通协调","tools":"Excel, Slides","verification_status":"虚构演示数据","external_permission":"可公开展示","verified":1}, [
            _asset("BLU-01","社交渠道招聘试验","渠道运营","测试社交内容对招聘转化的影响","新增有效候选人线索20+","3类内容、2个渠道","招聘, 内容运营, 数据分析"),
            _asset("BLU-02","新员工入职指南重构","培训运营","将分散材料重构为模块化入职指南","新员工常见问题减少约20%","重构6个内容模块","信息架构, 培训, 员工体验"),
        ]),
        ({"experience_code":"NOVA","organization":"NovaHR Labs","alternate_name":"NovaHR","experience_type":"咨询项目","role":"HR Tech Strategy Consultant","role_en":"HR Tech Strategy Consultant","responsibility_direction":"市场研究、竞品分析、投资叙事","location":"Philadelphia / Remote","start_date":"2026-01","end_date":"2026-04","team":"5-person consulting team","summary_zh":"为虚构HR科技初创企业完成市场与产品策略研究。","summary_en":"Developed market and product strategy for a fictional HR technology startup.","background":"课程中的虚构企业咨询案例。","description":"负责竞争格局、市场机会和路演叙事模块。","skills":"市场研究, 战略分析, 商业表达","tools":"PowerPoint, Excel, Public Research","verification_status":"虚构演示数据","external_permission":"可公开展示","verified":1}, [
            _asset("NOVA-01","HR Tech竞争格局矩阵","市场研究","将零散竞品信息整理为四类竞争格局","形成可用于产品定位的比较矩阵","4类、8个示例平台","竞品分析, 框架设计, 研究"),
            _asset("NOVA-02","投资人叙事模块化","商业策略","压缩复杂材料并重构短时路演逻辑","完成一套6分钟团队路演材料","5人团队、3轮迭代","商业表达, 协作, 信息设计"),
            _asset("NOVA-03","早期市场机会筛选","战略研究","建立适配阶段、行业和地区的筛选标准","输出6项候选机会及优先级建议","3项筛选维度","研究, 决策支持, 风险意识"),
        ]),
        ({"experience_code":"LUM","organization":"lumooi","alternate_name":"Career OS","experience_type":"个人产品项目","role":"Product Designer & Developer","role_en":"Product Designer and Developer","responsibility_direction":"产品策略、信息架构、交互设计、本地开发","location":"Local-first","start_date":"2026-05","end_date":"Present","team":"Independent product project","summary_zh":"设计并开发以职业资产为事实底座的个人Career OS。","summary_en":"Designed and built a local-first Career OS grounded in verified career assets.","background":"为解决求职信息分散和重复准备问题而设计。","description":"完成职业资产库、申请追踪、简历定制和面试复盘工作流。","skills":"产品设计, Python, Streamlit, SQLite, AI工作流","tools":"Python, Streamlit, SQLite, Figma","verification_status":"产品功能可在本Demo中验证","external_permission":"可公开展示","verified":1}, [
            _asset("LUM-01","Experience Bank信息架构","产品设计","设计经历—资产—证据—权限的数据结构","形成可支持多个求职场景的事实底座","4类核心实体","信息架构, 数据建模, 产品策略"),
            _asset("LUM-02","申请旅程工作台","产品开发","将职位收藏和申请进度整合为统一工作台","支持9个阶段和可逆状态更新","9阶段流程","交互设计, Python, 项目管理"),
            _asset("LUM-03","事实边界与人工复核机制","AI产品","为生成内容增加事实状态、贡献边界和审核节点","降低简历与面试内容被夸大的风险","3层审核规则","AI工作流, 风险控制, 产品设计"),
        ]),
        ({"experience_code":"URB","organization":"Urban Futures Lab","alternate_name":"UFL","experience_type":"科研经历","role":"Research Assistant","role_en":"Research Assistant","responsibility_direction":"文献研究、问卷设计、研究表达","location":"Remote","start_date":"2023-09","end_date":"2024-06","team":"Student research team","summary_zh":"参与青年工作体验主题的虚构研究项目。","summary_en":"Contributed to a fictional study on early-career work experience.","background":"公开作品集中使用的合成研究案例。","description":"参与文献综述、问卷结构和报告表达。","skills":"研究设计, 文献综述, 数据表达","tools":"SPSS, Excel","verification_status":"虚构演示数据","external_permission":"可公开展示","verified":1}, [
            _asset("URB-01","青年工作体验问卷设计","研究方法","将研究问题转换为可测量的问卷结构","形成包含5个维度的问卷初稿","5个研究维度","问卷设计, 文献研究, 结构化思考"),
            _asset("URB-02","研究发现可视化表达","数据表达","把复杂分析整理为面向非研究受众的摘要","完成一套10页研究汇报","10页汇报材料","数据表达, 演示, 跨学科沟通"),
        ]),
    ]
    for experience, assets in experiences:
        experience_id = _upsert_experience(experience)
        for asset in assets:
            _upsert_asset(experience_id, asset)
        connection = get_connection()
        connection.executemany(
            "INSERT INTO experience_rules(experience_id,rule_type,rule_text) VALUES(?,?,?)",
            [
                (experience_id, "作品集说明", "此经历及相关数字均为虚构演示数据。"),
                (experience_id, "贡献边界", "保留个人贡献与团队结果的区别，不扩大责任范围。"),
            ],
        )
        connection.commit(); connection.close()

    jobs = [
        ("Northstar Commerce","People Operations Associate","New York / Hybrid","People Operations","高","初试","进行中","active","2026-08-28","2026-08-08","2026-08-20","准备Hiring Manager面试","待确认","正在准备"),
        ("Mosaic Health","Talent Programs Coordinator","Remote","Talent Programs","中","投递简历","已完成","active","2026-09-02","2026-08-10","","完成岗位版简历","已完成","待生成问题"),
        ("Orbit Systems","HR Technology Analyst","Philadelphia","HR Technology","高","准备投递","进行中","active","2026-09-10","","","完成JD拆解","正在定制","尚未开始"),
        ("Greenline Studio","Recruiting Operations Specialist","Boston / Hybrid","Recruiting Operations","中","业务面","进行中","active","2026-08-25","2026-08-01","2026-08-22","准备业务案例","已完成","正在准备"),
        ("Harbor Labs","People Analytics Intern","Remote","People Analytics","低","已结束","已结束","ended","2026-08-18","2026-07-28","2026-08-12","记录复盘并归档","已完成","已完成"),
    ]
    jd = "负责支持People团队的项目运营、数据分析和流程优化；与跨职能伙伴协作，维护准确记录并改善候选人与员工体验。要求具备结构化思考、沟通能力和基础数据分析能力。"
    connection = get_connection()
    for row in jobs:
        cursor = connection.execute(
            "INSERT INTO jobs(company,position,location,application_url,job_description,target_direction,priority,status,current_stage_status,application_state,deadline,applied_date,interview_date,next_action,resume_status,interview_prep_status,notes) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (row[0],row[1],row[2],"https://example.com/demo-role",jd,row[3],row[4],row[5],row[6],row[7],row[8],row[9],row[10],row[11],row[12],row[13],"作品集虚构岗位，请勿用于真实申请。"),
        )
        job_id = cursor.lastrowid
        if row[5] in PIPELINE_STAGES:
            connection.execute("INSERT INTO job_stage_events(job_id,stage,stage_status,event_date,notes) VALUES(?,?,?,?,?)", (job_id,row[5],row[6],row[10] or row[9],"虚构流程节点"))
    first_job = connection.execute("SELECT id FROM jobs ORDER BY id LIMIT 1").fetchone()[0]
    connection.execute("INSERT INTO interview_sessions(job_id,round_name,interview_date,status,transcript,review_notes) VALUES(?,?,?,?,?,?)", (first_job,"Recruiter Screen","2026-08-20","已完成","Interviewer: Tell me about a process you improved.\nMaya: I mapped the workflow, identified the longest feedback delay, and introduced a shared tracker with clear owners.","回答结构清楚；下一轮需要补充取舍过程和失败复盘。"))
    connection.commit(); connection.close()


def get_all_jobs():
    return _rows("SELECT * FROM jobs ORDER BY CASE WHEN deadline IS NULL OR deadline='' THEN 1 ELSE 0 END, deadline")


def get_all_experiences():
    return _rows("SELECT * FROM experiences ORDER BY start_date DESC")


def get_experience_assets(experience_id):
    return _rows("SELECT * FROM experience_assets WHERE experience_id=? ORDER BY asset_code", (experience_id,))


def get_experience_rules(experience_id):
    return _rows("SELECT id,rule_type,rule_text FROM experience_rules WHERE experience_id=? ORDER BY id", (experience_id,))


def get_asset_by_code(asset_code):
    rows = _rows("SELECT a.*,e.experience_code,e.organization,e.role FROM experience_assets a JOIN experiences e ON e.id=a.experience_id WHERE a.asset_code=?", (asset_code,))
    return rows[0] if rows else None


def add_job(company, position, location, application_url, job_description, target_direction, priority, status, deadline, next_action, details=""):
    initialize_database()
    connection = get_connection()
    cursor = connection.execute("INSERT INTO jobs(company,position,location,application_url,job_description,target_direction,details,priority,status,deadline,next_action) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (company.strip(),position.strip(),location.strip(),application_url.strip(),job_description.strip(),target_direction.strip(),details.strip(),priority,status,deadline or None,next_action.strip()))
    job_id = cursor.lastrowid; connection.commit(); connection.close(); return job_id


def update_job_progress(job_id, status, applied_date, interview_date, next_action, notes, pipeline_stage=None, pipeline_state=None):
    connection = get_connection(); cursor = connection.execute("UPDATE jobs SET status=?,applied_date=?,interview_date=?,next_action=?,notes=?,pipeline_stage=?,pipeline_state=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (status,applied_date,interview_date,next_action,notes,pipeline_stage or "",pipeline_state or "",job_id)); connection.commit(); changed=cursor.rowcount; connection.close(); return changed > 0


def _upsert_stage_event(connection, job_id, stage, status, event_date="", notes="", scheduled_at="", status_changed_at=""):
    connection.execute("INSERT INTO job_stage_events(job_id,stage,stage_status,event_date,notes,scheduled_at,status_changed_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(job_id,stage) DO UPDATE SET stage_status=excluded.stage_status,event_date=excluded.event_date,notes=excluded.notes,scheduled_at=excluded.scheduled_at,status_changed_at=excluded.status_changed_at,updated_at=CURRENT_TIMESTAMP", (int(job_id),stage,status,event_date,notes,scheduled_at,status_changed_at))


def get_job_applications():
    jobs = get_all_jobs(); events = _rows("SELECT * FROM job_stage_events ORDER BY job_id,id")
    grouped = {}
    for event in events: grouped.setdefault(event["job_id"], []).append(event)
    for job in jobs: job["stage_events"] = grouped.get(job["id"], [])
    return jobs


def save_job_application(job_id, company, position, location, application_url, job_description, target_direction, status, current_stage_status, deadline, stage_date, next_action, notes, resume_status, interview_prep_status):
    if job_id is not None: raise ValueError("该接口仅用于新增职位。")
    if not company.strip() or not position.strip() or not job_description.strip(): raise ValueError("请填写公司、岗位和完整JD。")
    connection = get_connection(); cursor = connection.execute("INSERT INTO jobs(company,position,location,application_url,job_description,target_direction,status,current_stage_status,deadline,applied_date,interview_date,next_action,notes,resume_status,interview_prep_status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (company.strip(),position.strip(),location.strip(),application_url.strip(),job_description.strip(),target_direction.strip(),status,current_stage_status,deadline or None,stage_date if status=="投递简历" else "",stage_date if status in {"群面","初试","复试","业务面","HR面"} else "",next_action.strip(),notes.strip(),resume_status,interview_prep_status)); saved=cursor.lastrowid
    if status in PIPELINE_STAGES: _upsert_stage_event(connection,saved,status,current_stage_status,stage_date)
    connection.commit(); connection.close(); return saved


def update_job_application_details(job_id, company, position, location, application_url, job_description, target_direction, deadline, notes):
    connection=get_connection(); cursor=connection.execute("UPDATE jobs SET company=?,position=?,location=?,application_url=?,job_description=?,target_direction=?,deadline=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(company.strip(),position.strip(),location.strip(),application_url.strip(),job_description.strip(),target_direction.strip(),deadline or None,notes.strip(),int(job_id))); connection.commit(); changed=cursor.rowcount; connection.close(); return changed>0


def update_job_application_progress(job_id, current_stage, stage_status, stage_date, stage_notes, next_action, resume_status, interview_prep_status):
    connection=get_connection()
    if current_stage in PIPELINE_STAGES: _upsert_stage_event(connection,job_id,current_stage,stage_status,stage_date,stage_notes)
    state="ended" if current_stage in {"拒绝","放弃","已结束"} or stage_status=="已结束" else "offer" if current_stage=="Offer" and stage_status=="已完成" else "active"
    connection.execute("UPDATE jobs SET status=?,current_stage_status=?,application_state=?,ended_stage=?,next_action=?,resume_status=?,interview_prep_status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(current_stage,stage_status,state,current_stage if state=="ended" else "",next_action.strip(),resume_status,interview_prep_status,int(job_id))); connection.commit(); connection.close(); return True


def update_application_stage_event(job_id, stage, stage_status, scheduled_at, status_changed_at, notes, make_current=True):
    connection=get_connection()
    if stage != "准备投递": _upsert_stage_event(connection,job_id,stage,stage_status,(status_changed_at or scheduled_at)[:10],notes,scheduled_at,status_changed_at)
    if make_current: connection.execute("UPDATE jobs SET status=?,current_stage_status=?,application_state=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(stage,stage_status,"ended" if stage_status=="已结束" else "active",int(job_id)))
    connection.commit(); connection.close(); return True


def update_application_timeline_node(job_id, stage, action):
    status={"complete":"已完成","end":"已结束","undo":"进行中"}.get(action)
    if not status: raise ValueError("无效的时间线操作。")
    connection=get_connection(); _upsert_stage_event(connection,job_id,stage,status)
    state="ended" if action=="end" else "offer" if stage=="Offer" and action=="complete" else "active"
    connection.execute("UPDATE jobs SET status=?,current_stage_status=?,application_state=?,ended_stage=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",("已结束" if action=="end" else stage,status,state,stage if action=="end" else "",int(job_id))); connection.commit(); connection.close(); return True


def update_application_termination_notes(job_id, termination_notes):
    connection=get_connection(); connection.execute("UPDATE jobs SET termination_notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(termination_notes.strip(),int(job_id))); connection.commit(); connection.close(); return True


def update_application_interview_notes(job_id, notes):
    connection=get_connection(); connection.execute("UPDATE jobs SET notes=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(notes.strip(),int(job_id))); connection.commit(); connection.close(); return True


def get_interview_sessions(job_id):
    return _rows("SELECT * FROM interview_sessions WHERE job_id=? ORDER BY id DESC",(int(job_id),))


def create_interview_session(job_id, round_name, interview_date=""):
    connection=get_connection(); cursor=connection.execute("INSERT INTO interview_sessions(job_id,round_name,interview_date) VALUES(?,?,?)",(int(job_id),round_name.strip(),interview_date.strip())); row_id=cursor.lastrowid; connection.commit(); connection.close(); return row_id


def update_interview_session(session_id, **fields):
    allowed={"round_name","interview_date","status","audio_path","transcript","extraction_prompt","review_notes"}; clean={key:value for key,value in fields.items() if key in allowed}
    if not clean: return True
    connection=get_connection(); connection.execute(f"UPDATE interview_sessions SET {','.join(f'{key}=?' for key in clean)},updated_at=CURRENT_TIMESTAMP WHERE id=?",(*clean.values(),int(session_id))); connection.commit(); connection.close(); return True


def create_resume_version(job_id, version_name, content, version_type="manual", ai_raw_response="", parent_version_id=None, source_prompt=""):
    connection=get_connection(); cursor=connection.execute("INSERT INTO resume_versions(job_id,parent_version_id,version_name,version_type,content_json,source_prompt,ai_raw_response) VALUES(?,?,?,?,?,?,?)",(job_id,parent_version_id,version_name,version_type,json.dumps(content,ensure_ascii=False),source_prompt,ai_raw_response)); row_id=cursor.lastrowid; connection.commit(); connection.close(); return row_id


def get_resume_versions(job_id):
    return _rows("SELECT * FROM resume_versions WHERE job_id=? ORDER BY id DESC",(int(job_id),))


def save_resume_prompt(job_id, resume_version_id, prompt_text, selected_experience_ids):
    connection=get_connection(); cursor=connection.execute("INSERT INTO resume_prompts(job_id,resume_version_id,prompt_text,selected_experience_ids) VALUES(?,?,?,?)",(job_id,resume_version_id,prompt_text,json.dumps(selected_experience_ids,ensure_ascii=False))); row_id=cursor.lastrowid; connection.commit(); connection.close(); return row_id


def save_import_record(resume_version_id, raw_response, parsed_json, import_status, error_message=""):
    connection=get_connection(); cursor=connection.execute("INSERT INTO resume_import_records(resume_version_id,raw_response,parsed_json,import_status,error_message) VALUES(?,?,?,?,?)",(resume_version_id,raw_response,json.dumps(parsed_json,ensure_ascii=False) if parsed_json is not None else None,import_status,error_message)); row_id=cursor.lastrowid; connection.commit(); connection.close(); return row_id
