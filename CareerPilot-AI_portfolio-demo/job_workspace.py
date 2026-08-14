from __future__ import annotations

import hashlib
import html
import re
from datetime import date, datetime, time
from typing import Any
from urllib.parse import quote

import streamlit as st

from demo_database import (
    get_job_applications,
    save_job_application,
    update_application_interview_notes,
    update_application_stage_event,
    update_application_termination_notes,
    update_application_timeline_node,
    update_job_application_details,
    update_job_application_progress,
)


PIPELINE_STAGES = [
    "投递简历",
    "笔试测评",
    "群面",
    "初试",
    "复试",
    "业务面",
    "HR面",
    "谈薪",
    "Offer",
]

CURRENT_STAGE_OPTIONS = ["准备投递", *PIPELINE_STAGES, "拒绝", "放弃"]
STAGE_STATE_OPTIONS = ["进行中", "已完成", "已跳过", "未通过", "已结束"]
PROGRESS_STATE_OPTIONS = ["准备中", "进行中", "已完成", "已结束"]
PROGRESS_STAGE_OPTIONS = ["准备投递", *PIPELINE_STAGES]

RESUME_STATUS_OPTIONS = [
    "尚未开始",
    "待分析JD",
    "正在定制",
    "待确认",
    "已完成",
]

INTERVIEW_PREP_OPTIONS = [
    "尚未开始",
    "待生成问题",
    "正在准备",
    "待模拟面试",
    "已完成",
]

PASTEL_BADGES = [
    ("#d9f1e1", "#237a4d"),
    ("#ffe4cf", "#a45c2a"),
    ("#eadcff", "#7150a7"),
    ("#dceefa", "#3276a4"),
    ("#ffe4ed", "#a94e70"),
    ("#fff0c7", "#8b6a16"),
]


# =========================================================
# Basic helpers
# =========================================================
def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _safe(value: Any, default: str = "") -> str:
    cleaned = _text(value) or default
    return html.escape(cleaned)


def _option_index(options: list[str], value: Any, default: int = 0) -> int:
    cleaned = _text(value)
    try:
        return options.index(cleaned)
    except ValueError:
        return default


def _format_job_description_html(value: Any) -> str:
    lines = [_text(line) for line in _text(value).replace("\r", "").split("\n")]
    blocks: list[dict[str, str]] = []
    separated = True

    for line in lines:
        if not line:
            separated = True
            continue

        numbered = re.match(r"^(\d+)[.、．]\s*(.+)$", line)
        bulleted = re.match(r"^[-•·▪]\s*(.+)$", line)
        is_heading = len(line) <= 32 and line.endswith(("：", ":"))

        if is_heading:
            blocks.append({"kind": "heading", "marker": "", "text": line.rstrip("：:")})
        elif numbered:
            blocks.append({"kind": "item", "marker": numbered.group(1), "text": numbered.group(2)})
        elif bulleted:
            blocks.append({"kind": "item", "marker": "•", "text": bulleted.group(1)})
        elif blocks and not separated and blocks[-1]["kind"] in {"item", "paragraph"}:
            blocks[-1]["text"] = f'{blocks[-1]["text"]} {line}'
        else:
            blocks.append({"kind": "paragraph", "marker": "", "text": line})

        separated = False

    if not blocks:
        return '<p class="jd-paragraph jd-empty">暂未保存岗位 JD</p>'

    rendered = []
    for block in blocks:
        text = _safe(block["text"])
        if block["kind"] == "heading":
            rendered.append(f'<h4 class="jd-heading">{text}</h4>')
        elif block["kind"] == "item":
            rendered.append(
                f'<div class="jd-item"><span class="jd-marker">{_safe(block["marker"])}</span><p>{text}</p></div>'
            )
        else:
            rendered.append(f'<p class="jd-paragraph">{text}</p>')
    return "".join(rendered)


def _normalise_date(value: str, label: str) -> str:
    cleaned = _text(value).replace("/", "-")
    if not cleaned:
        return ""

    try:
        datetime.strptime(cleaned, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"{label}需要使用 YYYY-MM-DD 格式。") from exc

    return cleaned


def _short_date(value: Any) -> str:
    cleaned = _text(value)
    if not cleaned:
        return ""
    try:
        return datetime.strptime(cleaned, "%Y-%m-%d").strftime("%m.%d")
    except ValueError:
        return cleaned[-5:].replace("-", ".")


def _validate_url(value: str) -> str:
    cleaned = _text(value)
    if cleaned and not cleaned.startswith(("http://", "https://")):
        raise ValueError("投递官网链接需要以 http:// 或 https:// 开头。")
    return cleaned


def _company_badge(company: str) -> tuple[str, str, str]:
    cleaned = _text(company) or "?"
    character = next((char for char in cleaned if char.isalnum()), "?").upper()
    digest = hashlib.sha1(cleaned.encode("utf-8")).hexdigest()
    background, foreground = PASTEL_BADGES[int(digest[:4], 16) % len(PASTEL_BADGES)]
    return character, background, foreground


def _event_map(job: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        _text(event.get("stage")): event
        for event in (job.get("stage_events") or [])
        if _text(event.get("stage"))
    }


def _overview_bucket(job: dict[str, Any]) -> str:
    application_state = _text(job.get("application_state"))
    if application_state == "ended":
        return "已结束"
    if application_state == "offer":
        return "谈薪 / Offer"
    stage = _text(job.get("status")) or "准备投递"
    if stage == "准备投递":
        return "准备投递"
    if stage in {"投递简历", "笔试测评"}:
        return "测评中"
    if stage in {"群面", "初试", "复试", "业务面", "HR面"}:
        return "面试中"
    if stage in {"谈薪", "Offer"}:
        return "谈薪 / Offer"
    if stage in {"拒绝", "放弃", "已结束"}:
        return "已结束"
    return "全部"


def _current_progress_text(job: dict[str, Any]) -> str:
    stage = _text(job.get("status")) or "准备投递"
    stage_state = _text(job.get("current_stage_status"))

    if _text(job.get("application_state")) == "ended" or stage == "已结束":
        ended_stage = _text(job.get("ended_stage"))
        return f"流程已结束 · {ended_stage}" if ended_stage else "流程已结束"

    if stage == "准备投递":
        return "准备投递"
    if stage == "拒绝":
        return "流程已结束 · 未通过"
    if stage == "放弃":
        return "流程已结束 · 已放弃"
    if stage == "Offer":
        return "已获得 Offer" if stage_state == "已完成" else "当前在 Offer 阶段"
    if stage_state == "已完成":
        try:
            next_stage = PIPELINE_STAGES[PIPELINE_STAGES.index(stage) + 1]
            return f"{stage}已完成 · 等待{next_stage}"
        except (ValueError, IndexError):
            return f"{stage}已完成"
    if stage_state == "已跳过":
        return f"{stage}已跳过"
    if stage_state == "未通过":
        return f"{stage}未通过"
    return f"当前在{stage}"


def _stage_visual(job: dict[str, Any], stage: str) -> tuple[str, str]:
    events = _event_map(job)
    event = events.get(stage)
    current_stage = _text(job.get("status"))
    if _text(job.get("application_state")) == "ended" and _text(job.get("ended_stage")):
        current_stage = _text(job.get("ended_stage"))

    # A job has exactly one visible frontier. This positional rule prevents
    # stale event rows from making two stages look active on the overview.
    if current_stage in PIPELINE_STAGES and stage in PIPELINE_STAGES:
        stage_index = PIPELINE_STAGES.index(stage)
        current_index = PIPELINE_STAGES.index(current_stage)
        date_text = _short_date(event.get("event_date")) if event else ""
        if stage_index < current_index:
            return "done", date_text
        if stage_index > current_index:
            return "upcoming", ""

    state = (
        _text(job.get("current_stage_status"))
        if stage == current_stage
        else _text(event.get("stage_status")) if event else ""
    )

    if state == "已完成":
        return "done", _short_date(event.get("event_date"))
    if state == "进行中":
        return "current", _short_date(event.get("event_date"))
    if state == "已跳过":
        return "skipped", _short_date(event.get("event_date"))
    if state == "未通过":
        return "failed", _short_date(event.get("event_date"))
    if state == "已结束":
        return "failed", _short_date(event.get("event_date"))
    if current_stage == stage:
        return "current", ""
    return "upcoming", ""


def _stage_state_for_job(job: dict[str, Any], stage: str) -> str:
    if stage in {"准备投递", "拒绝", "放弃"}:
        return "进行中"
    event = _event_map(job).get(stage)
    if event and _text(event.get("stage_status")) in STAGE_STATE_OPTIONS:
        return _text(event.get("stage_status"))
    existing = _text(job.get("current_stage_status"))
    return existing if existing in STAGE_STATE_OPTIONS else "进行中"


def _stage_date_for_job(job: dict[str, Any], stage: str) -> str:
    event = _event_map(job).get(stage)
    if event:
        return _text(event.get("event_date"))
    if stage == "投递简历":
        return _text(job.get("applied_date"))
    return ""


def _stage_notes_for_job(job: dict[str, Any], stage: str) -> str:
    event = _event_map(job).get(stage)
    return _text(event.get("notes")) if event else ""


def _parse_datetime(value: Any) -> datetime | None:
    cleaned = _text(value)
    if not cleaned:
        return None
    try:
        return datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.strptime(cleaned[:10], "%Y-%m-%d")
        except ValueError:
            return None


def _join_datetime(selected_date: date, selected_time: time) -> str:
    return datetime.combine(selected_date, selected_time).strftime("%Y-%m-%dT%H:%M")


def _display_datetime(value: Any) -> tuple[str, str]:
    parsed = _parse_datetime(value)
    if not parsed:
        return "时间待定", "收到通知后再添加"
    return parsed.strftime("%m月%d日"), parsed.strftime("%H:%M")


def _status_class(status: Any) -> str:
    return {
        "准备中": "preparing",
        "进行中": "active",
        "已完成": "completed",
        "已结束": "ended",
        "已跳过": "ended",
        "未通过": "ended",
    }.get(_text(status), "preparing")


