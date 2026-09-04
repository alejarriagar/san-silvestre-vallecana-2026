"""Sistema visual global: tema oscuro tipo 'Intelligence Console'.

Paleta y tipografía inspiradas en un panel de inteligencia operativa:
canvas casi negro, acentos cian/violeta, tipografía Space Grotesk + Inter
y tarjetas de resultado con rango, etiquetas de estado y metadatos.
"""

from __future__ import annotations

import plotly.io as pio
import streamlit as st

CANVAS = "#05070d"
SURFACE = "#0c1220"
SURFACE_GLASS = "rgba(15,21,36,.72)"
CYAN = "#22e5ff"
VIOLET = "#8a5cff"
TEXT_PRIMARY = "#eef2fb"
TEXT_MUTED = "#8b93ac"
BORDER = "rgba(0,229,255,.14)"
BORDER_STRONG = "rgba(0,229,255,.40)"
SUCCESS = "#33e0a1"
WARNING = "#ffb547"
DANGER = "#ff5d7d"


def apply_global_styles() -> None:
    """Aplica el sistema visual oscuro con acentos cian y violeta."""
    st.markdown(
        f"""
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link
            href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap"
            rel="stylesheet"
        >
        <style>
            :root {{
                --canvas: {CANVAS};
                --surface: {SURFACE};
                --surface-glass: {SURFACE_GLASS};
                --cyan: {CYAN};
                --violet: {VIOLET};
                --text-primary: {TEXT_PRIMARY};
                --text-muted: {TEXT_MUTED};
                --border: {BORDER};
                --border-strong: {BORDER_STRONG};
                --success: {SUCCESS};
                --warning: {WARNING};
                --danger: {DANGER};
            }}

            html, body, [class*="css"] {{
                font-family: "Inter", sans-serif;
            }}

            [data-testid="stAppViewContainer"] {{
                background-color: var(--canvas);
                background-image:
                    radial-gradient(
                        900px circle at 15% -10%,
                        rgba(34, 229, 255, 0.16),
                        transparent 60%
                    ),
                    radial-gradient(
                        800px circle at 100% 0%,
                        rgba(138, 92, 255, 0.14),
                        transparent 55%
                    ),
                    linear-gradient(
                        rgba(255, 255, 255, 0.035) 1px,
                        transparent 1px
                    ),
                    linear-gradient(
                        90deg,
                        rgba(255, 255, 255, 0.035) 1px,
                        transparent 1px
                    );
                background-size: auto, auto, 42px 42px, 42px 42px;
                background-attachment: fixed;
                background-position: 0 0, 0 0, 0 0, 0 0;
            }}

            [data-testid="stHeader"] {{
                background: transparent;
            }}

            [data-testid="stSidebar"] {{
                background: #070a12;
                border-right: 1px solid var(--border);
            }}

            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] label {{
                color: var(--text-muted);
            }}

            h1, h2, h3 {{
                font-family: "Space Grotesk", "Inter", sans-serif;
                color: var(--text-primary);
                letter-spacing: -0.02em;
            }}

            h1 {{ font-size: 2.05rem; font-weight: 700; }}
            h2 {{ font-size: 1.3rem; font-weight: 650; }}
            h3 {{ font-size: 1.05rem; font-weight: 650; }}

            p, li, span, label {{
                color: var(--text-primary);
            }}

            .qi-eyebrow {{
                color: var(--cyan);
                font-size: 0.78rem;
                font-weight: 700;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin-bottom: 4px;
            }}

            .qi-subtitle {{
                color: var(--text-muted);
                font-size: 0.95rem;
                margin-top: -8px;
            }}

            [data-testid="stMetric"] {{
                background: var(--surface-glass);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 14px 16px;
                transition: border-color 150ms ease;
            }}

            [data-testid="stMetric"]:hover {{
                border-color: var(--border-strong);
            }}

            [data-testid="stMetricLabel"] {{
                color: var(--text-muted);
            }}

            [data-testid="stMetricValue"] {{
                color: var(--text-primary);
                font-family: "Space Grotesk", sans-serif;
                font-weight: 700;
            }}

            .stButton > button {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 10px;
                color: var(--text-primary);
                font-weight: 600;
                transition: border-color 150ms ease, transform 120ms ease;
            }}

            .stButton > button:hover {{
                border-color: var(--border-strong);
                color: var(--cyan);
                transform: translateY(-1px);
            }}

            button[data-testid="stBaseButton-primary"] {{
                background: linear-gradient(90deg, var(--cyan), var(--violet));
                border: none;
                color: #05070d;
                font-weight: 700;
            }}

            button[data-testid="stBaseButton-primary"]:hover {{
                filter: brightness(1.08);
                color: #05070d;
            }}

            [data-testid="stTextInput"] input,
            [data-testid="stNumberInput"] input,
            [data-testid="stTextArea"] textarea {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 10px;
                color: var(--text-primary);
            }}

            [data-testid="stTextInput"] input:focus,
            [data-testid="stTextArea"] textarea:focus {{
                border-color: var(--border-strong);
                box-shadow: 0 0 0 1px var(--border-strong);
            }}

            [data-baseweb="select"] > div {{
                background: var(--surface);
                border-color: var(--border);
                border-radius: 10px;
            }}

            [data-testid="stExpander"] {{
                background: var(--surface-glass);
                border: 1px solid var(--border);
                border-radius: 12px;
            }}

            [data-testid="stTabs"] [role="tab"] {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-radius: 999px;
                color: var(--text-muted);
                margin-right: 6px;
                padding: 6px 15px;
            }}

            [data-testid="stTabs"] [aria-selected="true"] {{
                background: var(--cyan);
                border-color: var(--cyan);
                color: #05070d;
            }}

            [data-testid="stProgressBar"] > div > div > div > div {{
                background: linear-gradient(90deg, var(--cyan), var(--violet));
            }}

            [data-testid="stDataFrame"] {{
                border: 1px solid var(--border);
                border-radius: 12px;
                overflow: hidden;
            }}

            [data-testid="stAlert"] {{
                border-radius: 10px;
            }}

            hr {{
                border-color: var(--border);
            }}

            /* Tarjetas de resultado tipo "intelligence console" */
            .qi-card {{
                background: var(--surface-glass);
                border: 1px solid var(--border);
                border-radius: 12px;
                margin-bottom: 10px;
                padding: 16px 18px;
                transition: border-color 150ms ease;
            }}

            .qi-card:hover {{
                border-color: var(--border-strong);
            }}

            .qi-card-header {{
                align-items: flex-start;
                display: flex;
                gap: 12px;
                justify-content: space-between;
            }}

            .qi-rank {{
                color: var(--cyan);
                font-family: "Space Grotesk", sans-serif;
                font-size: 0.82rem;
                font-weight: 700;
                margin-right: 8px;
            }}

            .qi-card-title {{
                color: var(--text-primary);
                font-family: "Space Grotesk", sans-serif;
                font-size: 1.05rem;
                font-weight: 650;
            }}

            .qi-card-subtitle {{
                color: var(--text-muted);
                font-size: 0.82rem;
                margin-top: 2px;
            }}

            .qi-match {{
                background: rgba(34, 229, 255, 0.10);
                border: 1px solid var(--border);
                border-radius: 999px;
                color: var(--cyan);
                font-size: 0.78rem;
                font-weight: 700;
                padding: 3px 10px;
                white-space: nowrap;
            }}

            .qi-description {{
                -webkit-box-orient: vertical;
                -webkit-line-clamp: 3;
                color: var(--text-muted);
                display: -webkit-box;
                font-size: 0.86rem;
                line-height: 1.4;
                margin: 10px 0;
                overflow: hidden;
            }}

            .qi-tags {{
                display: flex;
                flex-wrap: wrap;
                gap: 6px;
                margin-bottom: 10px;
            }}

            .qi-tag {{
                border-radius: 6px;
                font-size: 0.72rem;
                font-weight: 700;
                letter-spacing: 0.03em;
                padding: 3px 8px;
                text-transform: uppercase;
            }}

            .qi-tag-success {{ background: rgba(51,224,161,0.12); color: var(--success); }}
            .qi-tag-warning {{ background: rgba(255,181,71,0.12); color: var(--warning); }}
            .qi-tag-danger {{ background: rgba(255,93,125,0.12); color: var(--danger); }}
            .qi-tag-neutral {{ background: rgba(139,147,172,0.12); color: var(--text-muted); }}

            .qi-metadata-grid {{
                border-top: 1px solid var(--border);
                display: grid;
                gap: 10px;
                grid-template-columns: repeat(4, 1fr);
                padding-top: 10px;
            }}

            @media (max-width: 640px) {{
                .qi-metadata-grid {{
                    grid-template-columns: repeat(2, 1fr);
                }}
            }}

            .qi-metadata-label {{
                color: var(--text-muted);
                font-size: 0.68rem;
                letter-spacing: 0.05em;
                text-transform: uppercase;
            }}

            .qi-metadata-value {{
                color: var(--text-primary);
                font-size: 0.86rem;
                font-weight: 600;
                margin-top: 2px;
            }}

            .qi-scope-badge {{
                background: rgba(34, 229, 255, 0.08);
                border: 1px solid var(--border);
                border-radius: 999px;
                color: var(--cyan);
                display: inline-block;
                font-size: 0.74rem;
                font-weight: 700;
                padding: 4px 12px;
            }}

            /* Compatibilidad con componentes existentes del calendario */
            .calendar-session {{
                background: var(--surface);
                border: 1px solid var(--border);
                border-left: 3px solid var(--cyan);
                border-radius: 8px;
                color: var(--text-primary);
                font-size: 0.74rem;
                line-height: 1.25;
                margin: 5px 0;
                padding: 8px;
            }}

            .calendar-session.completed {{ border-left-color: var(--success); }}
            .calendar-session.modified {{ border-left-color: var(--warning); }}
            .calendar-session.cancelled {{
                border-left-color: var(--danger);
                opacity: 0.6;
            }}

            .planner-detail {{
                background: var(--surface-glass);
                border: 1px solid var(--border);
                border-radius: 14px;
                color: var(--text-primary);
                padding: 20px;
            }}

            .planner-detail h3 {{ margin-top: 0; }}

            .status-badge {{
                border-radius: 999px;
                display: inline-block;
                font-size: 0.74rem;
                font-weight: 700;
                letter-spacing: 0.03em;
                margin-bottom: 12px;
                padding: 4px 11px;
                text-transform: uppercase;
            }}

            .status-pending {{ background: rgba(255,181,71,0.12); color: var(--warning); }}
            .status-completed {{ background: rgba(51,224,161,0.12); color: var(--success); }}
            .status-modified {{ background: rgba(255,181,71,0.12); color: var(--warning); }}
            .status-cancelled {{ background: rgba(255,93,125,0.12); color: var(--danger); }}

            .section-caption {{
                color: var(--text-muted);
                font-size: 0.86rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    _apply_plotly_theme()


def _apply_plotly_theme() -> None:
    """Registra una plantilla Plotly coherente con el tema oscuro.

    Al registrarla como plantilla por defecto, todos los gráficos creados
    con Plotly Express heredan la paleta sin tener que modificar cada
    gráfico de forma individual.
    """
    template = pio.templates["plotly_dark"]
    template.layout.paper_bgcolor = SURFACE
    template.layout.plot_bgcolor = SURFACE
    template.layout.font.color = TEXT_PRIMARY
    template.layout.colorway = [
        CYAN,
        VIOLET,
        SUCCESS,
        WARNING,
        DANGER,
        "#6CA8D8",
    ]
    template.layout.xaxis.gridcolor = "rgba(255,255,255,0.06)"
    template.layout.yaxis.gridcolor = "rgba(255,255,255,0.06)"

    pio.templates["qi_dark"] = template
    pio.templates.default = "qi_dark"


def render_hero(
    eyebrow: str,
    title: str,
    description: str | None = None,
) -> None:
    """Renderiza una cabecera tipo 'hero': eyebrow, titular grande y texto."""
    st.markdown(
        f'<div class="qi-eyebrow">{eyebrow}</div>',
        unsafe_allow_html=True,
    )
    st.title(title)

    if description:
        st.markdown(
            f'<div class="qi-subtitle">{description}</div>',
            unsafe_allow_html=True,
        )


def render_status_tag(label: str, tone: str = "neutral") -> str:
    """Devuelve el HTML de una etiqueta de estado del sistema visual."""
    css_class = {
        "success": "qi-tag-success",
        "warning": "qi-tag-warning",
        "danger": "qi-tag-danger",
    }.get(tone, "qi-tag-neutral")

    return f'<span class="qi-tag {css_class}">{label}</span>'
