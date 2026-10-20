import importlib

import pytest

from app.core.config import get_settings

INTEGRACIONES = [
    "familiograma",
    "snomed",
    "cupones",
    "cdss",
    "apigen",
    "obras_sociales",
    "avisos",
    "optimizacion_recorrido",
    "fedex",
    "ministerio_salud",
]


@pytest.mark.parametrize("nombre", INTEGRACIONES)
def test_el_simulador_es_el_modo_por_defecto(nombre):
    modulo = importlib.import_module(f"app.integrations.{nombre}")
    adaptador = getattr(modulo, f"obtener_{nombre}")()
    assert type(adaptador).__name__.endswith("Simulador")


@pytest.mark.parametrize("nombre", INTEGRACIONES)
def test_modo_real_devuelve_el_cliente_real(nombre, monkeypatch):
    monkeypatch.setattr(get_settings(), f"integracion_{nombre}", "real")
    modulo = importlib.import_module(f"app.integrations.{nombre}")
    adaptador = getattr(modulo, f"obtener_{nombre}")()
    assert type(adaptador).__name__.endswith("Real")