# =========================================================
# Query-state handling
# =========================================================
def _consume_query_request() -> None:
    requested_mode = st.query_params.get("mode")
    if isinstance(requested_mode, list):
        requested_mode = requested_mode[0] if requested_mode else None

    mode_map = {
        "overview": "申请总览",
        "update": "更新申请",
        "new": "新增职位",
    }
    if requested_mode in mode_map:
        st.session_state["job_workspace_mode"] = mode_map[requested_mode]
        try:
            del st.query_params["mode"]
        except Exception:
            pass

    requested_job_id = st.query_params.get("job_id")
    if isinstance(requested_job_id, list):
        requested_job_id = requested_job_id[0] if requested_job_id else None
    if requested_job_id:
        try:
            st.session_state["job_workspace_requested_job_id"] = int(requested_job_id)
        except (TypeError, ValueError):
            pass
        try:
            del st.query_params["job_id"]
        except Exception:
            pass


def _consume_timeline_action() -> None:
    """Handle the two actions exposed by each overview timeline node."""
    action = st.query_params.get("timeline_action")
    job_id = st.query_params.get("timeline_job_id")
    stage = st.query_params.get("timeline_stage")
    if isinstance(action, list):
        action = action[0] if action else None
    if isinstance(job_id, list):
        job_id = job_id[0] if job_id else None
    if isinstance(stage, list):
        stage = stage[0] if stage else None
    if not (action and job_id and stage):
        return

    try:
        update_application_timeline_node(int(job_id), stage, action)
        if action == "end":
            st.session_state["expanded_termination_job_id"] = int(job_id)
            message = "流程已结束，请在职位卡片下方填写终止原因。"
        elif action == "undo":
            message = f"已撤销误操作，{stage}已恢复为进行中。"
        else:
            message = "时间线已更新。"
        st.session_state["job_workspace_toast"] = ("success", message)
    except Exception as error:
        st.session_state["job_workspace_toast"] = ("error", str(error))
    finally:
        for key in ("timeline_action", "timeline_job_id", "timeline_stage"):
            try:
                del st.query_params[key]
            except Exception:
                pass
    # The link navigation has already started a fresh Streamlit run. Running
    # st.rerun() here caused a second full redraw and made the page jump.
    # The job list is queried immediately after this handler, so the updated
    # state is rendered in this same run without another refresh.

