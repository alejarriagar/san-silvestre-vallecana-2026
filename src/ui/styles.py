"""Estilos globales de la aplicación Streamlit."""

from __future__ import annotations

import streamlit as st


def apply_global_styles() -> None:
    """Aplica estilos visuales compartidos en todas las pantallas."""
    st.markdown(
        """
        <style>
            [data-testid="stAppViewContainer"] {
                background: #F7F8F5;
            }

            [data-testid="stSidebar"] {
                background: #FFFFFF;
                border-right: 1px solid #E3E8E3;
            }

            [data-testid="stSidebar"] h1,
            [data-testid="stSidebar"] h2,
            [data-testid="stSidebar"] h3 {
                color: #123526;
            }

            h1, h2, h3 {
                color: #17211C;
                letter-spacing: -0.02em;
            }

            [data-testid="stMetric"] {
                background: #FFFFFF;
                border: 1px solid #E3E8E3;
                border-radius: 14px;
                padding: 14px;
            }

            .stButton > button {
                border-radius: 10px;
                border: 1px solid #D9E1DA;
                font-weight: 600;
            }

            button[data-testid="stBaseButton-primary"] {
                background-color: #123526;
                border-color: #123526;
                color: #FFFFFF;
            }

            button[data-testid="stBaseButton-primary"]:hover {
                background-color: #1D5139;
                border-color: #1D5139;
            }

            .calendar-session {
                background: #FFFFFF;
                border: 1px solid #E0E7E1;
                border-left: 4px solid #123526;
                border-radius: 8px;
                color: #17211C;
                font-size: 0.76rem;
                line-height: 1.25;
                margin: 5px 0;
                padding: 7px;
            }

            .calendar-session.cancelled {
                border-left-color: #B54040;
                color: #7A3535;
                opacity: 0.72;
            }

            .calendar-session.completed {
                border-left-color: #2D8A57;
            }

            .calendar-session.modified {
                border-left-color: #B7771C;
            }

            .planner-detail {
                background: #FFFFFF;
                border: 1px solid #E0E7E1;
                border-radius: 16px;
                color: #17211C;
                padding: 20px;
            }

            .planner-detail h3 {
                margin-top: 0;
            }

            .status-badge {
                border-radius: 999px;
                display: inline-block;
                font-size: 0.78rem;
                font-weight: 700;
                margin-bottom: 12px;
                padding: 5px 10px;
            }

            .status-pending {
                background: #FFF3CD;
                color: #765900;
            }

            .status-completed {
                background: #DCF4E5;
                color: #1D6A40;
            }

            .status-modified {
                background: #FCE7C1;
                color: #85570B;
            }

            .status-cancelled {
                background: #F9DCDC;
                color: #8A3030;
            }

            .section-caption {
                color: #657067;
                font-size: 0.9rem;
            }

            [data-testid="stDataFrame"] {
                border: 1px solid #E3E8E3;
                border-radius: 12px;
                overflow: hidden;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
