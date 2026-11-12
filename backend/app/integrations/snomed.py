"""Adaptador del módulo externo MA2."""

import unicodedata
from abc import ABC, abstractmethod

from app.core.config import get_settings

_TODO = (
    "TODO: el contrato real de Snomed todavía no está cerrado (decisión 1 de la especificación)."
)

# SUPUESTO (docs/Supuestos_y_pendientes.md, S2): el tamaño de página y la forma de la respuesta
# no están definidos por el otro grupo. `SnomedReal` tiene que traducir lo que mande el módulo
# (total, enlace a la siguiente página, etc.) a este formato.
PAGE_SIZE = 10

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


class SnomedIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def buscar_terminos(self, texto: str, pagina: int = 1) -> dict:
        """Devuelve: {"items": [{"code", "term"}], "has_more": bool}, con términos que coinciden
        (3 letras o más, con paginación)."""


class SnomedSimulador(SnomedIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def buscar_terminos(self, texto: str, pagina: int = 1) -> dict:
        needle = _normalize(texto)
        matches = [item for item in _SIMULATED_CATALOG if needle in _normalize(item["term"])]
        start = (pagina - 1) * PAGE_SIZE
        return {
            "items": matches[start : start + PAGE_SIZE],
            "has_more": len(matches) > start + PAGE_SIZE,
        }


class SnomedReal(SnomedIntegracion):
    """Cliente del módulo real.

    Requisitos para quien lo implemente: usar un timeout corto, pasar el texto con `params=` (no
    armar la URL con f-strings), tomar la URL de la configuración, devolver solo `code` y `term`
    y traducir sus errores a `OSError` o `TimeoutError`.
    """

    def buscar_terminos(self, texto: str, pagina: int = 1) -> dict:
        raise NotImplementedError(_TODO)


def obtener_snomed() -> SnomedIntegracion:
    if get_settings().integracion_snomed == "real":
        return SnomedReal()
    return SnomedSimulador()
