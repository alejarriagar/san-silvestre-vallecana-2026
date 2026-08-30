"""Pruebas de la abstracción LLM sin llamadas de red."""

from src.services.llm_service import (
    DemoCoachAnalysisProvider,
    ProviderConfiguration,
    load_provider_configuration,
)


def test_missing_api_key_uses_demo_mode(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    configuration = load_provider_configuration()

    assert configuration.is_demo_mode is True
    assert configuration.provider == "demo"


def test_demo_provider_generates_valid_structured_analysis():
    configuration = ProviderConfiguration(
        provider="demo",
        model=None,
        is_demo_mode=True,
        message="Modo demo activo.",
    )

    provider = DemoCoachAnalysisProvider(configuration)

    analysis = provider.generate(
        {
            "evaluacion_determinista": {
                "estado": "amarillo",
                "alertas": ["Dolor de rodilla de 4/10."],
                "recomendaciones": ["Evitar calidad temporalmente."],
                "preguntas_pendientes": ["Falta sueño."],
                "confianza": 0.65,
                "restringir_calidad": True,
                "resumen": "Precaución por dolor.",
            },
            "metricas": {
                "km_carrera_semana": 6.0,
                "km_planificados_semana": 13.0,
                "carga_semanal": 280.0,
                "sesiones_ultimos_28_dias": 2,
            },
            "proximo_entrenamiento": {
                "fecha": "2026-09-01",
                "tipo": "Progresivos",
                "descripcion": "6-7 km fáciles + progresivos.",
            },
        }
    )

    assert analysis.estado == "amarillo"
    assert analysis.confianza == 0.65
    assert len(analysis.cambios_propuestos) == 1
    assert analysis.cambios_propuestos[0].fecha == "2026-09-01"


def test_ollama_configuration_does_not_require_api_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:3b")
    monkeypatch.setenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434/v1",
    )
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    configuration = load_provider_configuration()

    assert configuration.is_demo_mode is False
    assert configuration.provider == "ollama"
    assert configuration.model == "qwen2.5:3b"
    assert configuration.base_url == "http://localhost:11434/v1"
