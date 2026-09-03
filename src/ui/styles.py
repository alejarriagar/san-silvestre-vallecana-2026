"""Estilos visuales globales de la aplicación."""

from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    """Aplica el sistema visual oscuro de la aplicación."""
    st.markdown(
        """
        <style>
            :root {
                --app-background: #0B0C0E;
                --surface: #18191D;
                --surface-elevated: #222328;
                --border: #303239;
                --text-primary: #F4F5F2;
                --text-secondary: #A8AAA5;
                --accent: #C9F05A;
                --accent-dark: #152000;
                --success: #8EDB9C;
                --warning: #F0C76B;
                --danger: #F28585;
            }

            [data-testid="stAppViewContainer"] {
                background: var(--app-background);
            }

            [data-testid="stHeader"] {
                background: var(--app-background);
            }

            [data-testid="stSidebar"] {
                background: #111216;
                border-right: 1px solid var(--border);
            }

            [data-testid="stSidebar"] section {
                padding-top: 2rem;
            }

            [data-testid="stSidebar"] label,
            [data-testid="stSidebar"] p {
                color: var(--text-secondary);
            }

            h1,
            h2,
            h3 {
                color: var(--text-primary);
                letter-spacing: -0.025em;
            }

            h1 {
                font-size: 2.1rem;
                font-weight: 750;
            }

            h2 {
                font-size: 1.35rem;
                font-weight: 700;
            }

            h3 {
                font-size: 1.05rem;
                font-weight: 700;
            }

            p,
            li,
            label {
                color: var(--text-primary);
            }

            [data-testid="stMetric"] {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 14px 16px;
            }

            [data-testid="stMetricLabel"] {
                color: var(--text-secondary);
            }

            [data-testid="stMetricValue"] {
                color: var(--text-primary);
                font-weight: 750;
            }

            .stButton > button {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 999px;
                color: var(--text-primary);
                font-weight: 650;
                min-height: 2.35rem;
                transition: border-color 120ms ease,
                            background 120ms ease,
                            transform 120ms ease;
            }

            .stButton > button:hover {
                background: var(--surface-elevated);
                border-color: var(--accent);
                color: var(--text-primary);
                transform: translateY(-1px);
            }

            button[data-testid="stBaseButton-primary"] {
                background: var(--accent);
                border-color: var(--accent);
                color: #111508;
            }

            button[data-testid="stBaseButton-primary"]:hover {
                background: #D8F879;
                border-color: #D8F879;
                color: #111508;
            }

            [data-testid="stTextInput"] input,
            [data-testid="stNumberInput"] input,
            [data-testid="stTextArea"] textarea {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 10px;
                color: var(--text-primary);
            }

            [data-baseweb="select"] > div {
                background: var(--surface);
                border-color: var(--border);
                border-radius: 10px;
            }

            [data-testid="stExpander"] {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 14px;
            }

            [data-testid="stTabs"] [role="tab"] {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 999px;
                color: var(--text-secondary);
                margin-right: 6px;
                padding: 7px 16px;
            }

            [data-testid="stTabs"] [aria-selected="true"] {
                background: var(--accent);
                color: #111508;
            }

            [data-testid="stProgressBar"] > div > div > div > div {
                background: var(--accent);
            }

            .calendar-session {
                background: var(--surface);
                border: 1px solid var(--border);
                border-left: 3px solid var(--accent);
                border-radius: 9px;
                color: var(--text-primary);
                font-size: 0.74rem;
                line-height: 1.25;
                margin: 5px 0;
                padding: 8px;
            }

            .calendar-session.completed {
                border-left-color: var(--success);
            }

            .calendar-session.modified {
                border-left-color: var(--warning);
            }

            .calendar-session.cancelled {
                border-left-color: var(--danger);
                opacity: 0.65;
            }

            .planner-detail {
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 16px;
                color: var(--text-primary);
                padding: 20px;
            }

            .planner-detail h3 {
                margin-top: 0;
            }

            .status-badge {
                border-radius: 999px;
                display: inline-block;
                font-size: 0.75rem;
                font-weight: 750;
                margin-bottom: 12px;
                padding: 5px 11px;
            }

            .status-pending {
                background: #3D371D;
                color: var(--warning);
            }

            .status-completed {
                background: #193422;
                color: var(--success);
            }

            .status-modified {
                background: #40341D;
                color: var(--warning);
            }

            .status-cancelled {
                background: #422323;
                color: var(--danger);
            }

            .section-caption {
                color: var(--text-secondary);
                font-size: 0.88rem;
            }

            [data-testid="stDataFrame"] {
                border: 1px solid var(--border);
                border-radius: 12px;
                overflow: hidden;
            }

            [data-testid="stAlert"] {
                border-radius: 12px;
            }

            hr {
                border-color: var(--border);
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
