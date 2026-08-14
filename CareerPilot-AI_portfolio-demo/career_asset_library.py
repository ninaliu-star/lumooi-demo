"""职业资产库独立模块。

从原 app(1).py 中提取，包含完整三层交互界面：
1. 经历分类集合页
2. 分类内经历选择页
3. 职业资产画布与资产详情抽屉

数据仍由现有 database.py 提供。
"""

import hashlib
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from demo_database import get_experience_assets, get_experience_rules


COMPONENT_DIR = Path(__file__).with_name("career_asset_component")
CAREER_ASSET_COMPONENT = components.declare_component(
    "career_asset_library_v0802",
    path=str(COMPONENT_DIR),
)


def _compact_name(experience):
    """Return a short display name for an experience cover card."""
    code = (experience.get("experience_code") or "").upper()
    aliases = {
        "CP": "CareerPilot", "CAT": "HR Tech 咨询", "WD": "水滴筹",
        "XN": "HR 研究", "CB": "无人配送项目", "EY": "EY",
        "NDC": "国家级大创", "MZY": "人口经济学", "SOHU": "Sohu", "FESCO": "FESCO",
    }
    if code in aliases:
        return aliases[code]

    alternate_name = (experience.get("alternate_name") or "").strip()
    if alternate_name:
        return alternate_name

    return (experience.get("organization") or "Experience").strip()


def _virtual_logo(experience):
    """Create a simple virtual logo instead of using a real company logo."""
    code = (experience.get("experience_code") or "").upper()
    name = _compact_name(experience).lower()

    logos = {"CP":"◉", "CAT":"◇", "WD":"♡", "XN":"▤", "CB":"⌁", "EY":"E", "NDC":"◎", "MZY":"∿", "SOHU":"S", "FESCO":"F"}
    if code in logos:
        return logos[code]
    return "◌"


def _experience_palette(experience):
    """Stable pastel cover-card palette."""
    code = (experience.get("experience_code") or "").upper()
    palettes = {
        "CP":{"bg":"#E8E2FF","accent":"#7052B8"}, "CAT":{"bg":"#FFE6D2","accent":"#C76F43"},
        "WD":{"bg":"#DDF3E7","accent":"#3C946C"}, "EY":{"bg":"#FFF0CF","accent":"#A87919"},
        "SOHU":{"bg":"#DCEBFF","accent":"#3976C8"}, "FESCO":{"bg":"#E9E1D7","accent":"#786B5A"},
        "CB":{"bg":"#FFE4E7","accent":"#C94E65"}, "NDC":{"bg":"#EFE4FF","accent":"#8254F5"},
        "XN":{"bg":"#D9F0F9","accent":"#2E829F"}, "MZY":{"bg":"#ECE8E1","accent":"#776B5D"},
    }
    return palettes.get(code, {"bg": "#F4F0E8", "accent": "#9A8D78"})


def _experience_collection(experience):
    """Map a verified Experience Bank record into one of four UI collections."""
    code = (experience.get("experience_code") or "").strip().upper()
    code_map = {
        "WD":"internship", "EY":"internship", "SOHU":"internship", "FESCO":"internship",
        "CP":"project", "CAT":"project", "CB":"competition", "NDC":"competition",
        "XN":"research", "MZY":"research",
    }
    if code in code_map:
        return code_map[code]

    identity_text = " ".join(
        str(experience.get(field) or "").strip().lower()
        for field in (
            "organization",
            "alternate_name",
            "experience_type",
            "role",
            "team",
        )
    )

    if any(keyword in identity_text for keyword in ("实习", "intern")):
        return "internship"
    if any(keyword in identity_text for keyword in ("竞赛", "比赛", "competition", "challenge")):
        return "competition"
    if any(keyword in identity_text for keyword in ("课题组", "研究助理", "科研", "research", "大创")):
        return "research"
    return "project"


def _build_experience_bank_payload(experiences):
    """Build a complete payload using real database records only."""
    prepared = []

    # Prefer structured records with an experience_code over legacy duplicates.
    ordered = sorted(
        experiences,
        key=lambda item: (
            0 if (item.get("experience_code") or "").strip() else 1,
            item.get("id") or 0,
        ),
    )

    seen_keys = set()

    for experience in ordered:
        item = dict(experience)
        code = (item.get("experience_code") or "").strip().upper()
        name = _compact_name(item)

        # Merge legacy rows into their structured experience records. Some old
        # database rows may not yet have an experience_code, so infer the UI code
        # from stable organization/name fields before assigning card positions.
        identity_text = " ".join(
            str(item.get(field) or "").strip().lower()
            for field in (
                "organization",
                "alternate_name",
                "team",
                "display_name",
            )
        )

        ui_code = code

        if ui_code:
            dedupe_key = ui_code
            item["experience_code"] = ui_code
        else:
            dedupe_key = (
                (item.get("organization") or "").strip().lower(),
                (item.get("role") or "").strip().lower(),
                item.get("start_date") or "",
                item.get("end_date") or "",
            )

        if dedupe_key in seen_keys:
            continue

        seen_keys.add(dedupe_key)
        item["display_name"] = name
        item["virtual_logo"] = _virtual_logo(item)
        item["palette"] = _experience_palette(item)
        item["collection"] = _experience_collection(item)
        item["assets"] = get_experience_assets(item["id"])
        item["rules"] = get_experience_rules(item["id"])
        prepared.append(item)

    prepared.sort(
        key=lambda item: item.get("start_date") or "",
        reverse=True,
    )

    return prepared