# =========================================================
# Styling
# =========================================================
def _inject_workspace_css() -> None:
    st.markdown(
        r"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&family=Manrope:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap');

            :root {
                /* This workspace is intentionally light-only.  Declaring the
                   scheme prevents Safari/Chrome from repainting native form
                   controls when the OS or browser is using dark mode. */
                color-scheme: light only;
                --journey-bg: #fef5f5;
                --journey-panel: #fffafa;
                --journey-panel-line: #f1e7e7;
                --journey-ink: #141414;
                --journey-muted: #8b8b88;
                --journey-line: rgba(17,17,17,.09);
                --journey-mint: #d9f1e1;
                --journey-peach: #ffe4cf;
                --journey-violet: #eadcff;
                --journey-blue: #dceefa;
                --journey-green: #15945f;
            }

            html,
            body,
            .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stMain"] {
                color-scheme: light only !important;
                background: var(--journey-bg) !important;
                color: var(--journey-ink) !important;
            }

            .st-key-job_application_panel,
            .st-key-job_application_panel * {
                color-scheme: light only !important;
            }

            header[data-testid="stHeader"] {
                background: transparent !important;
            }

            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            [data-testid="collapsedControl"] {
                display: none !important;
            }

            /* Keep the shared sidebar as a fixed icon rail. */
            section[data-testid="stSidebar"],
            section[data-testid="stSidebar"]:hover,
            section[data-testid="stSidebar"]:focus-within {
                position: fixed !important;
                inset: 0 auto 0 0 !important;
                z-index: 999 !important;
                width: 80px !important;
                min-width: 80px !important;
                max-width: 80px !important;
                height: 100dvh !important;
                overflow: hidden !important;
                background: var(--journey-bg) !important;
                border-right: 1px solid transparent !important;
                box-shadow: none !important;
                transition: none !important;
            }

            section[data-testid="stSidebar"] > div,
            section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                width: 100% !important;
                width: 80px !important;
                min-width: 80px !important;
                max-width: 80px !important;
                height: 100% !important;
                overflow: hidden !important;
                background: transparent !important;
            }

            section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                padding: 26px 18px 24px !important;
            }

            [data-testid="stMain"] {
                margin-left: 80px !important;
                width: calc(100% - 80px) !important;
                transition: none !important;
            }

            .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"] {
                margin-left: 80px !important;
                width: calc(100% - 80px) !important;
            }

            .lum-sidebar-brand {
                width: 250px !important;
                height: 76px !important;
                padding: 8px 14px !important;
                color: var(--journey-ink) !important;
                font-family: 'Gaegu', cursive !important;
                font-size: 31px !important;
                line-height: 1 !important;
                font-weight: 700 !important;
                letter-spacing: .04em !important;
                white-space: nowrap !important;
            }

            section[data-testid="stSidebar"]:not(:hover) .lum-sidebar-brand {
                font-size: 0 !important;
                padding-left: 12px !important;
            }

            section[data-testid="stSidebar"]:not(:hover) .lum-sidebar-brand::after {
                content: 'l.';
                font-family: 'Gaegu', cursive;
                font-size: 30px;
                font-weight: 700;
            }

            section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
                width: 250px !important;
                margin: 18px 14px 14px !important;
                color: #aaaaa7 !important;
                font-family: 'Manrope', sans-serif !important;
                font-size: 12px !important;
                font-weight: 800 !important;
                letter-spacing: .12em !important;
                text-transform: uppercase !important;
                white-space: nowrap !important;
                opacity: 0 !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] {
                width: 48px !important;
                gap: 7px !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label {
                position: relative !important;
                width: 48px !important;
                min-width: 48px !important;
                max-width: 48px !important;
                min-height: 54px !important;
                margin: 0 !important;
                padding: 0 !important;
                border: 0 !important;
                border-radius: 18px !important;
                background: transparent !important;
                display: flex !important;
                align-items: center !important;
                overflow: hidden !important;
                transition: background .18s ease !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
            section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
                display: none !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
                position: absolute;
                left: 20px;
                top: 50%;
                width: 28px;
                transform: translateY(-50%);
                color: #666663;
                font: 22px/1 'Manrope', sans-serif;
                text-align: center;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(1)::before { content: '⌂'; }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(2)::before { content: '◇'; }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(3)::before { content: '▣'; }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(4)::before { content: '↗'; }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(5)::before { content: '◷'; }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
                background: rgba(17,17,17,.055) !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
                background: #151515 !important;
                color: #fff !important;
                border-left: 0 !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before {
                color: #fff !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label p {
                color: inherit !important;
                font-family: 'Noto Sans SC', sans-serif !important;
                font-size: 16px !important;
                font-weight: 650 !important;
                white-space: nowrap !important;
                opacity: 0 !important;
                transform: translateX(-8px) !important;
                transition: opacity .18s ease, transform .22s ease !important;
            }

            .block-container,
            [data-testid="stMainBlockContainer"] {
                width: 100% !important;
                max-width: none !important;
                padding: 8px 14px 18px !important;
            }

            .st-key-job_application_panel,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.job-application-panel-marker) {
                position: relative !important;
                width: 100% !important;
                min-height: calc(100dvh - 26px) !important;
                margin: 0 !important;
                padding: 42px clamp(24px, 3vw, 54px) 38px !important;
                overflow: hidden !important;
                border: 1px solid var(--journey-panel-line) !important;
                border-radius: clamp(38px, 4vw, 66px) !important;
                background: var(--journey-panel) !important;
                box-shadow: 0 20px 70px rgba(30,30,30,.055) !important;
            }

            .st-key-job_application_panel > div,
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.job-application-panel-marker) > div {
                border: 0 !important;
                background: transparent !important;
            }

            .job-application-panel-marker,
            .journey-card-marker {
                display: none !important;
            }

            .journey-heading {
                max-width: 900px;
                margin: 0 auto 20px;
                text-align: center;
            }

            .journey-heading h1 {
                margin: 0;
                color: #111;
                font-family: 'Gaegu', 'Noto Sans SC', sans-serif;
                font-size: clamp(3.2rem, 5vw, 5rem);
                font-weight: 700;
                line-height: .93;
                letter-spacing: .04em;
            }

            .journey-heading p {
                margin: 13px 0 0;
                color: #92928f;
                font: 600 clamp(.88rem, 1.15vw, 1.08rem)/1.55 'Noto Sans SC', sans-serif;
            }

            .st-key-job_workspace_mode {
                display: flex;
                justify-content: center;
                margin: 8px auto 28px;
            }

            .st-key-job_workspace_mode div[data-testid="stRadio"] > label,
            .st-key-overview_filter div[data-testid="stRadio"] > label {
                display: none !important;
            }

            .st-key-job_workspace_mode div[role="radiogroup"] {
                display: inline-flex !important;
                width: auto !important;
                gap: 8px !important;
                padding: 0 !important;
            }

            .st-key-job_workspace_mode div[role="radiogroup"] label {
                min-width: 180px !important;
                min-height: 50px !important;
                margin: 0 !important;
                padding: .65rem 1.25rem !important;
                border: 0 !important;
                border-radius: 999px !important;
                background: #f1f1ef !important;
            }

            .st-key-job_workspace_mode div[role="radiogroup"] label:nth-child(2) {
                background: #fff0e6 !important;
            }

            .st-key-job_workspace_mode div[role="radiogroup"] label:nth-child(3) {
                background: #f0e5ff !important;
            }

            .st-key-job_workspace_mode div[role="radiogroup"] label > div:first-child,
            .st-key-overview_filter div[role="radiogroup"] label > div:first-child {
                display: none !important;
            }

            .st-key-job_workspace_mode div[role="radiogroup"] label:has(input:checked) {
                background: #151515 !important;
            }

            .st-key-job_workspace_mode div[role="radiogroup"] label p {
                color: #4f4f4c !important;
                font: 700 .88rem/1.2 'Noto Sans SC', sans-serif !important;
                text-align: center !important;
            }

            .st-key-job_workspace_mode div[role="radiogroup"] label:has(input:checked) p {
                color: #fff !important;
            }

            .overview-controls {
                margin: 0 0 18px;
            }

            .st-key-overview_filter div[role="radiogroup"] {
                display: flex !important;
                flex-wrap: wrap !important;
                gap: 8px !important;
            }

            .st-key-overview_filter div[role="radiogroup"] label {
                min-height: 38px !important;
                margin: 0 !important;
                padding: .42rem .92rem !important;
                border: 0 !important;
                border-radius: 999px !important;
                background: #f0f0ee !important;
            }

            .st-key-overview_filter div[role="radiogroup"] label:has(input:checked) {
                background: #e3f4ea !important;
                box-shadow: inset 0 0 0 1px #49a978 !important;
            }

            .st-key-overview_filter div[role="radiogroup"] label p {
                color: #666662 !important;
                font: 700 .75rem/1.2 'Noto Sans SC', sans-serif !important;
            }

            .st-key-overview_filter div[role="radiogroup"] label:has(input:checked) p {
                color: #198455 !important;
            }

            .st-key-overview_search input,
            .st-key-job_selector_wrap div[data-baseweb="select"] > div {
                min-height: 46px !important;
                border: 1px solid #dedbd4 !important;
                border-radius: 999px !important;
                background: #fff !important;
                background-color: #fff !important;
                color: #5f5f5b !important;
                -webkit-text-fill-color: #5f5f5b !important;
                box-shadow: none !important;
                forced-color-adjust: none !important;
            }

            .st-key-overview_search input::placeholder {
                color: #8b8b88 !important;
                -webkit-text-fill-color: #8b8b88 !important;
                opacity: 1 !important;
            }

            .st-key-job_workspace_mode input[type="radio"],
            .st-key-overview_filter input[type="radio"] {
                color-scheme: light only !important;
                accent-color: #0b7659 !important;
                forced-color-adjust: none !important;
            }

            .st-key-overview_search label,
            .st-key-job_selector_wrap label {
                display: none !important;
            }

            .journey-list {
                display: grid;
                gap: 8px;
                margin-top: 5px;
            }

            .journey-row {
                display: grid;
                grid-template-columns: minmax(270px, 330px) minmax(760px, 1fr);
                min-height: 104px;
                overflow: hidden;
                border: 1px solid rgba(17,17,17,.07);
                border-radius: 18px;
                background: rgba(255,255,255,.92);
                box-shadow: 0 10px 26px rgba(31,31,31,.045);
                transition: transform .18s ease, box-shadow .18s ease;
            }

            .journey-jd-disclosure {
                grid-column: 1 / -1;
                border-top: 1px solid var(--journey-line);
                background: #fbfaf7;
            }

            .journey-jd-disclosure summary {
                min-height: 30px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                padding: 4px 14px;
                cursor: pointer;
                list-style: none;
                user-select: none;
            }

            .journey-jd-disclosure summary::-webkit-details-marker {
                display: none;
            }

            .journey-jd-label {
                color: #77736d;
                font: 750 .6rem/1.35 'Noto Sans SC', sans-serif;
                letter-spacing: .04em;
            }

            .journey-jd-toggle {
                flex: 0 0 auto;
                min-width: 62px;
                padding: 3px 8px;
                border: 1px solid #d8d4cc;
                border-radius: 999px;
                background: #fff;
                color: #5f5c56;
                font: 700 .6rem/1.2 'Noto Sans SC', sans-serif;
                text-align: center;
                transition: background .16s ease, border-color .16s ease;
            }

            .journey-jd-toggle::before {
                content: '展开 JD';
            }

            .journey-jd-disclosure summary:hover .journey-jd-toggle {
                border-color: #aaa59c;
                background: #f4f2ed;
            }

            .journey-jd-disclosure[open] .journey-jd-toggle::before {
                content: '收起 JD';
            }

            .journey-jd-text {
                max-height: 240px;
                overflow: auto;
                padding: 0 22px 18px;
                color: #4e4d49;
                font-family: 'Noto Sans SC', sans-serif;
                font-size: 13px;
                font-weight: 550;
                line-height: 1.65;
                white-space: normal;
                scrollbar-width: thin;
                scrollbar-color: #d5d2ca transparent;
            }

            .journey-row:hover {
                transform: translateY(-2px);
                box-shadow: 0 16px 34px rgba(31,31,31,.075);
            }

            .journey-row.ended {
                opacity: .62;
            }

            .journey-summary {
                display: grid;
                grid-template-columns: 42px minmax(0,1fr);
                gap: 10px;
                align-items: center;
                padding: 8px 14px;
                border-right: 1px solid var(--journey-line);
            }

            .company-badge {
                width: 40px;
                height: 40px;
                display: grid;
                place-items: center;
                border-radius: 50%;
                font: 800 1rem/1 'Noto Sans SC', sans-serif;
                box-shadow: inset 0 0 0 1px rgba(255,255,255,.55);
            }

            .journey-company {
                color: #171717;
                font: 800 .88rem/1.2 'Noto Sans SC', sans-serif;
            }

            .journey-position {
                margin-top: 2px;
                overflow: hidden;
                color: #71716e;
                font: 550 .68rem/1.25 'Noto Sans SC', sans-serif;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .journey-meta-grid {
                grid-column: 1 / -1;
                display: grid;
                grid-template-columns: 1fr;
                gap: 2px;
                margin-top: 3px;
                padding-left: 52px;
            }

            .journey-meta-line {
                display: flex;
                align-items: center;
                gap: 5px;
                min-width: 0;
                color: #8b8b87;
                font: 600 .6rem/1.25 'Noto Sans SC', sans-serif;
            }

            .journey-demo-note {
                grid-column: 1 / -1;
                margin-top: 3px;
                padding-left: 52px;
                color: #aaa49c;
                font: 550 .54rem/1.35 'Noto Sans SC', sans-serif;
                letter-spacing: .01em;
            }

            .journey-progress-pill {
                max-width: 210px;
                overflow: hidden;
                padding: 2px 7px;
                border-radius: 999px;
                background: #e4f4eb;
                color: #19845a;
                font-weight: 750;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .journey-next-action {
                overflow: hidden;
                color: #4d4d49;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .journey-track-wrap {
                min-width: 0;
                overflow-x: auto;
                padding: 11px 18px 7px;
                scrollbar-width: thin;
                scrollbar-color: #d5d5d1 transparent;
            }

            .journey-track {
                min-width: 900px;
                display: grid;
                grid-template-columns: repeat(9, minmax(92px, 1fr));
                align-items: start;
            }

            .journey-step {
                position: relative;
                min-width: 0;
                text-align: center;
            }

            .journey-step::after {
                content: '';
                position: absolute;
                z-index: 0;
                top: 27px;
                left: 50%;
                width: 100%;
                height: 2px;
                background: #d9d9d5;
            }

            .journey-step:last-child::after {
                display: none;
            }

            .journey-step.done:has(+ .journey-step.done)::after,
            .journey-step.done:has(+ .journey-step.failed)::after {
                background: #30a071;
            }

            .journey-step-label {
                min-height: 16px;
                color: #4f4f4b;
                font: 700 .6rem/1.15 'Noto Sans SC', sans-serif;
                white-space: nowrap;
            }

            .journey-node {
                position: relative;
                z-index: 2;
                width: 16px;
                height: 16px;
                display: grid;
                place-items: center;
                margin: 3px auto 0;
                border: 2px solid #cfcfcb;
                border-radius: 50%;
                background: #fff;
                color: transparent;
                font: 900 .65rem/1 'Manrope', sans-serif;
                cursor: pointer;
                list-style: none;
            }

            .journey-node::-webkit-details-marker { display: none; }

            .journey-node-menu {
                position: relative;
                z-index: 8;
                width: 22px;
                height: 22px;
                margin: 6px auto 0;
            }

            .journey-node-menu .journey-node { margin: 0; }

            .journey-node-actions {
                position: absolute;
                top: 30px;
                left: 50%;
                z-index: 20;
                width: 154px;
                overflow: hidden;
                transform: translateX(-50%);
                border: 1px solid rgba(17,17,17,.1);
                border-radius: 13px;
                background: #fff;
                box-shadow: 0 12px 28px rgba(20,20,20,.14);
                text-align: left;
            }

            .journey-node-actions a {
                display: block;
                padding: 9px 11px;
                color: #242421 !important;
                font: 700 .68rem/1.25 'Noto Sans SC', sans-serif;
                text-decoration: none !important;
                white-space: nowrap;
            }

            .journey-node-actions a + a { border-top: 1px solid #efefec; }
            .journey-node-actions a:hover { background: #f4f4f1; }
            .journey-node-actions .end-action { color: #b34d48 !important; }
            .journey-node-actions .undo-action { color: #6f5a8e !important; }

            .journey-step.done .journey-node {
                border-color: var(--journey-green);
                background: var(--journey-green);
                color: #fff;
            }

            .journey-step.current .journey-node {
                border: 2px solid #21a16c;
                background: #fff;
                color: #21a16c;
                box-shadow: 0 0 0 4px rgba(33,161,108,.13);
            }

            .journey-step.skipped .journey-node {
                border-style: dashed;
                color: #aaa9a5;
            }

            .journey-step.failed .journey-node {
                border-color: #d97b77;
                background: #fff0ef;
                color: #c75954;
            }

            .journey-step.offer.current .journey-node,
            .journey-step.offer.done .journey-node {
                border-color: #825bc5;
                background: #efe5ff;
                color: #7650bc;
                box-shadow: 0 0 0 4px rgba(130,91,197,.13);
            }

            [class*="st-key-termination_notes_"] {
                margin: -5px 18px 14px !important;
                padding: 14px 18px 16px !important;
                border: 1px solid rgba(17,17,17,.07) !important;
                border-top: 0 !important;
                border-radius: 0 0 22px 22px !important;
                background: rgba(255,255,255,.92) !important;
            }

            [class*="st-key-termination_notes_"] textarea {
                min-height: 76px !important;
                border: 1px solid #dedbd4 !important;
                border-radius: 14px !important;
                background: #fff !important;
            }

            [class*="st-key-save_termination_notes_"] button {
                min-height: 36px !important;
                border-radius: 999px !important;
            }

            .journey-date {
                min-height: 12px;
                margin-top: 3px;
                color: #6e6e69;
                font: 650 .56rem/1.1 'Manrope', sans-serif;
            }

            .journey-row-link {
                position: absolute;
                top: 0;
                left: 0;
                z-index: 5;
                width: 330px;
                height: 74px;
                border-radius: 18px 0 0 18px;
            }

            .journey-row-shell {
                position: relative;
            }

            .journey-empty {
                padding: 70px 24px;
                border: 1px dashed #d8d8d3;
                border-radius: 30px;
                color: #8d8d88;
                font: 600 .9rem/1.7 'Noto Sans SC', sans-serif;
                text-align: center;
            }

            .journey-legend {
                display: flex;
                justify-content: center;
                flex-wrap: wrap;
                gap: 22px;
                margin-top: 20px;
                color: #777773;
                font: 600 .7rem/1.4 'Noto Sans SC', sans-serif;
            }

            .journey-legend span {
                display: inline-flex;
                align-items: center;
                gap: 7px;
            }

            .journey-legend i {
                width: 14px;
                height: 14px;
                border: 2px solid #cfcfca;
                border-radius: 50%;
                background: #fff;
            }

            .journey-legend .done i { border-color:#15945f; background:#15945f; }
            .journey-legend .current i { border:3px solid #15945f; }
            .journey-legend .skipped i { border-style:dashed; }
            .journey-legend .failed i { border-color:#d97b77; background:#fff0ef; }

            .st-key-job_selector_wrap {
                max-width: 760px;
                margin: 0 auto 20px;
            }

            .update-summary-card {
                display: grid;
                grid-template-columns: 72px 1fr auto;
                gap: 18px;
                align-items: center;
                margin: 0 auto 20px;
                padding: 22px 24px;
                border: 1px solid var(--journey-line);
                border-radius: 28px;
                background: #fff;
                box-shadow: 0 10px 26px rgba(31,31,31,.045);
            }

            .update-jd-card {
                margin: 0 auto 22px;
                padding: 18px 20px;
                border: 1px solid var(--journey-line);
                border-radius: 24px;
                background: #fbfaf7;
                box-shadow: 0 10px 26px rgba(31,31,31,.035);
            }

            .update-jd-title {
                color: #171717;
                font: 800 .9rem/1.35 'Noto Sans SC', sans-serif;
            }

            .update-jd-copy {
                max-height: 180px;
                overflow: auto;
                margin-top: 9px;
                padding: 12px 14px;
                border-radius: 16px;
                background: #fff;
                color: #4d4c48;
                font-family: 'Noto Sans SC', sans-serif;
                font-size: 14px;
                font-weight: 500;
                line-height: 1.65;
                scrollbar-width: thin;
                scrollbar-color: #d5d2ca transparent;
            }

            .update-jd-copy .jd-heading {
                margin: 14px 0 7px;
                color: #24231f;
                font-family: 'Noto Sans SC', sans-serif;
                font-size: 15px;
                font-weight: 800;
                line-height: 1.4;
            }

            .update-jd-copy .jd-heading:first-child { margin-top: 0; }

            .update-jd-copy .jd-item {
                display: grid;
                grid-template-columns: 24px minmax(0, 1fr);
                gap: 8px;
                align-items: start;
                margin: 0 0 7px;
            }

            .update-jd-copy .jd-marker {
                color: #77736d;
                font-size: 13px;
                font-weight: 750;
                line-height: 1.75;
                text-align: right;
            }

            .update-jd-copy .jd-item p,
            .update-jd-copy .jd-paragraph {
                margin: 0 0 7px;
                color: inherit;
                font: inherit;
                line-height: inherit;
            }

            .update-jd-copy .jd-empty { color: #99958f; }

            .update-summary-company {
                font: 800 1.15rem/1.25 'Noto Sans SC', sans-serif;
            }

            .update-summary-position {
                margin-top: 4px;
                color: #6f6f6b;
                font: 550 .82rem/1.45 'Noto Sans SC', sans-serif;
            }

            .update-summary-meta {
                margin-top: 8px;
                color: #92928e;
                font: 600 .7rem/1.5 'Noto Sans SC', sans-serif;
            }

            .update-summary-actions {
                display: flex;
                flex-wrap: wrap;
                justify-content: flex-end;
                gap: 8px;
            }

            .summary-link {
                display: inline-flex;
                align-items: center;
                min-height: 36px;
                padding: 7px 12px;
                border-radius: 999px;
                background: #f1f1ef;
                color: #3e3e3b !important;
                font: 700 .7rem/1.2 'Noto Sans SC', sans-serif;
                text-decoration: none !important;
            }

            .summary-link.dark {
                background: #171717;
                color: #fff !important;
            }

            [class*="st-key-update_card_"],
            [class*="st-key-new_role_card_"],
            [class*="st-key-new_progress_card_"],
            [class*="st-key-new_material_card_"] {
                height: 100% !important;
                padding: clamp(21px, 2.2vw, 30px) !important;
                border: 0 !important;
                border-radius: 32px !important;
                box-shadow: none !important;
            }

            [class*="st-key-update_card_"]:nth-of-type(odd) {
                background: var(--journey-mint) !important;
            }

            [class*="st-key-update_card_"] {
                background: #f1eee9 !important;
            }

            [class*="st-key-new_role_card_"] { background: var(--journey-mint) !important; }
            [class*="st-key-new_progress_card_"] { background: var(--journey-peach) !important; }
            [class*="st-key-new_material_card_"] { background: var(--journey-violet) !important; }

            /* New role is intentionally a compact, one-screen task. */
            .st-key-job_application_panel:has([class*="st-key-new_application_form_"]),
            div[data-testid="stVerticalBlockBorderWrapper"]:has(.job-application-panel-marker):has([class*="st-key-new_application_form_"]) {
                height: calc(100dvh - 62px) !important;
                min-height: calc(100dvh - 62px) !important;
                padding-top: 24px !important;
                padding-bottom: 20px !important;
                overflow-y: auto !important;
            }

            .st-key-job_application_panel:has([class*="st-key-new_application_form_"]) .journey-heading,
            div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-new_application_form_"]) .journey-heading {
                margin-bottom: 10px !important;
            }

            .st-key-job_application_panel:has([class*="st-key-new_application_form_"]) .journey-heading h1,
            div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-new_application_form_"]) .journey-heading h1 {
                font-size: clamp(3rem, 4vw, 4.15rem) !important;
            }

            .st-key-job_application_panel:has([class*="st-key-new_application_form_"]) .journey-heading p,
            div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-new_application_form_"]) .journey-heading p {
                margin-top: 7px !important;
            }

            .st-key-job_application_panel:has([class*="st-key-new_application_form_"]) .st-key-job_workspace_mode,
            div[data-testid="stVerticalBlockBorderWrapper"]:has([class*="st-key-new_application_form_"]) .st-key-job_workspace_mode {
                margin-top: 2px !important;
                margin-bottom: 16px !important;
            }

            [class*="st-key-new_application_form_"] {
                width: min(1080px, 100%) !important;
                margin: 0 auto !important;
            }

            [class*="st-key-new_role_card_"] {
                padding: 22px 34px 18px !important;
                border-radius: 30px !important;
            }

            [class*="st-key-new_role_card_"] .journey-section-title {
                margin-bottom: 8px !important;
            }

            [class*="st-key-new_role_card_"] div[data-testid="stVerticalBlock"] {
                gap: .55rem !important;
            }

            [class*="st-key-new_role_card_"] input {
                min-height: 44px !important;
            }

            [class*="st-key-new_role_card_"] textarea {
                min-height: 108px !important;
                max-height: 108px !important;
                resize: vertical !important;
            }

            [class*="st-key-new_role_card_"] label p {
                font-size: .7rem !important;
                line-height: 1.2 !important;
            }

            [class*="st-key-update_card_"] > div,
            [class*="st-key-new_role_card_"] > div,
            [class*="st-key-new_progress_card_"] > div,
            [class*="st-key-new_material_card_"] > div {
                border: 0 !important;
                background: transparent !important;
            }

            .journey-section-title {
                margin: 0 0 18px;
            }

            .journey-section-title strong {
                display: block;
                color: #5d5d59;
                font: 700 clamp(1.55rem, 2vw, 2.05rem)/1 'Gaegu', 'Noto Sans SC', sans-serif;
                letter-spacing: .03em;
            }

            .journey-section-title span {
                display: block;
                margin-top: 5px;
                color: rgba(75,75,72,.68);
                font: 650 .7rem/1.4 'Noto Sans SC', sans-serif;
            }

            .st-key-job_application_panel label p,
            .st-key-job_application_panel [data-testid="stWidgetLabel"] p {
                color: #4f4f4c !important;
                font: 650 .76rem/1.35 'Noto Sans SC', sans-serif !important;
            }

            .st-key-job_application_panel input,
            .st-key-job_application_panel textarea,
            .st-key-job_application_panel div[data-baseweb="input"] > div,
            .st-key-job_application_panel div[data-baseweb="select"] > div,
            .st-key-job_application_panel button[role="combobox"] {
                border: 0 !important;
                border-radius: 17px !important;
                background: rgba(255,255,255,.78) !important;
                color: #171717 !important;
                box-shadow: none !important;
                font-family: 'Noto Sans SC', sans-serif !important;
            }

            .st-key-job_application_panel input,
            .st-key-job_application_panel div[data-baseweb="select"] > div,
            .st-key-job_application_panel button[role="combobox"] {
                min-height: 50px !important;
            }

            .st-key-job_application_panel textarea {
                padding: 13px 15px !important;
                line-height: 1.55 !important;
            }

            .st-key-job_application_panel input:focus,
            .st-key-job_application_panel textarea:focus,
            .st-key-job_application_panel div[data-baseweb="input"] > div:focus-within,
            .st-key-job_application_panel div[data-baseweb="select"] > div:focus-within {
                outline: none !important;
                box-shadow: 0 0 0 2px rgba(20,20,20,.86) !important;
            }

            .st-key-save_progress_button,
            .st-key-create_application_button {
                display: flex;
                justify-content: center;
                margin-top: 24px;
            }

            .st-key-save_progress_button button,
            .st-key-create_application_button button {
                width: min(390px, 100%) !important;
                min-height: 62px !important;
                border: 0 !important;
                border-radius: 999px !important;
                background: #151515 !important;
                color: #fff !important;
                font: 700 1rem/1.2 'Noto Sans SC', sans-serif !important;
                box-shadow: none !important;
            }

            [class*="st-key-new_application_form_"] .st-key-create_application_button {
                margin-top: 10px !important;
            }

            [class*="st-key-new_application_form_"] .st-key-create_application_button button {
                min-height: 50px !important;
            }

            html body .stApp [class*="st-key-new_application_form_"] .st-key-create_application_button button,
            html body .stApp [class*="st-key-new_application_form_"] .st-key-create_application_button button * {
                color: #ffffff !important;
                fill: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                opacity: 1 !important;
            }

            /* Streamlit's global paragraph rule can repaint the internal
               label after this page is rendered. Keep the accessible source
               text in the DOM and draw a stable white visual label above it. */
            html body .stApp .st-key-create_application_button button [data-testid="stMarkdownContainer"] p {
                font-size: 0 !important;
                color: transparent !important;
                -webkit-text-fill-color: transparent !important;
            }

            html body .stApp .st-key-create_application_button button::after {
                content: "创建职位  →" !important;
                display: inline-block !important;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
                font: 700 .78rem/1.2 'Noto Sans SC', 'Inter', sans-serif !important;
                white-space: nowrap !important;
                opacity: 1 !important;
            }

            .st-key-save_progress_button button:hover,
            .st-key-create_application_button button:hover {
                transform: translateY(-2px);
                background: #292929 !important;
            }

            .st-key-job_application_panel div[data-testid="stExpander"] {
                margin-top: 18px;
                border: 1px solid var(--journey-line) !important;
                border-radius: 20px !important;
                background: #fff !important;
            }

            .st-key-job_application_panel div[data-testid="stAlert"] {
                max-width: 820px;
                margin: 8px auto 16px;
                border: 0 !important;
                border-radius: 18px !important;
                background: #f0f0ee !important;
                color: #151515 !important;
            }

            @media (max-width: 1120px) {
                .journey-row {
                    grid-template-columns: 280px minmax(720px, 1fr);
                }

                .journey-summary {
                    padding: 8px 12px;
                }

                .journey-row-link {
                    width: 280px;
                }
            }

            @media (max-width: 820px) {
                section[data-testid="stSidebar"] {
                    width: 80px !important;
                    min-width: 80px !important;
                    max-width: 80px !important;
                }

                section[data-testid="stSidebar"]:hover {
                    width: 80px !important;
                    min-width: 80px !important;
                    max-width: 80px !important;
                }

                [data-testid="stMain"] {
                    margin-left: 80px !important;
                    width: calc(100% - 80px) !important;
                }

                .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"] {
                    margin-left: 80px !important;
                    width: calc(100% - 80px) !important;
                }

                .block-container,
                [data-testid="stMainBlockContainer"] {
                    padding: 6px 8px 12px !important;
                }

                .st-key-job_application_panel,
                div[data-testid="stVerticalBlockBorderWrapper"]:has(.job-application-panel-marker) {
                    padding: 46px 16px 26px !important;
                    border-radius: 34px !important;
                }

                .st-key-job_workspace_mode div[role="radiogroup"] {
                    width: 100% !important;
                    display: grid !important;
                    grid-template-columns: repeat(3, 1fr) !important;
                    gap: 5px !important;
                }

                .st-key-job_workspace_mode div[role="radiogroup"] label {
                    min-width: 0 !important;
                    padding: .55rem .4rem !important;
                }

                .update-summary-card {
                    grid-template-columns: 58px 1fr;
                }

                .update-summary-actions {
                    grid-column: 1 / -1;
                    justify-content: flex-start;
                }

                .journey-jd-disclosure summary {
                    padding-inline: 16px;
                }

                .journey-jd-text {
                    padding-inline: 16px;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# Overview rendering
# =========================================================
def _render_journey_row(job: dict[str, Any]) -> str:
    character, badge_bg, badge_fg = _company_badge(_text(job.get("company")))
    ended = _text(job.get("application_state")) == "ended" or _text(job.get("status")) in {"拒绝", "放弃", "已结束"}

    stages_html = []
    for stage in PIPELINE_STAGES:
        visual, date_text = _stage_visual(job, stage)
        symbol = {
            "done": "✓",
            "current": "●",
            "skipped": "–",
            "failed": "×",
            "upcoming": "",
        }[visual]
        offer_class = " offer" if stage == "Offer" else ""
        encoded_stage = quote(stage)
        complete_url = (
            f"?page=职位申请&mode=overview&timeline_action=complete"
            f"&timeline_job_id={int(job['id'])}&timeline_stage={encoded_stage}"
        )
        end_url = (
            f"?page=职位申请&mode=overview&timeline_action=end"
            f"&timeline_job_id={int(job['id'])}&timeline_stage={encoded_stage}"
        )
        undo_url = (
            f"?page=职位申请&mode=overview&timeline_action=undo"
            f"&timeline_job_id={int(job['id'])}&timeline_stage={encoded_stage}"
        )
        stages_html.append(
            f"""
            <div class="journey-step {visual}{offer_class}">
                <div class="journey-step-label">{_safe(stage)}</div>
                <details class="journey-node-menu">
                    <summary class="journey-node" aria-label="更新{_safe(stage)}">{symbol}</summary>
                    <div class="journey-node-actions">
                        <a href="{complete_url}" target="_self">Mark as Completed</a>
                        <a class="end-action" href="{end_url}" target="_self">End Process</a>
                        <a class="undo-action" href="{undo_url}" target="_self">撤销 / 恢复进行中</a>
                    </div>
                </details>
                <div class="journey-date">{_safe(date_text)}</div>
            </div>
            """
        )

    next_action = _text(job.get("next_action")) or "暂未设置下一步行动"
    progress = _current_progress_text(job)
    job_description = _text(job.get("job_description")) or "暂未保存岗位 JD"
    return f"""
        <div class="journey-row-shell">
            <article class="journey-row{' ended' if ended else ''}">
                <div class="journey-summary">
                    <div class="company-badge" style="background:{badge_bg};color:{badge_fg};">{_safe(character)}</div>
                    <div>
                        <div class="journey-company">{_safe(job.get('company'), '未命名公司')}</div>
                        <div class="journey-position">{_safe(job.get('position'), '未命名岗位')}</div>
                    </div>
                    <div class="journey-meta-grid">
                        <div class="journey-meta-line">
                            <span>当前进度</span>
                            <span class="journey-progress-pill">{_safe(progress)}</span>
                        </div>
                        <div class="journey-meta-line">
                            <span>下一步行动</span>
                            <span class="journey-next-action">{_safe(next_action)}</span>
                        </div>
                    </div>
                    <div class="journey-demo-note">Demo 备注：公司名称与申请进度均为虚拟信息，岗位 JD 仅用于功能展示。</div>
                </div>
                <div class="journey-track-wrap">
                    <div class="journey-track">{''.join(stages_html)}</div>
                </div>
                <details class="journey-jd-disclosure">
                    <summary>
                        <span class="journey-jd-label">岗位 JD</span>
                        <span class="journey-jd-toggle" aria-hidden="true"></span>
                    </summary>
                    <div class="journey-jd-text">{_safe(' '.join(job_description.split()))}</div>
                </details>
            </article>
            <a class="journey-row-link" href="?page=职位申请&mode=update&job_id={int(job['id'])}" target="_self" aria-label="更新{_safe(job.get('company'))}{_safe(job.get('position'))}"></a>
        </div>
    """


def _render_overview(all_jobs: list[dict[str, Any]]) -> None:
    control_left, control_right = st.columns([2.25, 1], gap="large")
    with control_left:
        with st.container(key="overview_filter"):
            selected_filter = st.radio(
                "筛选申请",
                ["全部", "准备投递", "测评中", "面试中", "谈薪 / Offer", "已结束"],
                horizontal=True,
                label_visibility="collapsed",
                key="application_overview_filter",
            )
    with control_right:
        with st.container(key="overview_search"):
            search_value = st.text_input(
                "搜索公司或岗位",
                placeholder="搜索公司或岗位…",
                label_visibility="collapsed",
                key="application_overview_search",
            )

    search_term = _text(search_value).lower()
    filtered = []
    for job in all_jobs:
        if selected_filter != "全部" and _overview_bucket(job) != selected_filter:
            continue
        haystack = f"{_text(job.get('company'))} {_text(job.get('position'))}".lower()
        if search_term and search_term not in haystack:
            continue
        filtered.append(job)

    if not filtered:
        st.markdown(
            '<div class="journey-empty">没有找到匹配的职位申请。<br>可以切换筛选条件，或进入“新增职位”建立第一条申请。</div>',
            unsafe_allow_html=True,
        )
        return

    for job in filtered:
        st.html(f'<div class="journey-list">{_render_journey_row(job)}</div>')
        if _overview_bucket(job) == "已结束":
            job_id = int(job["id"])
            with st.container(key=f"termination_notes_{job_id}"):
                termination_notes = st.text_area(
                    "终止备注",
                    value=_text(job.get("termination_notes")),
                    placeholder="记录被拒、主动放弃、岗位关闭或其他终止原因。",
                    key=f"termination_notes_input_{job_id}",
                )
                if st.button("保存备注", key=f"save_termination_notes_{job_id}"):
                    try:
                        update_application_termination_notes(job_id, termination_notes)
                        st.session_state["job_workspace_flash"] = ("success", "终止备注已保存。")
                        st.rerun()
                    except Exception as error:
                        st.error(str(error))

    st.html(
        """
        <div class="journey-legend">
            <span class="done"><i></i>已完成</span>
            <span class="current"><i></i>进行中</span>
            <span class="skipped"><i></i>已跳过</span>
            <span class="failed"><i></i>未通过</span>
            <span><i></i>未开始</span>
        </div>
        """
    )


# =========================================================
# Update mode
# =========================================================
def _selected_job(all_jobs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not all_jobs:
        return None

    labels = [
        f"{job.get('company') or '未命名公司'} ｜ {job.get('position') or '未命名岗位'} ｜ {_current_progress_text(job)}"
        for job in all_jobs
    ]

    requested_id = st.session_state.pop("job_workspace_requested_job_id", None)
    default_index = 0
    if requested_id is not None:
        for index, job in enumerate(all_jobs):
            if int(job["id"]) == int(requested_id):
                default_index = index
                break
        st.session_state.pop("job_workspace_selected_job", None)

    with st.container(key="job_selector_wrap"):
        selected_label = st.selectbox(
            "选择已有职位",
            labels,
            index=default_index,
            label_visibility="collapsed",
            key="job_workspace_selected_job",
        )
    return all_jobs[labels.index(selected_label)]


def _render_update_summary(job: dict[str, Any]) -> None:
    character, badge_bg, badge_fg = _company_badge(_text(job.get("company")))
    deadline = _text(job.get("deadline")) or "未设置"
    location = _text(job.get("location")) or "未设置工作地点"
    url = _text(job.get("application_url"))
    url_html = (
        f'<a class="summary-link" href="{_safe(url)}" target="_blank">打开投递官网 ↗</a>'
        if url
        else '<span class="summary-link">暂无投递链接</span>'
    )

    st.markdown(
        f"""
        <div class="update-summary-card">
            <div class="company-badge" style="width:68px;height:68px;background:{badge_bg};color:{badge_fg};">{_safe(character)}</div>
            <div>
                <div class="update-summary-company">{_safe(job.get('company'), '未命名公司')}</div>
                <div class="update-summary-position">{_safe(job.get('position'), '未命名岗位')}</div>
                <div class="update-summary-meta">{_safe(_current_progress_text(job))} · 截止 {_safe(deadline)} · {_safe(location)}</div>
            </div>
            <div class="update-summary-actions">
                {url_html}
                <a class="summary-link dark" href="?page=职位申请&mode=overview" target="_self">返回申请总览</a>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <section class="update-jd-card">
            <div class="update-jd-title">岗位 JD</div>
            <div class="update-jd-copy">{_format_job_description_html(job.get('job_description'))}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _inject_progress_detail_css() -> None:
    st.markdown(
        r"""
        <style>
            .progress-detail-grid { display:grid; grid-template-columns:minmax(0,1.15fr) minmax(320px,.85fr); gap:22px; margin-top:22px; }
            .progress-card-shell { height:100%; padding:30px; border:1px solid rgba(20,20,20,.04); border-radius:34px; background:#fff; box-shadow:0 20px 50px rgba(0,0,0,.045); }
            .progress-card-shell.lilac { background:#f3e8ff; }
            .progress-card-shell.mint { background:#dff2e7; }
            .progress-card-shell.sky { background:#e7f3f8; }
            [class*="st-key-progress_main_card_"] { height:100%; padding:30px!important; border:1px solid rgba(20,20,20,.04)!important; border-radius:34px!important; background:#fff!important; box-shadow:0 20px 50px rgba(0,0,0,.045)!important; }
            [class*="st-key-next_event_card_"] { height:100%; padding:30px!important; border:1px solid rgba(20,20,20,.04)!important; border-radius:34px!important; background:#f3e8ff!important; box-shadow:0 20px 50px rgba(0,0,0,.045)!important; }
            [class*="st-key-notes_card_"] { margin-top:22px; padding:30px!important; border:1px solid rgba(20,20,20,.04)!important; border-radius:34px!important; background:#e7f3f8!important; box-shadow:0 20px 50px rgba(0,0,0,.045)!important; }
            .progress-eyebrow { color:#71569a; font:700 1.65rem/1 'Gaegu',cursive; }
            .progress-card-title { margin:6px 0 0; color:#171717; font:750 1.02rem/1.3 'Noto Sans SC',sans-serif; }
            .progress-card-copy { margin:9px 0 0; color:#85847f; font:550 .7rem/1.65 'Noto Sans SC',sans-serif; }
            .next-event-body { min-height:188px; display:flex; flex-direction:column; justify-content:space-between; padding-top:24px; }
            .next-event-stage { display:flex; align-items:center; justify-content:space-between; gap:12px; }
            .next-event-stage strong { font:750 1.15rem/1.25 'Noto Sans SC',sans-serif; }
            .progress-status { display:inline-flex; align-items:center; gap:6px; padding:6px 10px; border-radius:999px; font:700 .63rem/1 'Noto Sans SC',sans-serif; }
            .progress-status::before { content:''; width:6px; height:6px; border-radius:50%; background:currentColor; }
            .progress-status.preparing { color:#74579b; background:rgba(255,255,255,.66); }
            .progress-status.active { color:#397e91; background:#fff; }
            .progress-status.completed { color:#237552; background:#eefaf3; }
            .progress-status.ended { color:#77736e; background:#efefec; }
            .next-event-time { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:20px 0 13px; }
            .next-event-time span { padding:14px; border-radius:17px; background:rgba(255,255,255,.72); color:#343432; font:700 .78rem/1.2 'Noto Sans SC',sans-serif; }
            .next-event-time small { display:block; margin-bottom:5px; color:#99958f; font:700 .56rem/1 'Inter',sans-serif; letter-spacing:.08em; }
            .timeline-panel { margin-top:22px; padding:30px; border:1px solid rgba(20,20,20,.04); border-radius:34px; background:#fff; box-shadow:0 20px 50px rgba(0,0,0,.045); }
            .detail-timeline { display:grid; grid-template-columns:repeat(9,minmax(84px,1fr)); margin-top:28px; overflow-x:auto; padding:8px 0 14px; }
            .detail-step { position:relative; min-width:84px; color:#aaa9a4; text-align:center; text-decoration:none!important; }
            .detail-step::after { content:''; position:absolute; z-index:0; top:34px; left:50%; width:100%; height:2px; background:#e4e3df; }
            .detail-step:last-child::after { display:none; }
            .detail-step.done::after { background:#9bc9af; }
            .detail-step-label { min-height:22px; color:#5f5f5a; font:700 .64rem/1.2 'Noto Sans SC',sans-serif; }
            .detail-step-node { position:relative; z-index:2; width:22px; height:22px; display:grid; place-items:center; margin:2px auto 7px; border:2px solid #d1d0cb; border-radius:50%; background:#fff; color:#aaa; font:800 .66rem/1 Inter,sans-serif; transition:.2s ease; }
            .detail-step:hover .detail-step-node { transform:scale(1.18); border-color:#171717; color:#171717; }
            .detail-step.done .detail-step-node { border-color:#79b594; background:#dff2e7; color:#26714e; }
            .detail-step.current .detail-step-node { border:6px solid #9574bd; background:#fff; box-shadow:0 0 0 5px #f3e8ff; }
            .detail-step.ended .detail-step-node { border-color:#c98680; background:#fff0ef; color:#a6524b; }
            .detail-step-date { color:#a7a6a0; font:600 .57rem/1.2 Inter,sans-serif; }
            .timeline-tip { margin:13px 0 0; color:#aaa7a1; font:600 .65rem/1.5 'Noto Sans SC',sans-serif; text-align:center; }
            .notes-layout { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:14px; align-items:end; }
            .notes-layout .notes-heading { grid-column:1/-1; }
            .notes-layout .notes-heading p { margin:8px 0 0; color:#71838a; font:550 .68rem/1.55 'Noto Sans SC',sans-serif; }
            [class*="st-key-progress_stage_"] div[data-testid="stPills"], [class*="st-key-progress_status_"] div[data-testid="stPills"] { margin-top:10px; }
            [class*="st-key-progress_stage_"] div[role="radiogroup"], [class*="st-key-progress_status_"] div[role="radiogroup"] { gap:8px!important; }
            [class*="st-key-progress_stage_"] div[role="radiogroup"] label, [class*="st-key-progress_status_"] div[role="radiogroup"] label { min-height:40px!important; padding:8px 14px!important; border:1px solid #ecebe7!important; border-radius:14px!important; background:#fff!important; }
            [class*="st-key-progress_stage_"] div[role="radiogroup"] label:has(input:checked), [class*="st-key-progress_status_"] div[role="radiogroup"] label:has(input:checked) { border-color:#9c80c0!important; background:#f3e8ff!important; box-shadow:none!important; }
            [class*="st-key-progress_stage_"] p, [class*="st-key-progress_status_"] p { font:650 .69rem/1.2 'Noto Sans SC',sans-serif!important; }
            [class*="st-key-progress_save_"], [class*="st-key-next_event_edit_"], [class*="st-key-notes_save_"] { display:flex; justify-content:flex-end; }
            [class*="st-key-progress_save_"] button, [class*="st-key-next_event_edit_"] button, [class*="st-key-notes_save_"] button { min-height:42px!important; padding:9px 18px!important; border:0!important; border-radius:999px!important; background:#171717!important; color:#fff!important; font:700 .7rem/1 'Noto Sans SC',sans-serif!important; transition:.2s ease!important; }
            [class*="st-key-progress_save_"] button *, [class*="st-key-next_event_edit_"] button *, [class*="st-key-notes_save_"] button * { color:#fff!important; fill:#fff!important; }
            [class*="st-key-progress_save_"] button:hover, [class*="st-key-next_event_edit_"] button:hover, [class*="st-key-notes_save_"] button:hover { transform:translateY(-2px)!important; }
            [class*="st-key-next_event_card_"] input, [class*="st-key-next_event_card_"] div[data-baseweb="select"]>div { border:0!important; border-radius:15px!important; background:rgba(255,255,255,.72)!important; box-shadow:none!important; }
            [class*="st-key-next_event_card_"] label p { color:#62576d!important; font-size:.68rem!important; font-weight:650!important; }
            [class*="st-key-interview_notes_"] textarea { min-height:150px!important; border:0!important; border-radius:20px!important; background:rgba(255,255,255,.76)!important; padding:17px!important; line-height:1.7!important; }
            div[data-testid="stDialog"] > div[role="dialog"] { max-width:900px!important; border-radius:42px!important; padding:12px!important; box-shadow:0 30px 70px rgba(0,0,0,.12)!important; }
            div[data-testid="stDialog"] h2 { font-family:'Gaegu','Noto Sans SC',sans-serif!important; font-size:2.2rem!important; }
            .stage-dialog-intro { margin:-8px 0 18px; color:#8d8b86; font:600 .7rem/1.5 'Noto Sans SC',sans-serif; }
            .stage-dialog-label { margin-bottom:8px; font:700 1.25rem/1 'Gaegu',cursive; color:#666; }
            [class*="st-key-dialog_date_card_"], [class*="st-key-dialog_time_card_"], [class*="st-key-dialog_detail_card_"] { height:100%; padding:20px!important; border:0!important; border-radius:26px!important; }
            [class*="st-key-dialog_date_card_"] { background:#dff2e7!important; }
            [class*="st-key-dialog_time_card_"] { background:#ffe8d6!important; }
            [class*="st-key-dialog_detail_card_"] { background:#f3e8ff!important; }
            div[data-testid="stDialog"] input, div[data-testid="stDialog"] textarea, div[data-testid="stDialog"] div[data-baseweb="select"]>div { border:0!important; border-radius:14px!important; background:rgba(255,255,255,.7)!important; }
            [class*="st-key-dialog_save_"] { display:flex; justify-content:center; margin-top:20px; }
            [class*="st-key-dialog_save_"] button { min-width:230px!important; min-height:52px!important; border:0!important; border-radius:999px!important; background:#171717!important; color:#fff!important; font-weight:700!important; }
            @media(max-width:900px){ .progress-detail-grid,.notes-layout{grid-template-columns:1fr}.notes-layout .notes-heading{grid-column:auto}.detail-timeline{grid-template-columns:repeat(9,90px)} }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.dialog("edit this stage ↓", width="large")
def _render_stage_editor(job: dict[str, Any], stage: str, make_current_default: bool = False) -> None:
    event = _event_map(job).get(stage) or {}
    event_status = _text(event.get("stage_status"))
    if event_status not in PROGRESS_STATE_OPTIONS:
        event_status = "已完成" if event_status == "已跳过" else "已结束" if event_status == "未通过" else "准备中"

    scheduled = _parse_datetime(event.get("scheduled_at"))
    changed = _parse_datetime(event.get("status_changed_at")) or _parse_datetime(event.get("event_date"))
    now = datetime.now().replace(second=0, microsecond=0)
    widget_key = f"{job['id']}_{stage}"

    st.markdown(
        f'<p class="stage-dialog-intro">编辑「{_safe(stage)}」的计划时间、状态记录与备注。所有时间后期都可以再次修改。</p>',
        unsafe_allow_html=True,
    )
    date_col, time_col, detail_col = st.columns(3, gap="medium")
    with date_col:
        with st.container(key=f"dialog_date_card_{widget_key}", border=True):
            st.markdown('<div class="stage-dialog-label">pick a date ↓</div>', unsafe_allow_html=True)
            has_schedule = st.toggle("已收到具体安排", value=bool(scheduled), key=f"has_schedule_{widget_key}")
            planned_date = st.date_input(
                "计划日期",
                value=(scheduled or now).date(),
                disabled=not has_schedule,
                key=f"planned_date_{widget_key}",
            )
            record_date = st.date_input(
                "状态记录日期",
                value=(changed or now).date(),
                key=f"record_date_{widget_key}",
                help="默认使用状态更新时的当前日期，也可以手动修改。",
            )
    with time_col:
        with st.container(key=f"dialog_time_card_{widget_key}", border=True):
            st.markdown('<div class="stage-dialog-label">at what time? ↓</div>', unsafe_allow_html=True)
            planned_time = st.time_input(
                "计划时间",
                value=(scheduled or now.replace(hour=9, minute=0)).time(),
                disabled=not has_schedule,
                step=900,
                key=f"planned_time_{widget_key}",
            )
            record_time = st.time_input(
                "状态记录时间",
                value=(changed or now).time(),
                step=300,
                key=f"record_time_{widget_key}",
            )
    with detail_col:
        with st.container(key=f"dialog_detail_card_{widget_key}", border=True):
            st.markdown('<div class="stage-dialog-label">stage details ↓</div>', unsafe_allow_html=True)
            selected_status = st.selectbox(
                "节点状态",
                PROGRESS_STATE_OPTIONS,
                index=_option_index(PROGRESS_STATE_OPTIONS, event_status),
                key=f"dialog_status_{widget_key}",
            )
            node_notes = st.text_area(
                "节点备注",
                value=_text(event.get("notes")),
                height=112,
                placeholder="例如：线上面试；准备 Case；补充 SQL 案例",
                key=f"dialog_notes_{widget_key}",
            )
            make_current = st.toggle(
                "同步为当前阶段",
                value=make_current_default,
                key=f"make_current_{widget_key}",
            )

    with st.container(key=f"dialog_save_{widget_key}"):
        if st.button("保存节点  →", key=f"save_stage_event_{widget_key}"):
            try:
                original_status = _text(event.get("stage_status"))
                status_changed_at = _join_datetime(record_date, record_time)
                if selected_status != original_status and not changed:
                    status_changed_at = now.strftime("%Y-%m-%dT%H:%M")
                update_application_stage_event(
                    job_id=int(job["id"]),
                    stage=stage,
                    stage_status=selected_status,
                    scheduled_at=_join_datetime(planned_date, planned_time) if has_schedule else "",
                    status_changed_at=status_changed_at,
                    notes=node_notes,
                    make_current=make_current,
                )
                st.session_state["job_workspace_flash"] = ("success", f"{stage}已更新。")
                st.session_state["job_workspace_requested_job_id"] = int(job["id"])
                st.rerun()
            except Exception as error:
                st.error(str(error))


def _render_update_mode(all_jobs: list[dict[str, Any]]) -> None:
    job = _selected_job(all_jobs)
    if not job:
        st.info("目前还没有职位记录，请先进入“新增职位”。")
        return

    _inject_progress_detail_css()
    _render_update_summary(job)
    job_id = int(job["id"])
    record_key = f"update_{job_id}"
    current_stage = _text(job.get("status"))
    if current_stage not in PROGRESS_STAGE_OPTIONS:
        current_stage = "准备投递"
    current_status = _text(job.get("current_stage_status"))
    if current_status not in PROGRESS_STATE_OPTIONS:
        current_status = "已结束" if current_status in {"未通过", "已跳过"} else "进行中"

    events = _event_map(job)
    scheduled_events = []
    for stage in PIPELINE_STAGES:
        event = events.get(stage) or {}
        scheduled_at = _parse_datetime(event.get("scheduled_at"))
        if scheduled_at:
            scheduled_events.append((scheduled_at, stage, event))
    future_events = [item for item in scheduled_events if item[0] >= datetime.now()]
    next_item = min(future_events, default=None, key=lambda item: item[0])
    if not next_item:
        current_event = events.get(current_stage) or {}
        current_scheduled = _parse_datetime(current_event.get("scheduled_at"))
        if current_scheduled:
            next_item = (current_scheduled, current_stage, current_event)

    left, right = st.columns([1.15, .85], gap="large")
    with left:
        with st.container(key=f"progress_main_card_{record_key}", border=False):
            st.markdown(
                '<div class="progress-eyebrow">Current Progress</div><div class="progress-card-title">当前进度</div><p class="progress-card-copy">只保留你现在走到哪一步，以及这一阶段的状态。</p>',
                unsafe_allow_html=True,
            )
            selected_stage = st.pills(
                "当前阶段",
                PROGRESS_STAGE_OPTIONS,
                default=current_stage,
                key=f"progress_stage_{record_key}",
            ) or current_stage
            selected_status = st.pills(
                "当前状态",
                PROGRESS_STATE_OPTIONS,
                default=current_status,
                key=f"progress_status_{record_key}",
            ) or current_status
            with st.container(key=f"progress_save_{record_key}"):
                if st.button("保存当前进度  →", type="primary", key=f"save_current_progress_{record_key}"):
                    event = events.get(selected_stage) or {}
                    status_changed = selected_stage != current_stage or selected_status != current_status
                    try:
                        update_application_stage_event(
                            job_id=job_id,
                            stage=selected_stage,
                            stage_status=selected_status,
                            scheduled_at=_text(event.get("scheduled_at")),
                            status_changed_at=(datetime.now().strftime("%Y-%m-%dT%H:%M") if status_changed else _text(event.get("status_changed_at")) or datetime.now().strftime("%Y-%m-%dT%H:%M")),
                            notes=_text(event.get("notes")),
                            make_current=True,
                        )
                        st.session_state["job_workspace_flash"] = ("success", "当前进度已保存，并自动记录更新时间。")
                        st.session_state["job_workspace_requested_job_id"] = job_id
                        st.rerun()
                    except Exception as error:
                        st.error(str(error))

    with right:
        current_index = PIPELINE_STAGES.index(current_stage) if current_stage in PIPELINE_STAGES else -1
        available_schedule_stages = PIPELINE_STAGES[max(current_index, 0):]
        suggested_stage = (
            PIPELINE_STAGES[current_index + 1]
            if current_status == "已完成" and current_index + 1 < len(PIPELINE_STAGES)
            else current_stage if current_stage in available_schedule_stages
            else available_schedule_stages[0]
        )
        event_stage = next_item[1] if next_item else suggested_stage
        if event_stage not in available_schedule_stages:
            event_stage = suggested_stage
        with st.container(key=f"next_event_card_{record_key}", border=False):
            st.markdown(
                """
                <div>
                    <div class="progress-eyebrow">Next Event</div>
                    <div class="progress-card-title">下一轮安排</div>
                    <p class="progress-card-copy">收到通知时在这里直接填写；没有时间就留空，不影响进度。</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            schedule_stage = st.selectbox(
                "安排阶段",
                available_schedule_stages,
                index=_option_index(available_schedule_stages, event_stage),
                key=f"schedule_stage_{record_key}",
            )
            schedule_event = events.get(schedule_stage) or {}
            scheduled_value = _parse_datetime(schedule_event.get("scheduled_at"))
            schedule_enabled = st.toggle(
                "已收到具体时间",
                value=bool(scheduled_value),
                key=f"schedule_enabled_{record_key}_{schedule_stage}",
            )
            schedule_date_col, schedule_time_col = st.columns(2, gap="small")
            with schedule_date_col:
                schedule_date = st.date_input(
                    "日期",
                    value=(scheduled_value or datetime.now()).date(),
                    disabled=not schedule_enabled,
                    key=f"schedule_date_{record_key}_{schedule_stage}",
                )
            with schedule_time_col:
                schedule_time = st.time_input(
                    "时间",
                    value=(scheduled_value or datetime.now().replace(hour=9, minute=0)).time(),
                    disabled=not schedule_enabled,
                    step=900,
                    key=f"schedule_time_{record_key}_{schedule_stage}",
                )
            with st.container(key=f"next_event_edit_{record_key}"):
                if st.button("保存时间  →", type="primary", key=f"save_next_event_{record_key}"):
                    try:
                        existing_status = _text(schedule_event.get("stage_status"))
                        if existing_status not in PROGRESS_STATE_OPTIONS:
                            existing_status = current_status if schedule_stage == current_stage else "准备中"
                        update_application_stage_event(
                            job_id=job_id,
                            stage=schedule_stage,
                            stage_status=existing_status,
                            scheduled_at=_join_datetime(schedule_date, schedule_time) if schedule_enabled else "",
                            status_changed_at=_text(schedule_event.get("status_changed_at")),
                            notes=_text(schedule_event.get("notes")),
                            make_current=False,
                        )
                        st.session_state["job_workspace_flash"] = ("success", f"{schedule_stage}时间已保存。")
                        st.session_state["job_workspace_requested_job_id"] = job_id
                        st.rerun()
                    except Exception as error:
                        st.error(str(error))

    timeline_html = []
    current_index = PIPELINE_STAGES.index(current_stage) if current_stage in PIPELINE_STAGES else -1
    for stage_index, stage in enumerate(PIPELINE_STAGES):
        event = events.get(stage) or {}
        if stage_index < current_index:
            visual = "done"
        elif stage_index == current_index:
            visual = "done" if current_status == "已完成" else "ended" if current_status == "已结束" else "current"
        else:
            visual = ""
        symbol = "✓" if visual == "done" else "×" if visual == "ended" else ""
        node_date = _parse_datetime(event.get("status_changed_at")) or _parse_datetime(event.get("event_date"))
        date_label = node_date.strftime("%m.%d") if node_date else "待添加"
        timeline_html.append(
            f'<div class="detail-step {visual}"><div class="detail-step-label">{_safe(stage)}</div><span class="detail-step-node">{symbol}</span><div class="detail-step-date">{_safe(date_label)}</div></div>'
        )
    st.markdown(
        f'<div class="timeline-panel"><div class="progress-eyebrow">Timeline</div><div class="progress-card-title">申请记录</div><div class="detail-timeline">{"".join(timeline_html)}</div><p class="timeline-tip">时间轴会跟随“当前进度”自动更新，不需要逐个维护</p></div>',
        unsafe_allow_html=True,
    )

    with st.container(key=f"notes_card_{record_key}", border=False):
        st.markdown(
            '<div class="notes-layout"><div class="notes-heading"><div class="progress-eyebrow">Interview Notes</div><div class="progress-card-title">面试记录</div><p>复盘这一轮发生了什么，也记下下一轮需要准备什么。</p></div></div>',
            unsafe_allow_html=True,
        )
        interview_notes = st.text_area(
            "面试记录",
            value=_text(job.get("notes")),
            height=170,
            placeholder="面试复盘……\n\n下一轮准备……",
            label_visibility="collapsed",
            key=f"interview_notes_{record_key}",
        )
        with st.container(key=f"notes_save_{record_key}"):
            if st.button("保存面试记录  →", type="primary", key=f"save_interview_notes_{record_key}"):
                try:
                    update_application_interview_notes(job_id, interview_notes)
                    st.session_state["job_workspace_flash"] = ("success", "面试记录已保存。")
                    st.session_state["job_workspace_requested_job_id"] = job_id
                    st.rerun()
                except Exception as error:
                    st.error(str(error))


# =========================================================
# New application mode
# =========================================================
def _render_new_mode() -> None:
    nonce = int(st.session_state.get("job_workspace_new_nonce", 0))
    record_key = f"new_{nonce}"

    outer_left, form_column, outer_right = st.columns([0.7, 5, 0.7])
    del outer_left, outer_right
    with form_column:
        with st.form(key=f"new_application_form_{record_key}", clear_on_submit=False):
            with st.container(key=f"new_role_card_{record_key}", border=True):
                st.markdown(
                    '<div class="journey-section-title"><strong>role details ↓</strong><span>填写岗位的基础信息，申请进度稍后再更新</span></div>',
                    unsafe_allow_html=True,
                )
                row_one_left, row_one_right = st.columns(2, gap="large")
                with row_one_left:
                    company = st.text_input("公司名称 *", placeholder="例如：Northstar Commerce")
                with row_one_right:
                    position = st.text_input("岗位名称 *", placeholder="例如：TET管理培训生—综合方向")

                row_two_left, row_two_right = st.columns(2, gap="large")
                with row_two_left:
                    location = st.text_input("工作地点", placeholder="例如：北京、上海")
                with row_two_right:
                    target_direction = st.text_input("目标方向", placeholder="例如：招聘运营／商业分析")

                row_three_left, row_three_right = st.columns(2, gap="large")
                with row_three_left:
                    deadline = st.text_input("申请截止日期", placeholder="2026-08-15")
                with row_three_right:
                    application_url = st.text_input("投递官网链接", placeholder="https://...")

                job_description = st.text_area(
                    "完整 JD *",
                    height=108,
                    placeholder="粘贴完整职位描述，后续将用于简历定制和面试问题生成。",
                )

            with st.container(key="create_application_button"):
                submitted = st.form_submit_button("创建职位  →", type="primary", use_container_width=False)

    if not submitted:
        return

    try:
        cleaned_company = _text(company)
        cleaned_position = _text(position)
        if not cleaned_company:
            raise ValueError("请填写公司名称。")
        if not cleaned_position:
            raise ValueError("请填写岗位名称。")
        cleaned_jd = _text(job_description)
        if not cleaned_jd:
            raise ValueError("请粘贴完整 JD，后续简历定制和面试准备会使用这部分内容。")

        saved_id = save_job_application(
            job_id=None,
            company=cleaned_company,
            position=cleaned_position,
            location=_text(location),
            application_url=_validate_url(application_url),
            job_description=cleaned_jd,
            target_direction=_text(target_direction),
            status="准备投递",
            current_stage_status="准备中",
            deadline=_normalise_date(deadline, "申请截止日期"),
            stage_date="",
            next_action="",
            notes="",
            resume_status="尚未开始",
            interview_prep_status="尚未开始",
        )

        st.session_state["job_workspace_flash"] = ("success", "新职位已建立，并已加入申请总览。")
        st.session_state["job_workspace_new_nonce"] = nonce + 1
        st.session_state["job_workspace_force_mode"] = "更新申请"
        st.session_state["job_workspace_requested_job_id"] = int(saved_id)
        st.rerun()
    except Exception as error:
        st.error(str(error))


# =========================================================
# Public renderer
# =========================================================
def render_job_application_workspace(
    jobs: list[dict[str, Any]] | None = None,
    status_options: list[str] | None = None,
) -> None:
    """Render the merged application overview, update, and creation workspace."""
    del jobs, status_options

    _consume_timeline_action()
    _consume_query_request()
    _inject_workspace_css()
    all_jobs = get_job_applications()

    forced_mode = st.session_state.pop("job_workspace_force_mode", None)
    if forced_mode:
        st.session_state["job_workspace_mode"] = forced_mode

    if "job_workspace_mode" not in st.session_state:
        st.session_state["job_workspace_mode"] = "申请总览"

    with st.container(key="job_application_panel", border=True):
        st.markdown('<span class="job-application-panel-marker"></span>', unsafe_allow_html=True)
        st.markdown(
            """
            <div class="journey-heading">
                <h1>application journey</h1>
            </div>
            """,
            unsafe_allow_html=True,
        )

        mode = st.radio(
            "页面模式",
            ["申请总览", "新增职位", "更新申请"],
            horizontal=True,
            label_visibility="collapsed",
            key="job_workspace_mode",
        )

        flash = st.session_state.pop("job_workspace_flash", None)
        if flash:
            level, message = flash
            if level == "success":
                st.success(message)
            else:
                st.error(message)

        toast = st.session_state.pop("job_workspace_toast", None)
        if toast:
            level, message = toast
            st.toast(message, icon="↩️" if level == "success" else "⚠️")

        if mode == "申请总览":
            _render_overview(all_jobs)
        elif mode == "更新申请":
            _render_update_mode(all_jobs)
        else:
            _render_new_mode()
