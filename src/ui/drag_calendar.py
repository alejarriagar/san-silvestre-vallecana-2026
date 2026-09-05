"""Calendario interactivo con movimiento de sesiones planificadas."""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from src.database import move_planned_training


try:
    from streamlit_calendar import calendar
except ImportError:
    calendar = None


def parse_event_date(value: Any) -> date | None:
    """Convierte una fecha de evento a date."""
    if not value:
        return None

    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def extract_event(payload: Any) -> dict[str, Any] | None:
    """Extrae recursivamente un evento de la respuesta del componente."""
    if isinstance(payload, dict):
        if "id" in payload or "start" in payload:
            return payload

        nested_event = payload.get("event")

        if isinstance(nested_event, dict):
            return nested_event

        for value in payload.values():
            extracted_event = extract_event(value)

            if extracted_event is not None:
                return extracted_event

    elif isinstance(payload, list):
        for value in payload:
            extracted_event = extract_event(value)

            if extracted_event is not None:
                return extracted_event

    return None


def build_calendar_events(
    trainings: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    selected_date: str | None = None,
) -> list[dict[str, Any]]:

    """Convierte sesiones planificadas y realizadas en eventos visuales."""
    events: list[dict[str, Any]] = []

    plan_colors = {
        "Pendiente": "#22e5ff",
        "Completado": "#33e0a1",
        "Modificado": "#ffb547",
        "Cancelado": "#ff5d7d",
    }


    for training in trainings:
        status = training["status"]
        distance = training["target_distance_km"]

        distance_text = (
            f" · {distance:g} km"
            if isinstance(distance, (int, float))
            else ""
        )

        events.append(
            {
                "id": f"plan-{training['id']}",
                "title": (
                    f"{training['session_type']}"
                    f"{distance_text}"
                ),
                "start": training["planned_date"],
                "allDay": True,
                "editable": status != "Cancelado",
                "eventStartEditable": status != "Cancelado",
                "eventDurationEditable": False,
                "backgroundColor": plan_colors.get(
                    status,
                    "#C9F05A",
                ),
                "borderColor": plan_colors.get(
                    status,
                    "#C9F05A",
                ),
                "textColor": "#10140D",
                "extendedProps": {
                    "kind": "planned",
                    "training_id": training["id"],
                    "status": status,
                },
            }
        )

    for activity in activities:
        activity_type = activity["session_type"] or activity["sport"]

        events.append(
            {
                "id": f"activity-{activity['id']}",
                "title": f"Registrado · {activity_type}",
                "start": activity["session_date"],
                "allDay": True,
                "editable": False,
                "eventStartEditable": False,
                "eventDurationEditable": False,
                "backgroundColor": "#6CA8D8",
                "borderColor": "#6CA8D8",
                "textColor": "#101820",
                "extendedProps": {
                    "kind": "activity",
                    "activity_id": activity["id"],
                },
            }
        )

    if selected_date:
        events.append(
            {
                "start": selected_date,
                "end": selected_date,
                "display": "background",
                "backgroundColor": "rgba(34, 229, 255, 0.20)",
                "allDay": True,
            }
        )


    return events


