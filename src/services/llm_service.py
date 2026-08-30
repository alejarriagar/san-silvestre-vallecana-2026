"""Abstracción de proveedores LLM para el entrenador deportivo."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class LLMServiceError(RuntimeError):
    """Error seguro de comunicación o formato con un proveedor LLM."""


class ProposedChange(BaseModel):
    """Cambio de plan sugerido, nunca aplicado automáticamente."""

    model_config = ConfigDict(extra="ignore")

    fecha: str
    cambio: str
    motivo: str


class CoachAnalysis(BaseModel):
    """Respuesta estructurada esperada del entrenador."""

    model_config = ConfigDict(extra="ignore")

    estado: Literal["verde", "amarillo", "rojo"] = "amarillo"
    resumen: str = ""
    logros: list[str] = Field(default_factory=list)
    alertas: list[str] = Field(default_factory=list)
    analisis_de_carga: str = ""
    analisis_de_rodilla: str = ""
    recomendaciones: list[str] = Field(default_factory=list)
    cambios_propuestos: list[ProposedChange] = Field(default_factory=list)
    preguntas_pendientes: list[str] = Field(default_factory=list)
    confianza: float = Field(default=0.0, ge=0.0, le=1.0)


@dataclass(frozen=True)
class ProviderConfiguration:
    """Configuración del proveedor sin incluir secretos."""

    provider: str
    model: str | None
    is_demo_mode: bool
    message: str
    base_url: str | None = None


class CoachAnalysisProvider(Protocol):
    """Contrato que deben cumplir los proveedores de análisis."""

    configuration: ProviderConfiguration

    def generate(self, context: dict[str, Any]) -> CoachAnalysis:
        """Genera un análisis estructurado a partir de contexto mínimo."""


def load_provider_configuration() -> ProviderConfiguration:
    """Lee variables de entorno sin exponer nunca claves API."""
    provider = os.getenv("LLM_PROVIDER", "demo").strip().lower()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "").strip() or None
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None

    if provider == "demo":
        return ProviderConfiguration(
            provider="demo",
            model=None,
            is_demo_mode=True,
            message=(
                "Modo demo activo: añade una clave de modelo para activar "
                "el análisis personalizado."
            ),
        )

    if not api_key:
        return ProviderConfiguration(
            provider="demo",
            model=None,
            is_demo_mode=True,
            message=(
                "Modo demo activo: añade una clave de modelo para activar "
                "el análisis personalizado."
            ),
        )

    if not model:
        return ProviderConfiguration(
            provider="demo",
            model=None,
            is_demo_mode=True,
            message=(
                "Modo demo activo: define OPENAI_MODEL junto con la clave "
                "para activar el análisis personalizado."
            ),
        )

    return ProviderConfiguration(
        provider=provider,
        model=model,
        is_demo_mode=False,
        message=f"Proveedor configurado: {provider} · Modelo: {model}.",
        base_url=base_url,
    )


class DemoCoachAnalysisProvider:
    """Proveedor local que no realiza llamadas externas."""

    def __init__(self, configuration: ProviderConfiguration) -> None:
        self.configuration = configuration

    def generate(self, context: dict[str, Any]) -> CoachAnalysis:
        """Genera un análisis básico usando únicamente reglas locales."""
        safety = context.get("evaluacion_determinista", {})
        metrics = context.get("metricas", {})
        next_training = context.get("proximo_entrenamiento")

        estado = safety.get("estado", "amarillo")
        alertas = list(safety.get("alertas", []))
        recommendations = list(safety.get("recomendaciones", []))
        questions = list(safety.get("preguntas_pendientes", []))

        weekly_km = metrics.get("km_carrera_semana", 0)
        planned_km = metrics.get("km_planificados_semana", 0)
        weekly_load = metrics.get("carga_semanal", 0)
        session_count = metrics.get("sesiones_ultimos_28_dias", 0)

        logros = []

        if session_count > 0:
            logros.append(
                "Ya existen sesiones registradas para construir una base de análisis."
            )

        if weekly_km > 0:
            logros.append(
                f"Se han registrado {weekly_km:.1f} km de carrera esta semana."
            )

        if not logros:
            logros.append(
                "El plan inicial está precargado y listo para registrar datos reales."
            )

        if not alertas:
            alertas.append(
                "No hay alertas deterministas activas con los datos disponibles."
            )

        if next_training:
            next_date = next_training["fecha"]
            next_type = next_training["tipo"]
            next_description = next_training["descripcion"]
        else:
            next_date = None
            next_type = "Sin sesión pendiente"
            next_description = "No hay una sesión futura pendiente en el plan."

        changes: list[ProposedChange] = []

        if safety.get("restringir_calidad") and next_date:
            changes.append(
                ProposedChange(
                    fecha=next_date,
                    cambio=(
                        "Sustituir temporalmente la sesión intensa por "
                        "rodaje fácil o recuperación."
                    ),
                    motivo=(
                        "Las reglas deterministas detectan dolor, fatiga "
                        "o recuperación insuficiente."
                    ),
                )
            )

        return CoachAnalysis(
            estado=estado,
            resumen=(
                f"Se han registrado {session_count} sesiones en los últimos "
                f"28 días. Carga semanal disponible: {weekly_load:.0f}. "
                f"Próxima sesión: {next_type}. {next_description}"
            ),
            logros=logros,
            alertas=alertas,
            analisis_de_carga=(
                f"Kilómetros reales de carrera esta semana: {weekly_km:.1f}. "
                f"Kilómetros planificados: {planned_km:.1f}. "
                "La carga se calcula como duración en minutos × RPE "
                "solo cuando ambos datos están disponibles."
            ),
            analisis_de_rodilla=(
                safety.get("resumen")
                or "No hay suficientes datos de rodilla para una valoración."
            ),
            recomendaciones=recommendations,
            cambios_propuestos=changes,
            preguntas_pendientes=questions,
            confianza=float(safety.get("confianza", 0.20)),
        )


class OpenAICompatibleCoachAnalysisProvider:
    """Proveedor compatible con la API de chat de OpenAI."""

    def __init__(
        self,
        configuration: ProviderConfiguration,
        api_key: str,
    ) -> None:
        self.configuration = configuration
        self._api_key = api_key

    def generate(self, context: dict[str, Any]) -> CoachAnalysis:
        """Solicita un JSON estructurado al modelo configurado."""
        try:
            from openai import OpenAI
        except ImportError as error:
            raise LLMServiceError(
                "No se ha instalado el paquete openai. Ejecuta pip install -r requirements.txt."
            ) from error

        client_arguments: dict[str, Any] = {
            "api_key": self._api_key,
            "timeout": 45.0,
        }

        if self.configuration.base_url:
            client_arguments["base_url"] = self.configuration.base_url

        client = OpenAI(**client_arguments)

        system_prompt = """
