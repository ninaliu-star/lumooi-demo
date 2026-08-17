import re
import zipfile
from html import escape
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

import streamlit as st

from demo_database import (
    create_interview_session,
    get_all_experiences,
    get_experience_assets,
    get_interview_sessions,
    update_interview_session,
)


PASTELS = {
    "blue": "#DCEBFF",
    "green": "#DDF3E7",
    "purple": "#EFE4FF",
    "orange": "#FFE6D2",
}

COMPETENCY_RULES = [
    ("用户与客户体验", ["用户体验", "客户体验", "用户满意", "用户研究", "用户投诉", "customer experience", "user experience"]),
    ("项目管理与交付", ["项目管理", "项目推进", "项目进度", "流程落地", "交付", "执行", "project management", "delivery"]),
    ("数据分析与洞察", ["数据分析", "数据洞察", "指标", "复盘", "分析", "analytics", "insight"]),
    ("沟通与跨团队协作", ["跨团队", "跨部门", "沟通", "协同", "协调", "stakeholder", "communication", "teamwork"]),
    ("运营与流程优化", ["运营", "流程", "服务质量", "质量管理", "持续迭代", "效率", "operations", "process"]),
    ("策略与问题解决", ["策略", "解决方案", "改进方案", "问题解决", "判断", "决策", "strategy", "problem solving"]),
    ("商业与业务理解", ["商业", "业务逻辑", "业务流程", "零售", "商务拓展", "市场", "business", "commercial"]),
    ("多语言与跨文化", ["多语言", "多文化", "语言能力", "国家", "国际业务", "cross-cultural", "multilingual", "language"]),
    ("AI 与技术应用", ["ai", "人工智能", "智能化", "科技", "技术", "automation", "technology"]),
    ("学习与适应", ["学习能力", "好奇心", "适应", "快速学习", "轮岗", "learning", "adapt"]),
    ("领导力与影响力", ["领导", "影响", "推动", "带领", "担当", "leadership", "influence"]),
    ("细节、诚信与风险", ["细节", "准确", "合规", "风险", "诚信", "质量", "detail", "accuracy", "risk"]),
]

def _safe(value, fallback="未设置"):
    value = fallback if value is None or not str(value).strip() else str(value).strip()
    return escape(value)


def _lines(value):
    if not value:
        return []
    parts = re.split(r"[\n\r]+", str(value))
    return [part.strip(" •-\t") for part in parts if part.strip(" •-\t")]


def _tokens(value):
    return set(re.findall(r"[a-zA-Z]{2,}|[\u4e00-\u9fff]{2,5}", str(value or "").lower()))


def _detect_competencies(value):
    text = str(value or "").lower()
    detected = []
    for name, keywords in COMPETENCY_RULES:
        evidence = [keyword for keyword in keywords if keyword in text]
        if evidence:
            detected.append({"name": name, "evidence": evidence[:4]})
    return detected


def _experience_groups(job):
    jd_text = " ".join(
        str(job.get(key) or "")
        for key in ("position", "target_direction", "details", "job_description")
    ).lower()
    jd_keyword_map = {
        name: [keyword for keyword in keywords if keyword in jd_text]
        for name, keywords in COMPETENCY_RULES
    }
    jd_keyword_map = {name: keywords for name, keywords in jd_keyword_map.items() if keywords}
    competency_positions = sorted(
        (
            min(jd_text.find(keyword) for keyword in keywords if jd_text.find(keyword) >= 0),
            name,
        )
        for name, keywords in jd_keyword_map.items()
    )
    jd_competency_weights = {
        name: 3 if index < 4 else 2 if index < 8 else 1
        for index, (_, name) in enumerate(competency_positions)
    }
    groups = []

    for experience in get_all_experiences():
        all_assets = [
            asset
            for asset in get_experience_assets(experience["id"])
            if asset.get("include_in_interview")
        ]
        experience_text = " ".join(
            str(experience.get(key) or "")
            for key in ("organization", "role", "skills", "summary_zh", "description")
        ).lower()
        relevant_assets = []
        matched_competencies = set()
        for asset in all_assets:
            asset_text = " ".join(
                str(asset.get(key) or "")
                for key in (
                    "title",
                    "overview_summary",
                    "skills",
                    "interview_angles",
                    "interview_questions",
                    "star_situation",
                    "star_task",
                    "star_action",
                    "star_result",
                )
            ).lower()
            combined_text = f"{experience_text} {asset_text}"
            competency_hits = {}
            asset_score = 0
            for competency, jd_keywords in jd_keyword_map.items():
                hits = [keyword for keyword in jd_keywords if keyword in combined_text]
                if not hits:
                    continue
                competency_hits[competency] = hits
                hit_weights = []
                for keyword in hits:
                    compact_length = len(keyword.replace(" ", ""))
                    hit_weights.append(3 if compact_length >= 4 else 2 if compact_length >= 3 else 1)
                asset_score += max(hit_weights) * jd_competency_weights.get(competency, 1)
            if asset_score > 0:
                enriched_asset = dict(asset)
                enriched_asset["_iw_matches"] = sorted(competency_hits)
                enriched_asset["_iw_score"] = asset_score
                relevant_assets.append(enriched_asset)
                matched_competencies.update(competency_hits)
        score = sum(asset.get("_iw_score", 0) for asset in relevant_assets)
        groups.append(
            {
                "experience": experience,
                "assets": relevant_assets,
                "matches": sorted(matched_competencies)[:8],
                "score": score,
            }
        )

    all_scores = [asset.get("_iw_score", 0) for group in groups for asset in group["assets"]]
    if all_scores:
        relevance_threshold = max(3, round(max(all_scores) * 0.45))
        for group in groups:
            group["assets"] = [
                asset for asset in group["assets"]
                if asset.get("_iw_score", 0) >= relevance_threshold
            ]
            group["score"] = sum(asset.get("_iw_score", 0) for asset in group["assets"])
            group["matches"] = sorted(
                {match for asset in group["assets"] for match in asset.get("_iw_matches", [])}
            )[:8]
    groups = [group for group in groups if group["assets"] and group["score"] > 0]
    groups.sort(
        key=lambda group: (
            group["score"],
            group["experience"].get("start_date") or "",
        ),
        reverse=True,
    )
    return groups