def render_experience_bank_canvas(experiences):
    """Render the Experience Bank as a true full-screen interactive canvas."""
    payload = _build_experience_bank_payload(experiences)
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    studio_value = st.query_params.get("studio", "")
    if isinstance(studio_value, list):
        studio_value = studio_value[0] if studio_value else ""
    studio_mode = str(studio_value or "").strip().lower()
    initial_studio_json = json.dumps(
        {
            "mode": "focus" if studio_mode == "focus" else "collection",
            "experienceCode": "CP",
        },
        ensure_ascii=False,
    )

    component_html = r"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Gaegu:wght@400;700&display=swap');

      * { box-sizing: border-box; }

      :root {
        --ink: #24221f;
        --muted: #7b756f;
        --line: rgba(69, 59, 49, .12);
        --glass: rgba(255, 255, 255, .72);
        --glass-strong: rgba(255, 255, 255, .92);
        --shadow: 0 24px 70px rgba(91, 69, 48, .15);
      }

      html,
      body {
        width: 100%;
        height: 100%;
        min-height: 100dvh;
        margin: 0;
        overflow: hidden;
        overscroll-behavior: none;
        background: #fffafa;
      }

      body {
        color: var(--ink);
        font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
      }

      button,
      input {
        font: inherit;
      }

      button,
      a {
        -webkit-tap-highlight-color: transparent;
      }

      .app {
        position: fixed;
        inset: 0;
        width: 100vw;
        height: 100dvh;
        min-height: 100dvh;
        overflow: hidden;
        isolation: isolate;
        background:
          radial-gradient(circle at 7% 6%, rgba(193, 219, 255, .78), transparent 31%),
          radial-gradient(circle at 92% 8%, rgba(255, 213, 181, .75), transparent 31%),
          radial-gradient(circle at 79% 91%, rgba(222, 209, 255, .62), transparent 30%),
          radial-gradient(circle at 12% 91%, rgba(198, 237, 215, .54), transparent 28%),
          #fbfaf7;
      }

      .app::before {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        opacity: .34;
        background-image:
          linear-gradient(rgba(255,255,255,.16) 1px, transparent 1px),
          linear-gradient(90deg, rgba(255,255,255,.14) 1px, transparent 1px);
        background-size: 36px 36px;
        mask-image: radial-gradient(circle at center, black, transparent 78%);
      }

      .screen {
        position: absolute;
        inset: 0;
        min-width: 0;
        min-height: 0;
        opacity: 0;
        transform: translate3d(28px, 0, 0) scale(.992);
        pointer-events: none;
        transition: opacity .18s ease-out, transform .18s ease-out;
      }

      .screen.active {
        opacity: 1;
        transform: translate3d(0, 0, 0) scale(1);
        pointer-events: auto;
      }

      .home-link,
      .pill-button,
      .icon-button,
      .bottom-nav-button {
        border: 1px solid var(--line);
        background: rgba(255,255,255,.72);
        color: var(--ink);
        box-shadow: 0 8px 24px rgba(82, 65, 49, .06);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
      }

      .home-link {
        position: absolute;
        top: 22px;
        left: 24px;
        z-index: 50;
        display: inline-flex;
        align-items: center;
        gap: 7px;
        min-height: 38px;
        padding: 8px 13px;
        border-radius: 999px;
        text-decoration: none;
        font-size: 12px;
        font-weight: 700;
        transition: transform .18s ease, background .18s ease;
      }

      .home-link:hover {
        transform: translateY(-2px);
        background: rgba(255,255,255,.94);
      }

      .eyebrow {
        color: var(--muted);
        font-size: 13px;
        font-weight: 800;
        letter-spacing: .20em;
        text-transform: uppercase;
      }

      .cute-title {
        margin: 8px 0 0;
        color: var(--ink);
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          sans-serif;
        font-size: clamp(38px, 5.1vw, 70px);
        line-height: .95;
        letter-spacing: .025em;
        font-weight: 700;
      }

      /* =====================================================
         Screen 0 — 极简分类横向浏览
      ===================================================== */

      .collection-screen {
        --collection-card-width: clamp(278px, 20.8vw, 326px);
        position: absolute;
        inset: 0;
        overflow: hidden;
        background: #fffafa;
        user-select: none;
        -webkit-user-select: none;
      }

      .collection-heading {
        position: absolute;
        top: clamp(40px, 6vh, 52px);
        left: 50%;
        z-index: 12;
        width: min(760px, 84vw);
        transform: translateX(-50%);
        text-align: center;
        pointer-events: none;
      }

      .collection-heading h1 {
        margin: 0;
        color: #111111;
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          sans-serif;
        font-size: clamp(42px, 4vw, 56px);
        line-height: .96;
        font-weight: 700;
        letter-spacing: .04em;
      }

      .collection-heading p {
        margin: 8px 0 0;
        color: #92908d;
        font-size: clamp(10px, .82vw, 12px);
        line-height: 1.45;
        font-weight: 500;
      }

      .collection-viewport {
        position: absolute;
        top: clamp(118px, 16vh, 136px);
        left: 0;
        right: 0;
        bottom: 62px;
        z-index: 10;
        overflow-x: auto;
        overflow-y: hidden;
        overscroll-behavior-x: contain;
        scroll-snap-type: x mandatory;
        scroll-behavior: smooth;
        scrollbar-width: none;
        -webkit-overflow-scrolling: touch;
        touch-action: pan-x;
        cursor: default;
      }

      .collection-viewport::-webkit-scrollbar { display: none; }

      .collection-track {
        position: relative;
        display: flex;
        align-items: center;
        gap: clamp(26px, 2.65vw, 36px);
        width: max-content;
        min-height: 100%;
        padding: 0 max(24px, calc((100vw - var(--collection-card-width)) / 2));
      }

      .collection-card {
        position: relative;
        width: var(--collection-card-width);
        height: clamp(286px, 39vh, 338px);
        flex: 0 0 auto;
        overflow: hidden;
        padding: clamp(22px, 1.9vw, 28px);
        border: 0;
        border-radius: clamp(28px, 2.5vw, 36px);
        background: var(--collection-bg);
        color: #171717;
        text-align: left;
        cursor: pointer;
        scroll-snap-align: center;
        scroll-snap-stop: always;
        box-shadow: 0 21px 48px rgba(40, 38, 34, .07);
        opacity: .62;
        transform: scale(.955);
        transition:
          transform .28s cubic-bezier(.2,.78,.2,1),
          opacity .24s ease,
          box-shadow .24s ease;
        -webkit-tap-highlight-color: transparent;
      }

      .collection-card.active {
        opacity: 1;
        transform: scale(1);
        box-shadow: 0 26px 62px rgba(40, 38, 34, .10);
      }

      .collection-card:hover,
      .collection-card:focus-visible {
        opacity: 1;
        outline: none;
      }

      .collection-kicker,
      .collection-title,
      .collection-description,
      .collection-stats,
      .collection-chart,
      .collection-preview,
      .collection-enter {
        position: relative;
        z-index: 2;
      }

      .collection-kicker {
        color: rgba(30,30,30,.48);
        font-size: 9px;
        font-weight: 850;
        letter-spacing: .13em;
        text-transform: uppercase;
      }

      .collection-title {
        margin-top: 9px;
        color: #141414;
        font-family:
          "PingFang SC",
          "Microsoft YaHei",
          "Noto Sans CJK SC",
          sans-serif;
        font-size: clamp(25px, 2.05vw, 31px);
        line-height: 1.08;
        font-weight: 800;
        letter-spacing: -.025em;
      }

      .collection-description {
        margin-top: 7px;
        color: rgba(31,31,31,.57);
        font-size: 9px;
        line-height: 1.5;
        font-weight: 650;
      }

      .collection-stats {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 9px;
        margin-top: clamp(15px, 1.8vh, 19px);
      }

      .collection-stat {
        min-height: 52px;
        padding: 10px 12px;
        border-radius: 15px;
        background: rgba(255,255,255,.62);
      }

      .collection-stat-label {
        color: rgba(30,30,30,.43);
        font-size: 7px;
        font-weight: 850;
        letter-spacing: .08em;
      }

      .collection-stat-value {
        margin-top: 5px;
        color: #171717;
        font-size: 16px;
        line-height: 1;
        font-weight: 850;
      }

      .collection-stat-value.accent { color: var(--collection-accent); }

      .collection-chart {
        height: clamp(46px, 6.1vh, 56px);
        margin-top: clamp(12px, 1.45vh, 15px);
      }

      .collection-chart svg {
        width: 100%;
        height: 100%;
        overflow: visible;
      }

      .collection-chart path {
        fill: none;
        stroke: var(--collection-accent);
        stroke-width: 4;
        stroke-linecap: round;
        stroke-linejoin: round;
      }

      .collection-preview {
        position: absolute;
        left: clamp(22px, 1.9vw, 28px);
        right: 54px;
        bottom: clamp(21px, 2.5vh, 27px);
        overflow: hidden;
        color: rgba(31,31,31,.64);
        font-family: "Gaegu", "Chalkboard SE", "Comic Sans MS", cursive;
        font-size: clamp(12px, .98vw, 14px);
        line-height: 1.4;
        letter-spacing: .02em;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .collection-enter {
        position: absolute;
        right: clamp(18px, 1.65vw, 23px);
        bottom: clamp(16px, 2vh, 21px);
        width: 31px;
        height: 31px;
        display: grid;
        place-items: center;
        border-radius: 50%;
        background: rgba(255,255,255,.72);
        color: #171717;
        font-size: 15px;
        font-weight: 900;
      }

      .collection-controls {
        position: absolute;
        left: 50%;
        bottom: 10px;
        z-index: 16;
        display: flex;
        align-items: center;
        gap: 18px;
        transform: translateX(-50%);
      }

      .collection-arrow {
        width: 38px;
        height: 38px;
        display: grid;
        place-items: center;
        border: 1px solid rgba(20,20,20,.10);
        border-radius: 50%;
        background: #fffafa;
        color: #171717;
        cursor: pointer;
        font-size: 16px;
        box-shadow: 0 9px 24px rgba(40,40,40,.055);
      }

      .collection-arrow:hover { transform: translateY(-1px); }

      .collection-progress {
        width: 102px;
        height: 2px;
        overflow: hidden;
        background: rgba(20,20,20,.08);
      }

      .collection-progress span {
        display: block;
        width: 25%;
        height: 100%;
        background: #171717;
        transform: translateX(0);
        transition: transform .28s cubic-bezier(.2,.78,.2,1);
      }

      .collection-back {
        position: absolute;
        top: 18px;
        left: 20px;
        z-index: 85;
        min-height: 34px;
        display: inline-flex;
        align-items: center;
        gap: 7px;
        padding: 7px 11px;
        border: 1px solid rgba(20,20,20,.10);
        border-radius: 999px;
        background: rgba(255,255,255,.88);
        color: #171717;
        cursor: pointer;
        font-size: 10px;
        font-weight: 800;
        box-shadow: 0 8px 24px rgba(30,30,30,.05);
      }

      .selector-collection-badge {
        position: absolute;
        top: 21px;
        right: 24px;
        z-index: 70;
        padding: 6px 10px;
        border-radius: 999px;
        background: rgba(248,248,247,.90);
        color: #7d7d7a;
        font-size: 8px;
        font-weight: 850;
        letter-spacing: .08em;
      }

      @media (max-width: 900px) {
        .collection-screen { --collection-card-width: min(64vw, 326px); }
        .collection-heading { top: 40px; }
        .collection-heading h1 { font-size: clamp(39px, 6vw, 49px); }
        .collection-viewport { top: 116px; bottom: 60px; }
        .collection-card { height: clamp(286px, 42vh, 334px); }
      }

      @media (max-width: 680px) {
        .collection-screen { --collection-card-width: 74vw; }
        .collection-heading { top: 32px; width: 92vw; }
        .collection-heading h1 { font-size: 39px; }
        .collection-heading p { font-size: 10px; }
        .collection-viewport { top: 108px; bottom: 58px; }
        .collection-track { gap: 20px; }
        .collection-card {
          height: 326px;
          padding: 23px;
          border-radius: 29px;
        }
        .collection-controls { bottom: 9px; }
        .selector-collection-badge { display: none; }
      }

      /* =====================================================
         Screen 1 — P1-style draggable experience selector
      ===================================================== */

      .selector-screen {
        position: absolute;
        inset: 0;
        overflow: hidden;
        background: #fffafa;
        user-select: none;
        -webkit-user-select: none;
      }

      .selector-screen::before {
        content: none;
      }

      .selector-brand {
        display: none !important;
        position: absolute;
        top: clamp(34px, 6vh, 62px);
        left: clamp(28px, 4.2vw, 68px);
        z-index: 70;
        color: #111111;
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          sans-serif;
        font-size: clamp(18px, 1.5vw, 23px);
        line-height: 1;
        font-weight: 700;
        letter-spacing: .04em;
        text-decoration: none;
        transform: rotate(-1.5deg);
        transition: transform .18s ease, opacity .18s ease;
      }

      .selector-brand:hover {
        opacity: .66;
        transform: rotate(-1.5deg) translateY(-2px);
      }

      .selector-heading {
        position: absolute;
        top: clamp(108px, 15vh, 170px);
        left: 50%;
        z-index: 26;
        width: min(720px, 58vw);
        transform: translateX(-50%);
        text-align: center;
        pointer-events: none;
      }

      .selector-title {
        margin: 0;
        color: #0f0f0f;
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          sans-serif;
        font-size: clamp(44px, 4.25vw, 64px);
        line-height: 1;
        font-weight: 700;
        letter-spacing: .055em;
      }

      .selector-subtitle {
        margin-top: 16px;
        color: #929292;
        font-size: clamp(13px, 1.15vw, 17px);
        line-height: 1.5;
        font-weight: 600;
        letter-spacing: .015em;
      }

      .selector-stage {
        position: absolute;
        inset: 0;
        overflow: hidden;
      }

      .selector-float-dot {
        position: absolute;
        z-index: 1;
        width: 9px;
        height: 9px;
        border-radius: 50%;
        background: rgba(25,25,25,.045);
        pointer-events: none;
      }
      .selector-float-dot.one { left: 41%; top: 11%; }
      .selector-float-dot.two { right: 29%; top: 31%; width: 6px; height: 6px; }
      .selector-float-dot.three { left: 29%; bottom: 18%; width: 7px; height: 7px; }
      .selector-float-dot.four { right: 38%; bottom: 8%; width: 11px; height: 11px; }

      .drop-zone {
        position: absolute;
        left: 50%;
        top: 66%;
        z-index: 10;
        width: clamp(250px, 20vw, 300px);
        aspect-ratio: 1 / 1;
        display: grid;
        place-items: center;
        padding: 28px;
        transform: translate(-50%, -50%) scale(1);
        border: 0;
        border-radius: 50%;
        background: transparent;
        box-shadow: none;
        transition:
          transform .22s cubic-bezier(.2,.8,.2,1),
          border-color .22s ease,
          background .22s ease,
          box-shadow .22s ease;
        pointer-events: none;
      }

      .drop-zone::before {
        content: none;
      }

      .drop-zone.active {
        transform: translate(-50%, -50%) scale(1.055);
        border-color: rgba(30,30,30,.34);
        background: rgba(248,248,247,.94);
        box-shadow:
          inset 0 0 0 1px rgba(255,255,255,.95),
          0 28px 86px rgba(25,25,25,.10),
          0 0 0 14px rgba(20,20,20,.025);
      }

      .drop-zone.accepted {
        transform: translate(-50%, -50%) scale(.95);
        border-color: rgba(30,30,30,.16);
        background: rgba(250,250,249,.98);
      }

      .drop-copy {
        display: none;
        position: relative;
        z-index: 2;
        color: rgba(41,41,41,.23);
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          sans-serif;
        font-size: clamp(20px, 1.65vw, 25px);
        line-height: 1.52;
        letter-spacing: .08em;
        text-align: center;
        transition: color .2s ease, transform .2s ease;
      }

      .drop-zone.active .drop-copy {
        color: rgba(25,25,25,.66);
        transform: scale(1.03);
      }

      .cover-stage {
        position: absolute;
        inset: 0;
        z-index: 20;
      }

      .experience-links {
        display: none;
        position: absolute;
        inset: 0;
        z-index: 2;
        width: 100%;
        height: 100%;
        overflow: visible;
        pointer-events: none;
      }

      .experience-link-path {
        fill: none;
        stroke: rgba(88, 74, 111, .34);
        stroke-width: 2;
        stroke-linecap: round;
        stroke-dasharray: 7 8;
        filter: drop-shadow(0 3px 8px rgba(73, 61, 92, .12));
      }

      .experience-link-dot {
        fill: rgba(255,255,255,.94);
        stroke: rgba(88, 74, 111, .44);
        stroke-width: 2;
      }

      .cover {
        position: absolute;
        left: var(--home-x);
        top: var(--home-y);
        width: clamp(190px, 14.8vw, 224px);
        height: clamp(250px, 29.5vh, 294px);
        padding: clamp(26px, 2vw, 32px) clamp(21px, 1.65vw, 25px);
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.9);
        border-radius: 32px;
        color: #171717;
        text-align: left;
        cursor: grab;
        touch-action: none;
        box-shadow: rgba(0, 0, 0, .05) 0 20px 50px;
        transform:
          translate(-50%, -50%)
          rotate(calc(var(--rotate) + var(--drag-r, 0deg)))
          scale(var(--cover-scale, 1));
        transform-origin: 50% 70%;
        transition:
          left .46s cubic-bezier(.22,.78,.22,1),
          top .46s cubic-bezier(.22,.78,.22,1),
          transform .26s cubic-bezier(.22,.78,.22,1),
          opacity .24s ease,
          filter .24s ease,
          box-shadow .22s ease;
        will-change: left, top, transform, opacity;
        -webkit-tap-highlight-color: transparent;
      }

      .cover.linked-cover {
        width: clamp(128px, 10vw, 155px);
        height: clamp(170px, 20.5vh, 204px);
        padding: clamp(14px, 1.15vw, 18px);
        border-radius: clamp(21px, 1.8vw, 27px);
      }

      .cover.linked-cover .cover-logo {
        left: clamp(14px, 1.05vw, 18px);
        bottom: clamp(54px, 6.4vh, 66px);
        font-size: clamp(23px, 2vw, 30px);
      }

      .cover.linked-cover .cover-name {
        left: clamp(14px, 1.05vw, 18px);
        right: 11px;
        bottom: clamp(32px, 3.8vh, 40px);
        font-size: clamp(15px, 1.25vw, 19px);
      }

      .cover.linked-cover .cover-role {
        left: clamp(14px, 1.05vw, 18px);
        right: 11px;
        bottom: clamp(18px, 2.15vh, 23px);
        font-size: clamp(6px, .5vw, 7.5px);
      }

      .cover.linked-cover .cover-date {
        left: clamp(14px, 1.05vw, 18px);
        bottom: 7px;
        font-size: 6px;
      }

      .cover::before {
        content: "";
        position: absolute;
        inset: 0;
        pointer-events: none;
        background:
          linear-gradient(145deg, rgba(255,255,255,.26), transparent 48%),
          radial-gradient(circle at 74% 16%, rgba(255,255,255,.22), transparent 34%);
      }

      .cover:hover,
      .cover:focus-visible {
        --cover-scale: 1.025;
        z-index: 60 !important;
        outline: none;
        box-shadow:
          0 34px 72px rgba(28,28,28,.13),
          inset 0 1px 0 rgba(255,255,255,.72);
      }

      .cover.dragging {
        --cover-scale: 1.075;
        z-index: 120 !important;
        cursor: grabbing;
        transition: none;
        box-shadow:
          0 42px 90px rgba(28,28,28,.18),
          inset 0 1px 0 rgba(255,255,255,.78);
      }

      .cover.drop-ready {
        --cover-scale: 1.025;
        box-shadow:
          0 30px 78px rgba(28,28,28,.15),
          0 0 0 5px rgba(255,255,255,.58),
          inset 0 1px 0 rgba(255,255,255,.84);
      }

      .cover.dropping {
        --cover-scale: .26;
        opacity: 0;
        filter: blur(3px);
        z-index: 130 !important;
        transition:
          left .34s cubic-bezier(.32,.72,.18,1),
          top .34s cubic-bezier(.32,.72,.18,1),
          transform .34s cubic-bezier(.32,.72,.18,1),
          opacity .26s ease,
          filter .26s ease;
      }

      .cover.fading-out {
        opacity: .18;
        filter: blur(1.4px);
        pointer-events: none;
      }

      .cover-kicker,
      .cover-logo,
      .cover-name,
      .cover-role,
      .cover-date {
        position: relative;
        z-index: 2;
      }

      .cover-kicker {
        color: rgba(0,0,0,.48);
        font-size: clamp(9px, .72vw, 11px);
        line-height: 1.2;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
      }

      .cover-logo {
        position: absolute;
        left: clamp(21px, 1.65vw, 25px);
        bottom: clamp(83px, 9.8vh, 98px);
        display: block;
        font-size: clamp(37px, 3.25vw, 48px);
        line-height: 1;
        filter: drop-shadow(0 5px 8px rgba(35,35,35,.08));
      }

      .cover-name {
        position: absolute;
        left: clamp(21px, 1.65vw, 25px);
        right: 14px;
        bottom: clamp(51px, 6vh, 61px);
        margin: 0;
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          sans-serif;
        font-size: clamp(28px, 2.45vw, 36px);
        line-height: 1.05;
        font-weight: 700;
        overflow-wrap: anywhere;
      }

      .cover-role {
        position: absolute;
        left: clamp(21px, 1.65vw, 25px);
        right: 14px;
        bottom: clamp(28px, 3.35vh, 34px);
        overflow: hidden;
        color: rgba(35,35,35,.58);
        font-size: clamp(8px, .66vw, 10px);
        line-height: 1.35;
        font-weight: 650;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .cover-date {
        position: absolute;
        left: clamp(21px, 1.65vw, 25px);
        right: 14px;
        bottom: 12px;
        color: rgba(35,35,35,.35);
        font-size: clamp(7px, .55vw, 8px);
        line-height: 1.2;
        font-weight: 650;
        letter-spacing: .025em;
      }

      .selector-hint {
        position: absolute;
        left: 50%;
        bottom: clamp(15px, 2.5vh, 28px);
        z-index: 18;
        transform: translateX(-50%);
        display: none;
        color: #a1a19f;
        font-size: 10px;
        line-height: 1.5;
        letter-spacing: .04em;
        white-space: nowrap;
        pointer-events: none;
      }

      .story-screen {
        background: #fffafa;
      }

      @media (max-width: 900px) {
        .selector-heading {
          top: 106px;
          width: min(590px, 72vw);
        }

        .selector-title {
          font-size: clamp(33px, 6.3vw, 52px);
        }

        .drop-zone {
          top: 62%;
          width: clamp(220px, 33vw, 300px);
        }

        .cover {
          width: clamp(160px, 22vw, 205px);
          height: clamp(220px, 29vh, 278px);
          border-radius: 30px;
        }
      }

      @media (max-width: 680px) {
        .selector-brand {
          top: 26px;
          left: 22px;
        }

        .selector-heading {
          top: 72px;
          width: 86vw;
        }

        .selector-subtitle {
          margin-top: 10px;
        }

        .drop-zone {
          top: 56%;
          width: 205px;
        }

        .cover {
          width: 142px;
          height: 184px;
          padding: 17px;
          border-radius: 25px;
        }

        .cover.linked-cover {
          width: 126px;
          height: 164px;
          padding: 14px;
        }

        .cover-logo {
          left: 18px;
          bottom: 73px;
          font-size: 31px;
        }

        .cover-name {
          left: 18px;
          bottom: 42px;
          font-size: 19px;
        }

        .cover-role {
          left: 18px;
          bottom: 23px;
          font-size: 8px;
        }

        .cover-date {
          display: none;
        }

        .selector-hint {
          bottom: 10px;
          font-size: 8px;
        }
      }

      /* =====================================================
         Screen 2 — P5-style experience overview
      ===================================================== */

      .story-screen {
        padding: 5px 8px 6px;
      }

      .story-shell {
        position: relative;
        width: 100%;
        height: 100%;
        min-width: 0;
        min-height: 0;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.52);
        border-radius: 19px;
        background: #fffafa;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.58);
      }

      .story-topbar {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        z-index: 30;
        min-height: 62px;
        display: grid;
        grid-template-columns: minmax(205px, 1fr) minmax(245px, 1.1fr) minmax(190px, .85fr);
        align-items: center;
        gap: 10px;
        padding: 6px 13px 5px;
        background: #fffafa;
        pointer-events: none;
      }

      .story-topbar > * { pointer-events: auto; }

      .experience-heading {
        display: flex;
        align-items: center;
        gap: 13px;
        min-width: 0;
      }

      .experience-logo {
        width: 39px;
        height: 39px;
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        border: 1px solid rgba(87,76,64,.10);
        border-radius: 50%;
        background: rgba(255,255,255,.84);
        color: var(--experience-accent, #5d9dff);
        box-shadow: 0 10px 28px rgba(77, 60, 45, .08);
        font-size: 19px;
      }

      .experience-copy { min-width: 0; }

      .experience-name {
        overflow: hidden;
        color: #22201e;
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          sans-serif;
        font-size: clamp(19px, 1.55vw, 24px);
        line-height: 1.05;
        font-weight: 700;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .experience-role {
        margin-top: 5px;
        overflow: hidden;
        color: #726c65;
        font-size: 11px;
        line-height: 1.45;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .experience-meta {
        margin-top: 7px;
        display: flex;
        flex-wrap: wrap;
        gap: 8px 14px;
        color: #857f78;
        font-size: 9.5px;
      }

      .experience-tags {
        display: flex;
        align-items: center;
        justify-content: center;
        flex-wrap: wrap;
        gap: 7px;
      }

      .experience-tag {
        min-height: 25px;
        display: inline-flex;
        align-items: center;
        padding: 5px 10px;
        border: 1px solid rgba(255,255,255,.65);
        border-radius: 999px;
        background: var(--tag-bg, rgba(255,255,255,.65));
        color: #5e5953;
        font-size: 9px;
        font-weight: 700;
        white-space: nowrap;
      }

      .top-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
      }

      .pill-button {
        min-height: 38px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        padding: 8px 13px;
        border-radius: 999px;
        cursor: pointer;
        font-size: 11px;
        font-weight: 750;
        transition: transform .18s ease, background .18s ease;
      }

      .pill-button:hover {
        transform: translateY(-2px);
        background: rgba(255,255,255,.95);
      }

      .story-stage {
        position: absolute;
        inset: 61px 0 42px;
        min-width: 0;
        min-height: 0;
        overflow: hidden;
      }

      .story-center {
        position: absolute;
        left: 50%;
        top: 50%;
        z-index: 7;
        width: min(760px, 84vw);
        transform: translate(-50%, -50%);
        text-align: center;
        pointer-events: none;
      }

      .story-center .bottom-nav { pointer-events: auto; }

      .story-center .cute-title {
        margin: 0;
        color: #111111;
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          sans-serif;
        font-size: clamp(42px, 4vw, 56px);
        line-height: .96;
        font-weight: 700;
        letter-spacing: .04em;
        text-shadow: none;
        animation: kinetic-hero-in .72s cubic-bezier(.23,1,.32,1) both;
      }

      .story-center .cute-title span {
        display: block;
        white-space: nowrap;
      }

      .center-doodles {
        display: none;
      }

      .doodle-line {
        position: absolute;
        left: 50%;
        bottom: 4px;
        width: 242px;
        height: 18px;
        transform: translateX(-50%) rotate(-1deg);
        border-top: 3px solid rgba(236, 126, 140, .72);
        border-radius: 50%;
      }

      .doodle-heart {
        position: absolute;
        left: calc(50% + 125px);
        bottom: 5px;
        color: rgba(236, 126, 140, .72);
        font-size: 22px;
        transform: rotate(10deg);
        animation: kinetic-heart 2.4s 1s ease-in-out infinite;
      }

      @keyframes kinetic-hero-in {
        from { opacity: 0; transform: translateY(18px) scale(.94); }
        to { opacity: 1; transform: translateY(0) scale(1); }
      }

      @keyframes kinetic-heart {
        0%, 18%, 100% { transform: rotate(10deg) scale(1); }
        8% { transform: rotate(10deg) scale(1.18); }
      }

      .center-arrow {
        margin-top: -2px;
        color: #3d3934;
        font-family: "Comic Sans MS", cursive;
        font-size: 25px;
        line-height: 1;
      }

      .center-caption {
        display: none;
      }

      .kinetic-annotation {
        position: absolute;
        z-index: 1;
        color: #aaa;
        font-family: "Gaegu", cursive;
        font-size: 18px;
        pointer-events: none;
        user-select: none;
      }
      .annotation-speed { top: 30%; left: 25%; }
      .annotation-managed { right: 25%; bottom: 30%; }
      .annotation-niche { top: 60%; left: 15%; transform: rotate(-10deg); }

      .kinetic-dot {
        position: absolute;
        z-index: 1;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #eee;
        opacity: .35;
        pointer-events: none;
        transition: transform .1s ease-out;
      }
      .dot-one { top: 10%; left: 40%; }
      .dot-two { bottom: 20%; left: 60%; }
      .dot-three { top: 80%; left: 5%; }
      .dot-four { top: 50%; right: 15%; }

      .asset-layer {
        position: absolute;
        inset: 0;
      }

      .asset-card {
        position: absolute;
        left: var(--x);
        top: var(--y);
        width: var(--card-w);
        min-height: var(--card-h);
        padding: 24px;
        border: 0;
        border-radius: 32px;
        background: var(--asset-bg, #ffffff);
        color: var(--ink);
        font-family: "Inter", "PingFang SC", sans-serif;
        text-align: left;
        cursor: grab;
        touch-action: none;
        opacity: var(--base-opacity, 1);
        box-shadow: 0 20px 50px rgba(0,0,0,.05);
        transform:
          translate3d(
            calc(-50% + var(--mx, 0px) + var(--drag-x, 0px)),
            calc(-50% + var(--my, 0px) + var(--drag-y, 0px)),
            0
          )
          rotate(calc(var(--angle) + var(--mr, 0deg)))
          scale(var(--scale, 1));
        transform-origin: center;
        backface-visibility: hidden;
        -webkit-backface-visibility: hidden;
        will-change: transform, opacity;
        contain: layout style;
        transition: transform .1s ease-out, opacity .22s ease, box-shadow .22s ease;
        z-index: var(--z, 2);
      }

      .asset-card.dragging {
        --scale: 1.05;
        cursor: grabbing;
        z-index: 100;
        transition: opacity .15s ease, box-shadow .15s ease;
        box-shadow: 0 28px 58px rgba(0,0,0,.10);
      }

      .asset-card.featured {
        --base-opacity: 1;
        --base-blur: 0px;
        --z: 12;
      }

      .asset-card:hover,
      .asset-card:focus-visible,
      .asset-card.pointer-near {
        --scale: 1.05;
        opacity: 1;
        box-shadow: 0 25px 55px rgba(0,0,0,.075);
        outline: none;
        z-index: 45;
      }

      .asset-card.selected {
        --scale: 1.065;
        opacity: 1;
        box-shadow:
          0 26px 48px rgba(70,54,40,.17),
          inset 0 1px 0 rgba(255,255,255,.70);
        z-index: 55;
      }

      .story-stage.has-selection .asset-card:not(.selected) {
        opacity: .14;
      }

      .decay-svg {
        display: none;
        position: absolute;
        inset: -12%;
        z-index: 0;
        width: 124%;
        height: 124%;
        overflow: visible;
        pointer-events: none;
        opacity: 0;
        visibility: hidden;
        transition: opacity .06s linear;
      }

      /* The expensive SVG displacement is rendered only for the nearest card.
         All other cards move using GPU-only transforms. */
      .asset-card.decay-active .decay-svg,
      .asset-card:hover .decay-svg,
      .asset-card.selected .decay-svg {
        display: none;
      }

      .decay-surface {
        transform-origin: center;
        will-change: transform;
      }

      .asset-content {
        position: relative;
        z-index: 2;
      }

      .asset-kicker-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .asset-kicker {
        display: inline-flex;
        align-items: center;
        min-height: 0;
        padding: 3px 10px;
        border-radius: 999px;
        background: rgba(255,255,255,.58);
        color: var(--asset-accent);
        font-size: 9px;
        line-height: 1.2;
        font-weight: 400;
        letter-spacing: .05em;
      }

      .asset-code {
        display: none;
      }

      .asset-title {
        margin-top: 16px;
        padding-right: 0;
        color: #111;
        font-family: "Inter", "PingFang SC", sans-serif;
        font-size: 18px;
        line-height: 1.3;
        font-weight: 400;
        letter-spacing: 0;
        overflow-wrap: anywhere;
      }

      .asset-detail {
        margin-top: 8px;
        color: #666;
        font-family: "Inter", "PingFang SC", sans-serif;
        font-size: 13px;
        line-height: 1.5;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .asset-footer {
        display: none;
      }

      .asset-status {
        color: #8a837d;
        font-size: 11px;
        font-weight: 500;
      }

      .asset-icon {
        color: var(--asset-accent);
        font-size: 21px;
        opacity: .82;
      }

      /* View panels */

      .view-panel {
        position: absolute;
        inset: 10px 22px 14px;
        z-index: 20;
        display: none;
        overflow: hidden;
        border: 1px solid rgba(75,63,51,.10);
        border-radius: 25px;
        background: rgba(255,255,255,.70);
        box-shadow: 0 22px 70px rgba(76,58,42,.12);
        backdrop-filter: blur(22px);
        -webkit-backdrop-filter: blur(22px);
      }

      .view-panel.active {
        display: flex;
        flex-direction: column;
      }

      .panel-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 18px 20px 14px;
        border-bottom: 1px solid var(--line);
      }

      .panel-title {
        font-family: "Nunito", "Noto Sans SC", "PingFang SC", sans-serif;
        font-size: 24px;
        font-weight: 700;
      }

      .panel-subtitle {
        margin-top: 3px;
        color: var(--muted);
        font-size: 10px;
      }

      .panel-scroll {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        padding: 18px 20px 24px;
        overscroll-behavior: contain;
      }

      .asset-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }

      .grid-card,
      .search-result {
        border: 1px solid rgba(75,63,51,.10);
        background: rgba(255,255,255,.73);
        color: var(--ink);
        cursor: pointer;
        text-align: left;
        transition: transform .18s ease, box-shadow .18s ease, background .18s ease;
      }

      .grid-card {
        min-height: 148px;
        padding: 15px;
        border-radius: 18px;
      }

      .grid-card:hover,
      .search-result:hover {
        transform: translateY(-3px);
        background: rgba(255,255,255,.94);
        box-shadow: 0 14px 32px rgba(74,57,42,.10);
      }

      .grid-code {
        color: var(--grid-accent);
        font-size: 9px;
        font-weight: 850;
      }

      .grid-title {
        margin-top: 8px;
        color: #403d39;
        font-size: 14px;
        line-height: 1.42;
        font-weight: 800;
      }

      .grid-meta {
        margin-top: 9px;
        color: #7a746e;
        font-size: 9px;
        line-height: 1.55;
      }

      .search-box-wrap {
        width: min(720px, 100%);
        margin: 0 auto 15px;
      }

      .search-box {
        width: 100%;
        min-height: 46px;
        padding: 10px 16px;
        border: 1px solid rgba(72,61,50,.14);
        border-radius: 999px;
        outline: none;
        background: rgba(255,255,255,.82);
        color: var(--ink);
        box-shadow: inset 0 1px 0 rgba(255,255,255,.60);
      }

      .search-box:focus {
        border-color: rgba(72,61,50,.34);
        box-shadow: 0 0 0 4px rgba(111,89,68,.06);
      }

      .search-results {
        width: min(820px, 100%);
        margin: 0 auto;
        display: grid;
        gap: 9px;
      }

      .search-result {
        padding: 13px 15px;
        border-radius: 15px;
      }

      .empty-state {
        padding: 30px;
        color: var(--muted);
        text-align: center;
        font-size: 12px;
      }

      /* Central view switcher; quick search occupies the original lower pill. */

      .bottom-nav {
        position: relative;
        z-index: 12;
        display: inline-flex;
        align-items: center;
        gap: 2px;
        margin-top: 12px;
        padding: 4px;
        border: 1px solid rgba(72,61,50,.10);
        border-radius: 999px;
        background: rgba(255,255,255,.76);
        box-shadow: 0 14px 36px rgba(70,53,39,.10);
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
      }

      .overview-search-trigger {
        position: absolute;
        left: 50%;
        bottom: clamp(72px, 11.2vh, 108px);
        z-index: 65;
        width: min(580px, 56vw);
        min-height: 72px;
        display: flex;
        align-items: center;
        gap: 20px;
        padding: 14px 28px;
        transform: translateX(-50%);
        border: 1px solid rgba(72,61,50,.06);
        border-radius: 999px;
        background: rgba(244,243,242,.90);
        color: #999795;
        box-shadow: 0 14px 36px rgba(70,53,39,.07);
        cursor: text;
        text-align: left;
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        transition: transform .22s ease, background .22s ease, box-shadow .22s ease;
      }

      .overview-search-trigger:hover,
      .overview-search-trigger:focus-visible {
        outline: none;
        transform: translateX(-50%) translateY(-3px);
        background: rgba(255,255,255,.96);
        box-shadow: 0 18px 42px rgba(70,53,39,.11);
      }

      .overview-search-trigger svg { width: 30px; height: 30px; flex: 0 0 auto; }
      .overview-search-trigger span {
        overflow: hidden;
        font-size: clamp(17px, 1.55vw, 28px);
        font-weight: 400;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .bottom-nav-button {
        min-height: 29px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 7px;
        padding: 5px 9px;
        border-color: transparent;
        border-radius: 999px;
        background: transparent;
        box-shadow: none;
        cursor: pointer;
        color: #77716b;
        font-size: 10px;
        font-weight: 760;
        transition: color .16s ease, background .16s ease, transform .16s ease;
      }

      .bottom-nav-button:hover {
        color: #2e2b28;
        transform: translateY(-1px);
      }

      .bottom-nav-button.active {
        color: #25221f;
        background: rgba(255,255,255,.94);
        box-shadow: 0 6px 16px rgba(74,56,41,.08);
      }

      /* Right drawer */

      .drawer {
        position: absolute;
        top: 7px;
        right: 8px;
        bottom: 7px;
        z-index: 100;
        width: min(450px, 42vw);
        min-width: 340px;
        display: flex;
        flex-direction: column;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 25px;
        background: var(--glass-strong);
        box-shadow: 0 28px 80px rgba(58,45,34,.20);
        opacity: 0;
        transform: translateX(calc(100% + 28px));
        pointer-events: none;
        transition: opacity .32s ease, transform .32s ease;
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
      }

      .drawer.open {
        opacity: 1;
        transform: translateX(0);
        pointer-events: auto;
      }

      .drawer-header {
        padding: 15px 17px 12px;
        border-bottom: 1px solid var(--line);
      }

      .drawer-controls {
        display: flex;
        justify-content: space-between;
        gap: 8px;
      }

      .drawer-control-group {
        display: flex;
        gap: 6px;
      }

      .icon-button {
        width: 34px;
        height: 34px;
        display: grid;
        place-items: center;
        padding: 0;
        border-radius: 12px;
        cursor: pointer;
        font-size: 16px;
        transition: transform .16s ease, background .16s ease;
      }

      .icon-button:hover {
        transform: translateY(-1px);
        background: rgba(255,255,255,.96);
      }

      .drawer-heading {
        margin-top: 12px;
        display: flex;
        align-items: flex-start;
        gap: 12px;
      }

      .drawer-icon {
        width: 46px;
        height: 46px;
        flex: 0 0 auto;
        display: grid;
        place-items: center;
        border-radius: 15px;
        background: var(--drawer-bg);
        color: var(--drawer-accent);
        font-size: 21px;
      }

      .drawer-code {
        color: var(--drawer-accent);
        font-size: 9px;
        font-weight: 850;
      }

      .drawer-title {
        margin-top: 4px;
        color: #302d2a;
        font-size: 19px;
        line-height: 1.26;
        font-weight: 850;
      }

      .drawer-meta {
        margin-top: 5px;
        color: var(--muted);
        font-size: 10px;
        line-height: 1.45;
      }

      .tabs {
        display: flex;
        gap: 2px;
        overflow-x: auto;
        padding: 0 9px;
        border-bottom: 1px solid var(--line);
        scrollbar-width: none;
      }

      .tabs::-webkit-scrollbar { display: none; }

      .tab {
        flex: 0 0 auto;
        padding: 11px 8px 9px;
        border: 0;
        border-bottom: 2px solid transparent;
        background: transparent;
        color: var(--muted);
        font-size: 9.5px;
        cursor: pointer;
      }

      .tab.active {
        color: var(--drawer-accent);
        border-bottom-color: var(--drawer-accent);
        font-weight: 850;
      }

      .drawer-body {
        flex: 1;
        min-height: 0;
        overflow-y: auto;
        padding: 15px 18px 24px;
        overscroll-behavior: contain;
      }

      .section {
        margin-bottom: 17px;
      }

      .section-label {
        margin-bottom: 6px;
        color: #3b3835;
        font-size: 11px;
        font-weight: 850;
      }

      .section-text {
        color: #55504b;
        font-size: 11.5px;
        line-height: 1.75;
        white-space: pre-wrap;
      }

      .star-grid {
        display: grid;
        gap: 8px;
      }

      .star-row {
        display: grid;
        grid-template-columns: 48px 1fr;
        overflow: hidden;
        border: 1px solid var(--line);
        border-radius: 13px;
      }

      .star-letter {
        display: grid;
        place-items: center;
        background: var(--drawer-bg);
        color: var(--drawer-accent);
        font-size: 20px;
        font-weight: 900;
      }

      .star-text {
        padding: 10px 11px;
        color: #55504b;
        font-size: 11px;
        line-height: 1.64;
        white-space: pre-wrap;
      }

      .tag-wrap {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .tag {
        padding: 5px 8px;
        border-radius: 999px;
        background: var(--drawer-bg);
        color: #55504b;
        font-size: 9.5px;
      }

      .note,
      .rule-item {
        padding: 11px 12px;
        border-radius: 13px;
        color: #5c5650;
        font-size: 10.5px;
        line-height: 1.62;
      }

      .note {
        border: 1px dashed var(--line);
        background: rgba(249,247,243,.74);
      }

      .rule-item {
        margin-bottom: 8px;
        border-left: 3px solid var(--drawer-accent);
        background: rgba(249,247,243,.76);
      }

      .overview-hero {
        margin-bottom: 14px;
        padding: 16px 16px 15px;
        border: 1px solid rgba(255,255,255,.72);
        border-radius: 17px;
        background: var(--drawer-bg);
        color: #3f3a35;
        font-size: 12px;
        line-height: 1.78;
        font-weight: 650;
      }

      .status-strip {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin: -3px 0 15px;
      }

      .status-chip {
        padding: 5px 8px;
        border: 1px solid var(--line);
        border-radius: 999px;
        background: rgba(255,255,255,.72);
        color: #625d57;
        font-size: 9px;
        line-height: 1.2;
        font-weight: 750;
      }

      .bullet-list,
      .question-list {
        display: grid;
        gap: 8px;
      }

      .bullet-item {
        position: relative;
        padding: 11px 12px 11px 30px;
        border: 1px solid var(--line);
        border-radius: 13px;
        background: rgba(255,255,255,.72);
        color: #514c47;
        font-size: 11px;
        line-height: 1.68;
      }

      .bullet-item::before {
        content: "↗";
        position: absolute;
        left: 11px;
        top: 11px;
        color: var(--drawer-accent);
        font-weight: 900;
      }

      .question-card {
        display: grid;
        grid-template-columns: 27px 1fr;
        gap: 9px;
        align-items: start;
        padding: 10px 11px;
        border: 1px solid var(--line);
        border-radius: 13px;
        background: rgba(255,255,255,.72);
      }

      .question-index {
        width: 25px;
        height: 25px;
        display: grid;
        place-items: center;
        border-radius: 9px;
        background: var(--drawer-bg);
        color: var(--drawer-accent);
        font-size: 9px;
        font-weight: 900;
      }

      .question-text {
        padding-top: 3px;
        color: #514c47;
        font-size: 11px;
        line-height: 1.58;
      }

      .memory-divider {
        height: 1px;
        margin: 18px 0;
        background: var(--line);
      }

      .empty-layer {
        padding: 28px 18px;
        border: 1px dashed var(--line);
        border-radius: 16px;
        background: rgba(249,247,243,.62);
        color: #77716b;
        font-size: 11px;
        line-height: 1.7;
        text-align: center;
      }

      @media (max-height: 760px) {
        .overview-search-trigger { bottom: clamp(50px, 8vh, 64px); }
        .collection-heading { top: 34px; }
        .collection-viewport { top: 106px; bottom: 56px; }
        .collection-card { height: min(314px, 45vh); }
        .selector-heading { top: 60px; }
        .drop-zone { top: 60%; width: min(238px, 19vw); }
        .cover { max-height: 212px; }
        .story-topbar {
          min-height: 58px;
          padding-top: 5px;
          padding-bottom: 4px;
        }
        .experience-logo { width: 37px; height: 37px; }
        .story-stage { inset: 58px 0 39px; }
        .asset-card { padding: 10px 11px 9px; }
        .asset-title { margin-top: 7px; }
        .asset-detail { margin-top: 4px; }
        .asset-footer { bottom: 6px; }
      }

      @media (max-width: 980px) {
        .story-topbar {
          grid-template-columns: 1fr auto;
        }
        .experience-tags { display: none; }
        .story-center { width: min(700px, 82vw); }
        .drawer { width: min(440px, 54vw); }
        .asset-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }

      @media (max-width: 720px) {
        .overview-search-trigger { bottom: 18px; width: min(330px, calc(100vw - 36px)); }
        .story-screen { padding: 8px; }
        .story-shell { border-radius: 22px; }
        .story-topbar {
          min-height: 80px;
          grid-template-columns: 1fr auto;
          padding: 10px 12px 8px;
        }
        .experience-meta { display: none; }
        .experience-logo { width: 43px; height: 43px; }
        .top-actions .pill-button:first-child { display: none; }
        .story-stage { inset: 78px 0 54px; }
        .story-center {
          top: 50%;
          width: 92vw;
        }
        .asset-card {
          width: min(var(--card-w), 180px);
          min-height: min(var(--card-h), 120px);
        }
        .bottom-nav-button span:last-child { display: none; }
        .bottom-nav-button { width: 38px; padding: 6px; }
        .drawer {
          left: 6px;
          right: 6px;
          width: auto;
          min-width: 0;
        }
        .asset-grid { grid-template-columns: 1fr; }
      }
    </style>

    <main class="app">
      <section id="collection-screen" class="screen collection-screen active">
        <div class="collection-heading">
          <h1>choose your collection</h1>
          <p>drag to browse · click a collection to explore</p>
        </div>

        <div id="collection-viewport" class="collection-viewport">
          <div id="collection-track" class="collection-track"></div>
        </div>

        <div class="collection-controls">
          <button id="collection-prev" class="collection-arrow" type="button" aria-label="上一个分类">‹</button>
          <div class="collection-progress" aria-hidden="true"><span id="collection-progress-bar"></span></div>
          <button id="collection-next" class="collection-arrow" type="button" aria-label="下一个分类">›</button>
        </div>
      </section>

      <section id="selector-screen" class="screen selector-screen">
        <button id="collections-button" class="collection-back" type="button">← All Collections</button>
        <div id="selector-collection-badge" class="selector-collection-badge"></div>
        <a class="selector-brand" href="?page=首页" target="_top" aria-label="返回主界面">lumooi.</a>

        <div class="selector-heading">
          <h1 id="selector-title" class="selector-title">which experience<br>are we exploring today?</h1>
          <div id="selector-subtitle" class="selector-subtitle">Drag an experience into the circle to start</div>
        </div>

        <div id="selector-stage" class="selector-stage">
          <span class="selector-float-dot one"></span>
          <span class="selector-float-dot two"></span>
          <span class="selector-float-dot three"></span>
          <span class="selector-float-dot four"></span>
          <div id="drop-zone" class="drop-zone" aria-hidden="true">
            <div id="drop-copy" class="drop-copy">Drop your<br>experience here</div>
          </div>
          <div id="cover-strip" class="cover-stage"></div>
        </div>

        <div class="selector-hint">Drag a card into the centre · or click once to open</div>
      </section>

      <section id="story-screen" class="screen story-screen">
        <div class="story-shell">
          <header class="story-topbar">
            <div id="experience-heading" class="experience-heading"></div>
            <div id="experience-tags" class="experience-tags"></div>
            <div class="top-actions">
              <button id="back-button" class="pill-button" type="button">← 经历选择</button>
              <button id="rule-button" class="pill-button" type="button">✦ 使用规则</button>
            </div>
          </header>

          <div id="story-stage" class="story-stage">
            <div id="story-center" class="story-center">
              <h2 class="cute-title"><span>which one do you</span><span>wanna choose?</span></h2>
              <div class="center-doodles">
                <span class="doodle-line"></span>
                <span class="doodle-heart">♡</span>
              </div>
              <nav id="bottom-nav" class="bottom-nav" aria-label="Experience views">
                <button class="bottom-nav-button active" type="button" data-view="overview"><span>⌂</span><span>Overview</span></button>
                <button class="bottom-nav-button" type="button" data-view="all"><span>▦</span><span>All Assets</span></button>
                <button class="bottom-nav-button" type="button" data-view="search"><span>⌕</span><span>Search</span></button>
              </nav>
              <div class="center-caption">Choose a view · or click a card to explore</div>
            </div>

            <div class="kinetic-annotation annotation-speed">← built for speed</div>
            <div class="kinetic-annotation annotation-managed">fully managed →</div>
            <div class="kinetic-annotation annotation-niche">your niche, amplified</div>
            <span class="kinetic-dot dot-one"></span>
            <span class="kinetic-dot dot-two"></span>
            <span class="kinetic-dot dot-three"></span>
            <span class="kinetic-dot dot-four"></span>

            <div id="asset-layer" class="asset-layer"></div>

            <section id="all-assets-panel" class="view-panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">All Assets</div>
                  <div class="panel-subtitle">查看这段经历中的全部职业资产</div>
                </div>
                <button class="icon-button panel-close" type="button" data-view="overview">×</button>
              </div>
              <div id="all-assets-grid" class="panel-scroll asset-grid"></div>
            </section>


            <section id="search-panel" class="view-panel">
              <div class="panel-header">
                <div>
                  <div class="panel-title">Search Assets</div>
                  <div class="panel-subtitle">搜索标题、类别、技能、结果或数据</div>
                </div>
                <button class="icon-button panel-close" type="button" data-view="overview">×</button>
              </div>
              <div class="panel-scroll">
                <div class="search-box-wrap">
                  <input id="asset-search" class="search-box" type="search" placeholder="输入关键词，例如：小红书、招聘交付、AI……">
                </div>
                <div id="search-results" class="search-results"></div>
              </div>
            </section>

            <aside id="drawer" class="drawer" aria-live="polite">
              <div class="drawer-header">
                <div class="drawer-controls">
                  <div class="drawer-control-group">
                    <button id="previous-asset" class="icon-button" type="button">←</button>
                    <button id="next-asset" class="icon-button" type="button">→</button>
                  </div>
                  <button id="close-drawer" class="icon-button" type="button">×</button>
                </div>
                <div id="drawer-heading" class="drawer-heading"></div>
              </div>
              <div id="tabs" class="tabs"></div>
              <div id="drawer-body" class="drawer-body"></div>
            </aside>
          </div>

          <button id="overview-search-trigger" class="overview-search-trigger" type="button" aria-label="搜索职业资产">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.25" aria-hidden="true">
              <circle cx="10.8" cy="10.8" r="7.2"></circle>
              <path d="m16.2 16.2 4.6 4.6"></path>
            </svg>
            <span>搜索：哪些经历最匹配当前岗位...</span>
          </button>
        </div>
      </section>
    </main>

    <script>
      try {
        if (window.frameElement) {
          window.frameElement.setAttribute("title", "");
          window.frameElement.setAttribute("aria-label", "");
        }
      } catch (_) {}

      const DATA = __DATA__;
      const INITIAL_STUDIO = __INITIAL_STUDIO__;

      const COLLECTIONS = [
        {
          id: "internship",
          label: "Work Experience",
          title: "实习经历",
          kicker: "TALENT & PEOPLE OPERATIONS",
          description: "水滴筹 · EY · Sohu · FESCO",
          bg: "#DDF3E7",
          accent: "#12B77A",
          chart: "M4 72 C48 48, 96 56, 142 39 S236 17, 306 22"
        },
        {
          id: "project",
          label: "Product & Consulting",
          title: "产品与咨询",
          kicker: "PRODUCT & BUSINESS",
          description: "CareerPilot · HR Tech 咨询项目",
          bg: "#FFE6D2",
          accent: "#FF8F65",
          chart: "M4 76 C58 72, 94 45, 142 42 S220 12, 306 17"
        },
        {
          id: "competition",
          label: "Competition & Innovation",
          title: "竞赛与创新",
          kicker: "RESEARCH TO PRACTICE",
          description: "无人配送创新项目 · 国家级大创",
          bg: "#EFE4FF",
          accent: "#8254F5",
          chart: "M4 75 C62 74, 104 68, 143 54 S220 23, 306 18"
        },
        {
          id: "research",
          label: "Research & Writing",
          title: "研究与写作",
          kicker: "RESEARCH & KNOWLEDGE",
          description: "人力资源管理 · 人口经济学",
          bg: "#DCEBFF",
          accent: "#4E83E7",
          chart: "M4 72 C54 58, 98 64, 146 44 S231 18, 306 26"
        }
      ];

      const state = {
        screen: "collection",
        collectionIndex: 0,
        collectionId: "internship",
        experienceIndex: Math.max(0, DATA.findIndex(item => item.experience_code === INITIAL_STUDIO.experienceCode)),
        assetIndex: null,
        activeView: "overview",
        tab: "overview",
        featuredAssetIndexes: []
      };

      const collectionScreen = document.getElementById("collection-screen");
      const collectionViewport = document.getElementById("collection-viewport");
      const collectionTrack = document.getElementById("collection-track");
      const collectionProgressBar = document.getElementById("collection-progress-bar");
      const selectorScreen = document.getElementById("selector-screen");
      const storyScreen = document.getElementById("story-screen");
      const selectorTitle = document.getElementById("selector-title");
      const selectorSubtitle = document.getElementById("selector-subtitle");
      const selectorCollectionBadge = document.getElementById("selector-collection-badge");
      const selectorStage = document.getElementById("selector-stage");
      const dropZone = document.getElementById("drop-zone");
      const dropCopy = document.getElementById("drop-copy");
      const coverStrip = document.getElementById("cover-strip");
      const experienceHeading = document.getElementById("experience-heading");
      const experienceTags = document.getElementById("experience-tags");
      const storyStage = document.getElementById("story-stage");
      const storyCenter = document.getElementById("story-center");
      const assetLayer = document.getElementById("asset-layer");
      const allAssetsPanel = document.getElementById("all-assets-panel");
      const allAssetsGrid = document.getElementById("all-assets-grid");
      const searchPanel = document.getElementById("search-panel");
      const assetSearch = document.getElementById("asset-search");
      const searchResults = document.getElementById("search-results");
      const bottomNav = document.getElementById("bottom-nav");
      const overviewSearchTrigger = document.getElementById("overview-search-trigger");
      const drawer = document.getElementById("drawer");
      const drawerHeading = document.getElementById("drawer-heading");
      const tabsElement = document.getElementById("tabs");
      const drawerBody = document.getElementById("drawer-body");
      const kineticDots = [...document.querySelectorAll(".kinetic-dot")];

      const coverRotations = ["-4deg", "2deg", "-2deg", "3deg", "-3deg", "2deg"];

      const overviewLayouts = [
        { x: 17, y: 78, angle: "4deg",  w: 240, h: 176, radius: 32, featured: true,  opacity: 1, blur: 0, title: 18, detail: 13 },
        { x: 15, y: 18, angle: "-3deg", w: 240, h: 176, radius: 32, featured: false, opacity: 1, blur: 0, title: 18, detail: 13 },
        { x: 84, y: 20, angle: "2deg",  w: 240, h: 176, radius: 32, featured: false, opacity: 1, blur: 0, title: 18, detail: 13 },
        { x: 86, y: 74, angle: "-2deg", w: 240, h: 176, radius: 32, featured: false, opacity: 1, blur: 0, title: 18, detail: 13 },
        { x: 7,  y: 48, angle: "3deg",  w: 180, h: 162, radius: 32, featured: false, opacity: 1, blur: 0, title: 18, detail: 13 },
        { x: 94, y: 48, angle: "-3deg", w: 200, h: 168, radius: 32, featured: false, opacity: 1, blur: 0, title: 18, detail: 13 }
      ];

      const colorPalettes = [
        ["#D7F2DE", "#2E9D5A", "♧", "rgba(212,242,221,.94)"],
        ["#DCEBFF", "#3787E8", "◎", "rgba(220,235,255,.94)"],
        ["#FFE8D8", "#D78646", "⌂", "rgba(255,232,216,.94)"],
        ["#EADFFF", "#7953C8", "✦", "rgba(234,223,255,.94)"],
        ["#FFE3ED", "#D45F87", "▧", "rgba(255,227,237,.94)"],
        ["#FFF0B9", "#B88416", "◷", "rgba(255,240,185,.94)"],
        ["#D9F0F9", "#2E829F", "♡", "rgba(217,240,249,.94)"],
        ["#E9E1D7", "#786B5A", "⌁", "rgba(233,225,215,.94)"],
        ["#DDE1FF", "#5968C8", "◌", "rgba(221,225,255,.94)"],
        ["#DFF1E4", "#4A8B5B", "⌕", "rgba(223,241,228,.94)"]
      ];

      const tabs = [
        ["overview", "Overview"],
        ["star", "STAR"],
        ["resume", "Resume"],
        ["interview", "Interview"],
        ["decision", "Decision 🔒"],
        ["lessons", "Lessons"],
        ["memory", "Memory 🔒"]
      ];

      const pointer = {
        clientX: window.innerWidth / 2,
        clientY: window.innerHeight / 2,
        previousX: window.innerWidth / 2,
        previousY: window.innerHeight / 2,
        active: false,
        speed: 0
      };

      let motionCards = [];
      const assetDragOffsets = new Map();
      let coverMotionCards = [];
      let animationFrameId = null;
      let hoveredAssetIndex = null;
      let coverPointerActive = false;
      let coverGeometryDirty = true;
      let lastFrameTime = performance.now();
      let lastFilterUpdateTime = 0;
      let stageMetrics = { left: 0, top: 0, width: 1, height: 1 };

      function escapeHtml(value) {
        return String(value ?? "")
          .replaceAll("&", "&amp;")
          .replaceAll("<", "&lt;")
          .replaceAll(">", "&gt;")
          .replaceAll('"', "&quot;")
          .replaceAll("'", "&#039;");
      }

      function cleanText(value) {
        return String(value || "").replace(/\s+/g, " ").trim();
      }

      function clamp(value, min, max) {
        return Math.min(max, Math.max(min, value));
      }

      function lerp(start, end, amount) {
        return start + (end - start) * amount;
      }

      function dampAmount(speed, deltaSeconds) {
        return 1 - Math.exp(-speed * deltaSeconds);
      }

      function currentExperience() {
        return DATA[state.experienceIndex] || DATA[0] || {};
      }

      function currentAssets() {
        return currentExperience().assets || [];
      }

      function currentAsset() {
        if (state.assetIndex === null) return null;
        return currentAssets()[state.assetIndex] || null;
      }

      function compactCategory(asset) {
        const value = cleanText(asset.category || "职业资产");
        return value.length > 12 ? `${value.slice(0, 12)}…` : value;
      }

      function compactDetail(asset, maxLength = 60) {
        const raw = asset.overview_summary || asset.results || asset.metrics || asset.participation_level || "";
        const value = cleanText(raw);
        if (!value) return "点击查看完整经历记录";
        return value.length > maxLength ? `${value.slice(0, maxLength)}…` : value;
      }

      function assetSearchText(asset) {
        return [
          asset.asset_code,
          asset.title,
          asset.category,
          asset.overview_summary,
          asset.overview_strengths,
          asset.background,
          asset.actions,
          asset.results,
          asset.metrics,
          asset.skills,
          asset.tools,
          asset.reflection,
          asset.star_situation,
          asset.star_task,
          asset.star_action,
          asset.star_result,
          asset.star_uses,
          asset.resume_bullets,
          asset.resume_strategy,
          asset.interview_questions,
          asset.interview_followups,
          asset.asset_position,
          asset.objective,
          asset.decisions,
          asset.constraints,
          asset.uncertainties,
          asset.star_b_situation,
          asset.star_b_task,
          asset.star_b_action,
          asset.star_b_result,
          asset.resume_roles,
          asset.resume_keywords,
          asset.interview_angles,
          asset.interview_risks,
          asset.design_decision,
          asset.lessons_learned,
          asset.differentiator,
          asset.evidence,
          asset.evidence_status
        ].map(cleanText).join(" ").toLowerCase();
      }

      function assetScore(asset) {
        const title = cleanText(asset.title).toLowerCase();
        const category = cleanText(asset.category).toLowerCase();
        let score = 0;

        if (asset.include_in_resume) score += 50;
        if (asset.include_in_interview) score += 22;
        if (cleanText(asset.metrics)) score += 18;
        if (cleanText(asset.results)) score += 13;
        if (cleanText(asset.actions)) score += 8;
        if (cleanText(asset.star_uses)) score += 7;
        const metrics = cleanText(asset.metrics).toLowerCase();
        if (/小红书|xiaohongshu/.test(title)) score += 300;
        if (/2,?900/.test(metrics)) score += 180;
        if (/employer branding|雇主品牌/.test(`${title} ${category}`)) score += 42;
        if (/招聘交付|recruitment delivery|offer/.test(`${title} ${category}`)) score += 28;
        if (/ai|人工智能/.test(`${title} ${category} ${asset.ai_usage || ""}`.toLowerCase())) score += 18;

        return score;
      }

      function normalizedAssetCode(asset) {
        return cleanText(asset?.asset_code).toUpperCase().replace(/[\s_]/g, "-");
      }

      function chooseFeaturedAssetIndexes() {
        const assets = currentAssets();
        const experienceCode = cleanText(currentExperience().experience_code).toUpperCase();

        // The lead demo experience uses a deliberate portfolio order.
        if (experienceCode === "CP") {
          const preferredCodes = ["CP-01", "CP-03", "CP-04", "CP-05"];
          const selected = preferredCodes
            .map(code => assets.findIndex(asset => normalizedAssetCode(asset) === code))
            .filter(index => index >= 0);

          const rankedFallback = assets
            .map((asset, index) => ({ index, score: assetScore(asset) }))
            .sort((a, b) => b.score - a.score || a.index - b.index)
            .map(item => item.index);

          rankedFallback.forEach(index => {
            if (!selected.includes(index) && selected.length < 6) selected.push(index);
          });
          return selected.slice(0, 6);
        }

        return assets
          .map((asset, index) => ({ index, score: assetScore(asset) }))
          .sort((a, b) => b.score - a.score || a.index - b.index)
          .slice(0, 6)
          .map(item => item.index);
      }

      function paletteForAsset(index) {
        return colorPalettes[index % colorPalettes.length];
      }

      function collectionMeta(id = state.collectionId) {
        return COLLECTIONS.find(collection => collection.id === id) || COLLECTIONS[0];
      }

      function collectionItems(id = state.collectionId) {
        return DATA
          .map((item, index) => ({ item, index }))
          .filter(entry => (entry.item.collection || "project") === id);
      }

      function collectionLatestYear(items) {
        const values = items
          .map(entry => cleanText(entry.item.end_date || entry.item.start_date))
          .map(value => Number((value.match(/\d{4}/) || [0])[0]))
          .filter(Boolean);
        return values.length ? Math.max(...values) : "—";
      }

      function collectionPreview(items) {
        if (!items.length) return "No verified experience yet";
        return items
          .slice(0, 3)
          .map(entry => cleanText(entry.item.display_name || entry.item.organization))
          .filter(Boolean)
          .join(" · ");
      }

      let collectionSuppressClick = false;
      let collectionScrollFrame = null;
      let collectionBlankDrag = null;

      function renderCollections() {
        collectionTrack.innerHTML = COLLECTIONS.map((collection, index) => {
          const items = collectionItems(collection.id);
          const count = items.length;
          const latest = collectionLatestYear(items);
          return `
            <button
              class="collection-card${index === state.collectionIndex ? " active" : ""}"
              type="button"
              data-collection="${escapeHtml(collection.id)}"
              data-index="${index}"
              style="
                --collection-bg:${collection.bg};
                --collection-accent:${collection.accent};
              "
            >
              <div class="collection-kicker">${escapeHtml(collection.kicker)}</div>
              <div class="collection-title">${escapeHtml(collection.title)}</div>
              <div class="collection-description">${escapeHtml(collection.description)}</div>
              <div class="collection-stats">
                <div class="collection-stat">
                  <div class="collection-stat-label">EXPERIENCES</div>
                  <div class="collection-stat-value accent">${count}</div>
                </div>
                <div class="collection-stat">
                  <div class="collection-stat-label">LATEST</div>
                  <div class="collection-stat-value">${escapeHtml(latest)}</div>
                </div>
              </div>
              <div class="collection-chart" aria-hidden="true">
                <svg viewBox="0 0 310 90" preserveAspectRatio="none">
                  <path d="${collection.chart}"></path>
                </svg>
              </div>
              <div class="collection-preview">${escapeHtml(collectionPreview(items))}</div>
              <span class="collection-enter">↗</span>
            </button>
          `;
        }).join("");

        collectionTrack.querySelectorAll(".collection-card").forEach(card => {
          card.addEventListener("click", () => {
            if (collectionSuppressClick) return;
            const index = Number(card.dataset.index);
            state.collectionIndex = index;
            state.collectionId = COLLECTIONS[index].id;
            setCollectionActive(index);
            openCollection(card.dataset.collection);
          });
        });

        window.requestAnimationFrame(() => updateCollectionCarousel(false));
      }

      function collectionCards() {
        return Array.from(collectionTrack.querySelectorAll(".collection-card"));
      }

      function setCollectionActive(index) {
        const cards = collectionCards();
        if (!cards.length) return;
        const nextIndex = clamp(index, 0, cards.length - 1);
        state.collectionIndex = nextIndex;
        state.collectionId = COLLECTIONS[nextIndex].id;
        cards.forEach((card, cardIndex) => {
          card.classList.toggle("active", cardIndex === nextIndex);
        });
        collectionProgressBar.style.transform = `translateX(${nextIndex * 100}%)`;
      }

      function collectionTargetLeft(card) {
        return card.offsetLeft - (collectionViewport.clientWidth - card.offsetWidth) / 2;
      }

      function updateCollectionCarousel(animate = true) {
        const cards = collectionCards();
        if (!cards.length) return;
        setCollectionActive(state.collectionIndex);
        const card = cards[state.collectionIndex];
        collectionViewport.scrollTo({
          left: Math.max(0, collectionTargetLeft(card)),
          behavior: animate ? "smooth" : "auto"
        });
      }

      function syncCollectionFromScroll() {
        if (collectionScrollFrame !== null) return;
        collectionScrollFrame = window.requestAnimationFrame(() => {
          collectionScrollFrame = null;
          const cards = collectionCards();
          if (!cards.length) return;
          const viewportCenter = collectionViewport.scrollLeft + collectionViewport.clientWidth / 2;
          let nearestIndex = 0;
          let nearestDistance = Number.POSITIVE_INFINITY;
          cards.forEach((card, index) => {
            const cardCenter = card.offsetLeft + card.offsetWidth / 2;
            const distance = Math.abs(cardCenter - viewportCenter);
            if (distance < nearestDistance) {
              nearestDistance = distance;
              nearestIndex = index;
            }
          });
          setCollectionActive(nearestIndex);
        });
      }

      function moveCollection(direction) {
        const nextIndex = clamp(state.collectionIndex + direction, 0, COLLECTIONS.length - 1);
        setCollectionActive(nextIndex);
        updateCollectionCarousel(true);
      }

      function openCollection(id) {
        const meta = collectionMeta(id);
        const items = collectionItems(id);
        state.collectionId = id;
        state.collectionIndex = Math.max(0, COLLECTIONS.findIndex(collection => collection.id === id));
        selectorTitle.innerHTML = `which experience<br>are we exploring today?`;
        selectorSubtitle.textContent = "Drag an experience into the circle to start";
        selectorCollectionBadge.textContent = `${meta.label.toUpperCase()} COLLECTION · ${items.length} EXPERIENCES`;
        renderCovers();
        switchScreen("selector");
      }

      function beginCollectionBlankDrag(event) {
        if (event.pointerType !== "mouse" || event.button !== 0) return;
        if (event.target.closest(".collection-card")) return;
        collectionBlankDrag = {
          pointerId: event.pointerId,
          startX: event.clientX,
          startScrollLeft: collectionViewport.scrollLeft,
          moved: false
        };
        collectionViewport.setPointerCapture(event.pointerId);
      }

      function moveCollectionBlankDrag(event) {
        if (!collectionBlankDrag || event.pointerId !== collectionBlankDrag.pointerId) return;
        const delta = event.clientX - collectionBlankDrag.startX;
        if (Math.abs(delta) > 7) collectionBlankDrag.moved = true;
        collectionViewport.scrollLeft = collectionBlankDrag.startScrollLeft - delta;
      }

      function endCollectionBlankDrag(event) {
        if (!collectionBlankDrag || event.pointerId !== collectionBlankDrag.pointerId) return;
        const moved = collectionBlankDrag.moved;
        collectionBlankDrag = null;
        try { collectionViewport.releasePointerCapture(event.pointerId); } catch (_) {}
        if (moved) {
          collectionSuppressClick = true;
          window.setTimeout(() => { collectionSuppressClick = false; }, 120);
          window.requestAnimationFrame(() => updateCollectionCarousel(true));
        }
      }

      function switchScreen(name) {
        state.screen = name;
        collectionScreen.classList.toggle("active", name === "collection");
        selectorScreen.classList.toggle("active", name === "selector");
        storyScreen.classList.toggle("active", name === "story");
        if (name === "collection") {
          window.setTimeout(() => updateCollectionCarousel(false), 40);
        }
        if (name === "selector") {
          window.setTimeout(resetSelectorCards, 40);
        }
      }

      function setView(view) {
        state.activeView = view;
        const overviewActive = view === "overview";

        storyCenter.style.display = overviewActive ? "block" : "none";
        assetLayer.style.display = overviewActive ? "block" : "none";
        allAssetsPanel.classList.toggle("active", view === "all");
        searchPanel.classList.toggle("active", view === "search");

        bottomNav.querySelectorAll(".bottom-nav-button").forEach(button => {
          button.classList.toggle("active", button.dataset.view === view);
        });

        if (view === "all") renderAllAssets();
        if (view === "search") {
          renderSearchResults(assetSearch.value || "");
          window.setTimeout(() => assetSearch.focus(), 80);
        }
      }

      const selectorCategoryLayouts = {
        internship: { WD: { x: 18, y: 69, angle: 4 }, EY: { x: 39, y: 29, angle: -3 }, SOHU: { x: 63, y: 29, angle: 3 }, FESCO: { x: 82, y: 69, angle: -4 } },
        project: { CP: { x: 24, y: 68, angle: 3 }, CAT: { x: 76, y: 33, angle: -4 } },
        competition: { CB: { x: 24, y: 68, angle: 3 }, NDC: { x: 76, y: 33, angle: -4 } },
        research: { XN: { x: 24, y: 68, angle: 3 }, MZY: { x: 76, y: 33, angle: -4 } }
      };

      const selectorFallbackLayouts = [
        { x: 23.0, y: 28.0, angle: -4 },
        { x: 22.0, y: 70.0, angle: 3 },
        { x: 77.0, y: 29.0, angle: 4 },
        { x: 78.0, y: 71.0, angle: -2 },
        { x: 50.0, y: 82.0, angle: 2 },
        { x: 50.0, y: 23.0, angle: -2 }
      ];

      const selectorKickers = { CP: "CAREER PRODUCT", CAT: "HR TECH CONSULTING", WD: "RECRUITING OPERATIONS", EY: "CAMPUS RECRUITING", SOHU: "HRBP & TALENT", FESCO: "HR OPERATIONS", CB: "INNOVATION PROJECT", NDC: "SOCIAL RESEARCH", XN: "HR RESEARCH", MZY: "POPULATION ECONOMICS" };

      let selectorDrag = null;
      let selectorOpening = false;
      const selectorCardPositions = new Map();

      function selectorIdentityCode(item) {
        const directCode = String(item.experience_code || "").trim().toUpperCase();
        if (directCode) return directCode;

        const identityText = [
          item.display_name,
          item.organization,
          item.alternate_name,
          item.team
        ].map(cleanText).join(" ").toLowerCase();

        if (/careerpilot/.test(identityText)) return "CP";
        if (/hr tech|咨询/.test(identityText)) return "CAT";
        if (/水滴|waterdrop/.test(identityText)) return "WD";
        if (/\bey\b|安永/.test(identityText)) return "EY";
        if (/搜狐|sohu/.test(identityText)) return "SOHU";
        if (/fesco/.test(identityText)) return "FESCO";
        if (/无人配送/.test(identityText)) return "CB";
        if (/创新创业训练|国家级大创/.test(identityText)) return "NDC";
        if (/人力资源管理课题组/.test(identityText)) return "XN";
        if (/人口经济学/.test(identityText)) return "MZY";
        return "";
      }

      function selectorLayoutFor(item, index) {
        const code = selectorIdentityCode(item);
        const categoryLayouts = selectorCategoryLayouts[state.collectionId] || {};
        return categoryLayouts[code] || selectorFallbackLayouts[index % selectorFallbackLayouts.length];
      }

      function selectorKickerFor(item) {
        const code = selectorIdentityCode(item);
        const fallback = cleanText(item.responsibility_direction || item.experience_type || "EXPERIENCE");
        return selectorKickers[code] || fallback || "EXPERIENCE";
      }

      function setDropMessage(message, active = false) {
        dropZone.classList.toggle("active", active);
        dropCopy.innerHTML = message;
      }

      function resetSelectorCards() {
        selectorOpening = false;
        selectorDrag = null;
        dropZone.classList.remove("active", "accepted");
        dropCopy.innerHTML = "Drop your<br>experience here";

        coverStrip.querySelectorAll(".cover").forEach(card => {
          card.classList.remove("dragging", "drop-ready", "dropping", "fading-out");
          card.style.pointerEvents = "";
          card.style.opacity = "";
          card.style.filter = "";
          card.style.left = `${card.dataset.homeX}%`;
          card.style.top = `${card.dataset.homeY}%`;
          card.style.setProperty("--drag-r", "0deg");
          card.style.setProperty("--cover-scale", "1");
        });
        window.requestAnimationFrame(updateExperienceLinks);
        window.setTimeout(updateExperienceLinks, 480);
      }

      function cardInsideDropZone(card) {
        const cardRect = card.getBoundingClientRect();
        const zoneRect = dropZone.getBoundingClientRect();
        const cardCenterX = cardRect.left + cardRect.width / 2;
        const cardCenterY = cardRect.top + cardRect.height / 2;
        const zoneCenterX = zoneRect.left + zoneRect.width / 2;
        const zoneCenterY = zoneRect.top + zoneRect.height / 2;
        const distance = Math.hypot(cardCenterX - zoneCenterX, cardCenterY - zoneCenterY);
        return distance <= zoneRect.width * .43;
      }

      function updateDropTarget(card, index) {
        const item = DATA[index];
        const inside = cardInsideDropZone(card);
        card.classList.toggle("drop-ready", inside);

        if (inside) {
          setDropMessage(`Release to open<br>${escapeHtml(item.display_name || "experience")}`, true);
        } else {
          setDropMessage("Drop your<br>experience here", false);
        }

        return inside;
      }

      function returnCardHome(card) {
        card.classList.remove("dragging", "drop-ready");
        card.style.left = `${card.dataset.homeX}%`;
        card.style.top = `${card.dataset.homeY}%`;
        card.style.setProperty("--drag-r", "0deg");
        setDropMessage("Drop your<br>experience here", false);
        window.requestAnimationFrame(updateExperienceLinks);
        window.setTimeout(updateExperienceLinks, 480);
      }

      function keepCardAtDropPosition(card) {
        const stageRect = selectorStage.getBoundingClientRect();
        const cardRect = card.getBoundingClientRect();
        const centerX = cardRect.left - stageRect.left + cardRect.width / 2;
        const centerY = cardRect.top - stageRect.top + cardRect.height / 2;
        const x = clamp(centerX / Math.max(stageRect.width, 1) * 100, 0, 100);
        const y = clamp(centerY / Math.max(stageRect.height, 1) * 100, 0, 100);
        const key = `${state.collectionId}:${card.dataset.code || card.dataset.index}`;

        selectorCardPositions.set(key, { x, y });
        card.dataset.homeX = x.toFixed(3);
        card.dataset.homeY = y.toFixed(3);
        card.classList.remove("dragging", "drop-ready");
        card.style.left = `${x}%`;
        card.style.top = `${y}%`;
        card.style.setProperty("--drag-r", "0deg");
        setDropMessage("Drop your<br>experience here", false);
        window.requestAnimationFrame(updateExperienceLinks);
      }

      function openExperienceFromSelector(index, card) {
        if (selectorOpening) return;
        selectorOpening = true;

        const item = DATA[index];
        const stageRect = selectorStage.getBoundingClientRect();
        const zoneRect = dropZone.getBoundingClientRect();
        const targetX = zoneRect.left - stageRect.left + zoneRect.width / 2;
        const targetY = zoneRect.top - stageRect.top + zoneRect.height / 2;

        coverStrip.querySelectorAll(".cover").forEach(other => {
          if (other !== card) other.classList.add("fading-out");
          other.style.pointerEvents = "none";
        });

        card.classList.remove("dragging", "drop-ready");
        card.classList.add("dropping");
        card.style.left = `${targetX}px`;
        card.style.top = `${targetY}px`;
        card.style.setProperty("--drag-r", "0deg");
        dropZone.classList.remove("active");
        dropZone.classList.add("accepted");
        dropCopy.innerHTML = `Opening<br>${escapeHtml(item.display_name || "experience")}`;

        window.setTimeout(() => {
          state.experienceIndex = index;
          state.assetIndex = null;
          state.tab = "overview";
          state.activeView = "overview";
          renderStory();
          switchScreen("story");
          window.setTimeout(resetSelectorCards, 90);
        }, 350);
      }

      function beginSelectorDrag(event, card, index) {
        if (selectorOpening) return;
        if (event.pointerType === "mouse" && event.button !== 0) return;

        event.preventDefault();
        const cardRect = card.getBoundingClientRect();
        const stageRect = selectorStage.getBoundingClientRect();
        const centerX = cardRect.left - stageRect.left + cardRect.width / 2;
        const centerY = cardRect.top - stageRect.top + cardRect.height / 2;

        selectorDrag = {
          pointerId: event.pointerId,
          card,
          index,
          stageRect,
          startX: event.clientX,
          startY: event.clientY,
          offsetX: event.clientX - (cardRect.left + cardRect.width / 2),
          offsetY: event.clientY - (cardRect.top + cardRect.height / 2),
          moved: false,
          inside: false
        };

        try {
          card.setPointerCapture(event.pointerId);
        } catch (_) {
          // Window-level listeners below keep mouse dragging working even when
          // pointer capture is unavailable inside an embedded browser frame.
        }
        card.style.left = `${centerX}px`;
        card.style.top = `${centerY}px`;
        card.classList.add("dragging");
      }

      function moveSelectorDrag(event) {
        if (!selectorDrag || selectorDrag.pointerId !== event.pointerId) return;
        event.preventDefault();

        const { card, stageRect } = selectorDrag;
        const deltaX = event.clientX - selectorDrag.startX;
        const deltaY = event.clientY - selectorDrag.startY;
        if (Math.hypot(deltaX, deltaY) > 5) selectorDrag.moved = true;

        const cardRect = card.getBoundingClientRect();
        const halfWidth = cardRect.width / 2;
        const halfHeight = cardRect.height / 2;
        const x = clamp(
          event.clientX - stageRect.left - selectorDrag.offsetX,
          halfWidth + 8,
          stageRect.width - halfWidth - 8
        );
        const y = clamp(
          event.clientY - stageRect.top - selectorDrag.offsetY,
          halfHeight + 8,
          stageRect.height - halfHeight - 8
        );

        card.style.left = `${x}px`;
        card.style.top = `${y}px`;
        card.style.setProperty("--drag-r", `${clamp(deltaX * .025, -8, 8).toFixed(2)}deg`);
        selectorDrag.inside = updateDropTarget(card, selectorDrag.index);
        updateExperienceLinks();
      }

      function endSelectorDrag(event) {
        if (!selectorDrag || selectorDrag.pointerId !== event.pointerId) return;
        event.preventDefault();

        const drag = selectorDrag;
        selectorDrag = null;

        try {
          drag.card.releasePointerCapture(event.pointerId);
        } catch (_) {}

        if (drag.inside || !drag.moved) {
          openExperienceFromSelector(drag.index, drag.card);
        } else {
          keepCardAtDropPosition(drag.card);
        }
      }

      function relationshipSvgMarkup() {
        return "";
      }

      function updateExperienceLinks() {
        return;
        const svg = document.getElementById("experience-links");
        const path = document.getElementById("project-link");
        const startDot = document.getElementById("project-link-start");
        const endDot = document.getElementById("project-link-end");
        const relationshipPairs = {
          internship: ["FESCO", "SOHU"], project: ["CAT", "CP"],
          competition: ["NDC", "CB"], research: ["MZY", "XN"]
        };
        const pair = relationshipPairs[state.collectionId] || [];
        const source = coverStrip.querySelector(`[data-code="${pair[0] || ""}"]`);
        const target = coverStrip.querySelector(`[data-code="${pair[1] || ""}"]`);

        if (!svg || !path || !startDot || !endDot || !source || !target) {
          if (svg) svg.style.display = "none";
          return;
        }

        svg.style.display = "";
        const stageRect = coverStrip.getBoundingClientRect();
        const sourceRect = source.getBoundingClientRect();
        const targetRect = target.getBoundingClientRect();

        const startX = sourceRect.left - stageRect.left + sourceRect.width * .50;
        const startY = sourceRect.bottom - stageRect.top - 6;
        const endX = targetRect.left - stageRect.left + targetRect.width * .50;
        const endY = targetRect.top - stageRect.top + 6;
        const controlX = Math.min(stageRect.width - 8, Math.max(startX, endX) + 20);
        const midY = (startY + endY) / 2;

        path.setAttribute(
          "d",
          `M ${startX.toFixed(1)} ${startY.toFixed(1)} ` +
          `C ${controlX.toFixed(1)} ${(midY - 24).toFixed(1)}, ` +
          `${controlX.toFixed(1)} ${(midY + 24).toFixed(1)}, ` +
          `${endX.toFixed(1)} ${endY.toFixed(1)}`
        );
        startDot.setAttribute("cx", startX.toFixed(1));
        startDot.setAttribute("cy", startY.toFixed(1));
        endDot.setAttribute("cx", endX.toFixed(1));
        endDot.setAttribute("cy", endY.toFixed(1));
      }

      function renderCovers() {
        const visibleEntries = collectionItems();
        coverStrip.innerHTML = visibleEntries.map((entry, localIndex) => {
          const item = entry.item;
          const index = entry.index;
          const baseLayout = selectorLayoutFor(item, localIndex);
          const role = item.role || item.role_en || "";
          const kicker = selectorKickerFor(item);
          const identityCode = selectorIdentityCode(item);
          const savedLayout = selectorCardPositions.get(`${state.collectionId}:${identityCode || index}`);
          const layout = savedLayout ? { ...baseLayout, ...savedLayout } : baseLayout;
          const linkedCodes = { internship: ["FESCO", "SOHU"], project: ["CAT", "CP"], competition: ["NDC", "CB"], research: ["MZY", "XN"] }[state.collectionId] || [];
          const linkedClass = linkedCodes.includes(identityCode) ? " linked-cover" : "";
          return `
            <button
              type="button"
              class="cover${linkedClass}"
              draggable="false"
              data-index="${index}"
              data-code="${escapeHtml(identityCode)}"
              data-home-x="${layout.x}"
              data-home-y="${layout.y}"
              aria-label="Open ${escapeHtml(item.display_name || "experience")}"
              style="
                --home-x:${layout.x}%;
                --home-y:${layout.y}%;
                --rotate:${layout.angle}deg;
                --layer:${index + 1};
                --accent:${item.palette?.accent || "#8a7a69"};
                background:${item.palette?.bg || "#f3eee6"};
                z-index:${index + 20};
              "
            >
              <div class="cover-kicker">${escapeHtml(kicker)}</div>
              <span class="cover-logo">${escapeHtml(item.virtual_logo || "◌")}</span>
              <div class="cover-name">${escapeHtml(item.display_name || "Experience")}</div>
              <div class="cover-role">${escapeHtml(role)}</div>
              <div class="cover-date">${escapeHtml(item.start_date || "")} — ${escapeHtml(item.end_date || "")}</div>
            </button>
          `;
        }).join("");

        coverMotionCards = [];

        coverStrip.querySelectorAll(".cover").forEach(button => {
          const index = Number(button.dataset.index);
          button.addEventListener("pointerdown", event => beginSelectorDrag(event, button, index));
          button.addEventListener("dragstart", event => event.preventDefault());
          button.addEventListener("keydown", event => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              openExperienceFromSelector(index, button);
            }
          });
        });

        window.requestAnimationFrame(updateExperienceLinks);
        window.setTimeout(updateExperienceLinks, 100);
      }

      function deriveExperienceTags() {
        const values = [];
        currentAssets().forEach(asset => {
          [asset.category, asset.skills].forEach(value => {
            String(value || "")
              .split(/[,，、;；\n/]+/)
              .map(item => item.trim())
              .filter(Boolean)
              .forEach(item => {
                const compact = item.length > 14 ? item.slice(0, 14) : item;
                if (!values.includes(compact)) values.push(compact);
              });
          });
        });
        return values.slice(0, 5);
      }

      function renderExperienceHeader() {
        const item = currentExperience();
        const accent = item.palette?.accent || "#5d9dff";
        const tags = deriveExperienceTags();

        experienceHeading.style.setProperty("--experience-accent", accent);
        experienceHeading.innerHTML = `
          <div class="experience-logo">${escapeHtml(item.virtual_logo || "◌")}</div>
          <div class="experience-copy">
            <div class="experience-name">${escapeHtml(item.display_name || "Experience")}</div>
            <div class="experience-role">${escapeHtml(item.role_en || item.role || "")}</div>
            <div class="experience-meta">
              <span>◷ ${escapeHtml(item.start_date || "")} — ${escapeHtml(item.end_date || "")}</span>
              ${item.location ? `<span>⌖ ${escapeHtml(item.location)}</span>` : ""}
              <span>Verified ◉</span>
            </div>
          </div>
        `;

        experienceTags.innerHTML = tags.map((tag, index) => {
          const palette = colorPalettes[(index + 1) % colorPalettes.length];
          return `<span class="experience-tag" style="--tag-bg:${palette[3]}">${escapeHtml(tag)}</span>`;
        }).join("");
      }

      function renderOverviewAssets() {
        const assets = currentAssets();
        state.featuredAssetIndexes = chooseFeaturedAssetIndexes();
        storyStage.classList.toggle("has-selection", state.assetIndex !== null);

        if (!assets.length) {
          assetLayer.innerHTML = `<div class="empty-state" style="position:absolute;left:50%;top:65%;transform:translate(-50%,-50%);">这段经历尚未导入结构化职业资产。</div>`;
          motionCards = [];
          return;
        }

        assetLayer.innerHTML = state.featuredAssetIndexes.map((assetIndex, layoutIndex) => {
          const asset = assets[assetIndex];
          const layout = overviewLayouts[layoutIndex];
          const palette = paletteForAsset(assetIndex);
          const selected = state.assetIndex === assetIndex;
          const filterId = `decay-${state.experienceIndex}-${assetIndex}`;
          const frequency = (0.0115 + (assetIndex % 4) * 0.0015).toFixed(4);
          const seed = 4 + assetIndex * 5;
          const dragKey = `${state.experienceIndex}:${assetIndex}`;
          const dragOffset = assetDragOffsets.get(dragKey) || { x: 0, y: 0 };

          return `
            <button
              type="button"
              class="asset-card ${layout.featured ? "featured" : ""} ${selected ? "selected" : ""}"
              data-asset-index="${assetIndex}"
              style="
                --x:${layout.x}%;
                --y:${layout.y}%;
                --angle:${layout.angle};
                --card-w:${layout.w}px;
                --card-h:${layout.h}px;
                --card-radius:${layout.radius}px;
                --base-opacity:${layout.opacity};
                --base-blur:${layout.blur}px;
                --asset-accent:${palette[1]};
                --asset-bg:${palette[0]};
                --title-size:${layout.title}px;
                --detail-size:${layout.detail}px;
                --drag-x:${dragOffset.x}px;
                --drag-y:${dragOffset.y}px;
              "
            >
              <svg class="decay-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                <defs>
                  <filter id="${filterId}" x="-14%" y="-14%" width="128%" height="128%" filterRes="48" color-interpolation-filters="sRGB">
                    <feTurbulence
                      type="turbulence"
                      baseFrequency="${frequency}"
                      numOctaves="1"
                      seed="${seed}"
                      stitchTiles="stitch"
                      result="cardNoise"
                    />
                    <feDisplacementMap
                      class="asset-displacement"
                      in="SourceGraphic"
                      in2="cardNoise"
                      scale="0"
                      xChannelSelector="R"
                      yChannelSelector="B"
                    />
                  </filter>
                </defs>
                <rect class="decay-surface" x="8" y="8" width="84" height="84" rx="14" fill="${palette[0]}" filter="url(#${filterId})" />
                <rect x="10" y="10" width="80" height="80" rx="12" fill="none" stroke="rgba(255,255,255,.48)" stroke-width=".75" />
              </svg>

              <div class="asset-content">
                <div class="asset-kicker-row">
                  <span class="asset-kicker">${escapeHtml(compactCategory(asset))}</span>
                  <span class="asset-code">${escapeHtml(asset.asset_code || "")}</span>
                </div>
                <div class="asset-title">${escapeHtml(asset.title || "Untitled")}</div>
                <div class="asset-detail">${escapeHtml(compactDetail(asset, layout.featured ? 92 : 58))}</div>
              </div>

              <div class="asset-footer">
                <span class="asset-status">${asset.include_in_resume ? "★ Resume Ready" : (asset.include_in_interview ? "Interview" : "Saved")}</span>
                <span class="asset-icon">${palette[2]}</span>
              </div>
            </button>
          `;
        }).join("");

        assetLayer.querySelectorAll(".asset-card").forEach(card => {
          const assetIndex = Number(card.dataset.assetIndex);
          const dragKey = `${state.experienceIndex}:${assetIndex}`;
          let dragState = null;

          card.addEventListener("mouseenter", () => {
            hoveredAssetIndex = assetIndex;
          });

          card.addEventListener("mouseleave", () => {
            hoveredAssetIndex = null;
          });

          card.addEventListener("pointerdown", event => {
            if (event.button !== 0) return;
            const stored = assetDragOffsets.get(dragKey) || { x: 0, y: 0 };
            dragState = {
              pointerId: event.pointerId,
              startX: event.clientX,
              startY: event.clientY,
              originX: stored.x,
              originY: stored.y,
              moved: false
            };
            card.setPointerCapture(event.pointerId);
            card.classList.add("dragging");
          });

          card.addEventListener("pointermove", event => {
            if (!dragState || dragState.pointerId !== event.pointerId) return;
            const dx = event.clientX - dragState.startX;
            const dy = event.clientY - dragState.startY;
            if (Math.hypot(dx, dy) > 5) dragState.moved = true;
            const next = { x: dragState.originX + dx, y: dragState.originY + dy };
            assetDragOffsets.set(dragKey, next);
            card.style.setProperty("--drag-x", `${next.x}px`);
            card.style.setProperty("--drag-y", `${next.y}px`);
          });

          const finishDrag = event => {
            if (!dragState || dragState.pointerId !== event.pointerId) return;
            card.__suppressAssetClick = dragState.moved;
            dragState = null;
            card.classList.remove("dragging");
            try { card.releasePointerCapture(event.pointerId); } catch (_) {}
          };

          card.addEventListener("pointerup", finishDrag);
          card.addEventListener("pointercancel", finishDrag);

          card.addEventListener("click", () => {
            if (card.__suppressAssetClick) {
              card.__suppressAssetClick = false;
              return;
            }
            openAsset(assetIndex);
          });
        });

        motionCards = [...assetLayer.querySelectorAll(".asset-card")].map((card, order) => ({
          card,
          assetIndex: Number(card.dataset.assetIndex),
          displacement: card.querySelector(".asset-displacement"),
          surface: card.querySelector(".decay-surface"),
          currentX: 0,
          currentY: 0,
          currentR: 0,
          targetX: 0,
          targetY: 0,
          targetR: 0,
          displacementScale: 0,
          appliedDisplacement: -1,
          appliedSurfaceScale: -1,
          phase: order * .82,
          idleSpeed: 1.18 + order * .10,
          movementBound: 34 + order * 3.2,
          maxDisplacement: 18 + order * 2.6,
          depth: 1 + order * .15,
          baseX: overviewLayouts[order].x / 100,
          baseY: overviewLayouts[order].y / 100,
          influence: 0
        }));
      }

      function renderAllAssets() {
        const assets = currentAssets();
        if (!assets.length) {
          allAssetsGrid.innerHTML = `<div class="empty-state">暂无职业资产。</div>`;
          return;
        }

        allAssetsGrid.innerHTML = assets.map((asset, index) => {
          const palette = paletteForAsset(index);
          return `
            <button class="grid-card" type="button" data-asset-index="${index}" style="--grid-accent:${palette[1]};background:linear-gradient(135deg, rgba(255,255,255,.82), ${palette[3]});">
              <div class="grid-code">${escapeHtml(asset.asset_code || "ASSET")}</div>
              <div class="grid-title">${escapeHtml(asset.title || "Untitled")}</div>
              <div class="grid-meta">${escapeHtml(compactCategory(asset))}<br>${escapeHtml(compactDetail(asset, 76))}</div>
            </button>
          `;
        }).join("");

        allAssetsGrid.querySelectorAll("[data-asset-index]").forEach(card => {
          card.addEventListener("click", () => openAsset(Number(card.dataset.assetIndex)));
        });
      }

      function renderSearchResults(query) {
        const assets = currentAssets();
        const normalized = cleanText(query).toLowerCase();
        const matches = assets
          .map((asset, index) => ({ asset, index }))
          .filter(item => !normalized || assetSearchText(item.asset).includes(normalized));

        if (!matches.length) {
          searchResults.innerHTML = `<div class="empty-state">没有找到匹配的职业资产。</div>`;
          return;
        }

        searchResults.innerHTML = matches.map(({ asset, index }) => {
          const palette = paletteForAsset(index);
          return `
            <button class="search-result" type="button" data-asset-index="${index}">
              <div class="grid-code" style="--grid-accent:${palette[1]}">${escapeHtml(asset.asset_code || "ASSET")}</div>
              <div class="grid-title">${escapeHtml(asset.title || "Untitled")}</div>
              <div class="grid-meta">${escapeHtml(compactCategory(asset))} · ${escapeHtml(compactDetail(asset, 100))}</div>
            </button>
          `;
        }).join("");

        searchResults.querySelectorAll("[data-asset-index]").forEach(card => {
          card.addEventListener("click", () => openAsset(Number(card.dataset.assetIndex)));
        });
      }

      function section(label, value) {
        if (!cleanText(value)) return "";
        return `
          <section class="section">
            <div class="section-label">${escapeHtml(label)}</div>
            <div class="section-text">${escapeHtml(value)}</div>
          </section>
        `;
      }

      function splitItems(value) {
        return String(value || "")
          .split(/\n+/)
          .map(item => item.replace(/^\s*(?:[-•·*]|\d+[.)、])\s*/, "").trim())
          .filter(Boolean);
      }

      function bulletList(value, emptyText = "该部分尚未形成可使用内容。") {
        const items = splitItems(value);
        if (!items.length) return `<div class="empty-layer">${escapeHtml(emptyText)}</div>`;
        return `<div class="bullet-list">${items.map(item => `<div class="bullet-item">${escapeHtml(item)}</div>`).join("")}</div>`;
      }

      function questionList(value, prefix = "Q") {
        const items = splitItems(value);
        if (!items.length) return `<div class="empty-layer">当前没有可使用的问题。</div>`;
        return `<div class="question-list">${items.map((item, index) => `
          <div class="question-card">
            <div class="question-index">${escapeHtml(prefix)}${index + 1}</div>
            <div class="question-text">${escapeHtml(item)}</div>
          </div>
        `).join("")}</div>`;
      }

      function tagList(value) {
        const list = String(value || "")
          .split(/[,，、;；\n]+/)
          .map(item => item.trim())
          .filter(Boolean);

        if (!list.length) return `<div class="note">待补充标签。</div>`;
        return `<div class="tag-wrap">${list.map(item => `<span class="tag">${escapeHtml(item)}</span>`).join("")}</div>`;
      }

      function tabContent(tab, asset) {
        if (tab === "overview") {
          const statusChips = [
            asset.role_in_asset,
            asset.fact_status,
            asset.external_permission
          ].filter(cleanText).map(value => `<span class="status-chip">${escapeHtml(value)}</span>`).join("");

          return `
            <div class="overview-hero">${escapeHtml(asset.overview_summary || asset.results || "该资产的快速摘要待补充。")}</div>
            ${statusChips ? `<div class="status-strip">${statusChips}</div>` : ""}
            ${section("资产定位", asset.asset_position)}
            <section class="section">
              <div class="section-label">证明能力</div>
              ${tagList(asset.overview_strengths || asset.skills)}
            </section>
            ${section("核心结果", asset.results)}
            ${section("可核验数据", asset.metrics)}
            ${section("差异化价值", asset.differentiator)}
          `;
        }

        if (tab === "star") {
          const hasStar = [asset.star_situation, asset.star_task, asset.star_action, asset.star_result].some(cleanText);
          if (!hasStar) {
            return `<div class="empty-layer">这项资产不适合生成独立STAR故事，或当前个人贡献证据不足。</div>${section("使用限制", asset.expression_limits)}`;
          }

          return `
            <div class="star-grid">
              <div class="star-row"><div class="star-letter">S</div><div class="star-text">${escapeHtml(asset.star_situation || asset.background || "待补充情境。")}</div></div>
              <div class="star-row"><div class="star-letter">T</div><div class="star-text">${escapeHtml(asset.star_task || asset.role_in_asset || asset.participation_level || "待明确任务。")}</div></div>
              <div class="star-row"><div class="star-letter">A</div><div class="star-text">${escapeHtml(asset.star_action || asset.actions || "待补充行动。")}</div></div>
              <div class="star-row"><div class="star-letter">R</div><div class="star-text">${escapeHtml(asset.star_result || asset.results || "待补充结果。")}</div></div>
            </div>
            ${[asset.star_b_situation, asset.star_b_task, asset.star_b_action, asset.star_b_result].some(cleanText) ? `
              <div class="memory-divider"></div>
              <div class="section-label" style="margin-bottom:8px;">STAR B · 挑战／迭代故事</div>
              <div class="star-grid">
                <div class="star-row"><div class="star-letter">S</div><div class="star-text">${escapeHtml(asset.star_b_situation || "待补充情境。")}</div></div>
                <div class="star-row"><div class="star-letter">T</div><div class="star-text">${escapeHtml(asset.star_b_task || "待明确任务。")}</div></div>
                <div class="star-row"><div class="star-letter">A</div><div class="star-text">${escapeHtml(asset.star_b_action || "待补充行动。")}</div></div>
                <div class="star-row"><div class="star-letter">R</div><div class="star-text">${escapeHtml(asset.star_b_result || "待补充结果。")}</div></div>
              </div>` : ""}
            <div class="memory-divider"></div>
            <section class="section">
              <div class="section-label">适用面试主题</div>
              ${tagList(asset.star_uses)}
            </section>
            ${section("讲述边界", asset.expression_limits)}
          `;
        }

        if (tab === "resume") {
          const resumeStatus = asset.include_in_resume ? "可进入简历候选库" : "不建议作为核心简历成果";
          return `
            <div class="status-strip">
              <span class="status-chip">${resumeStatus}</span>
              <span class="status-chip">AI生成后仍需本人审核</span>
            </div>
            <section class="section">
              <div class="section-label">中文简历候选表达</div>
              ${bulletList(asset.resume_bullets, "这项资产不建议单独写入核心简历。")}
            </section>
            ${section("使用策略", asset.resume_strategy)}
            <section class="section"><div class="section-label">适用岗位</div>${tagList(asset.resume_roles)}</section>
            <section class="section"><div class="section-label">关键词</div>${tagList(asset.resume_keywords)}</section>
            ${section("可使用数据", asset.metrics)}
            ${section("不可越界表述", asset.expression_limits)}
          `;
        }

        if (tab === "interview") {
          return `
            <section class="section">
              <div class="section-label">可回答的面试问题</div>
              ${questionList(asset.interview_questions, "Q")}
            </section>
            <section class="section">
              <div class="section-label">面试官可能继续追问</div>
              ${questionList(asset.interview_followups, "F")}
            </section>
            ${section("Recommended Angle", asset.interview_angles)}
            ${section("风险与易被追问点", asset.interview_risks)}
            <section class="section">
              <div class="section-label">能力主题</div>
              ${tagList(asset.star_uses || asset.skills)}
            </section>
            ${section("回答边界", asset.expression_limits)}
          `;
        }

        if (tab === "decision") {
          return `
            <section style="margin:28px 0;padding:34px 28px;border:1px solid rgba(36,34,31,.10);border-radius:24px;background:linear-gradient(145deg,rgba(255,255,255,.96),rgba(244,240,232,.88));text-align:center;box-shadow:0 18px 42px rgba(66,54,42,.07);">
              <div style="font-size:11px;font-weight:800;letter-spacing:.18em;color:var(--drawer-accent);">PRIVATE BY DESIGN</div>
              <div style="margin:14px 0 9px;font-size:23px;font-weight:800;line-height:1.35;color:#24221f;">完整决策记录仅开发者本人可见</div>
              <div style="max-width:350px;margin:0 auto;color:#77716b;font-size:13px;line-height:1.75;">公开 Demo 仅呈现可验证的成果与能力；内部判断、取舍依据和项目决策过程已做脱敏处理。</div>
              <div style="display:inline-flex;margin-top:20px;padding:8px 13px;border-radius:999px;background:var(--drawer-bg);color:var(--drawer-accent);font-size:11px;font-weight:800;">🔒 PRIVATE DECISIONS PROTECTED</div>
            </section>`;
        }

        if (tab === "lessons") {
          return [
            section("Reflection", asset.reflection),
            section("Lessons Learned／如果重新做", asset.lessons_learned),
            section("尚未确认", asset.uncertainties),
            section("风险与追问", asset.interview_risks)
          ].join("") || `<div class="empty-layer">该资产暂无复盘内容。</div>`;
        }


        if (tab === "memory") {
          return `
            <section style="margin:28px 0;padding:34px 28px;border:1px solid rgba(36,34,31,.10);border-radius:24px;background:linear-gradient(145deg,rgba(255,255,255,.96),rgba(244,240,232,.88));text-align:center;box-shadow:0 18px 42px rgba(66,54,42,.07);">
              <div style="font-size:11px;font-weight:800;letter-spacing:.18em;color:var(--drawer-accent);">PRIVATE BY DESIGN</div>
              <div style="margin:14px 0 9px;font-size:23px;font-weight:800;line-height:1.35;color:#24221f;">完整职业记忆仅开发者本人可见</div>
              <div style="max-width:330px;margin:0 auto;color:#77716b;font-size:13px;line-height:1.75;">公开 Demo 已完成脱敏。个人备忘、内部资料、协作细节与敏感数据不会对外展示。</div>
              <div style="display:inline-flex;margin-top:20px;padding:8px 13px;border-radius:999px;background:var(--drawer-bg);color:var(--drawer-accent);font-size:11px;font-weight:800;">🔒 PRIVATE MEMORY PROTECTED</div>
            </section>`;
        }

        return "";
      }

      function renderDrawer() {
        const asset = currentAsset();

        if (!asset) {
          drawer.classList.remove("open");
          drawerHeading.innerHTML = "";
          tabsElement.innerHTML = "";
          drawerBody.innerHTML = "";
          storyStage.classList.remove("has-selection");
          return;
        }

        const palette = paletteForAsset(state.assetIndex);
        drawer.style.setProperty("--drawer-bg", palette[0]);
        drawer.style.setProperty("--drawer-accent", palette[1]);
        drawer.classList.add("open");
        storyStage.classList.add("has-selection");

        drawerHeading.innerHTML = `
          <div class="drawer-icon">${palette[2]}</div>
          <div>
            <div class="drawer-code">${escapeHtml(asset.asset_code || "")}</div>
            <div class="drawer-title">${escapeHtml(asset.title || "Untitled")}</div>
            <div class="drawer-meta">${escapeHtml(asset.category || "")}${asset.fact_status ? ` · ${escapeHtml(asset.fact_status)}` : ""}</div>
          </div>
        `;

        tabsElement.innerHTML = tabs.map(([key, label]) => `
          <button type="button" class="tab ${state.tab === key ? "active" : ""}" data-tab="${key}">${label}</button>
        `).join("");

        tabsElement.querySelectorAll(".tab").forEach(button => {
          button.addEventListener("click", () => {
            state.tab = button.dataset.tab;
            renderDrawer();
          });
        });

        drawerBody.innerHTML = tabContent(state.tab, asset);
      }

      function openAsset(assetIndex, tab = "overview") {
        state.assetIndex = assetIndex;
        state.tab = tab;
        renderOverviewAssets();
        renderDrawer();
      }

      function closeDrawer() {
        state.assetIndex = null;
        renderOverviewAssets();
        renderDrawer();
      }

      function moveAsset(step) {
        const assets = currentAssets();
        if (!assets.length) return;
        const current = state.assetIndex ?? 0;
        state.assetIndex = (current + step + assets.length) % assets.length;
        state.tab = "overview";
        renderOverviewAssets();
        renderDrawer();
      }

      function renderStory() {
        renderExperienceHeader();
        state.featuredAssetIndexes = chooseFeaturedAssetIndexes();
        renderOverviewAssets();
        renderAllAssets();
        renderSearchResults("");
        renderDrawer();
        setView(state.activeView || "overview");
        requestAnimationFrame(refreshStageMetrics);
      }

      function refreshStageMetrics() {
        const rect = storyStage.getBoundingClientRect();
        stageMetrics = {
          left: rect.left,
          top: rect.top,
          width: Math.max(rect.width, 1),
          height: Math.max(rect.height, 1)
        };
        coverGeometryDirty = true;
      }

      function updatePointerTargets() {
        const globalX = ((pointer.clientX - stageMetrics.left) / stageMetrics.width - .5) * 2;
        const globalY = ((pointer.clientY - stageMetrics.top) / stageMetrics.height - .5) * 2;

        motionCards.forEach((item, index) => {
          const speed = (index + 1) * 10;
          item.targetX = globalX * speed;
          item.targetY = globalY * speed;
          item.targetR = 0;
          item.influence = 0;
        });
      }

      storyStage.addEventListener("pointerenter", refreshStageMetrics, { passive: true });
      storyStage.addEventListener("pointermove", event => {
        pointer.clientX = event.clientX;
        pointer.clientY = event.clientY;
        pointer.active = true;
        const mouseX = (event.clientX - stageMetrics.left) / stageMetrics.width - .5;
        const mouseY = (event.clientY - stageMetrics.top) / stageMetrics.height - .5;
        kineticDots.forEach((dot, index) => {
          const speed = (index + 1) * 40;
          dot.style.transform = `translate(${mouseX * speed}px, ${mouseY * speed}px)`;
        });
      }, { passive: true });

      storyStage.addEventListener("mouseleave", () => {
        pointer.active = false;
        hoveredAssetIndex = null;
        motionCards.forEach(item => {
          item.targetX = 0;
          item.targetY = 0;
          item.targetR = 0;
          item.influence = 0;
          item.card.classList.remove("pointer-near");
        });
        kineticDots.forEach(dot => { dot.style.transform = "translate(0, 0)"; });
      });

      window.addEventListener("resize", () => {
        refreshStageMetrics();
        coverGeometryDirty = true;
        updateExperienceLinks();
      }, { passive: true });

      function animateCards(time) {
        const deltaSeconds = Math.min(Math.max((time - lastFrameTime) / 1000, 0), .034);
        lastFrameTime = time;

        const coverMoveAmount = dampAmount(86, deltaSeconds);
        const coverOpacityAmount = dampAmount(90, deltaSeconds);
        coverMotionCards.forEach(item => {
          item.currentX = lerp(item.currentX, item.targetX, coverMoveAmount);
          item.currentY = lerp(item.currentY, item.targetY, coverMoveAmount);
          item.currentScale = lerp(item.currentScale, item.targetScale, coverMoveAmount);
          item.currentOpacity = lerp(item.currentOpacity, item.targetOpacity, coverOpacityAmount);

          item.card.style.setProperty("--cover-x", `${item.currentX.toFixed(2)}px`);
          item.card.style.setProperty("--cover-y", `${item.currentY.toFixed(2)}px`);
          item.card.style.setProperty("--cover-scale", item.currentScale.toFixed(4));
          item.card.style.opacity = item.currentOpacity.toFixed(3);
          item.card.style.zIndex = `${item.targetZ}`;
        });

        const rawSpeed = Math.hypot(pointer.clientX - pointer.previousX, pointer.clientY - pointer.previousY);
        const speedAmount = dampAmount(62, deltaSeconds);
        pointer.speed = lerp(pointer.speed, pointer.active ? rawSpeed : 0, speedAmount);

        if (pointer.active && state.screen === "story" && state.activeView === "overview") {
          updatePointerTargets();
        }

        const positionAmount = dampAmount(76, deltaSeconds);
        const rotationAmount = dampAmount(66, deltaSeconds);
        const displacementAmount = dampAmount(48, deltaSeconds);
        const updateFilters = time - lastFilterUpdateTime >= 34;

        motionCards.forEach(item => {
          item.currentX = lerp(item.currentX, item.targetX, positionAmount);
          item.currentY = lerp(item.currentY, item.targetY, positionAmount);
          item.currentR = lerp(item.currentR, item.targetR, rotationAmount);

          const idleX = 0;
          const idleY = 0;
          const decayActive = false;
          const targetDisplacement = 0;

          item.displacementScale = lerp(item.displacementScale, targetDisplacement, displacementAmount);
          item.card.classList.toggle("decay-active", decayActive && item.displacementScale > .4);

          item.card.style.setProperty("--mx", `${(item.currentX + idleX).toFixed(2)}px`);
          item.card.style.setProperty("--my", `${(item.currentY + idleY).toFixed(2)}px`);
          item.card.style.setProperty("--mr", `${item.currentR.toFixed(2)}deg`);

          if (updateFilters && item.displacement && Math.abs(item.displacementScale - item.appliedDisplacement) > .22) {
            item.appliedDisplacement = item.displacementScale;
            item.displacement.setAttribute("scale", item.displacementScale.toFixed(2));
          }

          if (updateFilters && item.surface) {
            const pulse = 1 + Math.min(item.displacementScale / 900, .026);
            if (Math.abs(pulse - item.appliedSurfaceScale) > .0012) {
              item.appliedSurfaceScale = pulse;
              item.surface.style.transform = `scale(${pulse.toFixed(4)})`;
            }
          }
        });

        if (updateFilters) lastFilterUpdateTime = time;

        pointer.previousX = pointer.clientX;
        pointer.previousY = pointer.clientY;
        animationFrameId = requestAnimationFrame(animateCards);
      }

      document.getElementById("back-button").addEventListener("click", () => {
        closeDrawer();
        state.activeView = "overview";
        setView("overview");
        renderCovers();
        switchScreen("selector");
      });

      document.getElementById("collections-button").addEventListener("click", () => {
        resetSelectorCards();
        switchScreen("collection");
      });

      document.getElementById("collection-prev").addEventListener("click", () => moveCollection(-1));
      document.getElementById("collection-next").addEventListener("click", () => moveCollection(1));
      collectionViewport.addEventListener("scroll", syncCollectionFromScroll, { passive: true });
      collectionViewport.addEventListener("pointerdown", beginCollectionBlankDrag);
      collectionViewport.addEventListener("pointermove", moveCollectionBlankDrag);
      collectionViewport.addEventListener("pointerup", endCollectionBlankDrag);
      collectionViewport.addEventListener("pointercancel", endCollectionBlankDrag);

      // Track selector drags on the window instead of the card itself. This is
      // reliable in Streamlit's iframe even when the pointer leaves the card.
      window.addEventListener("pointermove", moveSelectorDrag, { passive: false });
      window.addEventListener("pointerup", endSelectorDrag, { passive: false });
      window.addEventListener("pointercancel", event => {
        if (!selectorDrag || selectorDrag.pointerId !== event.pointerId) return;
        const card = selectorDrag.card;
        selectorDrag = null;
        returnCardHome(card);
      });

      document.getElementById("rule-button").addEventListener("click", () => {
        const assets = currentAssets();
        if (!assets.length) return;
        const firstRuleAsset = assets.findIndex(asset => cleanText(asset.expression_limits) || cleanText(asset.contribution_boundary));
        openAsset(firstRuleAsset >= 0 ? firstRuleAsset : 0, "memory");
        requestAnimationFrame(() => {
          drawerBody.scrollTop = drawerBody.scrollHeight;
        });
      });

      document.getElementById("previous-asset").addEventListener("click", () => moveAsset(-1));
      document.getElementById("next-asset").addEventListener("click", () => moveAsset(1));
      document.getElementById("close-drawer").addEventListener("click", closeDrawer);

      bottomNav.querySelectorAll(".bottom-nav-button").forEach(button => {
        button.addEventListener("click", () => setView(button.dataset.view));
      });

      overviewSearchTrigger.addEventListener("click", () => setView("search"));

      document.querySelectorAll(".panel-close").forEach(button => {
        button.addEventListener("click", () => setView(button.dataset.view || "overview"));
      });

      assetSearch.addEventListener("input", event => renderSearchResults(event.target.value));

      document.addEventListener("keydown", event => {
        if (event.key === "Escape") {
          if (drawer.classList.contains("open")) closeDrawer();
          else if (state.activeView !== "overview") setView("overview");
        }
        if (drawer.classList.contains("open") && event.key === "ArrowLeft") moveAsset(-1);
        if (drawer.classList.contains("open") && event.key === "ArrowRight") moveAsset(1);
      });

      renderCollections();
      renderStory();
      setView("overview");
      if (INITIAL_STUDIO.mode === "focus" && DATA.length) {
        document.documentElement.dataset.studio = "focus";
        switchScreen("story");
      } else {
        switchScreen("collection");
      }

      if (!animationFrameId) {
        animationFrameId = requestAnimationFrame(animateCards);
      }
    </script>
    """

    component_html = component_html.replace("__DATA__", data_json)
    component_html = component_html.replace("__INITIAL_STUDIO__", initial_studio_json)

    # Load the large August 2 interface as a normal local component document.
    # Safari can leave both srcdoc and data-URL iframes blank at this size.
    bridge_script = r"""
    <script>
      (() => {
        const send = (type, extra = {}) => window.parent.postMessage({
          isStreamlitMessage: true,
          type,
          ...extra
        }, "*");
        send("streamlit:componentReady", { apiVersion: 1 });
        const reportHeight = () => send("streamlit:setFrameHeight", {
          height: Math.max(window.innerHeight || 0, 720)
        });
        window.addEventListener("load", reportHeight);
        window.addEventListener("resize", reportHeight);
        reportHeight();
      })();
    </script>
    """
    standalone_html = (
        "<!doctype html><html><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "</head><body>" + bridge_script + component_html + "</body></html>"
    )
    index_path = COMPONENT_DIR / "index.html"
    if not index_path.exists() or index_path.read_text(encoding="utf-8") != standalone_html:
        index_path.write_text(standalone_html, encoding="utf-8")
    digest = hashlib.sha256(standalone_html.encode("utf-8")).hexdigest()[:12]
    CAREER_ASSET_COMPONENT(key=f"career-asset-{digest}", default=None)


def render_career_asset_library_page(experiences):
    """渲染职业资产库页面（含页面级样式和三层交互界面）。"""
    st.markdown(
        r"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&family=Manrope:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap');

            :root {
                --lum-bg: #fffafa;
                --lum-panel: #fbfbf9;
                --lum-ink: #111111;
                --lum-muted: #8b8b88;
                --lum-line: rgba(17,17,17,.08);
            }

            html,
            body,
            .stApp,
            [data-testid="stAppViewContainer"] {
                min-height: 100dvh !important;
                margin: 0 !important;
                overflow: hidden !important;
                background: var(--lum-bg) !important;
                color: var(--lum-ink) !important;
            }

            header[data-testid="stHeader"],
            [data-testid="stToolbar"],
            [data-testid="stDecoration"],
            [data-testid="collapsedControl"],
            [data-testid="stStatusWidget"] {
                display: none !important;
            }

            section[data-testid="stSidebar"] {
                position: fixed !important;
                inset: 0 auto 0 0 !important;
                z-index: 999999 !important;
                display: block !important;
                width: 82px !important;
                min-width: 82px !important;
                max-width: 82px !important;
                height: 100dvh !important;
                overflow: hidden !important;
                background: var(--lum-bg) !important;
                border-right: 1px solid transparent !important;
                box-shadow: none !important;
                transition:
                    width .30s cubic-bezier(.2,.8,.2,1),
                    min-width .30s cubic-bezier(.2,.8,.2,1),
                    max-width .30s cubic-bezier(.2,.8,.2,1),
                    background .25s ease,
                    box-shadow .25s ease !important;
            }

            section[data-testid="stSidebar"]:hover,
            section[data-testid="stSidebar"]:focus-within {
                width: 310px !important;
                min-width: 310px !important;
                max-width: 310px !important;
                background: rgba(251,251,249,.985) !important;
                border-right-color: var(--lum-line) !important;
                box-shadow: 24px 0 55px rgba(22,22,22,.08) !important;
            }

            section[data-testid="stSidebar"] > div,
            section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                width: 100% !important;
                min-width: 82px !important;
                max-width: none !important;
                height: 100% !important;
                overflow: hidden !important;
                background: transparent !important;
            }

            section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                padding: 26px 18px 24px !important;
            }

            section[data-testid="stSidebar"] .lum-sidebar-brand {
                width: 250px !important;
                height: 76px !important;
                padding: 8px 14px !important;
                color: var(--lum-ink) !important;
                font-family: "Gaegu", "Comic Sans MS", cursive !important;
                font-size: 31px !important;
                line-height: 1 !important;
                font-weight: 700 !important;
                letter-spacing: .04em !important;
                white-space: nowrap !important;
            }

            section[data-testid="stSidebar"]:not(:hover):not(:focus-within) .lum-sidebar-brand {
                padding-left: 12px !important;
                font-size: 0 !important;
            }

            section[data-testid="stSidebar"]:not(:hover):not(:focus-within) .lum-sidebar-brand::after {
                content: "l.";
                font-family: "Gaegu", "Comic Sans MS", cursive;
                font-size: 30px;
                font-weight: 700;
            }

            section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
                width: 250px !important;
                margin: 18px 14px 14px !important;
                color: #aaaaa7 !important;
                font-family: "Manrope", sans-serif !important;
                font-size: 12px !important;
                font-weight: 800 !important;
                letter-spacing: .12em !important;
                text-transform: uppercase !important;
                white-space: nowrap !important;
                opacity: 0 !important;
                transition: opacity .16s ease .05s !important;
            }

            section[data-testid="stSidebar"]:hover div[data-testid="stRadio"] > label,
            section[data-testid="stSidebar"]:focus-within div[data-testid="stRadio"] > label {
                opacity: 1 !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] {
                width: 270px !important;
                gap: 7px !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label {
                position: relative !important;
                display: flex !important;
                align-items: center !important;
                width: 270px !important;
                min-height: 54px !important;
                margin: 0 !important;
                padding: 0 18px 0 70px !important;
                overflow: hidden !important;
                border: 0 !important;
                border-radius: 18px !important;
                background: transparent !important;
                transition: background .18s ease !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
            section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
                position: absolute !important;
                width: 1px !important;
                height: 1px !important;
                opacity: 0 !important;
                pointer-events: none !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label::before {
                position: absolute;
                left: 20px;
                top: 50%;
                width: 28px;
                transform: translateY(-50%);
                color: #666663;
                font: 22px/1 "Manrope", sans-serif;
                text-align: center;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(1)::before { content: "⌂"; }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(2)::before { content: "◇"; }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(3)::before { content: "▣"; }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(4)::before { content: "↗"; }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(5)::before { content: "◷"; }

            section[data-testid="stSidebar"] div[role="radiogroup"] label::after {
                content: "";
                position: absolute;
                left: 56px;
                top: 50%;
                width: 12px;
                height: 12px;
                transform: translateY(-50%);
                border: 1px solid #cad5ce;
                border-radius: 50%;
                background: #eef6f0;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
                background: rgba(17,17,17,.055) !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
                background: #151515 !important;
                color: #ffffff !important;
                border-left: 0 !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before {
                color: #ffffff !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::after {
                border: 4px solid #0e7457;
                background: #ffffff;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label p {
                margin: 0 !important;
                overflow: hidden !important;
                color: #1b1b1a !important;
                font-family: "Noto Sans SC", sans-serif !important;
                font-size: 17px !important;
                line-height: 1.35 !important;
                font-weight: 750 !important;
                text-overflow: ellipsis !important;
                white-space: nowrap !important;
                opacity: 1 !important;
                transition: opacity .14s ease !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
                color: #ffffff !important;
            }

            section[data-testid="stSidebar"]:not(:hover):not(:focus-within)
            div[role="radiogroup"] label p {
                opacity: 0 !important;
            }

            [data-testid="stMain"] {
                width: calc(100% - 82px) !important;
                min-height: 100dvh !important;
                margin-left: 82px !important;
                padding: 0 !important;
                overflow: hidden !important;
                background: #fffafa !important;
                transition:
                    margin-left .30s cubic-bezier(.2,.8,.2,1),
                    width .30s cubic-bezier(.2,.8,.2,1) !important;
            }

            .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"],
            .stApp:has(section[data-testid="stSidebar"]:focus-within) [data-testid="stMain"] {
                width: calc(100% - 310px) !important;
                margin-left: 310px !important;
            }

            .block-container,
            [data-testid="stMainBlockContainer"] {
                width: 100% !important;
                max-width: none !important;
                min-height: 100dvh !important;
                margin: 0 !important;
                padding: 0 !important;
                overflow: hidden !important;
            }

            [data-testid="stVerticalBlock"],
            [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stElementContainer"] {
                margin: 0 !important;
                padding: 0 !important;
                gap: 0 !important;
            }

            .st-key-career-asset-canvas div[data-testid="stElementContainer"]:has(iframe[title="st.iframe"]),
            .st-key-career-asset-canvas div[data-testid="stCustomComponentV1"],
            .st-key-career-asset-canvas div[data-testid="stCustomComponentV1"] > div,
            .st-key-career-asset-canvas div[data-testid="stIFrame"] {
                position: relative !important;
                inset: auto !important;
                z-index: 1 !important;
                display: block !important;
                width: 100% !important;
                max-width: none !important;
                height: 100dvh !important;
                min-height: 100dvh !important;
                margin: 0 !important;
                padding: 0 !important;
                border: 0 !important;
                overflow: hidden !important;
                background: #fffafa !important;
                line-height: 0 !important;
            }

            .st-key-career-asset-canvas iframe[title="st.iframe"] {
                position: relative !important;
                inset: auto !important;
                z-index: 1 !important;
                display: block !important;
                width: 100% !important;
                max-width: none !important;
                height: 100dvh !important;
                min-height: 100dvh !important;
                margin: 0 !important;
                padding: 0 !important;
                border: 0 !important;
                background: #fffafa !important;
            }

            @media (max-width: 820px) {
                section[data-testid="stSidebar"] {
                    width: 70px !important;
                    min-width: 70px !important;
                    max-width: 70px !important;
                }

                section[data-testid="stSidebar"]:hover,
                section[data-testid="stSidebar"]:focus-within {
                    width: 280px !important;
                    min-width: 280px !important;
                    max-width: 280px !important;
                }

                [data-testid="stMain"] {
                    width: calc(100% - 70px) !important;
                    margin-left: 70px !important;
                }

                .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"],
                .stApp:has(section[data-testid="stSidebar"]:focus-within) [data-testid="stMain"] {
                    width: calc(100% - 70px) !important;
                    margin-left: 70px !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if not experiences:
        st.info("目前还没有保存职业经历。")
        return

    with st.container(key="career-asset-canvas"):
        render_experience_bank_canvas(experiences)
