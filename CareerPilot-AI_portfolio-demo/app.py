import html
import hashlib
import hmac
import json
import os
import uuid
from datetime import date, datetime

import streamlit as st
import streamlit.components.v1 as components

from demo_database import (
    add_job,
    configure_session_database,
    get_all_experiences,
    get_all_jobs,
    get_asset_by_code,
    get_experience_assets,
    get_experience_rules,
    initialize_database,
    seed_demo_data,
    update_job_progress,
)


from job_workspace import render_job_application_workspace
from resume_workspace import render_resume_workspace
from interview_workspace import render_interview_workspace
from career_asset_library import render_career_asset_library_page
from sidebar_p1 import render_p1_sidebar_styles


STATUS_OPTIONS = [
    "准备投递",
    "投递简历",
    "笔试测评",
    "群面",
    "初试",
    "复试",
    "业务面",
    "HR面",
    "谈薪",
    "Offer",
    "已结束",
    "拒绝",
    "放弃",
]

DEMO_ACCESS_COOKIE = "lumooi_demo_access"
PORTFOLIO_AUTH_SESSION_KEY = "portfolio_authenticated"


st.set_page_config(
    page_title="lumooi",
    page_icon="◌",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _demo_access_token(password):
    return hmac.new(
        password.encode("utf-8"),
        b"lumooi-demo-browser-access-v1",
        hashlib.sha256,
    ).hexdigest()


def _install_demo_session_cookie(token):
    """Bridge full-page links without extending login beyond this browser session."""
    token_json = json.dumps(token)
    components.html(
        f"""
        <script>
        (() => {{
            let owner;
            try {{ owner = window.parent; }} catch (_) {{ return; }}
            const secure = owner.location.protocol === "https:" ? "; Secure" : "";
            owner.document.cookie = "{DEMO_ACCESS_COOKIE}=" + {token_json}
                + "; Path=/; SameSite=Lax" + secure;
        }})();
        </script>
        """,
        height=0,
        scrolling=False,
    )


def require_portfolio_password():
    """Run the password gate once and keep authentication for this session."""
    try:
        configured_password = str(st.secrets.get("PORTFOLIO_PASSWORD", "")).strip()
    except Exception:
        configured_password = ""
    configured_password = configured_password or os.environ.get("PORTFOLIO_PASSWORD", "").strip()

    if not configured_password:
        st.error("该 lumooi Demo 尚未配置访问密码，当前已默认关闭访问。")
        st.caption("开发者请在 Streamlit Secrets 中配置 PORTFOLIO_PASSWORD。")
        st.stop()

    expected_access_token = _demo_access_token(configured_password)
    try:
        stored_access_token = str(st.context.cookies.get(DEMO_ACCESS_COOKIE, ""))
    except Exception:
        stored_access_token = ""

    access_is_valid = bool(stored_access_token) and hmac.compare_digest(
        stored_access_token,
        expected_access_token,
    )
    if st.session_state.get(PORTFOLIO_AUTH_SESSION_KEY) or access_is_valid:
        st.session_state[PORTFOLIO_AUTH_SESSION_KEY] = True
        _install_demo_session_cookie(expected_access_token)
        return

    st.markdown(
        r"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,600;1,400&family=VT323&display=swap');
        :root{--retro-light:#F0EDE0;--retro-main:#E0DCCF;--retro-dark:#C4C0B3;--retro-shadow:#A09C8F;--retro-black:#111;--retro-green:#33ff00}
        html body:has(.portfolio-retro-screen) [data-testid="stHeader"],html body:has(.portfolio-retro-screen) section[data-testid="stSidebar"]{display:none!important}
        html body:has(.portfolio-retro-screen),html body:has(.portfolio-retro-screen) .stApp,html body:has(.portfolio-retro-screen) [data-testid="stAppViewContainer"],html body:has(.portfolio-retro-screen) [data-testid="stMain"]{background:transparent!important}
        html body:has(.portfolio-retro-screen) [data-testid="stMain"]{margin-left:0!important}
        html body:has(.portfolio-retro-screen) .block-container{width:100%!important;max-width:none!important;padding:0!important}
        .portfolio-retro-screen{position:fixed;inset:0;z-index:0;overflow:hidden;background:#0a0a0a;transition:background-color 2s ease;font-family:'EB Garamond',Georgia,serif}
        .portfolio-retro-screen.boot-complete{background:#f4f1e6}
        .retro-product-col{position:absolute;left:50%;top:42%;width:440px;height:620px;display:flex;align-items:center;justify-content:center;perspective:2000px;transform:translate(-50%,-50%) scale(.76)}
        .retro-scene{position:relative;transform-style:preserve-3d;transform:rotateY(-10deg) rotateX(2deg)}
        .retro-computer{position:relative;width:360px;height:440px;transform-style:preserve-3d}
        .retro-face{position:absolute;background:var(--retro-main);border:1px solid rgba(0,0,0,.1)}
        .retro-front{width:360px;height:440px;transform:translateZ(100px);background:linear-gradient(135deg,var(--retro-light),var(--retro-main));display:flex;flex-direction:column;align-items:center;padding-top:40px}
        .retro-top{width:360px;height:200px;transform:rotateX(90deg) translateZ(100px);background:var(--retro-light)}
        .retro-bottom{width:360px;height:200px;transform:rotateX(-90deg) translateZ(340px);background:var(--retro-shadow);box-shadow:0 50px 100px rgba(0,0,0,.8)}
        .retro-left{width:200px;height:440px;transform:rotateY(-90deg) translateZ(100px);background:var(--retro-main)}
        .retro-right{width:200px;height:440px;transform:rotateY(90deg) translateZ(260px);background:var(--retro-dark)}
        .retro-screen-inset{width:280px;height:220px;background:#222;border-radius:16px;box-shadow:inset 2px 2px 10px rgba(0,0,0,.8);display:flex;align-items:center;justify-content:center;position:relative}
        .retro-crt{width:260px;height:200px;background:var(--retro-black);border-radius:40%/10%;position:relative;overflow:hidden;box-shadow:inset 0 0 40px #000;animation:retro-flicker .15s infinite}
        .retro-crt::after{content:"";position:absolute;inset:0;z-index:10;pointer-events:none;background:linear-gradient(rgba(18,16,16,0) 50%,rgba(0,0,0,.25) 50%),linear-gradient(90deg,rgba(255,0,0,.06),rgba(0,255,0,.02),rgba(0,0,255,.06));background-size:100% 2px,3px 100%}
        .retro-boot{padding:20px;color:var(--retro-green);font-family:'VT323','Courier New',monospace;font-size:11px;line-height:1.2;text-shadow:0 0 5px var(--retro-green);height:100%;overflow:hidden}
        .retro-boot-head{border-bottom:1px solid rgba(51,255,0,.6);padding-bottom:5px;margin-bottom:7px}.retro-demo-message{padding:3px 0 6px;border-bottom:1px solid rgba(51,255,0,.28);font-size:10px;line-height:1.35}.retro-demo-message strong{display:block;font-size:18px;letter-spacing:.08em}.retro-log{height:54px;overflow:hidden;display:flex;flex-direction:column;justify-content:flex-end}.retro-line{margin-bottom:2px;white-space:nowrap}
        .retro-progress{margin-top:6px}.retro-progress-label{margin-bottom:4px;font-size:10px;display:flex;justify-content:space-between}.retro-progress-outer{width:100%;height:10px;border:1px solid var(--retro-green);padding:1px}.retro-progress-inner{height:100%;width:0;background:var(--retro-green);transition:width .1s linear}
        .retro-logo{position:absolute;bottom:30px;left:30px;width:20px;height:26px;border-radius:50%/60% 60% 40% 40%;background:linear-gradient(180deg,#63B548 0 16.6%,#F6C829 16.6% 33.3%,#E57D25 33.3% 50%,#D83335 50% 66.6%,#9C4595 66.6% 83.3%,#468CCF 83.3%);opacity:.5}
        .retro-slot{width:140px;height:12px;background:#111;border-radius:6px;margin-left:100px}.retro-grill{position:absolute;bottom:25px;right:25px;display:grid;grid-template-columns:repeat(4,1fr);gap:2px;width:30px;height:20px}.retro-vent{background:#222;border-radius:1px}
        .retro-keyboard{display:none}.retro-status{position:absolute;left:50%;bottom:5%;width:440px;transform:translateX(-50%);text-align:center;font-family:'VT323',monospace;color:rgba(51,255,0,.48);font-size:16px;letter-spacing:2px;text-transform:uppercase;animation:retro-pulse 1.5s infinite}
        @keyframes retro-pulse{50%{opacity:.45}}@keyframes retro-flicker{0%{opacity:.97}10%{opacity:.9}15%{opacity:1}20%{opacity:.98}100%{opacity:1}}

        .portfolio-gate-card{display:none!important}
        .portfolio-gate-card::before{content:"ACCESS NOTE / 01";display:block;margin-bottom:20px;padding-bottom:9px;border-bottom:1px solid rgba(0,0,0,.26);font-family:'VT323','Courier New',monospace;font-size:18px;letter-spacing:.09em}
        .portfolio-gate-card .gate-kicker{font-family:'VT323','Courier New',monospace;font-size:17px;letter-spacing:.16em;text-transform:uppercase;color:#333}
        .portfolio-gate-card h1{margin:8px 0 12px!important;color:#0f0f0f;font-family:'EB Garamond',Georgia,serif!important;font-size:clamp(34px,3.4vw,52px)!important;line-height:1!important;font-weight:600!important;letter-spacing:-.035em!important}
        .portfolio-gate-card p{margin:0;color:#292826;font-size:17px;line-height:1.55}
        html body:has(.portfolio-retro-screen) [data-testid="stForm"]{position:fixed!important;z-index:4!important;left:50%!important;top:68%!important;width:min(410px,78vw)!important;height:178px!important;min-height:0!important;margin:0!important;padding:18px 22px 22px!important;border:1px solid rgba(0,0,0,.28)!important;border-radius:5px!important;background:linear-gradient(180deg,var(--retro-light),var(--retro-main))!important;box-shadow:0 13px 0 var(--retro-dark),0 28px 55px rgba(0,0,0,.30)!important;overflow:visible!important;transform:translateX(-50%) perspective(900px) rotateX(5deg)!important;transform-origin:center top!important}
        html body:has(.portfolio-retro-screen) [data-testid="stForm"]>div[data-testid="stVerticalBlock"]{height:auto!important;min-height:0!important}
        html body:has(.portfolio-retro-screen) [data-testid="stForm"]::before{content:"LUMOOI ACCESS KEYBOARD";display:block;margin-bottom:8px;padding-bottom:5px;border-bottom:1px solid rgba(0,0,0,.25);font-family:'VT323','Courier New',monospace;font-size:17px;letter-spacing:.08em;color:#111}
        html body:has(.portfolio-retro-screen) [data-testid="stTextInput"] label p{font-family:'VT323','Courier New',monospace!important;font-size:18px!important;color:#111!important}
        html body:has(.portfolio-retro-screen) [data-testid="stTextInput"] input{background:#111!important;color:#33ff00!important;border:1px solid #111!important;border-radius:0!important;font-family:'VT323','Courier New',monospace!important;font-size:18px!important;caret-color:#33ff00!important}
        html body:has(.portfolio-retro-screen) [data-testid="stTextInput"] input::placeholder{color:rgba(51,255,0,.52)!important}
        html body:has(.portfolio-retro-screen) button[kind="primaryFormSubmit"],html body:has(.portfolio-retro-screen) button[data-testid="stBaseButton-primaryFormSubmit"]{border:1px solid #111!important;border-radius:0!important;background:#111!important;color:#33ff00!important;font-family:'VT323','Courier New',monospace!important;font-size:20px!important;letter-spacing:.08em!important;box-shadow:none!important}
        html body:has(.portfolio-retro-screen) button[kind="primaryFormSubmit"]:hover,html body:has(.portfolio-retro-screen) button[data-testid="stBaseButton-primaryFormSubmit"]:hover{background:#33ff00!important;color:#111!important}
        html body:has(.portfolio-retro-screen) [data-testid="stAlert"]{position:fixed!important;z-index:6!important;left:50%!important;top:92%!important;width:min(410px,78vw)!important;transform:translateX(-50%)!important}
        @media(max-width:720px){.retro-product-col{top:37%;transform:translate(-50%,-50%) scale(.58)}.retro-status{display:none}html body:has(.portfolio-retro-screen) [data-testid="stForm"]{top:66%!important;width:min(390px,88vw)!important;height:174px!important;padding:16px 18px!important}html body:has(.portfolio-retro-screen) [data-testid="stAlert"]{top:91%!important;width:min(390px,88vw)!important}}
        @media(prefers-reduced-motion:reduce){.retro-crt,.retro-status{animation:none!important}}
        </style>
        <div class="portfolio-retro-screen" aria-hidden="true">
          <div class="retro-product-col"><div class="retro-scene"><div class="retro-computer">
            <div class="retro-face retro-front"><div class="retro-screen-inset"><div class="retro-crt"><div class="retro-boot"><div class="retro-boot-head">LUMOOI BIOS v1.0.4<br>(C) 2026 CAREER ASSET SYSTEM</div><div class="retro-demo-message"><strong>LUMOOI DEMO</strong><span>临时密码访问 · 公开内容已脱敏</span><br><span>请在下方键盘输入访问密码</span></div><div class="retro-log"></div><div class="retro-progress"><div class="retro-progress-label"><span>ACCESS SYSTEM...</span><span class="retro-percent">0%</span></div><div class="retro-progress-outer"><div class="retro-progress-inner"></div></div></div></div></div></div><div class="retro-logo"></div><div class="retro-slot"></div><div class="retro-grill"><i class="retro-vent"></i><i class="retro-vent"></i><i class="retro-vent"></i><i class="retro-vent"></i></div></div>
            <div class="retro-face retro-left"></div><div class="retro-face retro-right"></div><div class="retro-face retro-top"></div><div class="retro-face retro-bottom"></div>
            <div class="retro-keyboard"><div class="retro-kb-base"><div class="retro-keys"><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key"></i><i class="retro-key space"></i></div></div></div>
          </div></div></div><div class="retro-status">System Boot in Progress...</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    components.html(
        r"""
        <script>
        (()=>{let owner,doc;try{owner=window.parent;doc=owner.document}catch(_){return}
        if(typeof owner.__lumooiRetroCleanup==='function')owner.__lumooiRetroCleanup();
        const screen=doc.querySelector('.portfolio-retro-screen');if(!screen)return;
        const log=screen.querySelector('.retro-log'),bar=screen.querySelector('.retro-progress-inner'),percent=screen.querySelector('.retro-percent'),status=screen.querySelector('.retro-status');
        const lines=['CAREER ASSET ENGINE: READY','PRIVACY MASKS: ACTIVE','ACCESS GATE: SECURED','WAITING FOR PASSWORD...'];
        let lineIndex=0,progress=0,stopped=false,timers=[];
        const later=(fn,delay)=>{const id=owner.setTimeout(fn,delay);timers.push(id)};
        const addLine=()=>{if(stopped||lineIndex>=lines.length)return;const row=doc.createElement('div');row.className='retro-line';row.innerHTML='<span style="opacity:.5">[OK]</span> '+lines[lineIndex++];log.appendChild(row);while(log.children.length>7)log.firstElementChild.remove();later(addLine,260+Math.random()*430)};
        const tick=()=>{if(stopped)return;if(progress<100){progress=Math.min(100,progress+Math.random()*3.6);bar.style.width=progress+'%';percent.textContent=Math.floor(progress)+'%';later(tick,55+Math.random()*95)}else{status.textContent='SYSTEM READY · ENTER ACCESS PASSWORD';screen.classList.add('boot-complete')}};
        addLine();tick();
        owner.__lumooiRetroCleanup=()=>{stopped=true;timers.forEach(id=>owner.clearTimeout(id));delete owner.__lumooiRetroCleanup};
        })();
        </script>
        """,
        height=0,
        scrolling=False,
    )

    st.markdown(
        """
        <div class="portfolio-gate-card">
          <div class="gate-kicker">LUMOOI DEMO</div>
          <h1>lumooi Demo</h1>
          <p>
            这是 lumooi 的交互式产品演示。为了避免在招聘沟通范围之外呈现过多个人信息，
            Demo 中的部分内容已进行脱敏、虚拟化或打码处理，不影响产品功能与设计能力的展示。
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("portfolio_access_form", clear_on_submit=True):
        entered_password = st.text_input("访问密码", type="password", placeholder="请输入开发者提供的临时密码")
        submitted = st.form_submit_button("进入 Demo", type="primary", use_container_width=True)
    if submitted:
        if hmac.compare_digest(entered_password, configured_password):
            st.session_state[PORTFOLIO_AUTH_SESSION_KEY] = True
            _install_demo_session_cookie(expected_access_token)
            st.rerun()
        st.error("密码不正确，请向开发者确认临时密码。")
    st.stop()


# Keep the product landing page public. Entering the interactive Demo from its
# CTA runs the password gate once; all protected routes then reuse the same
# session_state authentication flag.
requested_entry_page = st.query_params.get("page", "产品首页")
if isinstance(requested_entry_page, list):
    requested_entry_page = requested_entry_page[0] if requested_entry_page else "产品首页"
if requested_entry_page != "产品首页":
    require_portfolio_password()

if "showcase_session_id" not in st.session_state:
    st.session_state["showcase_session_id"] = uuid.uuid4().hex
configure_session_database(st.session_state["showcase_session_id"])


# =========================================================
# 黑白稳定版样式
# =========================================================
st.markdown(
    """
    <style>
        :root {
            color-scheme: light only;
            --black: #171717;
            --dark-gray: #3f3f3f;
            --mid-gray: #737373;
            --line: #d5d5d5;
            --line-soft: #e7e7e7;
            --page-background: #fef5f5;
            --page-panel-background: #fffafa;
            --page-panel-line: #f1e7e7;
            --surface: #ffffff;
            --surface-soft: #f4f4f4;
            --surface-muted: #eeeeee;
        }

        html,
        body,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"],
        .stApp {
            color-scheme: light only !important;
            background: var(--page-background) !important;
            color: var(--black) !important;
        }

        /* The product has no dark variant. Keep native browser widgets light
           even when the browser/OS preference is dark or automatic. */
        input,
        textarea,
        select,
        button,
        [data-baseweb="input"],
        [data-baseweb="select"],
        [data-baseweb="radio"] {
            color-scheme: light only !important;
            forced-color-adjust: none !important;
        }

        header[data-testid="stHeader"] {
            background: rgba(255, 250, 250, 0.96) !important;
        }

        /* 主内容：保留顶部安全区域，标题不再被裁切 */
        .block-container {
            width: 96% !important;
            max-width: 1680px !important;
            padding-top: 1.2rem !important;
            padding-bottom: 3rem !important;
            padding-left: 0.35rem !important;
            padding-right: 0.35rem !important;
        }

        /* 使用 Streamlit 原生标题，避免自定义文字容器裁切字形 */
        div[data-testid="stHeadingWithActionElements"] h1 {
            color: var(--black) !important;
            font-size: clamp(2.15rem, 3vw, 2.8rem) !important;
            line-height: 1.35 !important;
            font-weight: 800 !important;
            letter-spacing: -0.035em !important;
            margin: 0 !important;
            padding: 0.35rem 0 0.15rem !important;
            overflow: visible !important;
        }

        div[data-testid="stHeadingWithActionElements"] {
            min-height: 4.35rem !important;
            overflow: visible !important;
        }

        .brand-meta {
            padding: 0 0 1.45rem;
        }

        .brand-subtitle {
            color: var(--dark-gray);
            font-size: 0.98rem;
            line-height: 1.6;
            margin: 0;
        }

        .brand-signature {
            color: var(--mid-gray);
            font-size: 0.78rem;
            line-height: 1.5;
            font-weight: 650;
            margin-top: 0.35rem;
        }

        h2,
        h3,
        p,
        label,
        span {
            color: var(--black);
        }

        /* =================================================
           左侧导航：更窄、纯黑白、无圆点
        ================================================= */
        section[data-testid="stSidebar"] {
            width: 220px !important;
            min-width: 220px !important;
            max-width: 220px !important;
            background: #f7f7f7 !important;
            border-right: 1px solid var(--line) !important;
        }

        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            width: 220px !important;
            min-width: 220px !important;
            max-width: 220px !important;
        }

        section[data-testid="stSidebar"] > div {
            padding-top: 0.8rem !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
            color: var(--dark-gray) !important;
            font-size: 0.78rem !important;
            font-weight: 700 !important;
            margin-bottom: 0.45rem !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] {
            gap: 0.16rem !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label {
            width: calc(100% - 0.5rem) !important;
            min-height: 39px !important;
            padding: 0.48rem 0.68rem !important;
            margin: 0 0.25rem !important;
            border-radius: 9px !important;
            border-left: 3px solid transparent !important;
            background: transparent !important;
            transition: background 0.15s ease !important;
        }

        /* 删除 Streamlit 单选圆点，避免残留绿色 */
        section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
        section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
            display: none !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background: #ececec !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background: #dedede !important;
            border-left-color: var(--black) !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label p {
            color: var(--black) !important;
            font-size: 0.94rem !important;
            line-height: 1.35 !important;
            font-weight: 680 !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {
            font-weight: 800 !important;
        }

        /* =================================================
           今日概览与通用卡片
        ================================================= */
        div[data-testid="stMetric"] {
            background: #fafafa !important;
            border: 1px solid var(--line) !important;
            border-radius: 12px !important;
            padding: 0.8rem 1rem !important;
            box-shadow: none !important;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: var(--surface) !important;
            border: 1px solid var(--line) !important;
            border-radius: 14px !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.035) !important;
        }

        .job-company {
            color: #666666;
            font-size: 0.78rem;
            font-weight: 700;
            margin-bottom: 0.15rem;
        }

        .job-title {
            color: var(--black);
            font-size: 1rem;
            line-height: 1.45;
            font-weight: 800;
            min-height: 2.9rem;
            margin-bottom: 0.55rem;
        }

        .job-meta {
            color: #555555;
            font-size: 0.78rem;
            line-height: 1.5;
            margin-top: 0.4rem;
        }

        .job-action-label {
            color: #666666;
            font-size: 0.72rem;
            font-weight: 700;
            margin-top: 0.75rem;
            margin-bottom: 0.18rem;
        }

        .job-action-text {
            color: #222222;
            font-size: 0.86rem;
            line-height: 1.5;
            min-height: 2.6rem;
        }

        .badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.22rem 0.52rem;
            margin-right: 0.3rem;
            margin-bottom: 0.18rem;
            font-size: 0.68rem;
            line-height: 1.2;
            font-weight: 750;
            border: 1px solid #bdbdbd;
            background: #f2f2f2;
            color: #222222;
        }

        .priority-high {
            background: #222222;
            color: #ffffff;
            border-color: #222222;
        }

        .priority-medium {
            background: #e4e4e4;
            color: var(--black);
        }

        .priority-low {
            background: #ffffff;
            color: #666666;
        }

        .tracker-summary {
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 1rem 1.1rem;
            margin: 0.55rem 0 0.9rem;
            background: #fafafa;
        }

        /* =================================================
           按钮：主要黑底白字；次要白底黑字；禁用浅灰
        ================================================= */
        .stButton button,
        .stLinkButton a,
        div[data-testid="stPopover"] button,
        button[data-testid="stBaseButton-secondary"] {
            background: #ffffff !important;
            color: var(--black) !important;
            border: 1px solid var(--black) !important;
            box-shadow: none !important;
        }

        .stButton button:hover:not(:disabled),
        .stLinkButton a:hover,
        div[data-testid="stPopover"] button:hover {
            background: #eeeeee !important;
            color: var(--black) !important;
            border-color: var(--black) !important;
        }

        .stButton button[kind="primary"],
        .stLinkButton a[kind="primary"],
        button[data-testid="stBaseButton-primary"] {
            background: var(--black) !important;
            border-color: var(--black) !important;
            color: #ffffff !important;
        }

        .stButton button:disabled,
        button[data-testid="stBaseButton-secondary"]:disabled {
            background: #eeeeee !important;
            color: #777777 !important;
            border-color: #cfcfcf !important;
            opacity: 1 !important;
        }

        /* 查看详情弹层保持黑白 */
        div[data-baseweb="popover"],
        div[data-baseweb="popover"] > div {
            background: #ffffff !important;
            color: var(--black) !important;
            border-color: var(--line) !important;
        }

        /* 表单输入框移除主题中的米色和绿色 */
        input,
        textarea,
        div[data-baseweb="input"] > div,
        div[data-baseweb="select"] > div,
        button[role="combobox"] {
            background: #ffffff !important;
            color: var(--black) !important;
            border-color: #c9c9c9 !important;
            box-shadow: none !important;
        }

        input:focus,
        textarea:focus,
        div[data-baseweb="input"] > div:focus-within,
        div[data-baseweb="select"] > div:focus-within {
            border-color: var(--black) !important;
            box-shadow: 0 0 0 1px var(--black) !important;
        }

        /* =================================================
           职业资产库：仅保留单层边框
        ================================================= */
        .asset-field {
            padding: 0.2rem 0 0.85rem;
            margin-bottom: 0.8rem;
            border-bottom: 1px solid var(--line-soft);
        }

        .asset-field-label {
            color: #555555;
            font-size: 0.78rem;
            line-height: 1.35;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }

        .asset-field-value {
            color: var(--black);
            font-size: 0.94rem;
            line-height: 1.55;
            font-weight: 500;
        }

        .asset-status {
            display: inline-flex;
            align-items: center;
            min-height: 34px;
            padding: 0.38rem 0.75rem;
            border: 1px solid #c8c8c8;
            border-radius: 999px;
            background: #f2f2f2;
            color: var(--black);
            font-size: 0.84rem;
            line-height: 1.3;
            font-weight: 650;
        }

        .asset-skills-box {
            margin-top: 0.2rem;
            margin-bottom: 0.9rem;
            padding: 0.85rem 1rem;
            border: 1px solid #dddddd;
            border-radius: 12px;
            background: #fafafa;
        }

        .asset-skills-title {
            color: #555555;
            font-size: 0.78rem;
            line-height: 1.35;
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        .asset-skills-text {
            color: #222222;
            font-size: 0.88rem;
            line-height: 1.7;
            font-weight: 400;
        }

        div[data-testid="stExpander"] {
            border: 1px solid var(--line) !important;
            border-radius: 12px !important;
            background: #ffffff !important;
            box-shadow: none !important;
            overflow: hidden !important;
        }

        div[data-testid="stExpander"] details {
            border: 0 !important;
            border-radius: 0 !important;
            background: transparent !important;
            box-shadow: none !important;
        }

        div[data-testid="stExpander"] summary {
            border: 0 !important;
            background: #ffffff !important;
        }

        div[data-testid="stExpander"] details[open] summary {
            border-bottom: 1px solid var(--line-soft) !important;
        }

        div[data-testid="stExpander"] details summary p {
            font-size: 0.88rem !important;
            font-weight: 650 !important;
        }

        .asset-description {
            color: #222222;
            font-size: 0.86rem;
            line-height: 1.85;
            font-weight: 400;
            padding: 0.35rem 0.25rem 0.45rem;
        }

        .experience-summary {
            padding: 1rem 1.1rem;
            margin: 0.35rem 0 1rem;
            border: 1px solid var(--line);
            border-radius: 12px;
            background: #fafafa;
        }

        .experience-summary-label {
            color: #666666;
            font-size: 0.74rem;
            font-weight: 750;
            margin-bottom: 0.35rem;
        }

        .experience-summary-text {
            color: #1f1f1f;
            font-size: 0.92rem;
            line-height: 1.75;
        }

        .asset-card {
            padding: 0.95rem 1rem;
            margin: 0.7rem 0;
            border: 1px solid var(--line-soft);
            border-radius: 12px;
            background: #ffffff;
        }

        .asset-card-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 0.8rem;
            margin-bottom: 0.65rem;
        }

        .asset-card-code {
            color: #666666;
            font-size: 0.72rem;
            font-weight: 750;
            letter-spacing: 0.04em;
            margin-bottom: 0.15rem;
        }

        .asset-card-title {
            color: var(--black);
            font-size: 1rem;
            line-height: 1.45;
            font-weight: 800;
        }

        .asset-card-meta {
            color: #666666;
            font-size: 0.76rem;
            line-height: 1.55;
            margin-bottom: 0.7rem;
        }

        .asset-section {
            margin-top: 0.7rem;
        }

        .asset-section-label {
            color: #666666;
            font-size: 0.74rem;
            font-weight: 750;
            margin-bottom: 0.25rem;
        }

        .asset-section-text {
            color: #222222;
            font-size: 0.86rem;
            line-height: 1.75;
        }

        .asset-flag {
            display: inline-block;
            border: 1px solid #bdbdbd;
            border-radius: 999px;
            background: #f5f5f5;
            color: #222222;
            padding: 0.2rem 0.5rem;
            font-size: 0.67rem;
            font-weight: 750;
            margin-left: 0.25rem;
            white-space: nowrap;
        }

        .asset-flag-internal {
            background: #222222;
            color: #ffffff;
            border-color: #222222;
        }

        .rule-box {
            border: 1px solid var(--line);
            border-radius: 12px;
            background: #fafafa;
            padding: 0.85rem 1rem;
            margin-top: 0.65rem;
        }

        .rule-item {
            color: #333333;
            font-size: 0.82rem;
            line-height: 1.65;
            padding: 0.22rem 0;
        }

        /* 简历定制、面试准备：单层浅灰提示卡，无边框 */
        .placeholder-card {
            background: var(--surface-soft);
            border: 0;
            border-radius: 14px;
            color: var(--black);
            font-size: 0.95rem;
            line-height: 1.65;
            padding: 1.05rem 1.2rem;
            margin-top: 0.4rem;
        }

        /* 其他系统提示也保持中性黑白 */
        div[data-testid="stAlert"] {
            background: #f4f4f4 !important;
            color: var(--black) !important;
            border: 1px solid var(--line) !important;
            box-shadow: none !important;
        }

        @media (max-width: 900px) {
            .block-container {
                width: 98% !important;
                padding-top: 4.25rem !important;
                padding-left: 0.8rem !important;
                padding-right: 0.8rem !important;
            }

            div[data-testid="stHeadingWithActionElements"] h1 {
                font-size: 2.15rem !important;
            }

            .job-title {
                min-height: auto;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 工具函数
# =========================================================
def safe_text(value, default="未设置"):
    if value is None or str(value).strip() == "":
        return html.escape(default)
    return html.escape(str(value).strip())


def format_date(value):
    if not value:
        return "未设置"

    cleaned = str(value).strip().replace("/", "-")
    try:
        return datetime.strptime(cleaned, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return cleaned


def get_deadline_display(value):
    formatted = format_date(value)

    if formatted == "未设置":
        return formatted, "待补充截止日期"

    try:
        deadline = datetime.strptime(formatted, "%Y-%m-%d").date()
    except ValueError:
        return formatted, "日期格式待检查"

    remaining = (deadline - date.today()).days

    if remaining < 0:
        return formatted, f"已截止 {abs(remaining)} 天"
    if remaining == 0:
        return formatted, "今天截止"
    return formatted, f"剩余 {remaining} 天"


def priority_badge(priority):
    css_class = {
        "高": "priority-high",
        "中": "priority-medium",
        "低": "priority-low",
    }.get(priority, "priority-low")

    return (
        f'<span class="badge {css_class}">'
        f'{safe_text(priority, "未设置")}优先级'
        "</span>"
    )


def status_badge(status):
    return f'<span class="badge">{safe_text(status, "未设置")}</span>'


def calculate_funnel_counts(all_jobs):
    counts = {
        "全部岗位": len(all_jobs),
        "准备投递": 0,
        "投递简历": 0,
        "笔试测评": 0,
        "群面": 0,
        "初试": 0,
        "复试": 0,
        "业务面": 0,
        "HR面": 0,
        "谈薪": 0,
        "Offer": 0,
        "已结束": 0,
    }

    legacy_map = {
        "待定制简历": "准备投递",
        "准备材料": "准备投递",
        "待投递": "准备投递",
        "已投递": "投递简历",
        "笔试": "笔试测评",
        "笔试／测评": "笔试测评",
        "一面": "初试",
        "二面": "复试",
        "终面": "HR面",
    }

    for job in all_jobs:
        status = legacy_map.get(job.get("status") or "", job.get("status") or "准备投递")
        if status in {"拒绝", "放弃"}:
            counts["已结束"] += 1
        elif status in counts:
            counts[status] += 1
        else:
            counts["准备投递"] += 1

    return counts


def render_job_card(job):
    formatted_deadline, remaining_text = get_deadline_display(job.get("deadline"))

    with st.container(border=True):
        st.markdown(
            f"""
            <div class="job-company">{safe_text(job.get('company'))}</div>
            <div class="job-title">{safe_text(job.get('position'))}</div>
            {priority_badge(job.get('priority'))}
            {status_badge(job.get('status'))}
            <div class="job-meta">
                截止：{safe_text(formatted_deadline)} · {safe_text(remaining_text)}
            </div>
            <div class="job-action-label">下一步行动</div>
            <div class="job-action-text">
                {safe_text(job.get('next_action'), '暂未设置下一步行动')}
            </div>
            <div class="job-meta">Demo 备注：公司名称与申请进度均为虚拟信息，岗位 JD 仅用于功能展示。</div>
            """,
            unsafe_allow_html=True,
        )

        application_url = (job.get("application_url") or "").strip()
        col1, col2 = st.columns(2, gap="small")

        with col1:
            if application_url:
                st.link_button(
                    "打开官网",
                    application_url,
                    key=f'home_url_{job["id"]}',
                    use_container_width=True,
                )
            else:
                st.button(
                    "暂无链接",
                    key=f'home_no_url_{job["id"]}',
                    disabled=True,
                    use_container_width=True,
                )

        with col2:
            with st.popover("查看详情", use_container_width=True):
                st.write(f'**公司：** {job.get("company") or "未设置"}')
                st.write(f'**岗位：** {job.get("position") or "未设置"}')
                st.write(f'**工作地点：** {job.get("location") or "未设置"}')
                st.write(f'**目标方向：** {job.get("target_direction") or "未设置"}')
                st.write("**完整JD：**")
                st.write(job.get("job_description") or "暂未保存JD。")


def render_job_grid(all_jobs):
    for start in range(0, len(all_jobs), 2):
        columns = st.columns(2, gap="medium")
        for column, job in zip(columns, all_jobs[start : start + 2]):
            with column:
                render_job_card(job)



def render_asset_section(label, value):
    if value is None or str(value).strip() == "":
        return ""

    safe_value = safe_text(value).replace("\n", "<br>")

    return f'''
        <div class="asset-section">
            <div class="asset-section-label">{safe_text(label)}</div>
            <div class="asset-section-text">{safe_value}</div>
        </div>
    '''


def get_asset_usage_label(asset):
    include_resume = bool(asset.get("include_in_resume"))
    include_interview = bool(asset.get("include_in_interview"))

    if include_resume and include_interview:
        return "可用于简历和面试", ""
    if include_interview:
        return "谨慎使用", ""
    return "仅内部保存", "asset-flag-internal"


def render_experience_asset(asset):
    usage_label, usage_class = get_asset_usage_label(asset)

    meta_parts = [
        asset.get("category"),
        asset.get("participation_level"),
        asset.get("fact_status"),
    ]
    meta_text = " · ".join(
        str(part).strip()
        for part in meta_parts
        if part is not None and str(part).strip()
    )

    body_html = "".join(
        [
            render_asset_section("背景", asset.get("background")),
            render_asset_section("本人行动", asset.get("actions")),
            render_asset_section("流程范围", asset.get("process_scope")),
            render_asset_section("结果", asset.get("results")),
            render_asset_section("数据／指标", asset.get("metrics")),
            render_asset_section("技能", asset.get("skills")),
            render_asset_section("工具", asset.get("tools")),
            render_asset_section("Reflection", asset.get("reflection")),
            render_asset_section("STAR用途", asset.get("star_uses")),
            render_asset_section("贡献边界", asset.get("contribution_boundary")),
            render_asset_section("表述限制", asset.get("expression_limits")),
        ]
    )

    st.html(
        f'''
        <div class="asset-card">
            <div class="asset-card-header">
                <div>
                    <div class="asset-card-code">
                        {safe_text(asset.get("asset_code"))}
                    </div>
                    <div class="asset-card-title">
                        {safe_text(asset.get("title"))}
                    </div>
                </div>
                <span class="asset-flag {usage_class}">
                    {safe_text(usage_label)}
                </span>
            </div>
            <div class="asset-card-meta">
                {safe_text(meta_text, "未设置分类")}
            </div>
            {body_html}
        </div>
        '''
    )



def _compact_name(experience):
    """Return a short display name for an experience cover card."""
    code = (experience.get("experience_code") or "").upper()
    aliases = {
        "AUR": "Aurora",
        "BLU": "BluePeak",
        "NOVA": "NovaHR",
        "LUM": "lumooi",
        "URB": "Urban Futures Lab",
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

    if code == "AUR":
        return "💧"
    if code == "BLU":
        return "↗"
    if code == "LUM":
        return "✦"
    if code == "NOVA":
        return "⚡"
    if code == "URB":
        return "✎"
    return "◌"


def _experience_palette(experience):
    """Stable pastel cover-card palette."""
    code = (experience.get("experience_code") or "").upper()
    palettes = {
        "AUR": {"bg": "#DDEBFF", "accent": "#5D9DFF"},
        "BLU": {"bg": "#E3F5E8", "accent": "#55AA72"},
        "NOVA": {"bg": "#FFE6EE", "accent": "#D87697"},
        "LUM": {"bg": "#EFE4FF", "accent": "#9270D8"},
        "URB": {"bg": "#FFF0C9", "accent": "#B17A18"},
    }
    return palettes.get(code, {"bg": "#F4F0E8", "accent": "#9A8D78"})


def _experience_collection(experience):
    """Map a verified Experience Bank record into one of four UI collections."""
    code = (experience.get("experience_code") or "").strip().upper()
    code_map = {"AUR": "internship", "BLU": "internship", "NOVA": "project", "LUM": "project", "URB": "research"}
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
    # KINETIC V3 verification build: exact selector geometry and free drag.
    """Render the Experience Bank as a true full-screen interactive canvas."""
    payload = _build_experience_bank_payload(experiences)
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    component_html = r"""
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&family=Nunito:wght@500;600;700;800&display=swap');

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
        background: #fbfaf7;
      }

      body {
        color: var(--ink);
        font-family:
          "Arial Rounded MT Bold",
          "Trebuchet MS",
          "PingFang SC",
          "Microsoft YaHei",
          sans-serif;
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
        --collection-card-width: clamp(252px, 18.2vw, 304px);
        position: absolute;
        inset: 0;
        overflow: hidden;
        background: #fbfaf7;
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
        top: clamp(132px, 18vh, 158px);
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
        justify-content: center;
        gap: clamp(22px, 2vw, 32px);
        width: max-content;
        min-width: 100%;
        min-height: 100%;
        padding: 0 clamp(28px, 4vw, 64px);
      }

      .collection-card {
        position: relative;
        width: var(--collection-card-width);
        height: clamp(350px, 47vh, 414px);
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
        opacity: .86;
        transform: translateY(0) scale(.97);
        transition:
          transform .28s cubic-bezier(.2,.78,.2,1),
          opacity .24s ease,
          box-shadow .24s ease;
        -webkit-tap-highlight-color: transparent;
      }

      .collection-card.active {
        opacity: 1;
        transform: translateY(0) scale(1);
        box-shadow: 0 26px 62px rgba(40, 38, 34, .10);
      }

      .collection-card:hover,
      .collection-card:focus-visible {
        z-index: 20;
        opacity: 1;
        outline: none;
        transform: translateY(-12px) scale(1.055);
        box-shadow: 0 34px 76px rgba(40, 38, 34, .15);
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
        background: #ffffff;
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
         Screen 1 — KINETIC selector, copied at the original scale
         Collection overview and story/detail screens remain unchanged.
      ===================================================== */

      .selector-screen {
        position: absolute;
        inset: 0;
        overflow: hidden;
        background: #ffffff;
        user-select: none;
        -webkit-user-select: none;
      }

      .selector-screen::before {
        content: none;
      }

      .selector-brand {
        display: none !important;
      }

      /*
        The original Kinetic onboarding stack is 487px tall:
        147px heading + 60px spacing + 280px circle.
        These positions reproduce that centered stack at a 720px viewport.
      */
      .selector-heading {
        position: absolute;
        top: calc(50% - 244px);
        left: 50%;
        z-index: 60;
        width: 620px;
        max-width: calc(100% - 48px);
        transform: translateX(-50%);
        text-align: center;
        pointer-events: none;
      }

      .selector-title {
        margin: 0 0 16px;
        color: #111111;
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          cursive;
        font-size: 56px;
        line-height: 1;
        font-weight: 700;
        letter-spacing: 0;
      }

      .selector-subtitle {
        margin: 0;
        color: #888888;
        font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 16px;
        line-height: 1.5;
        font-weight: 400;
        letter-spacing: 0;
      }

      .selector-stage {
        position: absolute;
        inset: 0;
        z-index: 2;
        overflow: hidden;
      }

      .drop-zone {
        position: absolute;
        left: 50%;
        top: calc(50% + 104px);
        z-index: 10;
        width: 280px;
        height: 280px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0;
        transform: translate(-50%, -50%);
        border: 0;
        border-radius: 50%;
        background: transparent;
        box-shadow: none;
        transition: all .4s cubic-bezier(.23, 1, .32, 1);
        pointer-events: none;
      }

      .drop-zone::before {
        content: none;
      }

      .drop-zone.active {
        border-color: #111111;
        background: #f0f0f0;
        transform: translate(-50%, -50%) scale(1.05);
        box-shadow: none;
      }

      .drop-zone.accepted {
        border-color: #111111;
        background: #f0f0f0;
        transform: translate(-50%, -50%) scale(1.05);
      }

      .drop-copy {
        display: none;
        position: relative;
        z-index: 2;
        color: #cccccc;
        font-family:
          "Gaegu",
          "Chalkboard SE",
          "Comic Sans MS",
          cursive;
        font-size: 24px;
        line-height: 1.25;
        font-weight: 400;
        letter-spacing: 0;
        text-align: center;
        pointer-events: none;
        transition: color .2s ease;
      }

      .drop-zone.active .drop-copy,
      .drop-zone.accepted .drop-copy {
        color: #777777;
        transform: none;
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
      }

      .experience-link-dot {
        fill: #ffffff;
        stroke: rgba(88, 74, 111, .44);
        stroke-width: 2;
      }

      /*
        Exact reference card geometry:
        200 × 260, 32px radius, 32px/24px padding.
      */
      .cover {
        position: absolute;
        width: 200px;
        height: 260px;
        padding: 32px 24px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        overflow: hidden;
        border: 0;
        border-radius: 32px;
        color: #111111;
        text-align: left;
        cursor: grab;
        user-select: none;
        touch-action: none;
        box-shadow: rgba(0, 0, 0, .05) 0 20px 50px;
        transform: rotate(var(--rotate));
        transform-origin: center;
        transition: transform .2s ease-out, box-shadow .2s ease-out;
        will-change: left, top, transform;
        -webkit-tap-highlight-color: transparent;
      }

      .cover.linked-cover {
        width: 200px;
        height: 260px;
        padding: 32px 24px;
        border-radius: 32px;
      }

      .cover::before {
        content: none;
      }

      .cover:hover,
      .cover:focus-visible {
        z-index: 90 !important;
        outline: none;
        transform: rotate(var(--rotate)) scale(1.025);
        box-shadow: rgba(0, 0, 0, .075) 0 25px 56px;
      }

      .cover:active,
      .cover.dragging {
        z-index: 1000 !important;
        cursor: grabbing;
        transition: none;
        transform: rotate(0deg) scale(1.05);
        box-shadow: rgba(0, 0, 0, .10) 0 30px 60px;
      }

      .cover.drop-ready {
        box-shadow: rgba(0, 0, 0, .10) 0 30px 60px;
      }

      .cover.dropping {
        z-index: 1300 !important;
        opacity: 0;
        filter: blur(3px);
        transform: rotate(0deg) scale(.26);
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

      .cover-kicker {
        position: relative;
        z-index: 2;
        max-width: 100%;
        overflow: hidden;
        color: rgba(0,0,0,.40);
        font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 10px;
        line-height: 1.2;
        font-weight: 600;
        letter-spacing: .1em;
        text-overflow: ellipsis;
        text-transform: uppercase;
        white-space: nowrap;
      }

      .cover-bottom {
        position: relative;
        z-index: 2;
      }

      .cover-logo {
        display: block;
        margin: 0 0 12px;
        color: #111111;
        font-size: 48px;
        line-height: 1;
        filter: none;
      }

      .cover-name {
        margin: 0;
        color: #111111;
        font-family: "Inter", "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: 24px;
        line-height: 1.08;
        font-weight: 600;
        letter-spacing: -.5px;
        overflow-wrap: anywhere;
      }

      /* The original card has no extra role/date rows. */
      .cover-role,
      .cover-date {
        display: none !important;
      }

      .selector-hint {
        position: absolute;
        left: 50%;
        bottom: 40px;
        z-index: 28;
        transform: translateX(-50%);
        color: #aaaaaa;
        font-family: "Inter", "PingFang SC", sans-serif;
        font-size: 11px;
        line-height: 1.5;
        letter-spacing: 0;
        white-space: nowrap;
        pointer-events: none;
      }

      @media (max-width: 900px) {
        .selector-heading {
          top: calc(50% - 234px);
        }

        .selector-title {
          font-size: 50px;
        }

        .drop-zone {
          top: calc(50% + 96px);
        }
      }

      @media (max-width: 680px) {
        .selector-heading {
          top: 72px;
          width: calc(100% - 36px);
        }

        .selector-title {
          font-size: 42px;
        }

        .selector-subtitle {
          font-size: 14px;
        }

        .drop-zone {
          top: 56%;
          width: 240px;
          height: 240px;
        }

        .selector-hint {
          bottom: 16px;
          font-size: 9px;
        }
      }

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
        background: rgba(255,252,247,.32);
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
        background: linear-gradient(to bottom, rgba(255,252,247,.88), rgba(255,252,247,.10));
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
        width: min(500px, 38vw);
        transform: translate(-50%, -50%);
        text-align: center;
        pointer-events: none;
      }

      .story-center .bottom-nav { pointer-events: auto; }

      .story-center .cute-title {
        font-size: clamp(42px, 4.15vw, 64px);
        line-height: .82;
        letter-spacing: .055em;
        text-shadow: 0 3px 0 rgba(255,255,255,.76);
        animation: kinetic-hero-in .72s cubic-bezier(.23,1,.32,1) both;
      }

      .center-doodles {
        position: relative;
        width: 100%;
        height: 29px;
        margin-top: 12px;
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
        margin-top: 2px;
        color: #867f78;
        font-family: "Comic Sans MS", "PingFang SC", cursive;
        font-size: 11px;
        letter-spacing: .04em;
      }

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
        padding: 11px 12px 10px;
        border: 1px solid rgba(255,255,255,.58);
        border-radius: var(--card-radius);
        background:
          linear-gradient(145deg, rgba(255,255,255,.34), transparent 48%),
          var(--asset-bg, rgba(255,255,255,.72));
        color: var(--ink);
        text-align: left;
        cursor: pointer;
        opacity: var(--base-opacity, 1);
        box-shadow:
          0 22px 50px rgba(70,54,40,.11),
          inset 0 1px 0 rgba(255,255,255,.62);
        transform:
          translate3d(
            calc(-50% + var(--mx, 0px)),
            calc(-50% + var(--my, 0px)),
            0
          )
          rotate(calc(var(--angle) + var(--mr, 0deg)))
          scale(var(--scale, 1));
        transform-origin: center;
        backface-visibility: hidden;
        -webkit-backface-visibility: hidden;
        will-change: transform, opacity;
        contain: layout style;
        transition: opacity .22s ease, box-shadow .28s cubic-bezier(.23,1,.32,1), filter .22s ease;
        z-index: var(--z, 2);
      }

      .asset-card.featured {
        --base-opacity: 1;
        --base-blur: 0px;
        --z: 12;
      }

      .asset-card:hover,
      .asset-card:focus-visible,
      .asset-card.pointer-near {
        --scale: 1.055;
        opacity: 1;
        filter: saturate(1.06);
        box-shadow:
          0 30px 58px rgba(70,54,40,.16),
          inset 0 1px 0 rgba(255,255,255,.68);
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
        min-height: 22px;
        padding: 4px 8px;
        border-radius: 999px;
        background: rgba(255,255,255,.58);
        color: var(--asset-accent);
        font-size: 8.5px;
        line-height: 1.2;
        font-weight: 800;
        letter-spacing: .04em;
      }

      .asset-code {
        color: var(--asset-accent);
        font-size: 9px;
        font-weight: 850;
        opacity: .72;
      }

      .asset-title {
        margin-top: 8px;
        padding-right: 10px;
        color: #47433f;
        font-family:
          "STKaiti",
          "KaiTi",
          "Kaiti SC",
          "Songti SC",
          "PingFang SC",
          serif;
        font-size: var(--title-size, 15px);
        line-height: 1.48;
        font-weight: 600;
        letter-spacing: .01em;
        overflow-wrap: anywhere;
      }

      .asset-detail {
        margin-top: 5px;
        color: rgba(68,63,58,.68);
        font-family: "PingFang SC", "Microsoft YaHei", sans-serif;
        font-size: var(--detail-size, 9px);
        line-height: 1.55;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }

      .asset-footer {
        position: absolute;
        left: 12px;
        right: 12px;
        bottom: 7px;
        z-index: 2;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .asset-status {
        color: #8a837d;
        font-size: 8px;
        font-weight: 700;
      }

      .asset-icon {
        color: var(--asset-accent);
        font-size: 17px;
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
        font-family: "Comic Sans MS", "PingFang SC", cursive;
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
        width: min(390px, 42vw);
        min-height: 52px;
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 10px 20px;
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

      .overview-search-trigger svg { width: 22px; height: 22px; flex: 0 0 auto; }
      .overview-search-trigger span {
        overflow: hidden;
        font-size: clamp(12px, 1.15vw, 16px);
        font-weight: 600;
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
        .selector-heading { top: calc(50% - 244px); }
        .drop-zone {
          top: calc(50% + 104px);
          width: 280px;
          height: 280px;
        }
        .cover {
          width: 200px;
          height: 260px;
          max-height: none;
        }
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
        .story-center { width: 42vw; }
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
          width: 52vw;
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
              <h2 class="cute-title">which one<br>do you<br>wanna choose?</h2>
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
            <span>Search this experience's assets...</span>
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

      const COLLECTIONS = [
        {
          id: "internship",
          label: "Internship",
          title: "实习经历",
          kicker: "WORK EXPERIENCE",
          description: "实习 · 招聘交付 · HRBP · HR服务",
          bg: "#DDF3E7",
          accent: "#12B77A",
          chart: "M4 72 C48 48, 96 56, 142 39 S236 17, 306 22"
        },
        {
          id: "project",
          label: "Project",
          title: "项目经历",
          kicker: "PRODUCT & CONSULTING",
          description: "项目 · 产品设计 · 咨询项目 · 创业实践",
          bg: "#FFE6D2",
          accent: "#FF8F65",
          chart: "M4 76 C58 72, 94 45, 142 42 S220 12, 306 17"
        },
        {
          id: "competition",
          label: "Competition",
          title: "竞赛经历",
          kicker: "COMPETITIONS",
          description: "竞赛 · 商业挑战 · 创新项目",
          bg: "#EFE4FF",
          accent: "#8254F5",
          chart: "M4 75 C62 74, 104 68, 143 54 S220 23, 306 18"
        },
        {
          id: "research",
          label: "Research",
          title: "科研经历",
          kicker: "RESEARCH",
          description: "科研 · 研究助理 · 学术写作",
          bg: "#DCEBFF",
          accent: "#4E83E7",
          chart: "M4 72 C54 58, 98 64, 146 44 S231 18, 306 26"
        }
      ];

      const state = {
        screen: "collection",
        collectionIndex: 0,
        collectionId: "internship",
        experienceIndex: Math.max(0, DATA.findIndex(item => item.experience_code === "AUR")),
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

      const coverRotations = ["-4deg", "2deg", "-2deg", "3deg", "-3deg", "2deg"];

      const overviewLayouts = [
        { x: 20, y: 73, angle: "-2deg", w: 240, h: 158, radius: 30, featured: true,  opacity: 1,   blur: 0, title: 17, detail: 10 },
        { x: 23, y: 23, angle: "-4deg", w: 220, h: 145, radius: 28, featured: false, opacity: .92, blur: 0, title: 15, detail: 9 },
        { x: 78, y: 22, angle: "3deg",  w: 222, h: 146, radius: 28, featured: false, opacity: .91, blur: 0, title: 15, detail: 9 },
        { x: 81, y: 50, angle: "2deg",  w: 220, h: 145, radius: 28, featured: false, opacity: .90, blur: 0, title: 15, detail: 9 },
        { x: 75, y: 76, angle: "-3deg", w: 218, h: 143, radius: 28, featured: false, opacity: .89, blur: 0, title: 15, detail: 9 },
        { x: 43, y: 83, angle: "2deg",  w: 205, h: 136, radius: 26, featured: false, opacity: .88, blur: 0, title: 14, detail: 9 }
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

      const selectorPointer = {
        clientX: window.innerWidth / 2,
        clientY: window.innerHeight / 2,
        active: false
      };

      let motionCards = [];
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
          asset.ai_usage,
          asset.interview_memory_notes,
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
        if (experienceCode === "AUR") {
          const preferredCodes = ["AUR-01", "AUR-02", "AUR-03"];
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
        selectorCollectionBadge.textContent = `${meta.label.toUpperCase()} COLLECTION · ${items.length} EXPERIENCES · KINETIC V3`;
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
        internship: { AUR: { bottom: "15%", left: "10%", angle: 5 }, BLU: { top: "20%", right: "15%", angle: -4 } },
        project: { LUM: { bottom: "15%", left: "10%", angle: 5 }, NOVA: { top: "20%", right: "15%", angle: 12 } },
        research: { URB: { top: "15%", left: "15%", angle: -8 } }
      };

      const selectorFallbackLayouts = [
        { top: "15%", left: "15%", angle: -8 },
        { bottom: "15%", left: "10%", angle: 5 },
        { top: "20%", right: "15%", angle: 12 },
        { bottom: "10%", right: "12%", angle: -4 },
        { top: "12%", left: "43%", angle: -2 },
        { bottom: "8%", left: "43%", angle: 2 }
      ];

      const selectorKickers = { AUR: "TALENT OPERATIONS", BLU: "PEOPLE EXPERIENCE", NOVA: "HR TECH", LUM: "PRODUCT BUILD", URB: "RESEARCH" };

      let selectorDrag = null;
      let selectorOpening = false;

      function selectorIdentityCode(item) {
        const directCode = String(item.experience_code || "").trim().toUpperCase();
        if (directCode) return directCode;

        const identityText = [
          item.display_name,
          item.organization,
          item.alternate_name,
          item.team
        ].map(cleanText).join(" ").toLowerCase();

        if (/aurora/.test(identityText)) return "AUR";
        if (/bluepeak/.test(identityText)) return "BLU";
        if (/novahr/.test(identityText)) return "NOVA";
        if (/lumooi|career os/.test(identityText)) return "LUM";
        if (/urban futures/.test(identityText)) return "URB";
        return "";
      }

      function selectorLayoutFor(item, index) {
        const code = selectorIdentityCode(item);
        const categoryLayouts = selectorCategoryLayouts[state.collectionId] || {};
        return categoryLayouts[code] || selectorFallbackLayouts[index % selectorFallbackLayouts.length];
      }

      function selectorLayoutStyle(layout) {
        return [
          `top:${layout.top || "auto"}`,
          `right:${layout.right || "auto"}`,
          `bottom:${layout.bottom || "auto"}`,
          `left:${layout.left || "auto"}`
        ].join(";");
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
          card.style.top = card.dataset.homeTop || "auto";
          card.style.right = card.dataset.homeRight || "auto";
          card.style.bottom = card.dataset.homeBottom || "auto";
          card.style.left = card.dataset.homeLeft || "auto";
          card.style.removeProperty("transform");
          card.style.removeProperty("box-shadow");
          card.style.removeProperty("z-index");
        });

        coverMotionCards.forEach(item => {
          item.currentX = 0;
          item.currentY = 0;
          item.currentR = 0;
          item.currentScale = 1;
          item.targetX = 0;
          item.targetY = 0;
          item.targetR = 0;
          item.targetScale = 1;
          item.hovered = false;
        });

        window.requestAnimationFrame(updateExperienceLinks);
        window.setTimeout(updateExperienceLinks, 480);
      }

      function cardInsideDropZone(card) {
        const cardRect = card.getBoundingClientRect();
        const zoneRect = dropZone.getBoundingClientRect();

        return !(
          cardRect.right < zoneRect.left ||
          cardRect.left > zoneRect.right ||
          cardRect.bottom < zoneRect.top ||
          cardRect.top > zoneRect.bottom
        );
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

      function settleCardWhereReleased(card) {
        card.classList.remove("dragging", "drop-ready");
        card.style.setProperty("--rotate", "0deg");
        card.style.transform = "rotate(0deg) scale(1)";
        card.style.boxShadow = "rgba(0, 0, 0, .05) 0 20px 50px";
        card.style.zIndex = "70";
        setDropMessage("Drop your<br>experience here", false);
        window.requestAnimationFrame(updateExperienceLinks);
      }

      function openExperienceFromSelector(index, card) {
        if (selectorOpening) return;
        selectorOpening = true;

        const item = DATA[index];
        const stageRect = selectorStage.getBoundingClientRect();
        const zoneRect = dropZone.getBoundingClientRect();
        const targetX =
          zoneRect.left - stageRect.left + (zoneRect.width - card.offsetWidth) / 2;
        const targetY =
          zoneRect.top - stageRect.top + (zoneRect.height - card.offsetHeight) / 2;

        coverStrip.querySelectorAll(".cover").forEach(other => {
          if (other !== card) other.classList.add("fading-out");
          other.style.pointerEvents = "none";
        });

        card.classList.remove("dragging", "drop-ready");
        card.classList.add("dropping");
        card.style.right = "auto";
        card.style.bottom = "auto";
        card.style.left = `${targetX}px`;
        card.style.top = `${targetY}px`;

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

        selectorDrag = {
          pointerId: event.pointerId,
          card,
          index,
          stageRect,
          startX: event.clientX,
          startY: event.clientY,
          initialLeft: cardRect.left - stageRect.left,
          initialTop: cardRect.top - stageRect.top,
          moved: false,
          inside: false
        };

        try {
          card.setPointerCapture(event.pointerId);
        } catch (_) {}

        /*
          Match the reference: convert any right/bottom anchored card into
          pixel-based left/top coordinates the moment dragging starts.
        */
        card.style.right = "auto";
        card.style.bottom = "auto";
        card.style.left = `${selectorDrag.initialLeft}px`;
        card.style.top = `${selectorDrag.initialTop}px`;
        card.style.zIndex = "1000";
        card.classList.add("dragging");
      }

      function moveSelectorDrag(event) {
        if (!selectorDrag || selectorDrag.pointerId !== event.pointerId) return;
        event.preventDefault();

        const drag = selectorDrag;
        const dx = event.clientX - drag.startX;
        const dy = event.clientY - drag.startY;

        if (Math.hypot(dx, dy) > 5) drag.moved = true;

        drag.card.style.left = `${drag.initialLeft + dx}px`;
        drag.card.style.top = `${drag.initialTop + dy}px`;
        drag.inside = updateDropTarget(drag.card, drag.index);
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
          settleCardWhereReleased(drag.card);
        }
      }

      function relationshipSvgMarkup() {
        return `
          <svg id="experience-links" class="experience-links" aria-hidden="true">
            <defs>
              <marker id="experience-link-arrow" markerWidth="8" markerHeight="8" refX="6.5" refY="4" orient="auto">
                <path d="M 0 0 L 8 4 L 0 8 z" fill="rgba(88, 74, 111, .44)"></path>
              </marker>
            </defs>
            <path id="project-link" class="experience-link-path" marker-end="url(#experience-link-arrow)"></path>
            <circle id="project-link-start" class="experience-link-dot" r="4"></circle>
            <circle id="project-link-end" class="experience-link-dot" r="4"></circle>
          </svg>
        `;
      }

      function updateExperienceLinks() {
        const svg = document.getElementById("experience-links");
        const path = document.getElementById("project-link");
        const startDot = document.getElementById("project-link-start");
        const endDot = document.getElementById("project-link-end");
        const source = coverStrip.querySelector('[data-code="LUM"]');
        const target = coverStrip.querySelector('[data-code="NOVA"]');

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

        coverStrip.innerHTML =
          relationshipSvgMarkup() +
          visibleEntries.map((entry, localIndex) => {
            const item = entry.item;
            const index = entry.index;
            const layout = selectorLayoutFor(item, localIndex);
            const kicker = selectorKickerFor(item);
            const identityCode = selectorIdentityCode(item);
            const linkedClass = ["LUM", "NOVA"].includes(identityCode) ? " linked-cover" : "";

            return `
              <button
                type="button"
                class="cover${linkedClass}"
                data-index="${index}"
                data-code="${escapeHtml(identityCode)}"
                data-home-top="${escapeHtml(layout.top || "auto")}"
                data-home-right="${escapeHtml(layout.right || "auto")}"
                data-home-bottom="${escapeHtml(layout.bottom || "auto")}"
                data-home-left="${escapeHtml(layout.left || "auto")}"
                aria-label="Open ${escapeHtml(item.display_name || "experience")}"
                style="
                  ${selectorLayoutStyle(layout)};
                  --rotate:${layout.angle}deg;
                  background:${item.palette?.bg || "#f3eee6"};
                  z-index:${index + 20};
                "
              >
                <div class="cover-kicker">${escapeHtml(kicker)}</div>
                <div class="cover-bottom">
                  <span class="cover-logo">${escapeHtml(item.virtual_logo || "◌")}</span>
                  <div class="cover-name">${escapeHtml(item.display_name || "Experience")}</div>
                </div>
              </button>
            `;
          }).join("");

        const renderedCovers = Array.from(coverStrip.querySelectorAll(".cover"));

        /*
          The reference has no autonomous floating effect.
          Cards move only when the user physically drags them.
        */
        coverMotionCards = [];

        renderedCovers.forEach(button => {
          const index = Number(button.dataset.index);

          button.addEventListener(
            "pointerdown",
            event => beginSelectorDrag(event, button, index)
          );
          button.addEventListener("pointermove", moveSelectorDrag);
          button.addEventListener("pointerup", endSelectorDrag);

          button.addEventListener("pointercancel", event => {
            if (!selectorDrag || selectorDrag.pointerId !== event.pointerId) return;
            const card = selectorDrag.card;
            selectorDrag = null;
            settleCardWhereReleased(card);
          });

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

          card.addEventListener("mouseenter", () => {
            hoveredAssetIndex = assetIndex;
          });

          card.addEventListener("mouseleave", () => {
            hoveredAssetIndex = null;
          });

          card.addEventListener("click", () => {
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
          const speed = 10 + index * 4;
          item.targetX = globalX * speed;
          item.targetY = globalY * speed * .72;
          item.targetR = globalX * (index % 2 === 0 ? .7 : -.7);
          item.influence = 0;
        });
      }

      selectorStage.addEventListener("pointerenter", event => {
        selectorPointer.active = true;
        selectorPointer.clientX = event.clientX;
        selectorPointer.clientY = event.clientY;
      }, { passive: true });

      selectorStage.addEventListener("pointermove", event => {
        selectorPointer.active = true;
        selectorPointer.clientX = event.clientX;
        selectorPointer.clientY = event.clientY;
      }, { passive: true });

      selectorStage.addEventListener("pointerleave", () => {
        selectorPointer.active = false;
        coverMotionCards.forEach(item => {
          item.targetX = 0;
          item.targetY = 0;
          item.targetR = 0;
          item.targetScale = 1;
          item.hovered = false;
        });
      });

      storyStage.addEventListener("pointerenter", refreshStageMetrics, { passive: true });
      storyStage.addEventListener("pointermove", event => {
        pointer.clientX = event.clientX;
        pointer.clientY = event.clientY;
        pointer.active = true;
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
      });

      window.addEventListener("resize", () => {
        refreshStageMetrics();
        coverGeometryDirty = true;
        updateExperienceLinks();
      }, { passive: true });

      function animateCards(time) {
        const deltaSeconds = Math.min(Math.max((time - lastFrameTime) / 1000, 0), .034);
        lastFrameTime = time;

        const coverMoveAmount = dampAmount(11.5, deltaSeconds);
        const selectorRect = selectorStage.getBoundingClientRect();

        coverMotionCards.forEach(item => {
          const blocked =
            state.screen !== "selector" ||
            selectorOpening ||
            item.card.classList.contains("dragging") ||
            item.card.classList.contains("dropping") ||
            item.card.classList.contains("fading-out");

          if (blocked) {
            item.targetX = 0;
            item.targetY = 0;
            item.targetR = 0;
          } else {
            const idleX = Math.sin(time * .00062 + item.phase) * 1.35;
            const idleY = Math.cos(time * .00054 + item.phase * 1.18) * 1.65;
            const idleR = Math.sin(time * .00043 + item.phase) * .34;
            let pointerX = 0;
            let pointerY = 0;
            let pointerR = 0;

            if (selectorPointer.active && selectorRect.width > 1) {
              const cardRect = item.card.getBoundingClientRect();
              const centerX = cardRect.left + cardRect.width / 2;
              const centerY = cardRect.top + cardRect.height / 2;
              const dx = selectorPointer.clientX - centerX;
              const dy = selectorPointer.clientY - centerY;
              const distance = Math.hypot(dx, dy);
              const influence = clamp(1 - distance / Math.max(420, selectorRect.width * .31), 0, 1);
              pointerX = clamp(dx * .015 * influence, -4.6, 4.6);
              pointerY = clamp(dy * .012 * influence, -3.8, 3.8);
              pointerR = clamp(dx * .0032 * influence, -1.05, 1.05);
            }

            item.targetX = idleX + pointerX;
            item.targetY = idleY + pointerY;
            item.targetR = idleR + pointerR;
          }

          if (item.card.classList.contains("dropping")) item.targetScale = .26;
          else if (item.card.classList.contains("dragging")) item.targetScale = 1.075;
          else if (item.card.classList.contains("drop-ready")) item.targetScale = 1.045;
          else item.targetScale = item.hovered ? 1.055 : 1;

          item.currentX = lerp(item.currentX, item.targetX, coverMoveAmount);
          item.currentY = lerp(item.currentY, item.targetY, coverMoveAmount);
          item.currentR = lerp(item.currentR, item.targetR, coverMoveAmount);
          item.currentScale = lerp(item.currentScale, item.targetScale, coverMoveAmount);

          item.card.style.setProperty("--cover-x", `${item.currentX.toFixed(2)}px`);
          item.card.style.setProperty("--cover-y", `${item.currentY.toFixed(2)}px`);
          item.card.style.setProperty("--cover-r", `${item.currentR.toFixed(2)}deg`);
          item.card.style.setProperty("--cover-scale", item.currentScale.toFixed(4));
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
      switchScreen("collection");

      if (!animationFrameId) {
        animationFrameId = requestAnimationFrame(animateCards);
      }
    </script>
    """

    component_html = component_html.replace("__DATA__", data_json)
    component_html = component_html.replace(
        '<main class="app">',
        r'''
        <div id="asset-runtime-error" style="display:none;position:fixed;inset:0;z-index:999999;padding:24px;background:#fff7f7;color:#7a1d1d;font:14px/1.6 monospace;white-space:pre-wrap;"></div>
        <script>
          window.addEventListener("error", event => {
            const panel = document.getElementById("asset-runtime-error");
            if (!panel) return;
            panel.style.display = "block";
            panel.textContent = `Asset UI error: ${event.message || "unknown error"}`;
          });
          window.addEventListener("unhandledrejection", event => {
            const panel = document.getElementById("asset-runtime-error");
            if (!panel) return;
            panel.style.display = "block";
            panel.textContent = `Asset UI promise error: ${String(event.reason || "unknown error")}`;
          });
        </script>
        <main class="app">''',
        1,
    )

    components.html(
        component_html,
        height=720,
        scrolling=False,
    )



# =========================================================
# lumooi 产品介绍页
# =========================================================
def render_product_landing():
    """渲染面向首次访问者的公开产品介绍页。"""
    st.markdown(
        r"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&family=Manrope:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap');

            :root {
                --landing-ink: #171717;
                --landing-muted: #6f696d;
                --landing-pink: #fcecf2;
                --landing-panel: rgba(255, 250, 251, .72);
                --landing-line: rgba(23, 23, 23, .10);
            }

            html body:has(.cp-landing) section[data-testid="stSidebar"] {
                display: none !important;
            }
            html body:has(.cp-landing) [data-testid="stMain"] {
                width: 100% !important;
                margin-left: 0 !important;
            }
            html body:has(.cp-landing) .block-container {
                width: 100% !important;
                max-width: none !important;
                padding: 12px !important;
            }

            .cp-landing {
                position: relative;
                min-height: 100vh;
                overflow: hidden;
                border: 1px solid var(--landing-line);
                border-radius: 32px;
                background: #fff8fa;
                color: var(--landing-ink);
                font-family: 'Manrope', 'Noto Sans SC', sans-serif;
                isolation: isolate;
            }

            .cp-ferrofluid {
                position: absolute;
                inset: 0;
                z-index: 0;
                display: block;
                width: 100%;
                height: 100%;
                pointer-events: none;
                background: #fceff4;
            }

            .cp-fluid {
                position: absolute;
                inset: -20%;
                z-index: 0;
                background:
                    radial-gradient(circle at 14% 20%, rgba(255,255,255,.98) 0 13%, transparent 32%),
                    radial-gradient(circle at 83% 15%, rgba(237,235,207,.52) 0 10%, transparent 28%),
                    radial-gradient(circle at 70% 72%, rgba(247,211,225,.85) 0 18%, transparent 38%),
                    radial-gradient(circle at 22% 82%, rgba(255,255,255,.95) 0 17%, transparent 36%),
                    linear-gradient(135deg, #fffdfd 0%, #f9e9ef 52%, #fff8f3 100%);
                filter: blur(10px) saturate(1.05);
                animation: cp-fluid-shift 18s ease-in-out infinite alternate;
                transform: scale(1.08);
            }

            .cp-fluid::before,
            .cp-fluid::after {
                content: '';
                position: absolute;
                border-radius: 44% 56% 65% 35% / 42% 38% 62% 58%;
                background: rgba(255,255,255,.66);
                box-shadow: inset 0 0 42px rgba(255,255,255,.92), 0 0 55px rgba(255,255,255,.65);
            }
            .cp-fluid::before {
                width: 42vw;
                height: 34vw;
                left: 13%;
                top: 10%;
                animation: cp-blob 15s ease-in-out infinite alternate;
            }
            .cp-fluid::after {
                width: 34vw;
                height: 42vw;
                right: 8%;
                bottom: 2%;
                animation: cp-blob 19s ease-in-out -6s infinite alternate-reverse;
            }

            .cp-fluid-lobe {
                position: absolute;
                display: block;
                pointer-events: none;
                will-change: translate, transform;
                border-radius: 44% 56% 61% 39% / 48% 43% 57% 52%;
                background:
                    radial-gradient(circle at 32% 28%, rgba(255,255,255,.96) 0 18%, transparent 42%),
                    radial-gradient(circle at 68% 70%, rgba(250,216,230,.72) 0 16%, transparent 55%),
                    linear-gradient(145deg, rgba(255,255,255,.92), rgba(250,216,230,.52));
                box-shadow:
                    inset 16px 18px 32px rgba(255,255,255,.82),
                    inset -18px -20px 38px rgba(250,216,230,.36),
                    0 26px 70px rgba(96,150,185,.10);
                filter: blur(1.5px);
                opacity: .86;
            }
            .cp-fluid-lobe.one {
                width: 39vw;
                height: 31vw;
                min-width: 420px;
                min-height: 330px;
                left: 7%;
                top: 7%;
                animation: cp-lobe-one 16s ease-in-out infinite alternate;
            }
            .cp-fluid-lobe.two {
                width: 33vw;
                height: 38vw;
                min-width: 350px;
                min-height: 410px;
                right: 4%;
                top: 17%;
                opacity: .72;
                animation: cp-lobe-two 20s ease-in-out -5s infinite alternate-reverse;
            }
            .cp-fluid-lobe.three {
                width: 30vw;
                height: 26vw;
                min-width: 330px;
                min-height: 280px;
                left: 34%;
                bottom: -2%;
                opacity: .64;
                animation: cp-lobe-three 18s ease-in-out -8s infinite alternate;
            }
            .cp-fluid-pointer {
                position: absolute;
                z-index: -1;
                left: 50%;
                top: 50%;
                width: min(34vw, 430px);
                aspect-ratio: 1;
                border-radius: 50%;
                pointer-events: none;
                opacity: 0;
                will-change: translate, opacity, transform;
                background: radial-gradient(circle, rgba(250,216,230,.48) 0, rgba(255,255,255,.58) 34%, transparent 70%);
                filter: blur(13px);
                transform: translate(-50%, -50%) scale(.78);
                transition: opacity .45s ease;
            }

            @keyframes cp-fluid-shift {
                from { transform: scale(1.08) translate3d(-1.5%, -1%, 0) rotate(-1deg); }
                to { transform: scale(1.14) translate3d(2%, 1.5%, 0) rotate(2deg); }
            }
            @keyframes cp-blob {
                0% { transform: translate3d(0,0,0) rotate(0deg) scale(1); border-radius: 44% 56% 65% 35% / 42% 38% 62% 58%; }
                100% { transform: translate3d(7%,9%,0) rotate(12deg) scale(1.12); border-radius: 58% 42% 35% 65% / 55% 64% 36% 45%; }
            }
            @keyframes cp-lobe-one {
                from { transform: rotate(-7deg) scale(1); border-radius: 44% 56% 61% 39% / 48% 43% 57% 52%; }
                to { transform: rotate(8deg) scale(1.10); border-radius: 60% 40% 46% 54% / 39% 58% 42% 61%; }
            }
            @keyframes cp-lobe-two {
                from { transform: rotate(5deg) scale(.96); border-radius: 53% 47% 38% 62% / 56% 36% 64% 44%; }
                to { transform: rotate(-11deg) scale(1.08); border-radius: 38% 62% 58% 42% / 44% 63% 37% 56%; }
            }
            @keyframes cp-lobe-three {
                from { transform: rotate(-4deg) scale(.92); }
                to { transform: rotate(13deg) scale(1.13); }
            }

            /* 白色 + 浅粉色丝绸流体背景。保持较慢的向下流动，并由下方脚本
               注入轻微的鼠标位移，效果对应 Ferrofluid 参数。 */
            .cp-fluid {
                inset: 0;
                overflow: hidden;
                background:
                    radial-gradient(ellipse at 18% 4%, rgba(255,255,255,1) 0 22%, transparent 55%),
                    radial-gradient(ellipse at 78% 82%, rgba(244,185,208,.58) 0 12%, transparent 48%),
                    linear-gradient(180deg, #ffffff 0%, #fffdfd 48%, #f4fcfd 100%);
                filter: none;
                transform: none;
                animation: none;
            }
            .cp-fluid::before,
            .cp-fluid::after {
                content: '';
                position: absolute;
                inset: -35% -20%;
                width: auto;
                height: auto;
                border-radius: 42% 58% 48% 52% / 55% 44% 56% 45%;
                pointer-events: none;
                will-change: transform;
            }
            .cp-fluid::before {
                background:
                    repeating-radial-gradient(ellipse at 48% 46%,
                        rgba(255,255,255,.96) 0 4%,
                        rgba(255,255,255,.22) 8%,
                        rgba(244,185,208,.30) 13%,
                        rgba(255,255,255,.78) 19%,
                        transparent 27%);
                box-shadow: none;
                filter: blur(20px) saturate(1.12);
                opacity: .86;
                animation: cp-silk-sheet-a 18s ease-in-out infinite alternate;
            }
            .cp-fluid::after {
                background:
                    repeating-radial-gradient(ellipse at 56% 40%,
                        transparent 0 7%,
                        rgba(255,255,255,.86) 12%,
                        rgba(244,185,208,.24) 17%,
                        rgba(255,255,255,.52) 23%,
                        transparent 31%);
                box-shadow: none;
                filter: blur(28px);
                opacity: .70;
                animation: cp-silk-sheet-b 24s ease-in-out -6s infinite alternate-reverse;
            }
            .cp-fluid-lobe {
                min-width: 0 !important;
                min-height: 0 !important;
                border-radius: 48% 52% 44% 56% / 58% 42% 58% 42%;
                background:
                    radial-gradient(ellipse at 34% 24%, rgba(255,255,255,.98) 0 13%, transparent 38%),
                    linear-gradient(128deg,
                        rgba(255,255,255,.86) 3%,
                        rgba(244,185,208,.16) 31%,
                        rgba(255,255,255,.96) 51%,
                        rgba(244,185,208,.42) 72%,
                        rgba(255,255,255,.56) 100%);
                box-shadow:
                    inset 34px 10px 55px rgba(255,255,255,.90),
                    inset -30px -18px 60px rgba(244,185,208,.30),
                    0 30px 90px rgba(198,105,143,.10);
                filter: blur(9px);
                opacity: .74;
                mix-blend-mode: multiply;
            }
            .cp-fluid-lobe.one {
                width: 78vw;
                height: 34vw;
                left: -17%;
                top: -13%;
                animation: cp-silk-ribbon-one 20s ease-in-out infinite alternate;
            }
            .cp-fluid-lobe.two {
                width: 64vw;
                height: 41vw;
                right: -18%;
                top: 13%;
                opacity: .58;
                animation: cp-silk-ribbon-two 24s ease-in-out -5s infinite alternate-reverse;
            }
            .cp-fluid-lobe.three {
                width: 69vw;
                height: 26vw;
                left: 15%;
                bottom: -16%;
                opacity: .50;
                animation: cp-silk-ribbon-three 28s ease-in-out -9s infinite alternate;
            }
            .cp-fluid-pointer {
                z-index: 1;
                width: min(35vw, 440px);
                opacity: 0;
                background: radial-gradient(circle,
                    rgba(244,185,208,.36) 0,
                    rgba(255,255,255,.44) 35%,
                    transparent 72%);
                filter: blur(18px);
                mix-blend-mode: normal;
            }

            @keyframes cp-silk-sheet-a {
                from { transform: translate3d(-4%, -10%, 0) rotate(-8deg) scale(1.04, .94); }
                to { transform: translate3d(5%, 14%, 0) rotate(7deg) scale(.94, 1.08); }
            }
            @keyframes cp-silk-sheet-b {
                from { transform: translate3d(7%, -14%, 0) rotate(11deg) scale(.96, 1.05); }
                to { transform: translate3d(-5%, 17%, 0) rotate(-6deg) scale(1.08, .94); }
            }
            @keyframes cp-silk-ribbon-one {
                from { transform: translate3d(-3%, -8%, 0) rotate(-11deg) skewX(-5deg) scale(1); }
                to { transform: translate3d(8%, 22%, 0) rotate(5deg) skewX(7deg) scale(1.10, .92); }
            }
            @keyframes cp-silk-ribbon-two {
                from { transform: translate3d(4%, -11%, 0) rotate(14deg) skewY(4deg) scale(.94); }
                to { transform: translate3d(-8%, 18%, 0) rotate(-7deg) skewY(-6deg) scale(1.09); }
            }
            @keyframes cp-silk-ribbon-three {
                from { transform: translate3d(-6%, -6%, 0) rotate(-4deg) scale(1.05, .90); }
                to { transform: translate3d(7%, 24%, 0) rotate(10deg) scale(.94, 1.10); }
            }

            .cp-landing-nav {
                position: relative;
                z-index: 2;
                width: min(1080px, calc(100% - 48px));
                min-height: 72px;
                margin: 28px auto 0;
                padding: 0 18px 0 24px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 24px;
                border: 1px solid var(--landing-line);
                border-radius: 24px;
                background: rgba(255,255,255,.58);
                box-shadow: 0 18px 48px rgba(76,50,59,.07);
                backdrop-filter: blur(20px);
            }
            .cp-landing-brand {
                color: var(--landing-ink) !important;
                font-family: 'Gaegu', 'Comic Sans MS', 'Chalkboard SE', cursive;
                font-size: 34px;
                font-weight: 700;
                line-height: 1;
                letter-spacing: .035em;
                text-decoration: none;
            }
            .cp-landing-links { display: flex; align-items: center; gap: 30px; }
            .cp-landing-links a {
                color: #6e686c !important;
                font-size: 14px;
                font-weight: 700;
                text-decoration: none;
            }
            .cp-landing-links .cp-nav-demo {
                padding: 14px 20px;
                border-radius: 16px;
                background: var(--landing-ink);
                color: #fff !important;
            }

            .cp-hero {
                position: relative;
                z-index: 1;
                min-height: 690px;
                padding: 116px 24px 76px;
                display: flex;
                flex-direction: column;
                align-items: center;
                text-align: center;
            }
            .cp-eyebrow {
                display: inline-flex;
                align-items: center;
                gap: 9px;
                padding: 9px 14px;
                border: 1px solid var(--landing-line);
                border-radius: 999px;
                background: rgba(255,255,255,.62);
                color: #575155;
                font-size: 11px;
                font-weight: 800;
                letter-spacing: .14em;
            }
            .cp-eyebrow::before {
                content: '';
                width: 7px;
                height: 7px;
                border-radius: 50%;
                background: #171717;
            }
            .cp-hero h1 {
                max-width: 1040px;
                margin: 34px auto 0;
                color: var(--landing-ink);
                font-family: 'Gaegu', 'Comic Sans MS', 'Chalkboard SE', cursive;
                font-size: clamp(62px, 7.2vw, 104px);
                line-height: .94;
                letter-spacing: .035em;
                font-weight: 700;
                text-wrap: balance;
                text-rendering: optimizeLegibility;
            }
            .cp-hero h1 span {
                display: block;
                white-space: nowrap;
            }
            .cp-hero-copy {
                max-width: none;
                margin: 26px auto 0;
                color: var(--landing-muted);
                font-family: 'Noto Sans SC', sans-serif;
                font-size: clamp(13px, 1.15vw, 16px);
                line-height: 1.6;
                font-weight: 500;
                white-space: nowrap;
            }
            .cp-hero-actions {
                margin-top: 38px;
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 14px;
                flex-wrap: wrap;
            }
            .cp-hero-actions a {
                min-width: 170px;
                padding: 17px 24px;
                border: 1px solid var(--landing-line);
                border-radius: 18px;
                color: var(--landing-ink) !important;
                background: rgba(255,255,255,.56);
                font-size: 15px;
                font-weight: 800;
                text-decoration: none;
                backdrop-filter: blur(14px);
                transition: transform .18s ease, box-shadow .18s ease;
            }
            .cp-hero-actions a:hover { transform: translateY(-2px); box-shadow: 0 14px 30px rgba(48,31,37,.09); }
            .cp-hero-actions .primary { background: var(--landing-ink); color: #fff !important; }

            .cp-flow {
                position: relative;
                z-index: 1;
                width: min(1120px, calc(100% - 48px));
                margin: 10px auto 52px;
                padding: 24px;
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 12px;
                border: 1px solid var(--landing-line);
                border-radius: 28px;
                background: rgba(255,255,255,.56);
                box-shadow: 0 22px 55px rgba(72,45,55,.07);
                backdrop-filter: blur(20px);
            }
            .cp-flow-heading {
                grid-column: 1 / -1;
                padding: 8px 8px 14px;
                text-align: center;
            }
            .cp-flow-kicker {
                color: #9a8f94;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: .15em;
            }
            .cp-flow-heading h2 {
                margin: 8px 0 0;
                color: var(--landing-ink);
                font: 700 clamp(23px, 2.4vw, 34px)/1.18 'Noto Sans SC', sans-serif;
            }
            .cp-flow-heading p {
                margin: 9px auto 0;
                color: #7d7478;
                font: 500 13px/1.65 'Noto Sans SC', sans-serif;
            }
            .cp-usage-hints {
                grid-column: 1 / -1;
                display: flex;
                justify-content: center;
                gap: 8px;
                flex-wrap: wrap;
                margin: -2px 0 8px;
            }
            .cp-usage-hint {
                padding: 8px 12px;
                border: 1px solid rgba(76,50,59,.07);
                border-radius: 999px;
                background: rgba(255,255,255,.54);
                color: #736b6f;
                font: 600 11px/1.25 'Noto Sans SC', sans-serif;
            }
            .cp-flow-item {
                position: relative;
                min-height: 120px;
                padding: 20px;
                border-radius: 20px;
                background: rgba(255,255,255,.62);
                text-align: left;
            }
            .cp-flow-item:not(:last-child)::after {
                content: '→';
                position: absolute;
                right: -13px;
                top: 48%;
                z-index: 2;
                color: #9a8f94;
                font-size: 19px;
                font-weight: 700;
            }
            .cp-flow-index { color: #a3999d; font-size: 11px; font-weight: 800; letter-spacing: .12em; }
            .cp-flow-item strong { display: block; margin-top: 18px; color: var(--landing-ink); font: 750 16px/1.35 'Noto Sans SC', sans-serif; }
            .cp-flow-item span:last-child { display: block; margin-top: 7px; color: #7d7478; font: 500 12px/1.55 'Noto Sans SC', sans-serif; }

            @media (max-width: 760px) {
                .cp-landing { border-radius: 22px; }
                .cp-landing-nav { width: calc(100% - 28px); margin-top: 14px; padding: 0 12px 0 17px; }
                .cp-landing-links > a:not(.cp-nav-demo) { display: none; }
                .cp-hero { min-height: 650px; padding-top: 100px; }
                .cp-hero h1 {
                    max-width: 96vw;
                    font-size: clamp(30px, 8.4vw, 56px);
                    line-height: .96;
                    letter-spacing: .02em;
                }
                .cp-hero-copy {
                    max-width: 88vw;
                    font-size: 13px;
                    white-space: normal;
                }
                .cp-flow { width: calc(100% - 28px); grid-template-columns: 1fr 1fr; }
                .cp-flow-heading { padding-inline: 0; }
                .cp-flow-heading p { font-size: 12px; }
                .cp-usage-hints { justify-content: flex-start; }
                .cp-flow-item:not(:last-child)::after { display: none; }
            }

            @media (prefers-reduced-motion: reduce) {
                .cp-fluid::before, .cp-fluid::after, .cp-fluid-lobe {
                    animation-duration: 60s !important;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.html(
        """
        <main class="cp-landing">
            <canvas class="cp-ferrofluid" aria-hidden="true"></canvas>
            <div class="cp-fluid" aria-hidden="true">
                <span class="cp-fluid-lobe one"></span>
                <span class="cp-fluid-lobe two"></span>
                <span class="cp-fluid-lobe three"></span>
                <span class="cp-fluid-pointer"></span>
            </div>
            <nav class="cp-landing-nav" aria-label="产品导航">
                <a class="cp-landing-brand" href="?page=产品首页" target="_self">lumooi.</a>
                <div class="cp-landing-links">
                    <a href="#how-it-works">如何使用</a>
                    <a class="cp-nav-demo" href="?page=工作台" target="_self">体验 Demo</a>
                </div>
            </nav>

            <section class="cp-hero">
                <div class="cp-eyebrow">AI CAREER WORKSPACE</div>
                <h1><span>Shape what you’ve done</span><span>into what’s next.</span></h1>
                <p class="cp-hero-copy">lumooi 产品 Demo：用10段真实经历与56项脱敏职业资产，演示系统如何长期沉淀经历，并为不同岗位筛选最匹配的证据与STAR故事。</p>
                <div class="cp-hero-actions">
                    <a class="primary" href="?page=工作台" target="_self">进入 lumooi Demo</a>
                    <a href="#how-it-works">查看 5 步使用指南 ↓</a>
                </div>
            </section>

            <section class="cp-flow" id="how-it-works" aria-label="lumooi 工作流程">
                <header class="cp-flow-heading">
                    <div class="cp-flow-kicker">HOW TO USE</div>
                    <h2>为每一次成长留档，让能力在机会面前被看见</h2>
                    <p>经历越多，越需要把技能、证据和STAR持续保存；面对新岗位时，再按能力要求筛选最相关的素材。</p>
                </header>
                <div class="cp-usage-hints" aria-label="页面操作提示">
                    <span class="cp-usage-hint">左侧导航切换功能</span>
                    <span class="cp-usage-hint">卡片可点击，资产卡还可拖动</span>
                    <span class="cp-usage-hint">不确定从哪开始？先打开 Experience Bank</span>
                </div>
                <div class="cp-flow-item"><span class="cp-flow-index">01</span><strong>长期沉淀职业资产</strong><span>把每段经历的任务、行动、结果、技能和证据持续保存。</span></div>
                <div class="cp-flow-item"><span class="cp-flow-index">02</span><strong>管理求职进程</strong><span>集中保存公司、岗位、截止日期和申请状态。</span></div>
                <div class="cp-flow-item"><span class="cp-flow-index">03</span><strong>筛选岗位匹配经历</strong><span>根据当前JD，从多年资产中选出最能证明能力的案例。</span></div>
                <div class="cp-flow-item"><span class="cp-flow-index">04</span><strong>跟进申请流程</strong><span>统计投递进度，记录面试轮次、时间和下一步行动。</span></div>
                <div class="cp-flow-item"><span class="cp-flow-index">05</span><strong>准备与复盘面试</strong><span>从真实素材组织回答，导入文稿并沉淀复盘。</span></div>
            </section>
        </main>
        """
    )

    # Streamlit 的静态 HTML 不执行脚本；通过一个零高度组件把父页面的
    # 鼠标坐标传给流体层，使多个液体团以不同惯性追随指针。
    components.html(
        r"""
        <script>
        (() => {
            let owner;
            let doc;
            try {
                owner = window.parent;
                doc = owner.document;
            } catch (error) {
                return;
            }

            if (typeof owner.__lumooiFluidCleanup === "function") {
                owner.__lumooiFluidCleanup();
            }

            const landing = doc.querySelector(".cp-landing");
            if (!landing) return;

            const canvas = landing.querySelector(".cp-ferrofluid");
            const fallbackFluid = landing.querySelector(".cp-fluid");
            let ferro = null;

            if (canvas) {
                const gl = canvas.getContext("webgl", {
                    alpha: false,
                    antialias: false,
                    depth: false,
                    stencil: false,
                    powerPreference: "high-performance",
                });

                if (gl) {
                    const compile = (type, source) => {
                        const shader = gl.createShader(type);
                        gl.shaderSource(shader, source);
                        gl.compileShader(shader);
                        if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
                            const message = gl.getShaderInfoLog(shader);
                            gl.deleteShader(shader);
                            throw new Error(message || "Ferrofluid shader compilation failed");
                        }
                        return shader;
                    };

                    try {
                        const vertexShader = compile(gl.VERTEX_SHADER, `
                            attribute vec2 a_position;
                            void main() {
                                gl_Position = vec4(a_position, 0.0, 1.0);
                            }
                        `);
                        const fragmentShader = compile(gl.FRAGMENT_SHADER, `
                            precision highp float;

                            uniform vec2 u_resolution;
                            uniform float u_time;
                            uniform vec2 u_mouse;
                            uniform float u_mouse_active;

                            float hash(vec2 p) {
                                p = fract(p * vec2(123.34, 456.21));
                                p += dot(p, p + 45.32);
                                return fract(p.x * p.y);
                            }

                            float noise(vec2 p) {
                                vec2 i = floor(p);
                                vec2 f = fract(p);
                                f = f * f * (3.0 - 2.0 * f);
                                return mix(
                                    mix(hash(i), hash(i + vec2(1.0, 0.0)), f.x),
                                    mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0)), f.x),
                                    f.y
                                );
                            }

                            float fbm(vec2 p) {
                                float value = 0.0;
                                float amplitude = 0.52;
                                mat2 rotation = mat2(0.82, -0.57, 0.57, 0.82);
                                for (int i = 0; i < 5; i++) {
                                    value += amplitude * noise(p);
                                    p = rotation * p * 2.03 + 17.17;
                                    amplitude *= 0.50;
                                }
                                return value;
                            }

                            float fluidField(vec2 p) {
                                /* speed .2 / scale 1.6 / turbulence 1 / downward flow */
                                float t = u_time * 0.085;
                                p.y -= t;
                                vec2 warp = vec2(
                                    fbm(p * 0.78 + vec2(2.7, -t * 0.35)),
                                    fbm(p * 0.78 + vec2(-3.1, t * 0.28))
                                ) - 0.5;
                                float broad = fbm(p * 0.72 + warp * 1.25);
                                float detail = fbm(p * 1.55 - warp * 0.58 + vec2(t * 0.16, 0.0));
                                return broad * 0.78 + detail * 0.22;
                            }

                            void main() {
                                vec2 uv = gl_FragCoord.xy / u_resolution.xy;
                                float aspect = u_resolution.x / u_resolution.y;
                                vec2 p = uv - 0.5;
                                p.x *= aspect;
                                p *= 1.6;

                                vec2 mouse = u_mouse - 0.5;
                                mouse.x *= aspect;
                                mouse *= 1.6;
                                vec2 mouseDelta = p - mouse;
                                float mousePull = exp(-dot(mouseDelta, mouseDelta) / 0.1225) * u_mouse_active;
                                p += normalize(mouseDelta + vec2(0.0001)) * mousePull * 0.20;

                                float field = fluidField(p);
                                float d = field - 0.505;
                                float epsilon = 2.5 / min(u_resolution.x, u_resolution.y);
                                vec2 gradient = vec2(
                                    fluidField(p + vec2(epsilon, 0.0)) - fluidField(p - vec2(epsilon, 0.0)),
                                    fluidField(p + vec2(0.0, epsilon)) - fluidField(p - vec2(0.0, epsilon))
                                );
                                vec2 normal = normalize(gradient + vec2(0.00001));
                                vec2 light = normalize(vec2(-0.62, 0.78));

                                float surface = smoothstep(-0.045, 0.045, d);
                                float rimBand = exp(-abs(d) * 52.0);
                                float softGlow = exp(-abs(d) * 18.0);
                                float litRim = pow(max(dot(normal, light), 0.0), 2.5) * rimBand;
                                float coolRim = pow(max(dot(-normal, light), 0.0), 1.8) * rimBand;
                                float shadow = pow(max(dot(normal, -light), 0.0), 2.0) * exp(-abs(d) * 31.0);
                                float shimmer = noise(p * 5.4 + u_time * 0.055) * litRim;

                                vec3 pink = vec3(1.0, 0.945, 0.968);
                                vec3 white = vec3(1.0);
                                vec3 blush = vec3(0.976, 0.760, 0.847);
                                vec3 color = pink;
                                color = mix(color, white, surface * 0.055);
                                color -= vec3(0.035, 0.026, 0.030) * shadow * 0.62;
                                color = mix(color, blush, coolRim * 0.32);
                                color += white * (litRim * 0.92 + shimmer * 0.24 + softGlow * litRim * 0.24);
                                color = clamp(color, 0.0, 1.0);

                                gl_FragColor = vec4(color, 1.0);
                            }
                        `);

                        const program = gl.createProgram();
                        gl.attachShader(program, vertexShader);
                        gl.attachShader(program, fragmentShader);
                        gl.linkProgram(program);
                        if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
                            throw new Error(gl.getProgramInfoLog(program) || "Ferrofluid shader link failed");
                        }

                        const buffer = gl.createBuffer();
                        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
                        gl.bufferData(
                            gl.ARRAY_BUFFER,
                            new Float32Array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1]),
                            gl.STATIC_DRAW,
                        );
                        gl.useProgram(program);
                        const position = gl.getAttribLocation(program, "a_position");
                        gl.enableVertexAttribArray(position);
                        gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

                        const resolutionUniform = gl.getUniformLocation(program, "u_resolution");
                        const timeUniform = gl.getUniformLocation(program, "u_time");
                        const mouseUniform = gl.getUniformLocation(program, "u_mouse");
                        const mouseActiveUniform = gl.getUniformLocation(program, "u_mouse_active");

                        ferro = {
                            gl,
                            program,
                            buffer,
                            vertexShader,
                            fragmentShader,
                            render(now, mouseX, mouseY, mouseIsActive) {
                                const rect = landing.getBoundingClientRect();
                                const pixelRatio = Math.min(owner.devicePixelRatio || 1, 1.5);
                                const width = Math.max(1, Math.round(rect.width * pixelRatio));
                                const height = Math.max(1, Math.round(rect.height * pixelRatio));
                                if (canvas.width !== width || canvas.height !== height) {
                                    canvas.width = width;
                                    canvas.height = height;
                                    gl.viewport(0, 0, width, height);
                                }
                                gl.useProgram(program);
                                gl.uniform2f(resolutionUniform, width, height);
                                gl.uniform1f(timeUniform, now * 0.001);
                                gl.uniform2f(
                                    mouseUniform,
                                    0.5 + mouseX / Math.max(rect.width, 1),
                                    0.5 - mouseY / Math.max(rect.height, 1),
                                );
                                gl.uniform1f(mouseActiveUniform, mouseIsActive ? 1 : 0);
                                gl.drawArrays(gl.TRIANGLES, 0, 6);
                            },
                            destroy() {
                                gl.deleteBuffer(buffer);
                                gl.deleteProgram(program);
                                gl.deleteShader(vertexShader);
                                gl.deleteShader(fragmentShader);
                            },
                        };
                        if (fallbackFluid) fallbackFluid.style.display = "none";
                    } catch (error) {
                        console.warn("Ferrofluid background unavailable; using CSS fallback.", error);
                    }
                }
            }

            const lobes = Array.from(landing.querySelectorAll(".cp-fluid-lobe"));
            const pointerGlow = landing.querySelector(".cp-fluid-pointer");
            const reducedMotion = owner.matchMedia("(prefers-reduced-motion: reduce)").matches;
            const coarsePointer = owner.matchMedia("(pointer: coarse)").matches;

            let targetX = 0;
            let targetY = 0;
            let currentX = 0;
            let currentY = 0;
            let active = false;
            let frame = 0;

            const lobeStrength = [0.16, -0.11, 0.075];

            const onPointerMove = (event) => {
                const rect = landing.getBoundingClientRect();
                const within =
                    event.clientX >= rect.left && event.clientX <= rect.right &&
                    event.clientY >= rect.top && event.clientY <= rect.bottom;

                if (!within) {
                    active = false;
                    targetX = 0;
                    targetY = 0;
                    if (pointerGlow) pointerGlow.style.opacity = "0";
                    return;
                }

                active = true;
                targetX = event.clientX - rect.left - rect.width / 2;
                targetY = event.clientY - rect.top - rect.height / 2;
                if (pointerGlow) pointerGlow.style.opacity = ".88";
            };

            const onPointerLeave = () => {
                active = false;
                targetX = 0;
                targetY = 0;
                if (pointerGlow) pointerGlow.style.opacity = "0";
            };

            const animate = () => {
                const easing = active ? 0.075 : 0.045;
                currentX += (targetX - currentX) * easing;
                currentY += (targetY - currentY) * easing;

                lobes.forEach((lobe, index) => {
                    if (lobe.classList.contains("cp-fluid-pointer")) return;
                    const strength = lobeStrength[index] ?? 0.06;
                    lobe.style.translate = `${currentX * strength}px ${currentY * strength}px`;
                });

                if (pointerGlow) {
                    pointerGlow.style.translate = `${currentX}px ${currentY}px`;
                }

                if (ferro) {
                    const motionTime = owner.performance.now() * (reducedMotion ? 0.3 : 1);
                    ferro.render(motionTime, currentX, currentY, active);
                }

                frame = owner.requestAnimationFrame(animate);
            };

            if (ferro) {
                ferro.render(owner.performance.now(), 0, 0, false);
            }

            if (!coarsePointer && !reducedMotion) {
                doc.addEventListener("pointermove", onPointerMove, { passive: true });
                landing.addEventListener("pointerleave", onPointerLeave, { passive: true });
            }
            // Keep the silk flowing on every device. Reduced-motion users get a
            // much slower passive animation and no pointer-following movement.
            frame = owner.requestAnimationFrame(animate);

            owner.__lumooiFluidCleanup = () => {
                owner.cancelAnimationFrame(frame);
                doc.removeEventListener("pointermove", onPointerMove);
                landing.removeEventListener("pointerleave", onPointerLeave);
                lobes.forEach(lobe => { lobe.style.translate = ""; });
                if (pointerGlow) {
                    pointerGlow.style.translate = "";
                    pointerGlow.style.opacity = "0";
                }
                if (ferro) ferro.destroy();
                if (fallbackFluid) fallbackFluid.style.display = "";
                delete owner.__lumooiFluidCleanup;
            };
        })();
        </script>
        """,
        height=0,
        scrolling=False,
    )


# =========================================================
# lumooi 工作台：Kinetic 风格职业管理 Dashboard
# =========================================================
def render_lumooi_home(all_jobs, counts):
    """渲染工作台，只读取现有数据库。"""
    active_jobs = [
        job for job in all_jobs
        if (job.get("status") or "") not in {"Offer", "已结束", "拒绝", "放弃"}
    ]
    active_jobs.sort(
        key=lambda job: (
            job.get("interview_date") or job.get("deadline") or "9999-12-31",
            job.get("updated_at") or "",
        )
    )

    focus_job = active_jobs[0] if active_jobs else None
    upcoming_jobs = active_jobs[:3]
    total = counts["全部岗位"]
    submitted = total - counts["准备投递"]
    interview_total = sum(counts[key] for key in ["群面", "初试", "复试", "业务面", "HR面"])
    completion = round((submitted / total) * 100) if total else 0

    if focus_job:
        focus_event_is_interview = bool(focus_job.get("interview_date"))
        focus_event_label = "面试时间" if focus_event_is_interview else "截止日期"
        focus_deadline, focus_remaining = get_deadline_display(
            focus_job.get("interview_date") or focus_job.get("deadline")
        )
        focus_company = safe_text(focus_job.get("company"), "暂无重点岗位")
        focus_position = safe_text(focus_job.get("position"), "在职位申请中添加岗位")
        focus_action = safe_text(focus_job.get("next_action"), "添加岗位后，这里会显示下一步行动")
        focus_status = safe_text(focus_job.get("status"), "待添加")
    else:
        focus_event_label = "近期节点"
        focus_deadline, focus_remaining = "未设置", "暂无截止日期"
        focus_company = "暂无重点岗位"
        focus_position = "在职位申请中添加岗位"
        focus_action = "添加岗位后，这里会显示下一步行动"
        focus_status = "待添加"

    upcoming_html = ""
    for index, job in enumerate(upcoming_jobs):
        event_is_interview = bool(job.get("interview_date"))
        event_label = "面试" if event_is_interview else "截止"
        deadline, remaining = get_deadline_display(
            job.get("interview_date") or job.get("deadline")
        )
        dot_class = ["mint", "orange", "violet"][index % 3]
        upcoming_html += f"""
            <div class="lum-deadline-item">
                <span class="lum-dot {dot_class}"></span>
                <div class="lum-deadline-copy">
                    <strong>{safe_text(job.get('company'))}</strong>
                    <span>{safe_text(job.get('position'))}</span>
                </div>
                <div class="lum-deadline-date">
                    {safe_text(deadline)}<small>{event_label} · {safe_text(remaining)}</small>
                </div>
            </div>
        """

    if not upcoming_html:
        upcoming_html = """
            <div class="lum-empty-mini">
                添加职位后，这里会自动显示最近截止的申请。
            </div>
        """

    st.markdown(
        r"""
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&family=Manrope:wght@400;500;600;700;800&family=Noto+Sans+SC:wght@400;500;600;700;800&display=swap');

            :root {
                --lum-bg: #fef5f5;
                --lum-panel: #fffafa;
                --lum-ink: #111111;
                --lum-muted: #8b8b88;
                --lum-blue: #dceefa;
                --lum-mint: #d9f1e1;
                --lum-orange: #ffe4cf;
                --lum-violet: #eadcff;
                --lum-line: rgba(17,17,17,.08);
            }

            html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
                background: var(--lum-bg) !important;
                color: var(--lum-ink) !important;
            }

            header[data-testid="stHeader"] { background: transparent !important; }
            [data-testid="stToolbar"], [data-testid="stDecoration"], [data-testid="collapsedControl"] { display: none !important; }

            section[data-testid="stSidebar"] {
                position: fixed !important;
                inset: 0 auto 0 0 !important;
                z-index: 999 !important;
                width: 80px !important;
                min-width: 80px !important;
                max-width: 80px !important;
                height: 100dvh !important;
                overflow: hidden !important;
                background: var(--lum-bg) !important;
                border-right: 1px solid transparent !important;
                box-shadow: none !important;
                transition: none !important;
            }

            section[data-testid="stSidebar"]:hover {
                width: 80px !important;
                min-width: 80px !important;
                max-width: 80px !important;
                background: var(--lum-bg) !important;
                border-right-color: transparent !important;
                box-shadow: none !important;
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

            [data-testid="stMain"] {
                margin-left: 80px !important;
                width: calc(100% - 80px) !important;
                transition: none !important;
            }

            .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"] {
                margin-left: 80px !important;
                width: calc(100% - 80px) !important;
            }

            .block-container {
                width: 100% !important;
                max-width: none !important;
                padding: 20px 22px 24px !important;
            }

            .lum-sidebar-brand {
                width: 250px;
                height: 76px;
                padding: 8px 14px;
                color: var(--lum-ink);
                font-family: 'Gaegu', cursive;
                font-size: 31px;
                line-height: 1;
                font-weight: 700;
                letter-spacing: .04em;
                white-space: nowrap;
            }

            section[data-testid="stSidebar"]:not(:hover) .lum-sidebar-brand {
                font-size: 0;
                padding-left: 12px;
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
                text-transform: uppercase;
                white-space: nowrap;
                opacity: 0;
            }
            section[data-testid="stSidebar"]:hover div[data-testid="stRadio"] > label { opacity: 1; }

            section[data-testid="stSidebar"] div[role="radiogroup"] {
                width: 270px !important;
                gap: 7px !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label {
                position: relative !important;
                width: 270px !important;
                min-height: 54px !important;
                margin: 0 !important;
                padding: 0 18px 0 70px !important;
                border: 0 !important;
                border-radius: 18px !important;
                background: transparent !important;
                display: flex !important;
                align-items: center !important;
                overflow: hidden !important;
                transition: background .18s ease !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
                background: rgba(17,17,17,.055) !important;
            }

            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
                background: #151515 !important;
                color: #fff !important;
                border-left: 0 !important;
            }
            section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before { color: #fff; }

            section[data-testid="stSidebar"] div[role="radiogroup"] label p {
                color: inherit !important;
                font-family: 'Noto Sans SC', sans-serif !important;
                font-size: 16px !important;
                font-weight: 650 !important;
                white-space: nowrap !important;
                opacity: 0 !important;
                transform: translateX(-8px);
                transition: opacity .16s ease .04s, transform .18s ease .04s !important;
            }
            section[data-testid="stSidebar"]:hover div[role="radiogroup"] label p {
                opacity: 1 !important;
                transform: translateX(0);
            }

            .lum-sidebar-focus {
                position: absolute;
                left: 18px;
                bottom: 22px;
                width: 274px;
                padding: 18px;
                border: 1px solid var(--lum-line);
                border-radius: 22px;
                background: rgba(255,255,255,.82);
                opacity: 0;
                transform: translateY(12px);
                pointer-events: none;
                transition: opacity .16s ease .08s, transform .20s ease .08s;
            }
            section[data-testid="stSidebar"]:hover .lum-sidebar-focus { opacity: 1; transform: translateY(0); }
            .lum-sidebar-focus .mini-pill {
                display: inline-flex;
                padding: 5px 10px;
                border-radius: 999px;
                background: var(--lum-blue);
                font: 700 11px/1 'Manrope', sans-serif;
            }
            .lum-sidebar-focus strong {
                display: block;
                margin-top: 12px;
                font: 750 15px/1.35 'Noto Sans SC', sans-serif;
            }
            .lum-sidebar-focus span:last-child {
                display: block;
                margin-top: 7px;
                color: var(--lum-muted);
                font: 500 12px/1.45 'Noto Sans SC', sans-serif;
            }

            .lum-shell {
                min-height: calc(100dvh - 44px);
                overflow: hidden;
                border: 1px solid var(--page-panel-line);
                border-radius: 26px;
                background: var(--lum-panel);
                box-shadow: 0 20px 55px rgba(20,20,20,.05);
                font-family: 'Manrope', 'Noto Sans SC', sans-serif;
            }

            .lum-topbar {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 24px;
                padding: 32px 52px 10px;
            }
            .lum-greeting h1 {
                margin: 0;
                color: var(--lum-ink);
                font-family: 'Gaegu', cursive;
                font-size: clamp(43px, 5vw, 72px);
                line-height: .95;
                letter-spacing: .025em;
                font-weight: 700;
            }
            .lum-demo-label {
                display: inline-flex;
                margin-top: 10px;
                padding: 6px 10px;
                border: 1px solid var(--lum-line);
                border-radius: 999px;
                background: rgba(255,255,255,.68);
                color: #777773;
                font-size: 10px;
                line-height: 1;
                font-weight: 800;
                letter-spacing: .11em;
            }
            .lum-top-actions { display: flex; align-items: center; gap: 14px; }
            .lum-circle-button, .lum-avatar {
                width: 56px;
                height: 56px;
                display: grid;
                place-items: center;
                border: 1px solid var(--lum-line);
                border-radius: 50%;
                background: #fff;
                color: var(--lum-ink);
                text-decoration: none;
                font-size: 23px;
            }
            .lum-avatar {
                border: 0;
                background: var(--lum-orange);
                font-family: 'Gaegu', cursive;
                font-size: 25px;
                font-weight: 700;
            }

            .lum-dashboard-grid {
                display: grid;
                grid-template-columns: minmax(390px, 1.7fr) minmax(240px, .78fr) minmax(280px, .92fr);
                grid-template-rows: minmax(430px, 1.2fr) minmax(260px, .72fr);
                gap: 28px;
                padding: 12px 52px 48px;
            }

            .lum-card {
                position: relative;
                overflow: hidden;
                border-radius: 52px;
                padding: 38px 42px;
                color: var(--lum-ink);
                box-shadow: 0 18px 42px rgba(19,19,19,.045);
            }
            .lum-card.blue { background: var(--lum-blue); }
            .lum-card.mint { background: var(--lum-mint); }
            .lum-card.orange { background: var(--lum-orange); }
            .lum-card.violet { background: var(--lum-violet); }

            .lum-performance { grid-row: 1; grid-column: 1; }
            .lum-stage { grid-row: 1; grid-column: 2; }
            .lum-focus { grid-row: 1; grid-column: 3; }
            .lum-deadlines { grid-row: 2; grid-column: 1 / span 2; }
            .lum-add { grid-row: 2; grid-column: 3; }

            .lum-pill {
                display: inline-flex;
                align-items: center;
                min-height: 34px;
                padding: 8px 18px;
                border-radius: 999px;
                background: rgba(255,255,255,.58);
                font-size: 12px;
                font-weight: 800;
                letter-spacing: .055em;
                text-transform: uppercase;
            }
            .lum-card h2 {
                margin: 26px 0 0;
                font-size: clamp(24px, 2.15vw, 34px);
                line-height: 1.05;
                font-weight: 800;
                letter-spacing: -.03em;
            }
            .lum-big-number {
                margin-top: 16px;
                font-size: clamp(62px, 7.2vw, 104px);
                line-height: .92;
                font-weight: 800;
                letter-spacing: -.065em;
            }
            .lum-growth { margin-top: 25px; color: #0aad79; font-size: 17px; font-weight: 800; }
            .lum-chart { position: absolute; left: 42px; right: 42px; bottom: 33px; height: 155px; }
            .lum-chart svg { width: 100%; height: 100%; overflow: visible; }
            .lum-hand-note {
                position: absolute;
                right: 36px;
                bottom: 20px;
                color: #92928e;
                font-family: 'Gaegu', cursive;
                font-size: 22px;
                letter-spacing: .08em;
                transform: rotate(-2deg);
            }

            .lum-stage-list { margin-top: 22px; display: grid; gap: 13px; }
            .lum-stage-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 14px;
                padding: 13px 15px;
                border-radius: 999px;
                background: rgba(255,255,255,.60);
                font-size: 14px;
                font-weight: 700;
            }
            .lum-stage-row b { font-size: 18px; }
            .lum-stage-row span::before {
                content: '';
                display: inline-block;
                width: 9px;
                height: 9px;
                margin-right: 9px;
                border-radius: 50%;
                background: #12b986;
            }
            .lum-stage-row:nth-child(3) span::before { background: #f2a314; }

            .lum-focus-company { margin-top: 28px; color: rgba(17,17,17,.56); font-size: 14px; font-weight: 800; }
            .lum-focus-position {
                margin-top: 8px;
                font-family: 'Noto Sans SC', sans-serif;
                font-size: clamp(22px, 2vw, 31px);
                line-height: 1.35;
                font-weight: 800;
            }
            .lum-focus-action {
                margin-top: 22px;
                padding: 17px 18px;
                border-radius: 20px;
                background: rgba(255,255,255,.55);
                color: #4e4e4b;
                font-family: 'Noto Sans SC', sans-serif;
                font-size: 13px;
                line-height: 1.65;
            }
            .lum-focus-meta {
                position: absolute;
                left: 42px;
                right: 42px;
                bottom: 34px;
                display: flex;
                align-items: flex-end;
                justify-content: space-between;
                gap: 14px;
                color: #62625f;
                font-size: 12px;
                font-weight: 700;
            }
            .lum-focus-meta strong { display: block; color: var(--lum-ink); font-size: 16px; margin-top: 3px; }
            .lum-focus-meta small { display: block; margin-top: 3px; color: #888884; font-size: 10px; }

            .lum-deadlines {
                padding: 30px 36px;
                display: grid;
                grid-template-columns: minmax(180px,.65fr) minmax(360px,1.35fr);
                gap: 30px;
                align-items: center;
            }
            .lum-deadlines h2 { margin-top: 18px; }
            .lum-deadline-list { display: grid; gap: 11px; }
            .lum-deadline-item {
                display: grid;
                grid-template-columns: 12px minmax(0,1fr) auto;
                align-items: center;
                gap: 13px;
                padding: 12px 15px;
                border-radius: 20px;
                background: rgba(255,255,255,.56);
            }
            .lum-dot { width: 9px; height: 9px; border-radius: 50%; background: #15b987; }
            .lum-dot.orange { background: #f1a41a; }
            .lum-dot.violet { background: #8d63d2; }
            .lum-deadline-copy { min-width: 0; }
            .lum-deadline-copy strong, .lum-deadline-copy span { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
            .lum-deadline-copy strong { font-size: 12px; }
            .lum-deadline-copy span { margin-top: 2px; color: #666663; font-family: 'Noto Sans SC', sans-serif; font-size: 12px; }
            .lum-deadline-date { color: #4e4e4b; font-size: 12px; font-weight: 800; text-align: right; }
            .lum-deadline-date small { display: block; margin-top: 2px; color: #999995; font-size: 10px; font-weight: 600; }
            .lum-empty-mini { color: #6f6f6b; font: 13px/1.7 'Noto Sans SC', sans-serif; }

            .lum-add {
                display: grid;
                place-items: center;
                border: 2px dashed rgba(17,17,17,.07);
                background: transparent;
                box-shadow: none;
            }
            .lum-add-inner { text-align: center; }
            .lum-add-button {
                width: 100px;
                height: 100px;
                display: grid;
                place-items: center;
                margin: 0 auto;
                border-radius: 50%;
                background: #151515;
                color: #fff !important;
                text-decoration: none;
                font-size: 48px;
                line-height: 1;
                box-shadow: 0 16px 28px rgba(0,0,0,.11);
                transition: transform .2s ease;
            }
            .lum-add-button:hover { transform: rotate(8deg) scale(1.04); }
            .lum-add-label { margin-top: 16px; color: #9a9a96; font-size: 15px; font-weight: 700; }

            @media (max-width: 1250px) {
                .lum-dashboard-grid { grid-template-columns: 1.45fr .8fr; grid-template-rows: auto auto auto; }
                .lum-performance { grid-column: 1; grid-row: 1; min-height: 430px; }
                .lum-stage { grid-column: 2; grid-row: 1; }
                .lum-focus { grid-column: 1; grid-row: 2; min-height: 360px; }
                .lum-add { grid-column: 2; grid-row: 2; }
                .lum-deadlines { grid-column: 1 / -1; grid-row: 3; }
            }

            @media (max-width: 820px) {
                section[data-testid="stSidebar"],
                section[data-testid="stSidebar"]:hover { width: 80px !important; min-width:80px !important; max-width:80px !important; }
                [data-testid="stMain"] { margin-left:80px !important; width:calc(100% - 80px) !important; }
                .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"] { margin-left:80px !important; width:calc(100% - 80px) !important; }
                .block-container { padding: 10px !important; }
                .lum-topbar { padding: 24px 24px 6px; }
                .lum-dashboard-grid { grid-template-columns: 1fr; grid-template-rows: auto; padding: 12px 24px 32px; }
                .lum-performance, .lum-stage, .lum-focus, .lum-deadlines, .lum-add { grid-column: 1; grid-row: auto; }
                .lum-card { border-radius: 34px; padding: 30px; }
                .lum-performance { min-height: 430px; }
                .lum-stage, .lum-focus { min-height: 330px; }
                .lum-deadlines { grid-template-columns: 1fr; }
                .lum-add { min-height: 230px; }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.html(
        f"""
        <div class="lum-shell">
            <header class="lum-topbar">
                <div class="lum-greeting">
                    <h1>Nina's Career Archive.</h1>
                    <span class="lum-demo-label">LUMOOI PRODUCT DEMO · 真实经历脱敏＋假设岗位</span>
                </div>
                <div class="lum-top-actions">
                    <a class="lum-circle-button" href="?page=职位申请" target="_self" aria-label="申请追踪">♧</a>
                    <div class="lum-avatar">NL</div>
                </div>
            </header>

            <section class="lum-dashboard-grid">
                <article class="lum-card blue lum-performance">
                    <span class="lum-pill">Application performance</span>
                    <h2>申请进度</h2>
                    <div class="lum-big-number">{total}</div>
                    <div class="lum-growth">↗ {completion}% 已进入投递及后续阶段</div>
                    <div class="lum-chart" aria-hidden="true">
                        <svg viewBox="0 0 520 160" preserveAspectRatio="none">
                            <path d="M0 112 C65 90,115 126,165 120 C225 113,245 28,305 38 C370 50,370 135,430 132 C470 130,495 72,520 18" fill="none" stroke="#149de4" stroke-width="7" stroke-linecap="round"/>
                        </svg>
                    </div>
                    <div class="lum-hand-note">keep moving →</div>
                </article>

                <article class="lum-card mint lum-stage">
                    <span class="lum-pill">Pipeline</span>
                    <h2>申请阶段</h2>
                    <div class="lum-stage-list">
                        <div class="lum-stage-row"><span>准备投递</span><b>{counts['准备投递']}</b></div>
                        <div class="lum-stage-row"><span>已投递</span><b>{counts['投递简历']}</b></div>
                        <div class="lum-stage-row"><span>面试流程</span><b>{interview_total}</b></div>
                    </div>
                </article>

                <article class="lum-card violet lum-focus">
                    <span class="lum-pill">Current focus</span>
                    <div class="lum-focus-company">{focus_company}</div>
                    <div class="lum-focus-position">{focus_position}</div>
                    <div class="lum-focus-action">{focus_action}</div>
                    <div class="lum-focus-meta">
                        <div>当前状态<strong>{focus_status}</strong></div>
                        <div>{focus_event_label}<strong>{safe_text(focus_deadline)}</strong><small>{safe_text(focus_remaining)}</small></div>
                    </div>
                </article>

                <article class="lum-card orange lum-deadlines">
                    <div>
                        <span class="lum-pill">Upcoming</span>
                        <h2>近期申请与面试</h2>
                    </div>
                    <div class="lum-deadline-list">{upcoming_html}</div>
                </article>

                <article class="lum-card lum-add">
                    <div class="lum-add-inner">
                        <a class="lum-add-button" href="?page=职位申请&mode=new" target="_self" aria-label="新增职位">+</a>
                        <div class="lum-add-label">Add a new job</div>
                    </div>
                </article>
            </section>
        </div>
        """
    )


# =========================================================
# 初始化数据库
# =========================================================
initialize_database()

seed_demo_data()

jobs = get_all_jobs()
experiences = get_all_experiences()
funnel_counts = calculate_funnel_counts(jobs)


# =========================================================
# 品牌区和导航
# =========================================================
NAV_OPTIONS = [
    "产品首页",
    "工作台",
    "职业资产库",
    "职位申请",
    "简历定制",
    "面试准备",
]

# 默认进入公开产品首页；工作台和其他功能使用同一套查询参数导航。
requested_page = st.query_params.get("page", "产品首页")
if isinstance(requested_page, list):
    requested_page = requested_page[0] if requested_page else "产品首页"

if requested_page not in NAV_OPTIONS:
    requested_page = "产品首页"

if st.session_state.get("main_nav") != requested_page:
    st.session_state["main_nav"] = requested_page


def sync_navigation_query():
    st.query_params["page"] = st.session_state["main_nav"]


def render_sidebar_kinetic_avatar():
    """Mount the mouse-following line avatar in place of the sidebar logo."""
    components.html(
        r"""
        <script>
        (() => {
            let owner;
            let doc;
            try {
                owner = window.parent;
                doc = owner.document;
            } catch (error) {
                return;
            }

            if (typeof owner.__careerpilotAvatarCleanup === "function") {
                owner.__careerpilotAvatarCleanup();
            }

            doc.getElementById("careerpilot-kinetic-avatar")?.remove();
            doc.getElementById("careerpilot-kinetic-avatar-style")?.remove();

            const style = doc.createElement("style");
            style.id = "careerpilot-kinetic-avatar-style";
            style.textContent = `
                #careerpilot-kinetic-avatar {
                    position: fixed;
                    left: 5px;
                    top: 8px;
                    bottom: auto;
                    z-index: 1000001;
                    width: 70px;
                    height: 74px;
                    display: grid;
                    place-items: center;
                    overflow: hidden;
                    color: #111111;
                    background: #ffffff;
                    pointer-events: none;
                    perspective: 520px;
                }

                #careerpilot-kinetic-avatar svg {
                    width: 62px;
                    height: 74px;
                    overflow: visible;
                }

                section[data-testid="stSidebar"] .lum-sidebar-brand {
                    visibility: hidden !important;
                    opacity: 0 !important;
                }

                #careerpilot-kinetic-avatar .cp-avatar-head {
                    transform-box: fill-box;
                    transform-origin: 50% 62%;
                    will-change: transform;
                }

                #careerpilot-kinetic-avatar .cp-avatar-line,
                #careerpilot-kinetic-avatar .cp-avatar-feature {
                    fill: none;
                    stroke: currentColor;
                    stroke-width: 7;
                    stroke-linecap: round;
                    stroke-linejoin: round;
                }

                #careerpilot-kinetic-avatar .cp-avatar-feature {
                    stroke-width: 6;
                }

                #careerpilot-kinetic-avatar .cp-avatar-pupil {
                    fill: currentColor;
                    transform-box: fill-box;
                    transform-origin: center;
                    will-change: transform;
                }

                #careerpilot-kinetic-avatar .cp-avatar-shadow {
                    fill: currentColor;
                    opacity: .12;
                    filter: blur(2px);
                    transform-box: fill-box;
                    transform-origin: center;
                    will-change: transform;
                }

                @media (max-height: 650px) {
                    #careerpilot-kinetic-avatar {
                        top: 6px;
                        height: 68px;
                    }

                    #careerpilot-kinetic-avatar svg {
                        width: 58px;
                        height: 68px;
                    }
                }
            `;
            doc.head.appendChild(style);

            const host = doc.createElement("div");
            host.id = "careerpilot-kinetic-avatar";
            host.setAttribute("aria-label", "跟随鼠标左右转头的女生线条头像");
            host.innerHTML = `
                <svg viewBox="70 34 280 332" role="img" aria-label="动态女生线条头像">
                    <ellipse class="cp-avatar-shadow" cx="210" cy="303" rx="34" ry="9"></ellipse>
                    <g fill="none" stroke="currentColor" stroke-width="7" stroke-linecap="round">
                        <path d="M179 294 L168 350"></path>
                        <path d="M241 294 L252 350"></path>
                    </g>
                    <g class="cp-avatar-head">
                        <path class="cp-avatar-line" d="M103 302 C78 209 82 105 141 54 C183 18 247 19 288 57 C343 109 343 218 317 306"></path>
                        <path class="cp-avatar-line" d="M129 132 C118 180 123 243 154 274 C183 305 235 306 266 275 C295 245 301 186 289 136"></path>
                        <path class="cp-avatar-line" d="M129 169 C106 160 102 198 127 203"></path>
                        <path class="cp-avatar-line" d="M290 169 C314 160 318 198 292 203"></path>
                        <path class="cp-avatar-line" d="M123 144 C130 96 153 61 187 51 C194 87 220 113 275 137"></path>
                        <path class="cp-avatar-line" d="M190 52 C200 83 225 108 278 132"></path>
                        <path class="cp-avatar-line" d="M113 216 C108 257 116 297 132 326"></path>
                        <path class="cp-avatar-line" d="M307 216 C312 257 304 297 288 326"></path>
                        <path class="cp-avatar-feature" d="M147 151 C161 142 177 142 190 151"></path>
                        <path class="cp-avatar-feature" d="M230 151 C243 142 259 142 273 151"></path>
                        <circle class="cp-avatar-line" cx="168" cy="187" r="42"></circle>
                        <circle class="cp-avatar-line" cx="252" cy="187" r="42"></circle>
                        <path class="cp-avatar-line" d="M210 181 C216 176 221 176 225 181"></path>
                        <circle class="cp-avatar-pupil cp-avatar-pupil-left" cx="171" cy="188" r="6"></circle>
                        <circle class="cp-avatar-pupil cp-avatar-pupil-right" cx="249" cy="188" r="6"></circle>
                        <path class="cp-avatar-feature" d="M207 201 C197 213 202 220 212 219"></path>
                        <path class="cp-avatar-feature" d="M185 237 C199 251 222 251 237 236"></path>
                    </g>
                </svg>
            `;
            doc.body.appendChild(host);

            const head = host.querySelector(".cp-avatar-head");
            const leftPupil = host.querySelector(".cp-avatar-pupil-left");
            const rightPupil = host.querySelector(".cp-avatar-pupil-right");
            const shadow = host.querySelector(".cp-avatar-shadow");
            let target = 0;
            let current = 0;

            const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

            const applyTurn = (turn) => {
                head.style.transform = `translateX(${turn * 18}px) rotateY(${turn * 26}deg) rotateZ(${turn * 1.8}deg)`;
                leftPupil.style.transform = `translateX(${turn * 11}px)`;
                rightPupil.style.transform = `translateX(${turn * 11}px)`;
                shadow.style.transform = `translateX(${turn * 4}px) scaleX(${1 - Math.abs(turn) * .12})`;
            };

            const onPointerMove = (event) => {
                target = clamp((event.clientX / Math.max(owner.innerWidth, 1)) * 2 - 1, -1, 1);
                current = target;
                applyTurn(current);
            };

            const onPointerLeave = () => {
                target = 0;
                current = 0;
                applyTurn(0);
            };

            doc.addEventListener("pointermove", onPointerMove, { passive: true });
            doc.documentElement.addEventListener("mouseleave", onPointerLeave);
            owner.addEventListener("blur", onPointerLeave);

            owner.__careerpilotAvatarCleanup = () => {
                doc.removeEventListener("pointermove", onPointerMove);
                doc.documentElement.removeEventListener("mouseleave", onPointerLeave);
                owner.removeEventListener("blur", onPointerLeave);
                host.remove();
                style.remove();
                delete owner.__careerpilotAvatarCleanup;
            };
        })();
        </script>
        """,
        height=0,
        scrolling=False,
    )


st.sidebar.markdown('<div class="lum-sidebar-brand" aria-label="CareerPilot">C.</div>', unsafe_allow_html=True)

page_name = st.sidebar.radio(
    "Main",
    NAV_OPTIONS,
    key="main_nav",
    on_change=sync_navigation_query,
)

# 不再在页面左上角挂载人物头像；同时清理热更新前可能残留的节点和样式。
components.html(
    r"""
    <script>
    (() => {
        try {
            const owner = window.parent;
            const doc = owner.document;
            if (typeof owner.__careerpilotAvatarCleanup === "function") {
                owner.__careerpilotAvatarCleanup();
            }
            doc.getElementById("careerpilot-kinetic-avatar")?.remove();
            doc.getElementById("careerpilot-kinetic-avatar-style")?.remove();
        } catch (error) {
            // 页面可能正在切换，下一次渲染会再次执行清理。
        }
    })();
    </script>
    """,
    height=0,
    scrolling=False,
)

# Final shared sidebar state override: selected card is black with white icon/text.
st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){
        background:#151515!important;color:#fff!important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p,
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) span,
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before{
        color:#fff!important;
    }
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) *{
        color:#fff!important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# 所有页面共用同一份 P1 固定图标栏规则。
render_p1_sidebar_styles()


if page_name == "工作台":
    focus_sidebar_job = jobs[0] if jobs else None
    st.sidebar.markdown(
        f"""
        <div class="lum-sidebar-focus">
            <span class="mini-pill">Active</span>
            <strong>{safe_text(focus_sidebar_job.get('company'), 'Career workspace') if focus_sidebar_job else 'Career workspace'}</strong>
            <span>{safe_text(focus_sidebar_job.get('position'), '添加岗位后开始管理申请') if focus_sidebar_job else '添加岗位后开始管理申请'}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.sidebar.markdown(
    """
    <div class="lum-demo-privacy-note"
         role="note"
         aria-label="lumooi Demo。因网站公开发布，部分个人、企业与项目信息已脱敏、虚拟化或打码。">
        <span aria-hidden="true">🔒</span>
        <strong>DEMO</strong>
        <small>脱敏版</small>
    </div>
    <style>
        .lum-demo-privacy-note{
            position:fixed!important;left:14px!important;bottom:16px!important;
            width:52px!important;height:62px!important;z-index:1000002!important;
            box-sizing:border-box!important;padding:8px 4px!important;
            border:1px solid rgba(40,40,40,.12)!important;border-radius:15px!important;
            background:rgba(255,255,255,.92);backdrop-filter:blur(12px);
            box-shadow:0 8px 24px rgba(30,30,30,.08);pointer-events:none;
            display:flex!important;flex-direction:column!important;
            align-items:center!important;justify-content:center!important;gap:2px!important;
            overflow:hidden!important;white-space:nowrap!important;
        }
        .lum-demo-privacy-note span{
            display:block!important;margin:0!important;font-size:13px!important;
            line-height:15px!important;letter-spacing:0!important;
        }
        .lum-demo-privacy-note strong{
            display:block!important;margin:0!important;color:#383838!important;
            font-size:8px!important;line-height:10px!important;font-weight:850!important;
            letter-spacing:.08em!important;white-space:nowrap!important;
        }
        .lum-demo-privacy-note small{
            display:block!important;margin:0!important;color:#777!important;
            font-size:8px!important;line-height:11px!important;font-weight:650!important;
            letter-spacing:0!important;white-space:nowrap!important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if page_name not in {"产品首页", "职业资产库", "工作台", "职位申请", "简历定制", "面试准备"}:
    st.title("lumooi.")
    st.html(
        """
        <div class="brand-meta">
            <div class="brand-subtitle">
                Your personal career workspace.
            </div>
            <div class="brand-signature">
                Designed &amp; built as a portfolio demonstration
            </div>
        </div>
        """
    )


# =========================================================
# 产品首页与工作台
# =========================================================
if page_name == "产品首页":
    render_product_landing()

elif page_name == "工作台":
    render_lumooi_home(jobs, funnel_counts)


# =========================================================
# 职业资产库
# =========================================================
elif page_name == "职业资产库":
    # 职业资产库只有这一个入口；其他页面继续使用当前版本。
    render_career_asset_library_page(experiences)

# =========================================================
# 职位申请
# =========================================================
elif page_name == "职位申请":
    render_job_application_workspace(
        jobs=jobs,
        status_options=STATUS_OPTIONS,
    )


# =========================================================
# 简历定制
# =========================================================
elif page_name == "简历定制":
    st.markdown(
        """
        <style>
        html,
        body,
        .stApp,
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {
            background: #fffafa !important;
        }
        header[data-testid="stHeader"] {
            background: rgba(255, 250, 250, 0.96) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    render_resume_workspace(jobs)


# =========================================================
# 面试准备
# =========================================================
elif page_name == "面试准备":
    render_interview_workspace(jobs)

# =========================================================
# 全局最终侧边栏覆盖：固定窄栏，不在悬停时改变页面布局
# =========================================================
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Gaegu:wght@400;700&family=Inter:wght@400;500;600;700&display=swap');

        :root {
            --demo-sidebar-collapsed: 80px;
            --demo-sidebar-expanded: 80px;
            --demo-sidebar-border: #eeeeee;
            --demo-sidebar-text: #666666;
            --demo-sidebar-black: #111111;
        }

        /* 侧边栏本体始终保持 80px，避免悬停时挤压主内容。 */
        section[data-testid="stSidebar"] {
            position: fixed !important;
            inset: 0 auto 0 0 !important;
            z-index: 999999 !important;
            display: block !important;
            width: var(--demo-sidebar-collapsed) !important;
            min-width: var(--demo-sidebar-collapsed) !important;
            max-width: var(--demo-sidebar-collapsed) !important;
            height: 100dvh !important;
            overflow: hidden !important;
            background: #ffffff !important;
            border-right: 1px solid var(--demo-sidebar-border) !important;
            box-shadow: none !important;
            transition:
                width .26s cubic-bezier(.2,.8,.2,1),
                min-width .26s cubic-bezier(.2,.8,.2,1),
                max-width .26s cubic-bezier(.2,.8,.2,1),
                box-shadow .22s ease !important;
        }

        section[data-testid="stSidebar"]:hover,
        section[data-testid="stSidebar"]:focus-within {
            width: var(--demo-sidebar-expanded) !important;
            min-width: var(--demo-sidebar-expanded) !important;
            max-width: var(--demo-sidebar-expanded) !important;
            background: #ffffff !important;
            border-right-color: var(--demo-sidebar-border) !important;
            box-shadow: 18px 0 38px rgba(0,0,0,.055) !important;
        }

        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            width: 100% !important;
            min-width: var(--demo-sidebar-collapsed) !important;
            max-width: none !important;
            height: 100% !important;
            overflow: hidden !important;
            background: #ffffff !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding: 32px 24px !important;
        }

        /* Logo：与 Demo 一致使用 Gaegu */
        section[data-testid="stSidebar"] .lum-sidebar-brand {
            width: 232px !important;
            height: auto !important;
            min-height: 34px !important;
            margin: 0 0 42px !important;
            padding: 0 !important;
            color: var(--demo-sidebar-black) !important;
            font-family: "Gaegu", "Comic Sans MS", cursive !important;
            font-size: 28px !important;
            line-height: 1 !important;
            font-weight: 700 !important;
            letter-spacing: 0 !important;
            white-space: nowrap !important;
        }

        section[data-testid="stSidebar"]:not(:hover):not(:focus-within) .lum-sidebar-brand {
            width: 24px !important;
            margin-left: 0 !important;
            margin-bottom: 42px !important;
            padding: 0 !important;
            overflow: hidden !important;
            font-size: 0 !important;
        }

        section[data-testid="stSidebar"]:not(:hover):not(:focus-within) .lum-sidebar-brand::after {
            content: "l.";
            display: block;
            color: var(--demo-sidebar-black);
            font-family: "Gaegu", "Comic Sans MS", cursive;
            font-size: 28px;
            line-height: 1;
            font-weight: 700;
        }

        /* MAIN 标题 */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
            display: block !important;
            width: 232px !important;
            margin: 0 0 16px !important;
            padding: 0 0 0 12px !important;
            color: #aaaaaa !important;
            font-family: "Inter", sans-serif !important;
            font-size: 11px !important;
            line-height: 1.2 !important;
            font-weight: 700 !important;
            letter-spacing: .10em !important;
            text-transform: uppercase !important;
            white-space: nowrap !important;
            opacity: 1 !important;
        }

        section[data-testid="stSidebar"]:not(:hover):not(:focus-within)
        div[data-testid="stRadio"] > label {
            opacity: 0 !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] {
            width: 232px !important;
            display: flex !important;
            flex-direction: column !important;
            gap: 4px !important;
        }

        /* 隐藏 Streamlit 原生 radio 圆点 */
        section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
        section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            margin: 0 !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }

        /* 导航卡片：Demo 的 12px 圆角、14px Inter */
        section[data-testid="stSidebar"] div[role="radiogroup"] label {
            position: relative !important;
            display: flex !important;
            align-items: center !important;
            width: 232px !important;
            min-height: 44px !important;
            margin: 0 !important;
            padding: 12px 12px 12px 44px !important;
            overflow: hidden !important;
            border: 0 !important;
            border-radius: 12px !important;
            background: transparent !important;
            color: var(--demo-sidebar-text) !important;
            transition:
                background .18s ease,
                color .18s ease,
                transform .18s ease !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            background: #f5f5f5 !important;
            color: var(--demo-sidebar-black) !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background: var(--demo-sidebar-black) !important;
            color: #ffffff !important;
            border: 0 !important;
            border-left: 0 !important;
        }

        /* 删除旧版本额外的小圆点 */
        section[data-testid="stSidebar"] div[role="radiogroup"] label::after {
            content: none !important;
            display: none !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label p,
        section[data-testid="stSidebar"] div[role="radiogroup"] label span {
            margin: 0 !important;
            color: inherit !important;
            font-family: "Inter", "Noto Sans SC", "PingFang SC", sans-serif !important;
            font-size: 14px !important;
            line-height: 1.35 !important;
            font-weight: 500 !important;
            letter-spacing: 0 !important;
            text-transform: none !important;
            white-space: nowrap !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p,
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) span,
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked)::before,
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) * {
            color: #ffffff !important;
        }

        section[data-testid="stSidebar"]:not(:hover):not(:focus-within)
        div[role="radiogroup"] label {
            width: 24px !important;
            min-width: 24px !important;
            height: 44px !important;
            min-height: 44px !important;
            padding: 0 !important;
            border-radius: 12px !important;
        }

        section[data-testid="stSidebar"]:not(:hover):not(:focus-within)
        div[role="radiogroup"] label::before {
            left: 3px !important;
        }

        section[data-testid="stSidebar"]:not(:hover):not(:focus-within)
        div[role="radiogroup"] label p,
        section[data-testid="stSidebar"]:not(:hover):not(:focus-within)
        div[role="radiogroup"] label span {
            opacity: 0 !important;
            width: 0 !important;
            overflow: hidden !important;
        }

        /* 底部状态卡：复刻 Demo 的 strategy module */
        section[data-testid="stSidebar"] .lum-sidebar-focus {
            position: absolute !important;
            left: 24px !important;
            right: auto !important;
            bottom: 24px !important;
            width: 232px !important;
            margin: 0 !important;
            padding: 16px !important;
            border: 1px solid var(--demo-sidebar-border) !important;
            border-radius: 16px !important;
            background: #fcfcfc !important;
            box-shadow: none !important;
            opacity: 0 !important;
            transform: translateY(8px) !important;
            pointer-events: none !important;
            transition: opacity .16s ease .05s, transform .18s ease .05s !important;
        }

        section[data-testid="stSidebar"]:hover .lum-sidebar-focus,
        section[data-testid="stSidebar"]:focus-within .lum-sidebar-focus {
            opacity: 1 !important;
            transform: translateY(0) !important;
        }

        section[data-testid="stSidebar"] .lum-sidebar-focus .mini-pill {
            display: inline-flex !important;
            padding: 3px 8px !important;
            border-radius: 999px !important;
            background: #e0f2fe !important;
            color: #111111 !important;
            font-family: "Inter", sans-serif !important;
            font-size: 10px !important;
            line-height: 1.2 !important;
            font-weight: 600 !important;
        }

        section[data-testid="stSidebar"] .lum-sidebar-focus strong {
            display: block !important;
            margin-top: 10px !important;
            color: #111111 !important;
            font-family: "Inter", "Noto Sans SC", sans-serif !important;
            font-size: 13px !important;
            line-height: 1.4 !important;
            font-weight: 600 !important;
        }

        section[data-testid="stSidebar"] .lum-sidebar-focus span:last-child {
            display: block !important;
            margin-top: 4px !important;
            color: #888888 !important;
            font-family: "Inter", "Noto Sans SC", sans-serif !important;
            font-size: 11px !important;
            line-height: 1.45 !important;
            font-weight: 400 !important;
        }

        /* 主页面仍从收起栏右侧开始；展开时同步让出空间 */
        [data-testid="stMain"] {
            margin-left: var(--demo-sidebar-collapsed) !important;
            width: calc(100% - var(--demo-sidebar-collapsed)) !important;
            transition:
                margin-left .26s cubic-bezier(.2,.8,.2,1),
                width .26s cubic-bezier(.2,.8,.2,1) !important;
        }

        .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"],
        .stApp:has(section[data-testid="stSidebar"]:focus-within) [data-testid="stMain"] {
            margin-left: var(--demo-sidebar-expanded) !important;
            width: calc(100% - var(--demo-sidebar-expanded)) !important;
        }

            @media (max-width: 820px) {
                :root {
                    --demo-sidebar-collapsed: 80px;
                    --demo-sidebar-expanded: 80px;
                }

            section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
                padding-left: 20px !important;
                padding-right: 20px !important;
            }

            .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"],
            .stApp:has(section[data-testid="stSidebar"]:focus-within) [data-testid="stMain"] {
                margin-left: var(--demo-sidebar-collapsed) !important;
                width: calc(100% - var(--demo-sidebar-collapsed)) !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# Sidebar bugfix：底部 Active 卡固定在视口底部，避免覆盖导航
# =========================================================
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] .lum-sidebar-focus {
            position: fixed !important;
            top: auto !important;
            left: 24px !important;
            right: auto !important;
            bottom: 24px !important;
            z-index: 1000000 !important;
            width: 232px !important;
            max-width: 232px !important;
            min-height: 0 !important;
            max-height: 150px !important;
            overflow: hidden !important;
            box-sizing: border-box !important;
        }

        section[data-testid="stSidebar"]:not(:hover):not(:focus-within)
        .lum-sidebar-focus {
            visibility: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }

        section[data-testid="stSidebar"]:hover .lum-sidebar-focus,
        section[data-testid="stSidebar"]:focus-within .lum-sidebar-focus {
            visibility: visible !important;
            opacity: 1 !important;
            pointer-events: auto !important;
        }

        /* 为导航区保留底部空间，避免低高度窗口中与状态卡相撞 */
        section[data-testid="stSidebar"] div[data-testid="stRadio"] {
            padding-bottom: 172px !important;
        }

        @media (max-height: 620px) {
            section[data-testid="stSidebar"] .lum-sidebar-focus {
                display: none !important;
            }

            section[data-testid="stSidebar"] div[data-testid="stRadio"] {
                padding-bottom: 0 !important;
            }
        }

        @media (max-width: 820px) {
            section[data-testid="stSidebar"] .lum-sidebar-focus {
                left: 20px !important;
                width: 220px !important;
                max-width: 220px !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# Sidebar visibility safeguard：仅保留 Streamlit 原有圆形状态标识
# =========================================================
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] {
            visibility: visible !important;
            opacity: 1 !important;
            transform: none !important;
        }

        /* 移除每个导航项前的线性图标。 */
        section[data-testid="stSidebar"] div[role="radiogroup"] label::before,
        section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(n)::before {
            content: none !important;
            display: none !important;
        }

        /* 不再额外绘制圆点，避免与 Streamlit 原有状态标识重复。 */
        section[data-testid="stSidebar"] div[role="radiogroup"] label::after {
            content: none !important;
            display: none !important;
        }

        section[data-testid="stSidebar"]:hover,
        section[data-testid="stSidebar"]:focus-within {
            visibility: visible !important;
            opacity: 1 !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)
# =========================================================
# Kinetic fixed icon rail: visual-only override.
# The existing Streamlit radio continues to own navigation and query syncing.
# =========================================================
st.markdown(
    r"""
    <style>
        :root {
            --kinetic-sidebar-width: 80px;
            --kinetic-sidebar-border: #f1f1f1;
            --kinetic-sidebar-ink: #111111;
            --kinetic-sidebar-muted: #888888;
            --kinetic-sidebar-active: #f0f0f0;
        }

        section[data-testid="stSidebar"],
        section[data-testid="stSidebar"]:hover,
        section[data-testid="stSidebar"]:focus-within {
            position: fixed !important;
            inset: 0 auto 0 0 !important;
            z-index: 999999 !important;
            display: block !important;
            width: var(--kinetic-sidebar-width) !important;
            min-width: var(--kinetic-sidebar-width) !important;
            max-width: var(--kinetic-sidebar-width) !important;
            height: 100dvh !important;
            overflow: hidden !important;
            visibility: visible !important;
            opacity: 1 !important;
            transform: none !important;
            background: #ffffff !important;
            border-right: 1px solid var(--kinetic-sidebar-border) !important;
            box-shadow: none !important;
            transition: none !important;
        }

        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            width: var(--kinetic-sidebar-width) !important;
            min-width: var(--kinetic-sidebar-width) !important;
            max-width: var(--kinetic-sidebar-width) !important;
            height: 100% !important;
            overflow: hidden !important;
            background: #ffffff !important;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding: 24px 16px !important;
        }

        section[data-testid="stSidebar"] .lum-sidebar-brand,
        section[data-testid="stSidebar"]:not(:hover):not(:focus-within) .lum-sidebar-brand {
            display: block !important;
            width: 48px !important;
            min-width: 48px !important;
            height: 32px !important;
            min-height: 32px !important;
            margin: 0 0 40px !important;
            padding: 0 !important;
            overflow: visible !important;
            color: var(--kinetic-sidebar-ink) !important;
            font-family: "Gaegu", "Comic Sans MS", cursive !important;
            font-size: 32px !important;
            line-height: 32px !important;
            font-weight: 700 !important;
            letter-spacing: 0 !important;
            text-align: center !important;
            white-space: nowrap !important;
        }

        section[data-testid="stSidebar"] .lum-sidebar-brand::after {
            content: none !important;
            display: none !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stRadio"] {
            width: 48px !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        section[data-testid="stSidebar"] div[data-testid="stRadio"] > label {
            display: none !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] {
            display: flex !important;
            flex-direction: column !important;
            width: 48px !important;
            gap: 20px !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label,
        section[data-testid="stSidebar"]:not(:hover):not(:focus-within) div[role="radiogroup"] label {
            position: relative !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            width: 48px !important;
            min-width: 48px !important;
            max-width: 48px !important;
            height: 48px !important;
            min-height: 48px !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            border: 0 !important;
            border-radius: 14px !important;
            background: transparent !important;
            color: var(--kinetic-sidebar-muted) !important;
            cursor: pointer !important;
            transition: background-color .2s ease, color .2s ease, transform .2s ease !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover,
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
            background: var(--kinetic-sidebar-active) !important;
            color: var(--kinetic-sidebar-ink) !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {
            transform: translateY(-1px) !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"],
        section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child,
        section[data-testid="stSidebar"] div[role="radiogroup"] label p,
        section[data-testid="stSidebar"] div[role="radiogroup"] label span {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            margin: 0 !important;
            padding: 0 !important;
            overflow: hidden !important;
            clip: rect(0 0 0 0) !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label::after {
            content: "" !important;
            position: static !important;
            display: block !important;
            width: 20px !important;
            height: 20px !important;
            border: 0 !important;
            border-radius: 0 !important;
            background-color: currentColor !important;
            -webkit-mask-position: center !important;
            mask-position: center !important;
            -webkit-mask-repeat: no-repeat !important;
            mask-repeat: no-repeat !important;
            -webkit-mask-size: 20px 20px !important;
            mask-size: 20px 20px !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(1)::after {
            -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5'%3E%3Crect x='3' y='3' width='7' height='7'/%3E%3Crect x='14' y='3' width='7' height='7'/%3E%3Crect x='14' y='14' width='7' height='7'/%3E%3Crect x='3' y='14' width='7' height='7'/%3E%3C/svg%3E") !important;
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5'%3E%3Crect x='3' y='3' width='7' height='7'/%3E%3Crect x='14' y='3' width='7' height='7'/%3E%3Crect x='14' y='14' width='7' height='7'/%3E%3Crect x='3' y='14' width='7' height='7'/%3E%3C/svg%3E") !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(2)::after {
            -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 4h7l2 2h9v14H3z'/%3E%3C/svg%3E") !important;
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M3 4h7l2 2h9v14H3z'/%3E%3C/svg%3E") !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(3)::after {
            -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round'%3E%3Crect x='3' y='7' width='18' height='13' rx='2'/%3E%3Cpath d='M9 7V4h6v3M3 12h18'/%3E%3C/svg%3E") !important;
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round'%3E%3Crect x='3' y='7' width='18' height='13' rx='2'/%3E%3Cpath d='M9 7V4h6v3M3 12h18'/%3E%3C/svg%3E") !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(4)::after {
            -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round'%3E%3Cpath d='M6 3h9l3 3v15H6zM15 3v4h4M9 12h6M9 16h6'/%3E%3C/svg%3E") !important;
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round'%3E%3Cpath d='M6 3h9l3 3v15H6zM15 3v4h4M9 12h6M9 16h6'/%3E%3C/svg%3E") !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(5)::after {
            -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/%3E%3C/svg%3E") !important;
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z'/%3E%3C/svg%3E") !important;
        }

        section[data-testid="stSidebar"] .lum-sidebar-focus {
            display: none !important;
        }

        [data-testid="stMain"],
        .stApp:has(section[data-testid="stSidebar"]:hover) [data-testid="stMain"],
        .stApp:has(section[data-testid="stSidebar"]:focus-within) [data-testid="stMain"] {
            margin-left: var(--kinetic-sidebar-width) !important;
            width: calc(100% - var(--kinetic-sidebar-width)) !important;
            transition: none !important;
        }

        @media (max-width: 820px) {
            :root { --kinetic-sidebar-width: 80px; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Streamlit 1.59 radio/header DOM normalization for the fixed icon rail.
st.markdown(
    """
    <style>
        section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
            display: none !important;
        }

        section[data-testid="stSidebar"] div[role="radiogroup"] label > div {
            position: absolute !important;
            width: 1px !important;
            height: 1px !important;
            overflow: hidden !important;
            opacity: 0 !important;
            pointer-events: none !important;
        }

        html body .stApp section[data-testid="stSidebar"] div[role="radiogroup"] label[data-selected="true"],
        html body .stApp section[data-testid="stSidebar"]:not(:hover):not(:focus-within)
        div[role="radiogroup"] label[data-selected="true"] {
            background: var(--kinetic-sidebar-active) !important;
            color: var(--kinetic-sidebar-ink) !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 正式产品界面不显示 Streamlit 的 Deploy、开发菜单或状态工具。
st.markdown(
    """
    <style>
        header[data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stMainMenu"],
        [data-testid="stAppDeployButton"],
        [data-testid="stStatusWidget"],
        [data-testid="stDecoration"],
        #MainMenu {
            display: none !important;
            visibility: hidden !important;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# 简历编辑器与面试工作台内容都会超过一屏。这里在所有页面与主题样式
# 之后恢复唯一纵向滚动容器，避免全屏页面规则把浏览器滚动链断开。
if page_name in {"简历定制", "面试准备"}:
    st.markdown(
        """
        <style>
            html,
            body,
            #root,
            .stApp {
                height: 100% !important;
                max-height: 100% !important;
                overflow: hidden !important;
            }

            [data-testid="stAppViewContainer"] {
                height: 100dvh !important;
                min-height: 100dvh !important;
                max-height: 100dvh !important;
                overflow-x: hidden !important;
                overflow-y: auto !important;
                overscroll-behavior-y: contain;
                -webkit-overflow-scrolling: touch;
            }

            [data-testid="stMain"],
            [data-testid="stMainBlockContainer"],
            .block-container,
            [data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] {
                height: auto !important;
                max-height: none !important;
                overflow: visible !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

# All pages, including the career asset library, finish with the exact same
# sidebar rules. Page modules must not own or override navigation chrome.
render_p1_sidebar_styles()

# 全站自定义鼠标：黑色箭头、白色描边和柔和阴影。
# 图案直接嵌入样式，部署时不依赖额外的静态文件。
st.markdown(
    """
    <style>
        html,
        body,
        body * {
            cursor: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMiIgaGVpZ2h0PSIyMiIgdmlld0JveD0iMCAwIDM2IDM2Ij4KICA8ZGVmcz4KICAgIDxmaWx0ZXIgaWQ9InNoYWRvdyIgeD0iLTUwJSIgeT0iLTUwJSIgd2lkdGg9IjIwMCUiIGhlaWdodD0iMjAwJSI+CiAgICAgIDxmZURyb3BTaGFkb3cgZHg9IjAiIGR5PSIyIiBzdGREZXZpYXRpb249IjIuMiIgZmxvb2QtY29sb3I9IiMwMDAiIGZsb29kLW9wYWNpdHk9Ii4yOCIvPgogICAgPC9maWx0ZXI+CiAgPC9kZWZzPgogIDxwYXRoCiAgICBkPSJNMy42IDIuOCAzMC44IDEzYzEuOC43IDEuOCAzLjItLjEgMy44bC0xMC45IDMuNS00LjYgMTAuMmMtLjggMS44LTMuNCAxLjYtMy45LS4zTDEgNS40Yy0uNi0xLjguOS0zLjMgMi42LTIuNloiCiAgICBmaWxsPSIjMTcxNzE3IgogICAgc3Ryb2tlPSIjZmZmIgogICAgc3Ryb2tlLXdpZHRoPSIzLjIiCiAgICBzdHJva2UtbGluZWpvaW49InJvdW5kIgogICAgZmlsdGVyPSJ1cmwoI3NoYWRvdykiCiAgLz4KPC9zdmc+Cg==") 2 2, auto !important;
        }

        a:active,
        button:active,
        [role="button"]:active,
        input[type="button"]:active,
        input[type="submit"]:active,
        input[type="reset"]:active {
            cursor: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMCIgaGVpZ2h0PSIyMCIgdmlld0JveD0iMCAwIDM2IDM2Ij4KICA8ZGVmcz4KICAgIDxmaWx0ZXIgaWQ9InNoYWRvdyIgeD0iLTUwJSIgeT0iLTUwJSIgd2lkdGg9IjIwMCUiIGhlaWdodD0iMjAwJSI+CiAgICAgIDxmZURyb3BTaGFkb3cgZHg9IjAiIGR5PSIxLjUiIHN0ZERldmlhdGlvbj0iMS43IiBmbG9vZC1jb2xvcj0iIzAwMCIgZmxvb2Qtb3BhY2l0eT0iLjMiLz4KICAgIDwvZmlsdGVyPgogIDwvZGVmcz4KICA8cGF0aAogICAgZD0iTTMuNiAyLjggMzAuOCAxM2MxLjguNyAxLjggMy4yLS4xIDMuOGwtMTAuOSAzLjUtNC42IDEwLjJjLS44IDEuOC0zLjQgMS42LTMuOS0uM0wxIDUuNGMtLjYtMS44LjktMy4zIDIuNi0yLjZaIgogICAgZmlsbD0iIzRhNGE0YSIKICAgIHN0cm9rZT0iI2ZmZiIKICAgIHN0cm9rZS13aWR0aD0iMy4yIgogICAgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIKICAgIGZpbHRlcj0idXJsKCNzaGFkb3cpIgogIC8+Cjwvc3ZnPgo=") 2 2, pointer !important;
        }

        input:not([type]),
        input[type="text"],
        input[type="email"],
        input[type="password"],
        input[type="search"],
        input[type="tel"],
        input[type="url"],
        input[type="number"],
        textarea,
        [contenteditable="true"] {
            cursor: text !important;
        }

        @media (pointer: coarse) {
            html,
            body,
            body * {
                cursor: auto !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)