def render_drag_calendar(
    trainings: list[dict[str, Any]],
    activities: list[dict[str, Any]],
) -> None:
    """Renderiza el calendario y procesa clics y movimientos."""
    st.subheader("Calendario de entrenamiento")
    st.caption(
        "Puedes arrastrar una sesión planificada a otro día. "
        "Las sesiones registradas no son arrastrables."
    )

    if calendar is None:
        st.error(
            "Falta la dependencia streamlit-calendar. "
            "Ejecuta: python -m pip install -r requirements.txt"
        )
        return

    selected_date = st.session_state.get(
        "home_selected_date",
        date.today().isoformat(),
    )

    events = build_calendar_events(
        trainings=trainings,
        activities=activities,
        selected_date=st.session_state.get("home_selected_date"),
    )


    calendar_options = {
        "editable": True,
        "eventStartEditable": True,
        "eventDurationEditable": False,
        "eventDragMinDistance": 10,
        "selectable": True,
        "initialDate": selected_date,
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek",
        },
        "height": 620,
        "dayMaxEvents": 4,
        "firstDay": 1,
        "locale": "es",
    }


    custom_css = """
        .fc {
            --fc-page-bg-color: #05070d;
            --fc-neutral-bg-color: #0c1220;
            --fc-border-color: rgba(0,229,255,.14);
            --fc-list-event-hover-bg-color: #0c1220;
            --fc-today-bg-color: rgba(34, 229, 255, 0.08);
            color: #eef2fb;
            font-family: "Inter", sans-serif;
        }

        .fc .fc-toolbar-title {
            color: #eef2fb;
            font-family: "Space Grotesk", sans-serif;
            font-size: 1.15rem;
            font-weight: 700;
        }

        .fc .fc-button {
            background: #0c1220;
            border: 1px solid rgba(0,229,255,.14);
            border-radius: 999px;
            color: #eef2fb;
            font-weight: 600;
        }

        .fc .fc-button:hover,
        .fc .fc-button-active {
            background: #22e5ff;
            border-color: #22e5ff;
            color: #05070d;
        }

        .fc .fc-col-header-cell-cushion,
        .fc .fc-daygrid-day-number {
            color: #8b93ac;
        }

        .fc-event {
            border-radius: 6px;
            cursor: grab;
            font-size: 0.76rem;
            font-weight: 700;
            padding: 2px 4px;
        }

        .fc-event:active {
            cursor: grabbing;
        }
    """


    state = calendar(
        events=events,
        options=calendar_options,
        custom_css=custom_css,
        callbacks=["dateClick", "eventClick", "eventChange"],
        key="home_drag_calendar",
    )



    if not isinstance(state, dict):
        return

    callback = state.get("callback")

    if callback not in {
        "dateClick",
        "eventClick",
        "eventChange",
    }:
        return


    callback_payload = state.get(callback)
    event_data = extract_event(callback_payload)

    if event_data is None:
        return

    event_id = str(event_data.get("id", ""))

    event_date = (
        event_data.get("start")
        or event_data.get("date")
    )

    callback_signature = (
        f"{callback}|{event_id}|{event_date}"
    )

    # El componente puede devolver el mismo callback después de cada
    # rerun de Streamlit. No debemos procesarlo dos veces.
    if (
        st.session_state.get("last_calendar_callback")
        == callback_signature
    ):
        return

    st.session_state["last_calendar_callback"] = callback_signature

    if callback in {"dateClick", "eventClick"}:
        clicked_date = parse_event_date(event_date)

        if event_id.startswith("plan-"):
            try:
                clicked_training_id = int(
                    event_id.removeprefix("plan-")
                )
            except ValueError:
                clicked_training_id = None

            already_open = (
                st.session_state.get("home_panel_open", False)
                and st.session_state.get("home_selected_training_id")
                == clicked_training_id
            )

            if already_open:
                st.session_state["home_panel_open"] = False
            else:
                st.session_state["home_panel_open"] = True
                st.session_state["home_selected_training_id"] = (
                    clicked_training_id
                )

                if clicked_date is not None:
                    st.session_state["home_selected_date"] = (
                        clicked_date.isoformat()
                    )

        elif event_id.startswith("activity-"):
            try:
                clicked_activity_id = int(
                    event_id.removeprefix("activity-")
                )
            except ValueError:
                clicked_activity_id = None

            already_open = (
                st.session_state.get("home_panel_open", False)
                and st.session_state.get("home_selected_activity_id")
                == clicked_activity_id
            )

            if already_open:
                st.session_state["home_panel_open"] = False
            else:
                st.session_state["home_panel_open"] = True
                st.session_state["home_selected_activity_id"] = (
                    clicked_activity_id
                )

                if clicked_date is not None:
                    st.session_state["home_selected_date"] = (
                        clicked_date.isoformat()
                    )

        else:
            # Clic en un día vacío del calendario.
            st.session_state["home_panel_open"] = True
            st.session_state["home_selected_training_id"] = None

            if clicked_date is not None:
                st.session_state["home_selected_date"] = (
                    clicked_date.isoformat()
                )

        st.rerun()


    if callback == "eventChange":
        if not event_id.startswith("plan-"):
            return

        try:
            training_id = int(
                event_id.removeprefix("plan-")
            )
        except ValueError:
            return

        new_date = parse_event_date(event_date)

        if new_date is None:
            return

        move_planned_training(
            training_id=training_id,
            new_date=new_date,
        )

        st.session_state["home_selected_date"] = (
            new_date.isoformat()
        )
        st.session_state["home_selected_training_id"] = training_id

        st.toast(
            f"Entrenamiento movido al {new_date.strftime('%d/%m/%Y')}"
        )
        st.rerun()


   