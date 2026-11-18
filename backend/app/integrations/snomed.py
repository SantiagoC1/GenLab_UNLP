"""Adaptador del módulo externo MA2 (síntomas SNOMED CT)."""

import unicodedata
from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

PAGE_SIZE = 10
MAX_RESULTS = 50
REGION = "us-east-1"
TIMEOUT_SECONDS = 15

# SIMULADOR: no son códigos de SNOMED reales. El prefijo `SIM-` evita que se confundan con datos
# clínicos si un síntoma de ejemplo se guarda en la tabla `symptoms`.
_SIMULATED_CATALOG = [
    {"code": "SIM-001", "term": "Acroparestesias"},
    {"code": "SIM-002", "term": "Angioqueratomas"},
    {"code": "SIM-003", "term": "Cardiomiopatía hipertrófica"},
    {"code": "SIM-004", "term": "Debilidad muscular proximal"},
    {"code": "SIM-005", "term": "Dolor óseo"},
    {"code": "SIM-006", "term": "Esplenomegalia"},
    {"code": "SIM-007", "term": "Hepatomegalia"},
    {"code": "SIM-008", "term": "Hipohidrosis"},
    {"code": "SIM-009", "term": "Hipotonía"},
    {"code": "SIM-010", "term": "Opacidad corneal"},
    {"code": "SIM-011", "term": "Rasgos faciales toscos"},
    {"code": "SIM-012", "term": "Trombocitopenia"},
]


def _normalize(text: str) -> str:
    """Pasa a minúsculas y quita los acentos, para buscar sin distinguirlos."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _page(terms: list[dict], page: int) -> dict:
    """Recorta la página pedida y avisa si queda otra después."""
    start = (page - 1) * PAGE_SIZE
    return {
        "items": terms[start : start + PAGE_SIZE],
        "has_more": len(terms) > start + PAGE_SIZE,
    }


class SnomedIntegracion(ABC):
    """Interfaz que usa el resto del sistema.

    El contrato real puede cambiar sin tocar a los demás.
    """

    @abstractmethod
    def buscar_terminos(self, texto: str, pagina: int = 1) -> dict:
        """Devuelve los términos que coinciden, con paginación.

        Forma: {'items': [{'code', 'term'}], 'has_more': bool}. Se busca
        desde 3 letras.
        """


class SnomedSimulador(SnomedIntegracion):
    """Datos de ejemplo para desarrollar sin depender de otro grupo."""

    def buscar_terminos(self, texto: str, pagina: int = 1) -> dict:
        needle = _normalize(texto)
        matches = [item for item in _SIMULATED_CATALOG if needle in _normalize(item["term"])]
        return _page(matches, pagina)


class SnomedReal(SnomedIntegracion):
    """Cliente de la API de síntomas SNOMED CT del otro grupo."""

    def buscar_terminos(self, texto: str, pagina: int = 1) -> dict:
        """Busca en la API real y pagina acá.

        La API no pagina: devuelve hasta 50 resultados, que se cortan de
        a PAGE_SIZE para que el buscador siga igual que con el
        simulador. Si responde con error, `raise_for_status` lo levanta y
        el servicio lo informa como módulo no disponible.
        """
        settings = get_settings()
        response = httpx.get(
            settings.snomed_url,
            params={"q": texto, "limite": MAX_RESULTS},
            headers={"X-API-Key": settings.snomed_apikey, "x-region": REGION},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        terms = [
            {"code": str(found["sctid"]), "term": found["termino_preferido"]}
            for found in response.json()["resultados"]
        ]
        return _page(terms, pagina)


def obtener_snomed() -> SnomedIntegracion:
    if get_settings().integracion_snomed == "real":
        return SnomedReal()
    return SnomedSimulador()
