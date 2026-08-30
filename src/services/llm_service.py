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
    """Cambio propuesto para revisión manual del usuario."""

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
    """Configuración del proveedor sin almacenar secretos."""

    provider: str
    model: str | None
    is_demo_mode: bool
    message: str
    base_url: str | None = None


class CoachAnalysisProvider(Protocol):
    """Contrato común para proveedores de análisis."""

    configuration: ProviderConfiguration

    def generate(self, context: dict[str, Any]) -> CoachAnalysis:
        """Genera un análisis a partir del contexto deportivo."""


def load_provider_configuration() -> ProviderConfiguration:
    """Lee variables de entorno sin exponer nunca claves API."""
    provider = os.getenv("LLM_PROVIDER", "demo").strip().lower()
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    openai_model = os.getenv("OPENAI_MODEL", "").strip() or None
    openai_base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None

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

    if provider == "ollama":
        ollama_model = (
            os.getenv("OLLAMA_MODEL", "").strip()
            or openai_model
        )
        ollama_base_url = (
            os.getenv("OLLAMA_BASE_URL", "").strip()
            or "http://localhost:11434/v1"
        )

        if not ollama_model:
            return ProviderConfiguration(
                provider="demo",
                model=None,
                is_demo_mode=True,
                message=(
                    "Modo demo activo: define OLLAMA_MODEL para activar "
                    "el análisis local gratuito."
                ),
            )

        return ProviderConfiguration(
            provider="ollama",
            model=ollama_model,
            is_demo_mode=False,
            message=(
                f"Modelo local configurado: Ollama · {ollama_model}."
            ),
            base_url=ollama_base_url,
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

    if not openai_model:
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
        model=openai_model,
        is_demo_mode=False,
        message=(
            f"Proveedor configurado: {provider} · Modelo: {openai_model}."
        ),
        base_url=openai_base_url,
    )


class DemoCoachAnalysisProvider:
    """Proveedor local que no realiza llamadas externas."""

    def __init__(self, configuration: ProviderConfiguration) -> None:
        self.configuration = configuration

    def generate(self, context: dict[str, Any]) -> CoachAnalysis:
        """Genera un análisis estructurado usando datos locales."""
        safety = context.get("evaluacion_determinista", {})
        metrics = context.get("metricas", {})
        next_training = context.get("proximo_entrenamiento")

        estado = safety.get("estado", "amarillo")
        alertas = list(safety.get("alertas", []))
        recommendations = list(safety.get("recomendaciones", []))
        questions = list(safety.get("preguntas_pendientes", []))

        weekly_km = float(metrics.get("km_carrera_semana", 0))
        planned_km = float(metrics.get("km_planificados_semana", 0))
        weekly_load = float(metrics.get("carga_semanal", 0))
        session_count = int(metrics.get("sesiones_ultimos_28_dias", 0))

        logros: list[str] = []

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
                "El plan inicial está precargado y listo para recibir datos reales."
            )

        if not alertas:
            alertas.append(
                "No hay alertas deterministas activas con los datos disponibles."
            )

        if next_training:
            next_date = next_training.get("fecha")
            next_type = next_training.get("tipo", "Sesión pendiente")
            next_description = next_training.get(
                "descripcion",
                "",
            )
        else:
            next_date = None
            next_type = "Sin sesión pendiente"
            next_description = "No hay sesiones futuras pendientes."

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
                or "No hay datos suficientes sobre la rodilla."
            ),
            recomendaciones=recommendations,
            cambios_propuestos=changes,
            preguntas_pendientes=questions,
            confianza=float(safety.get("confianza", 0.20)),
        )


class OpenAICompatibleCoachAnalysisProvider:
    """Proveedor compatible con la API de chat de OpenAI y Ollama."""

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
                "Falta el paquete openai. Ejecuta pip install -r requirements.txt."
            ) from error

        client_arguments: dict[str, Any] = {
            "api_key": self._api_key,
            "timeout": 45.0,
        }

        if self.configuration.base_url:
            client_arguments["base_url"] = self.configuration.base_url

        client = OpenAI(**client_arguments)

        system_prompt = """
Eres un entrenador de running prudente, orientado a datos y respondes en español.

Responde exclusivamente con JSON válido, sin Markdown ni texto adicional.

No diagnostiques lesiones, no sustituyas a profesionales sanitarios y no inventes
métricas que no estén en el contexto. No añadas automáticamente días de carrera.
Nunca modifiques el plan: solo puedes proponer cambios para revisión del usuario.

Usa exactamente esta estructura:
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
            "Analiza únicamente este contexto estructurado:\n\n"
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
                "No se pudo obtener el análisis. Comprueba que Ollama esté "
                "activo, que el modelo exista y que la configuración sea correcta."
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
                "El modelo devolvió una respuesta que no cumple el JSON esperado."
            ) from error


def get_coach_analysis_provider() -> CoachAnalysisProvider:
    """Construye el proveedor adecuado según la configuración local."""
    configuration = load_provider_configuration()

    if configuration.is_demo_mode:
        return DemoCoachAnalysisProvider(configuration)

    api_key = os.getenv("OPENAI_API_KEY", "").strip()

    # Ollama es local y no requiere una clave real. El cliente compatible
    # con OpenAI exige un texto no vacío, pero este valor no es un secreto.
    if configuration.provider == "ollama":
        api_key = "ollama-local"

    return OpenAICompatibleCoachAnalysisProvider(
        configuration=configuration,
        api_key=api_key,
    )