def _question_bank(groups):
    questions = []
    seen = set()
    for group in groups:
        experience = group["experience"]
        for asset in group["assets"]:
            for question in _lines(asset.get("interview_questions")):
                marker = question.lower()
                if marker in seen:
                    continue
                seen.add(marker)
                questions.append(
                    {
                        "question": question,
                        "organization": experience.get("organization"),
                        "source": asset.get("asset_code"),
                        "title": asset.get("title"),
                        "experience": experience,
                        "asset": asset,
                    }
                )
    return questions


def _story_bank(groups):
    stories = []
    for group in groups:
        experience = group["experience"]
        for asset in group["assets"]:
            if not any(
                asset.get(key)
                for key in ("star_situation", "star_task", "star_action", "star_result")
            ):
                continue
            stories.append(
                {
                    "organization": experience.get("organization"),
                    "source": asset.get("asset_code"),
                    "title": asset.get("title"),
                    "s": asset.get("star_situation"),
                    "t": asset.get("star_task"),
                    "a": asset.get("star_action"),
                    "r": asset.get("star_result"),
                    "followups": _lines(asset.get("interview_followups")),
                    "risk": asset.get("interview_risks") or asset.get("expression_limits"),
                }
            )
    return stories


def _read_transcript_file(uploaded_file):
    suffix = Path(uploaded_file.name or "").suffix.lower()
    data = uploaded_file.getvalue()
    if suffix in {".txt", ".md"}:
        for encoding in ("utf-8-sig", "utf-8", "gb18030"):
            try:
                return data.decode(encoding).strip()
            except UnicodeDecodeError:
                continue
        raise ValueError("无法识别文稿编码，请另存为 UTF-8 文本后重试。")
    if suffix == ".docx":
        with zipfile.ZipFile(BytesIO(data)) as archive:
            document = archive.read("word/document.xml")
        root = ElementTree.fromstring(document)
        namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
        paragraphs = []
        for paragraph in root.iter(f"{namespace}p"):
            text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
            if text.strip():
                paragraphs.append(text.strip())
        return "\n".join(paragraphs)
    raise ValueError("目前支持 TXT、Markdown 和 DOCX 文稿。")


def _review_prompt(job, session, transcript):
    return f"""你是一名严谨的面试复盘助手。请只依据下方逐字稿提取信息，不补写、不猜测、不美化。

岗位：{job.get('company') or ''}｜{job.get('position') or ''}
面试轮次：{session.get('round_name') or ''}
面试日期：{session.get('interview_date') or '未设置'}

请按以下结构输出：
1. 面试官提出的问题（按出现顺序）
2. 我的回答要点，以及使用的真实经历、事实和数字
3. 回答得比较清楚的部分
4. 回答含糊、遗漏、前后不一致或缺少证据的部分
5. 面试官的追问、关注点和可能的顾虑
6. 本轮暴露出的能力缺口与表达问题
7. 下一轮需要补充的事实、案例和准备动作
8. 可以沉淀到 Experience Bank 的 Story Fragments（只列候选，等待本人确认）

每条结论尽量附上逐字稿中的原句或时间顺序依据。无法确认的内容标记为“无法从逐字稿确认”。

【面试逐字稿】
{transcript.strip()}
"""


def _jd_competencies(job):
    jd = " ".join(
        str(job.get(key) or "")
        for key in ("position", "target_direction", "job_description", "details")
    )
    return _detect_competencies(jd)


ANSWER_PRINCIPLES = [
    "先直接回答问题，再补充背景，不绕圈。",
    "只使用已经确认的真实事实，不为了完整而补写。",
    "背景保持简短，把时间留给自己的行动与判断。",
    "明确区分团队成果和个人贡献。",
    "行为题优先使用 STAR：情境、任务、行动、结果。",
    "数字只使用可核验口径，并准备解释统计范围。",
    "回答必须连接岗位能力，而不是只讲经历经过。",
    "主动说明限制、失败和复盘，体现真实学习过程。",
    "提前准备连续追问，确保细节前后一致。",
    "结尾用一句话总结价值，并回到目标岗位。",
]


def _navigate_to_studio(active, source=""):
    """Navigate inside Interview Studio without starting a new browser session."""
    st.session_state["iw_active"] = active
    st.session_state["iw_requested_source"] = source


