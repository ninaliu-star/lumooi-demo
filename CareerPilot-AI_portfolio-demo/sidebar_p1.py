"""所有页面共用的 P1 固定窄栏样式。"""

import streamlit as st


def render_p1_sidebar_styles():
    """应用 P1：80px 固定图标栏，不随悬停展开。"""
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
                position: relative !important;
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
                position: fixed !important;
                top: 100px !important;
                left: 16px !important;
                z-index: 1000000 !important;
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

            /* Remove the older icon layer. Only the ::after mask above is kept. */
            html body .stApp section[data-testid="stSidebar"]
            div[role="radiogroup"] label::before,
            html body .stApp section[data-testid="stSidebar"]
            div[role="radiogroup"] label:nth-child(n)::before {
                content: none !important;
                display: none !important;
                width: 0 !important;
                height: 0 !important;
                background: none !important;
                -webkit-mask-image: none !important;
                mask-image: none !important;
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

            section[data-testid="stSidebar"] div[role="radiogroup"] label:nth-child(6)::after {
                -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='9'/%3E%3Cpath d='M12 7v5l3 2'/%3E%3C/svg%3E") !important;
                mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='black' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='9'/%3E%3Cpath d='M12 7v5l3 2'/%3E%3C/svg%3E") !important;
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