Eres un entrenador de running prudente y orientado a datos. Responde siempre
en español y exclusivamente con JSON válido, sin Markdown ni texto adicional.

Nunca diagnostiques lesiones ni sustituyas a un profesional sanitario.
No inventes métricas que no estén en el contexto.
No propongas añadir automáticamente días de carrera.
No apliques cambios al plan: solo proponlos para revisión del usuario.

Devuelve exactamente esta estructura conceptual:
{
  "estado": "verde|amarillo|rojo",
  "resumen": "string",
  "logros": ["string"],
  "alertas": ["string"],
  "analisis_de_carga": "string",
  "analisis_de_rodilla": "string",
  "recomendaciones": ["string"],
  "cambios_propuestos": [
    {
      "fecha": "YYYY-MM-DD",
      "cambio": "string",
      "motivo": "string"
    }
  ],
  "preguntas_pendientes": ["string"],
  "confianza": 0.0
}
""".strip()

        user_prompt = (
            "Analiza únicamente el siguiente contexto estructurado:\n\n"
            + json.dumps(
                context,
                ensure_ascii=False,
                default=str,
            )
        )

        try:
            response = client.chat.completions.create(
                model=self.configuration.model,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
            )
        except Exception as error:
            raise LLMServiceError(
                "No se pudo obtener el análisis del proveedor. "
                "Comprueba proveedor, modelo, clave y conexión."
            ) from error

        content = response.choices[0].message.content

        if not content:
            raise LLMServiceError(
                "El proveedor no devolvió contenido para el análisis."
            )

        cleaned_content = content.strip()

        if cleaned_content.startswith("```"):
            cleaned_content = cleaned_content.split("\n", 1)[-1]

            if cleaned_content.endswith("```"):
                cleaned_content = cleaned_content[:-3]

            cleaned_content = cleaned_content.strip()

        try:
            return CoachAnalysis.model_validate_json(cleaned_content)
        except Exception as error:
            raise LLMServiceError(
                "El proveedor devolvió una respuesta que no cumple el formato esperado."
            ) from error


def get_coach_analysis_provider() -> CoachAnalysisProvider:
    """Construye el proveedor adecuado según la configuración local."""
    configuration = load_provider_configuration()

    if configuration.is_demo_mode:
        return DemoCoachAnalysisProvider(configuration)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    return OpenAICompatibleCoachAnalysisProvider(
        configuration=configuration,
        api_key=api_key,
    )
