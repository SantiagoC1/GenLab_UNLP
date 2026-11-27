"""The in-memory repositories are only for DEV_AUTH: otherwise the database ones are used."""

import pytest

from app.modules.cupones import repositorio as cupones
from app.modules.cupones.repositorio_memoria import (
    RepositorioCuponesEnMemoria,
    RepositorioMedicosEnMemoria,
    RepositorioPacientesEnMemoria,
)
from app.modules.cupones.repositorio_supabase import (
    RepositorioCuponesSupabase,
    RepositorioMedicosSupabase,
    RepositorioPacientesSupabase,
)
from app.modules.presupuesto_pago import repositorio as estudios
from app.modules.presupuesto_pago.repositorio_memoria import RepositorioEstudiosEnMemoria
from app.modules.presupuesto_pago.repositorio_supabase import RepositorioEstudiosSupabase

CASES = [
    (estudios.obtener_repositorio, RepositorioEstudiosEnMemoria, RepositorioEstudiosSupabase),
    (cupones.obtener_repositorio, RepositorioCuponesEnMemoria, RepositorioCuponesSupabase),
    (cupones.obtener_repositorio_medicos, RepositorioMedicosEnMemoria, RepositorioMedicosSupabase),
    (
        cupones.obtener_repositorio_pacientes,
        RepositorioPacientesEnMemoria,
        RepositorioPacientesSupabase,
    ),
]


@pytest.mark.parametrize(("obtener", "memoria", "supabase"), CASES)
def test_dev_auth_uses_memory_and_otherwise_the_database(monkeypatch, obtener, memoria, supabase):
    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: True)
    assert isinstance(obtener(), memoria)

    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: False)
    assert isinstance(obtener(), supabase)