def _render_flow_nav(active, question_total, story_total):
    steps = [
        ("focus", "01", "jd analysis", "直接读取当前 JD"),
        ("questions", "02", "question match", f"{question_total} 个候选问题"),
        ("blueprint", "03", "answer method", f"{story_total} 个真实故事"),
        ("sessions", "04", "practice & review", "导入文稿并复盘"),
    ]
    st.markdown(
        f"""
        <style>
        .st-key-iw_flow_{active} [data-testid="stButton"] button {{
            border-color: rgba(17,17,17,.18) !important;
            background: var(--iw-purple) !important;
            color: #171717 !important;
            box-shadow: 0 10px 24px rgba(30,30,30,.045) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    columns = st.columns(4, gap="small")
    for column, (key, number, title, meta) in zip(columns, steps):
        with column:
            with st.container(key=f"iw_flow_{key}"):
                st.button(
                    f"{number}　{title}\n\n{meta}",
                    key=f"iw_flow_button_{key}",
                    on_click=_navigate_to_studio,
                    args=(key,),
                    use_container_width=True,
                )


def _styles():
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&family=Noto+Sans+SC:wght@400;500;600;700&display=swap');
        :root {{
            --iw-bg: #fef5f5;
            --iw-panel: #fffafa;
            --iw-line: #f1e7e7;
            --iw-ink: #111111;
            --iw-muted: #858582;
            --iw-blue: {PASTELS['blue']};
            --iw-green: {PASTELS['green']};
            --iw-purple: {PASTELS['purple']};
            --iw-orange: {PASTELS['orange']};
        }}
        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            min-height: 100dvh !important;
            background: var(--iw-bg) !important;
        }}
        html, body, .stApp {{
            height: 100dvh !important;
        }}
        .stApp {{
            overflow: hidden !important;
        }}
        [data-testid="stAppViewContainer"] {{
            height: 100dvh !important;
            overflow-x: hidden !important;
            overflow-y: auto !important;
            overscroll-behavior-y: contain;
        }}
        header[data-testid="stHeader"] {{
            background: rgba(255,250,250,.96) !important;
        }}
        [data-testid="stMain"] {{
            padding: 56px 14px 18px !important;
            overflow: visible !important;
            box-sizing: border-box !important;
        }}
        .block-container, [data-testid="stMainBlockContainer"] {{
            width: 100% !important;
            max-width: none !important;
            min-height: calc(100dvh - 74px) !important;
            margin: 0 !important;
            padding: 42px clamp(24px,3vw,54px) 48px !important;
            overflow: visible !important;
            border: 1px solid var(--iw-line) !important;
            border-radius: clamp(38px,4vw,66px) !important;
            background: var(--iw-panel) !important;
            box-shadow: 0 20px 70px rgba(30,30,30,.055) !important;
            box-sizing: border-box !important;
        }}
        .iw-heading {{max-width:900px;margin:-46px auto 8px;text-align:center}}
        .iw-heading h1 {{margin:0;color:var(--iw-ink);font-family:'Gaegu','Comic Sans MS',cursive;font-size:clamp(3.2rem,5vw,5rem);font-weight:700;line-height:.93;letter-spacing:.04em;text-transform:lowercase}}
        .iw-heading p {{margin:13px 0 0;color:var(--iw-muted);font:600 clamp(.78rem,1vw,.95rem)/1.55 'Noto Sans SC',sans-serif}}
        .iw-role-card {{position:relative;min-height:218px;padding:22px 30px 24px;border-radius:28px;background:var(--iw-blue);overflow:hidden;box-shadow:0 18px 44px rgba(67,91,105,.08)}}
        .iw-role-card:after {{content:'';position:absolute;right:-70px;top:-95px;width:190px;height:190px;border:28px solid rgba(255,255,255,.3);border-radius:50%}}
        .iw-topline {{position:relative;z-index:2;display:grid;grid-template-columns:auto auto minmax(0,1fr) auto;align-items:center;gap:14px}}
        .iw-progress-label {{display:flex;align-items:center;justify-content:space-between;gap:18px}}
        .iw-pill {{display:inline-flex;padding:6px 12px;border-radius:99px;background:rgba(255,255,255,.62);font-size:10px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}}
        .iw-date {{position:relative;z-index:1;color:#4f606a;font-size:11px;font-weight:700}}
        .iw-company {{color:#5b7180;font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;white-space:nowrap}}
        .iw-topline h2 {{margin:0;font-family:'Noto Sans SC',sans-serif;font-size:clamp(1.15rem,1.55vw,1.45rem);line-height:1.3;font-weight:700;letter-spacing:-.02em}}
        .iw-round {{position:absolute;right:31px;top:78px;z-index:2;display:grid;place-items:center;width:62px;height:62px;border:1px solid rgba(17,17,17,.14);border-radius:50%;font-family:'Gaegu','Noto Sans SC',cursive;font-size:13px;font-weight:700;transform:rotate(5deg)}}
        .iw-progress-stack {{margin-top:24px}}
        .iw-progress {{max-width:620px;margin:0 0 14px}}
        .iw-progress-label {{margin-bottom:8px;font-size:12px}}
        .iw-progress-label b {{font-size:11px}}
        .iw-track {{height:9px;border-radius:99px;background:rgba(255,255,255,.52);overflow:hidden}}
        .iw-track i {{display:block;height:100%;border-radius:inherit;background:#171717}}
        .iw-note {{position:absolute;right:27px;bottom:20px;color:#778993;font:700 14px/1 'Gaegu','Noto Sans SC',cursive;transform:rotate(-3deg)}}
        .iw-next {{min-height:260px;padding:30px;border-radius:30px;background:var(--iw-purple);display:flex;flex-direction:column;justify-content:center;box-shadow:0 18px 44px rgba(79,66,101,.07);transform:rotate(-.5deg)}}
        .iw-kicker {{margin:0 0 9px;color:#7b718d;font-family:'Gaegu','Comic Sans MS',cursive;font-size:15px;line-height:1;font-weight:700;letter-spacing:.06em;text-transform:lowercase}}
        .iw-next h2,.iw-section-head h2,.iw-detail h2 {{margin:0;font-family:'Gaegu','Noto Sans SC',cursive;font-weight:700;line-height:1;text-transform:lowercase}}
        .iw-next h2 {{font-size:clamp(1.8rem,2.5vw,2.4rem)}}
        .iw-next p {{margin:13px 0 22px;color:#67606e;font-size:12px;line-height:1.65}}
        .iw-link {{display:flex;align-items:center;justify-content:space-between;padding:12px 17px;border-radius:99px;background:#171717;color:#fff!important;text-decoration:none!important;font-size:12px;font-weight:800}}
        .iw-link,.iw-link:link,.iw-link:visited,.iw-link:hover,.iw-link span {{color:#fff!important}}
        .iw-section-head {{display:flex;align-items:end;justify-content:space-between;gap:20px;margin:34px 0 16px}}
        .iw-section-head h2 {{font-size:1.9rem}}
        .iw-section-head p {{margin:0;color:#96928e;font-size:10px}}
        .iw-workspace {{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}}
        .iw-workspace-card {{min-height:176px;padding:18px;border:1px solid transparent;border-radius:21px;display:flex;flex-direction:column;color:#171717!important;text-decoration:none!important;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}}
        .iw-workspace-card:hover,.iw-workspace-card.active {{transform:translateY(-4px);border-color:rgba(17,17,17,.18);box-shadow:0 14px 32px rgba(30,30,30,.055)}}
        .iw-workspace-card.blue {{background:var(--iw-blue)}}.iw-workspace-card.purple {{background:var(--iw-purple)}}.iw-workspace-card.orange {{background:var(--iw-orange)}}.iw-workspace-card.green {{background:var(--iw-green)}}
        .iw-card-number {{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;background:rgba(255,255,255,.7);font-size:9px;font-weight:800}}
        .iw-card-title {{margin:24px 0 7px;font-family:'Gaegu','Noto Sans SC',cursive;font-size:1.45rem;line-height:1;font-weight:700;text-transform:lowercase}}
        .iw-workspace-card p {{margin:0;color:#666;font-size:10px;line-height:1.5}}
        .iw-card-meta {{margin-top:auto;color:#666;font-size:9px;font-weight:800;letter-spacing:.06em;text-transform:uppercase}}
        .iw-subpage-head {{display:flex;align-items:flex-end;justify-content:space-between;gap:20px;margin:12px 0 22px;padding-bottom:20px;border-bottom:1px solid var(--iw-line)}}
        .iw-subpage-head h2 {{margin:4px 0 0;font-family:'Gaegu','Noto Sans SC',cursive;font-size:clamp(1.75rem,2.4vw,2.35rem);line-height:1;text-transform:lowercase}}
        .iw-subpage-head p {{margin:10px 0 0;color:#777;font-size:11px;line-height:1.6}}
        .iw-back {{display:inline-flex;align-items:center;gap:8px;padding:10px 15px;border:1px solid var(--iw-line);border-radius:999px;background:#fff;color:#171717!important;text-decoration:none!important;font-size:10px;font-weight:800;white-space:nowrap}}
        .iw-context {{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px;padding:14px 18px;border-radius:17px;background:var(--iw-blue)}}
        .iw-context b {{font-size:12px}}.iw-context span {{color:#697780;font-size:10px}}
        .iw-flow {{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:0 0 24px}}
        .iw-flow-step {{display:flex;align-items:center;gap:10px;min-height:66px;padding:11px 13px;border:1px solid var(--iw-line);border-radius:16px;background:#fff;color:#171717!important;text-decoration:none!important}}
        .iw-flow-step>span {{display:grid;place-items:center;min-width:29px;height:29px;border-radius:9px;background:#f5efef;font-size:9px;font-weight:800}}
        .iw-flow-step b {{display:block;font-family:'Gaegu','Noto Sans SC',cursive;font-size:1.05rem;line-height:1;text-transform:lowercase}}
        .iw-flow-step small {{display:block;margin-top:5px;color:#8c8884;font-size:8px}}
        .iw-flow-step.active {{border-color:rgba(17,17,17,.18);background:var(--iw-purple);box-shadow:0 10px 24px rgba(30,30,30,.045)}}
        [class*="st-key-iw_flow_"] [data-testid="stButton"] button {{min-height:66px;padding:11px 13px;border:1px solid var(--iw-line)!important;border-radius:16px;background:#fff!important;color:#171717!important;text-align:left;white-space:pre-line;box-shadow:none!important}}
        [class*="st-key-iw_flow_"] [data-testid="stButton"] button:hover {{border-color:rgba(17,17,17,.18)!important;color:#171717!important}}
        [class*="st-key-iw_workspace_"] [data-testid="stButton"] button {{min-height:176px;padding:18px;border:1px solid transparent!important;border-radius:21px;color:#171717!important;text-align:left;white-space:pre-line;box-shadow:none!important;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}}
        [class*="st-key-iw_workspace_"] [data-testid="stButton"] button:hover {{transform:translateY(-4px);border-color:rgba(17,17,17,.18)!important;color:#171717!important;box-shadow:0 14px 32px rgba(30,30,30,.055)!important}}
        .st-key-iw_workspace_focus [data-testid="stButton"] button {{background:var(--iw-blue)!important}}
        .st-key-iw_workspace_questions [data-testid="stButton"] button {{background:var(--iw-purple)!important}}
        .st-key-iw_workspace_blueprint [data-testid="stButton"] button {{background:var(--iw-orange)!important}}
        .st-key-iw_workspace_sessions [data-testid="stButton"] button {{background:var(--iw-green)!important}}
        .st-key-iw_back [data-testid="stButton"] button {{border:1px solid var(--iw-line);border-radius:999px;background:#fff;color:#171717;white-space:nowrap}}
        .iw-source {{margin:10px 0 18px;padding:13px 15px;border-radius:14px;background:#fff;border:1px solid var(--iw-line);color:#777;font-size:10px;line-height:1.6}}
        .iw-guidance {{margin:14px 0;padding:18px 20px;border-radius:18px;background:var(--iw-orange);font-size:11px;line-height:1.75}}
        .iw-guidance b {{display:block;margin-bottom:4px;font-family:'Gaegu','Noto Sans SC',cursive;font-size:1.25rem}}
        .iw-principles {{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin-top:12px}}
        .iw-principle {{display:flex;gap:9px;padding:11px 12px;border:1px solid var(--iw-line);border-radius:13px;background:#fff;color:#555;font-size:10px;line-height:1.55}}
        .iw-principle span {{font-weight:800;color:#111}}
        .iw-stage-grid {{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:9px;margin-top:15px}}
        .iw-stage {{padding:13px 10px;border-radius:14px;background:#fff;border:1px solid var(--iw-line);font-size:9px;line-height:1.45;text-align:center}}
        .iw-detail {{margin-top:18px;padding:27px 29px;border:1px solid var(--iw-line);border-radius:24px;background:rgba(255,255,255,.66)}}
        .iw-detail h2 {{font-size:2rem;margin-bottom:8px}}
        .iw-detail-copy {{margin:0 0 20px;color:#777;font-size:11px;line-height:1.65}}
        .iw-list {{border-top:1px solid #ece7e7}}
        .iw-list-row {{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:12px;align-items:center;padding:14px 2px;border-bottom:1px solid #ece7e7}}
        .iw-list-row>span:first-child {{color:#999;font-size:9px}}
        .iw-list-row b {{font-size:12px;line-height:1.5}}
        .iw-list-row small {{color:#8c8c88;font-size:9px;text-align:right}}
        .iw-story-grid {{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}
        .iw-story {{padding:17px;border:1px solid #ece6e4;border-radius:16px;background:#fff}}
        .iw-story h3 {{margin:0 0 5px;font-size:12px}}
        .iw-story>small {{color:#888;font-size:9px}}
        .iw-star {{margin-top:12px;display:grid;gap:7px}}
        .iw-star p {{margin:0;color:#555;font-size:10px;line-height:1.55}}
        .iw-star b {{display:inline-grid;place-items:center;width:18px;height:18px;margin-right:5px;border-radius:6px;background:var(--iw-orange);font-size:9px}}
        .iw-empty {{padding:28px;border:1px dashed #d9d0d0;border-radius:17px;background:#fff;color:#777;font-size:11px;line-height:1.7;text-align:center}}
        @media(max-width:1050px) {{.iw-workspace{{grid-template-columns:repeat(2,1fr)}}.iw-story-grid{{grid-template-columns:1fr}}.iw-stage-grid{{grid-template-columns:repeat(3,1fr)}}.iw-flow{{grid-template-columns:repeat(2,1fr)}}}}
        @media(max-width:760px) {{[data-testid="stMain"]{{padding:48px 8px 12px!important}}.block-container,[data-testid="stMainBlockContainer"]{{padding:46px 16px 28px!important;border-radius:34px!important}}.iw-heading{{margin:-20px auto 20px}}.iw-workspace{{grid-template-columns:1fr}}.iw-topline{{grid-template-columns:auto 1fr auto}}.iw-topline h2{{grid-column:1/-1;margin-top:3px}}.iw-round{{display:none}}.iw-note{{display:none}}.iw-subpage-head{{align-items:flex-start;flex-direction:column-reverse}}.iw-context{{align-items:flex-start;flex-direction:column}}.iw-stage-grid{{grid-template-columns:1fr 1fr}}.iw-flow{{grid-template-columns:1fr}}.iw-principles{{grid-template-columns:1fr}}}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_role_focus(job, groups):
    related = [group for group in groups if group["assets"]][:6]
    jd_text = job.get("job_description") or job.get("details") or "当前岗位还没有完整 JD。"
    competencies = _jd_competencies(job)
    theme_rows = "".join(
        f'<div class="iw-list-row"><span>{index:02d}</span><b>{_safe(item["name"])}</b><small>JD 依据：{_safe(" · ".join(item["evidence"]))}</small></div>'
        for index, item in enumerate(competencies[:8], 1)
    )
    st.markdown(
        '<div class="iw-detail"><h2>role map</h2>'
        f'<div class="iw-source"><b>JD 摘要</b><br>{_safe(jd_text[:1200])}</div>'
        f'<div class="iw-list">{theme_rows or "<div class=\"iw-empty\">暂未识别到明确的能力关键词。</div>"}</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    if not related:
        st.info("Experience Bank 中暂时没有可用于匹配的面试经历；JD 能力分析仍可正常查看。")
    st.button(
        "下一步：查看高频问题与经历匹配　→",
        key="iw_focus_next",
        on_click=_navigate_to_studio,
        args=("questions",),
        use_container_width=True,
        type="primary",
    )


def _render_questions(job, questions):
    if not questions:
        st.markdown('<div class="iw-empty">当前经历素材中还没有已确认的预测问题。</div>', unsafe_allow_html=True)
        return

    st.markdown(
        '<div class="iw-guidance"><b>问题不是孤立题库。</b>'
        '每个条目同时展示：为什么会问、最适合使用的真实经历、可用事实、连续追问和表达边界。</div>',
        unsafe_allow_html=True,
    )
    organizations = sorted({question.get("organization") or "未标注经历" for question in questions})
    selected_org = st.selectbox("按经历来源筛选", ["全部经历"] + organizations, key=f"iw_question_org_{job['id']}")
    filtered = questions if selected_org == "全部经历" else [q for q in questions if (q.get("organization") or "未标注经历") == selected_org]
    display_count = st.radio(
        "显示问题",
        ["Top 10", "Top 20"],
        horizontal=True,
        key=f"iw_question_limit_{job['id']}",
    )
    limit = 10 if display_count == "Top 10" else 20
    for index, question in enumerate(filtered[:limit], 1):
        experience = question.get("experience") or {}
        asset = question.get("asset") or {}
        with st.expander(f'{index:02d}｜{question["question"]}', expanded=index == 1):
            st.markdown(
                f'<div class="iw-source"><b>推荐经历</b><br>{_safe(experience.get("organization"))}｜{_safe(experience.get("role"))}<br>'
                f'{_safe(experience.get("summary_zh") or experience.get("description"), "暂未填写经历摘要")}</div>'
                f'<div class="iw-source"><b>可用条目</b><br>{_safe(question.get("source"), "EXP")}｜{_safe(question.get("title"))}</div>'
                f'<div class="iw-source"><b>回答角度</b><br>{_safe(asset.get("interview_angles"), "围绕个人行动、判断和可核验结果回答。")}</div>'
                f'<div class="iw-source"><b>连续追问</b><br>{_safe("；".join(_lines(asset.get("interview_followups"))), "暂未记录连续追问")}</div>'
                f'<div class="iw-source"><b>表达边界</b><br>{_safe(asset.get("interview_risks") or asset.get("expression_limits"), "只使用已确认事实，不补写结果。")}</div>',
                unsafe_allow_html=True,
            )
            marker = abs(hash(question.get("question")))
            st.checkbox("这道题已完成经历选择", key=f"iw_prepared_{job['id']}_{marker}")
            st.button(
                "用这段经历组织回答　→",
                key=f"iw_question_to_blueprint_{job['id']}_{marker}",
                on_click=_navigate_to_studio,
                args=("blueprint", str(question.get("source") or "")),
                use_container_width=True,
                type="primary",
            )


def _render_blueprints(job, stories):
    if not stories:
        st.markdown('<div class="iw-empty">当前还没有完整的 STAR 经历素材，请先在 Experience Bank 中补充事实。</div>', unsafe_allow_html=True)
        return

    st.markdown(
        '<div class="iw-guidance"><b>先选方法，再组织答案。</b>'
        '行为题使用 STAR；观点和动机题使用 PREP；案例题先拆问题、再给证据与建议。</div>',
        unsafe_allow_html=True,
    )
    labels = {f'{story.get("source") or "EXP"}｜{story.get("title") or "未命名故事"}': story for story in stories}
    requested_source = st.session_state.get("iw_requested_source", "")
    if not requested_source:
        requested_source = st.query_params.get("source", "")
        if isinstance(requested_source, list):
            requested_source = requested_source[0] if requested_source else ""
    label_list = list(labels)
    default_index = next((i for i, label in enumerate(label_list) if label.startswith(f"{requested_source}｜")), 0)
    selected = st.selectbox("选择一个真实故事", label_list, index=default_index, key=f"iw_story_{job['id']}")
    story = labels[selected]
    method = st.selectbox(
        "选择回答方法",
        ["STAR｜行为经历题", "PREP｜观点与动机题", "结构化分析｜案例与情景题"],
        key=f"iw_answer_method_{job['id']}",
    )
    method_copy = {
        "STAR｜行为经历题": "Situation 交代必要背景 → Task 明确目标与责任 → Action 重点讲个人判断和行动 → Result 给出可核验结果与复盘。",
        "PREP｜观点与动机题": "Point 先给结论 → Reason 说明原因 → Example 用真实经历举证 → Point 回到岗位与问题。",
        "结构化分析｜案例与情景题": "先澄清目标和限制 → 拆分问题 → 提出假设 → 用证据验证 → 给出建议、风险和下一步。",
    }
    st.info(method_copy[method])
    star_rows = []
    for key, label in (("s", "S"), ("t", "T"), ("a", "A"), ("r", "R")):
        star_rows.append(f'<p><b>{label}</b>{_safe(story.get(key), "待补充")}</p>')
    followups = "；".join(story.get("followups") or []) or "当前素材还没有连续追问"
    st.markdown(
        '<div class="iw-detail"><h2>star answer structure</h2>'
        f'<p class="iw-detail-copy">{_safe(story.get("organization"))} · {_safe(story.get("source"), "EXP")}</p>'
        f'<div class="iw-star">{"".join(star_rows)}</div>'
        f'<div class="iw-source"><b>连续追问</b><br>{_safe(followups)}</div>'
        f'<div class="iw-source"><b>表达边界 / 风险</b><br>{_safe(story.get("risk"), "暂未标注")}</div></div>',
        unsafe_allow_html=True,
    )
    st.text_area("我的口语版回答", key=f"iw_story_notes_{job['id']}_{abs(hash(selected))}", placeholder="基于上方事实，整理成你自己的口语表达……", height=160)
    st.checkbox("这段故事已完成口语练习", key=f"iw_story_practiced_{job['id']}_{abs(hash(selected))}")
    with st.expander("查看 10 条回答原则", expanded=False):
        principles = "".join(
            f'<div class="iw-principle"><span>{index:02d}</span><div>{_safe(principle)}</div></div>'
            for index, principle in enumerate(ANSWER_PRINCIPLES, 1)
        )
        st.markdown(f'<div class="iw-principles">{principles}</div>', unsafe_allow_html=True)
    st.button(
        "下一步：开始练习、录音与复盘　→",
        key="iw_blueprint_next",
        on_click=_navigate_to_studio,
        args=("sessions",),
        use_container_width=True,
        type="primary",
    )


def _render_sessions(job):
    st.markdown(
        '<div class="iw-detail"><h2>interview sessions</h2>'
        '<p class="iw-detail-copy">不在 CareerPilot 内录音。你可以使用任意平台录音和转写，再把文稿导入这里完成复盘。</p>'
        '<div class="iw-stage-grid"><div class="iw-stage">01<br><b>Session</b></div><div class="iw-stage">02<br><b>Import Transcript</b></div><div class="iw-stage">03<br><b>Review Template</b></div><div class="iw-stage">04<br><b>Findings</b></div><div class="iw-stage">05<br><b>Next Round</b></div></div></div>',
        unsafe_allow_html=True,
    )

    with st.expander("＋ 新建面试轮次", expanded=False):
        round_col, date_col = st.columns([1.4, 1])
        with round_col:
            round_name = st.text_input(
                "轮次名称",
                placeholder="例如：HR Screening / Hiring Manager Interview",
                key=f"iw_new_round_{job['id']}",
            )
        with date_col:
            round_date = st.text_input(
                "面试日期",
                value=job.get("interview_date") or "",
                placeholder="YYYY-MM-DD",
                key=f"iw_new_round_date_{job['id']}",
            )
        if st.button("创建 Interview Session", key=f"iw_create_session_{job['id']}", type="primary"):
            if not round_name.strip():
                st.warning("请先填写轮次名称。")
            else:
                create_interview_session(job["id"], round_name, round_date)
                st.success("面试轮次已创建。")
                st.rerun()

    sessions = get_interview_sessions(job["id"])
    if not sessions:
        st.markdown(
            '<div class="iw-empty">还没有面试轮次。请先创建一轮面试，结束后再导入转写文稿。</div>',
            unsafe_allow_html=True,
        )
        return

    session_labels = {
        f'{item.get("round_name") or "未命名轮次"} · {item.get("interview_date") or "日期待定"} · {item.get("status") or "准备中"} · #{item["id"]}': item
        for item in sessions
    }
    selected_label = st.selectbox(
        "选择面试轮次",
        list(session_labels),
        key=f"iw_session_select_{job['id']}",
    )
    session = session_labels[selected_label]
    session_id = session["id"]

    transcript_key = f"iw_transcript_{session_id}"
    if transcript_key not in st.session_state:
        st.session_state[transcript_key] = session.get("transcript") or ""
    with st.expander("1. 导入或粘贴面试文稿", expanded=not bool(st.session_state[transcript_key].strip())):
        uploaded_document = st.file_uploader(
            "导入转写文稿",
            type=["txt", "md", "docx"],
            key=f"iw_transcript_upload_{session_id}",
            help="支持 TXT、Markdown 和 DOCX；也可以直接粘贴到下方文字框。",
        )
        if uploaded_document is not None and st.button("读取这份文稿", key=f"iw_import_transcript_{session_id}"):
            try:
                imported_text = _read_transcript_file(uploaded_document)
                st.session_state[transcript_key] = imported_text
                st.success("文稿已读取，请校对后保存。")
            except Exception as error:
                st.error(str(error))
        transcript = st.text_area(
            "面试逐字稿（可编辑）",
            key=transcript_key,
            height=300,
            placeholder="把其他平台生成的逐字稿粘贴到这里……",
        )
        save_text_col, download_text_col = st.columns(2)
        with save_text_col:
            if st.button("保存本轮文稿", key=f"iw_save_transcript_{session_id}", use_container_width=True):
                update_interview_session(session_id, transcript=transcript, status="文稿已导入" if transcript.strip() else "准备中")
                st.success("文稿已保存。")
        with download_text_col:
            st.download_button(
                "下载文稿 .txt",
                data=transcript,
                file_name=f"interview_transcript_{session_id}.txt",
                mime="text/plain",
                key=f"iw_download_transcript_{session_id}",
                use_container_width=True,
                disabled=not transcript.strip(),
            )

    prompt_key = f"iw_review_prompt_{session_id}"
    if prompt_key not in st.session_state:
        st.session_state[prompt_key] = session.get("extraction_prompt") or ""
    transcript = st.session_state[transcript_key]
    with st.expander("2. 生成可复制的复盘模板", expanded=bool(transcript.strip()) and not bool(st.session_state[prompt_key])):
        st.caption("这是可选步骤：CareerPilot 不调用付费 AI，只整理一份带岗位和逐字稿的复盘指令，供你复制到任意工具。")
        if st.button(
            "生成复盘模板",
            key=f"iw_generate_prompt_{session_id}",
            disabled=not transcript.strip(),
        ):
            prompt = _review_prompt(job, session, transcript)
            st.session_state[prompt_key] = prompt
            update_interview_session(session_id, transcript=transcript, extraction_prompt=prompt, status="待复盘")
            st.success("复盘模板已生成。")
        if st.session_state[prompt_key]:
            st.code(st.session_state[prompt_key], language=None)
            st.caption("代码框右上角可以一键复制。")

    review_key = f"iw_review_result_{session_id}"
    if review_key not in st.session_state:
        st.session_state[review_key] = session.get("review_notes") or ""
    with st.expander("3. 保存复盘结论与下一轮动作", expanded=bool(st.session_state[prompt_key]) and not bool(st.session_state[review_key])):
        review_notes = st.text_area(
            "复盘结论",
            key=review_key,
            height=260,
            placeholder="粘贴提炼结果，或直接记录：回答亮点、表达缺口、需要补充的事实和下一轮动作。",
        )
        if st.button("保存本轮复盘", key=f"iw_save_review_{session_id}", disabled=not review_notes.strip()):
            update_interview_session(session_id, review_notes=review_notes, status="已复盘")
            st.success("本轮复盘已保存。")


def _render_subpage_header(active, job, question_total, story_total):
    copy = {
        "focus": ("JD ANALYSIS", "start with the role", "直接读取当前 JD，识别岗位能力主题。"),
        "questions": ("QUESTION MATCH", "question → experience", "高频问题与 Experience Bank 经历逐条关联。"),
        "blueprint": ("ANSWER METHOD", "build one clear answer", "选择真实故事、回答方法和表达原则。"),
        "sessions": ("PRACTICE & REVIEW", "import, reflect, improve", "导入外部转写文稿，完成复盘与下一轮准备。"),
    }
    kicker, title, description = copy[active]
    heading_column, back_column = st.columns([5, 1.4], vertical_alignment="bottom")
    with heading_column:
        st.markdown(
            f'<div class="iw-subpage-head"><div><span class="iw-kicker">{kicker}</span><h2>{title}</h2><p>{description}</p></div></div>',
            unsafe_allow_html=True,
        )
    with back_column:
        with st.container(key="iw_back"):
            st.button(
                "← 返回 Interview Studio",
                key="iw_back_button",
                on_click=_navigate_to_studio,
                args=("home",),
                use_container_width=True,
            )
    st.markdown(
        f'<div class="iw-context"><b>{_safe(job.get("company"))}｜{_safe(job.get("position"))}</b>'
        f'<span>{question_total} 个岗位相关问题 · {story_total} 个相关 STAR 故事 · {_safe(job.get("pipeline_stage") or job.get("status") or "准备中")}</span></div>',
        unsafe_allow_html=True,
    )


def render_interview_workspace(jobs):
    _styles()
    if not jobs:
        st.warning("请先在“职位申请”中创建目标岗位。")
        return

    st.markdown(
        '<div class="iw-heading"><h1>interview studio</h1></div>',
        unsafe_allow_html=True,
    )

    job_labels = {f'{job["company"]}｜{job["position"]}': job for job in jobs}
    selected_label = st.selectbox("选择目标岗位 / JD", list(job_labels), key="iw_job")
    job = job_labels[selected_label]
    groups = _experience_groups(job)
    questions = _question_bank(groups)
    stories = _story_bank(groups)
    stage = job.get("pipeline_stage") or job.get("status") or "准备中"
    interview_date = job.get("interview_date") or "日期待定"
    question_total = len(questions)
    story_total = len(stories)
    question_width = min(100, max(8, question_total * 7))
    story_width = min(100, max(8, story_total * 10))

    if "iw_active" not in st.session_state:
        requested_studio = st.query_params.get("studio", "home")
        if isinstance(requested_studio, list):
            requested_studio = requested_studio[0] if requested_studio else "home"
        st.session_state["iw_active"] = requested_studio
    active = st.session_state["iw_active"]
    if active not in {"home", "focus", "questions", "blueprint", "sessions"}:
        active = "home"
        st.session_state["iw_active"] = active

    if active != "home":
        _render_subpage_header(active, job, question_total, story_total)
        _render_flow_nav(active, question_total, story_total)
        if active == "focus":
            _render_role_focus(job, groups)
        elif active == "questions":
            _render_questions(job, questions)
        elif active == "blueprint":
            _render_blueprints(job, stories)
        else:
            _render_sessions(job)
        return

    st.markdown(
        f"""
        <section class="iw-role-card">
          <div class="iw-topline"><span class="iw-pill">{_safe(stage)}</span><span class="iw-company">{_safe(job.get('company'))}</span><h2>{_safe(job.get('position'))}</h2><span class="iw-date">{_safe(interview_date)}</span></div>
          <span class="iw-round">当前轮次</span>
          <div class="iw-progress-stack"><div class="iw-progress"><div class="iw-progress-label"><span>可用预测问题</span><b>{question_total}</b></div><div class="iw-track"><i style="width:{question_width}%"></i></div></div>
          <div class="iw-progress"><div class="iw-progress-label"><span>可用 STAR 经历</span><b>{story_total}</b></div><div class="iw-track"><i style="width:{story_width}%"></i></div></div></div>
          <span class="iw-note">linked to your real experience</span>
        </section>
        """,
        unsafe_allow_html=True,
    )

    cards = [
        ("focus", "01", "jd analysis", "直接读取当前 JD，识别岗位能力与面试重点。", "准备起点", "blue"),
        ("questions", "02", "question match", "高频问题逐条连接 Experience Bank 真实经历。", f"{question_total} 个问题", "purple"),
        ("blueprint", "03", "answer method", "选择 STAR、PREP 等方法，并遵循 10 条回答原则。", f"{story_total} 个故事", "orange"),
        ("sessions", "04", "practice & review", "导入外部转写文稿，保存复盘和下一轮动作。", "无需录音 API", "green"),
    ]
    st.markdown(
        '<div class="iw-section-head"><div><p class="iw-kicker">PREPARATION FLOW</p><h2>follow one clear path</h2></div>'
        '<p>从 01 开始，按顺序完成</p></div>',
        unsafe_allow_html=True,
    )
    columns = st.columns(4, gap="small")
    for column, (key, number, title, description, meta, _tone) in zip(columns, cards):
        with column:
            with st.container(key=f"iw_workspace_{key}"):
                st.button(
                    f"{number}　{title}\n\n{description}\n\n{meta}",
                    key=f"iw_workspace_button_{key}",
                    on_click=_navigate_to_studio,
                    args=(key,),
                    use_container_width=True,
                )
