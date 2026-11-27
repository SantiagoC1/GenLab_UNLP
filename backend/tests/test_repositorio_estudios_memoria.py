"""The in-memory repository of the studies (only for DEV_AUTH and as a test double)."""

from datetime import UTC, datetime

from app.core.enums import EstadoEstudio
from app.modules.presupuesto_pago.repositorio_memoria import RepositorioEstudiosEnMemoria

AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=UTC)


def test_lists_the_studies_in_the_given_states_in_order_with_the_dni():
    repo = RepositorioEstudiosEnMemoria()
    for estado in (
        EstadoEstudio.PAGADO,
        EstadoEstudio.TURNO_SACADO,
        EstadoEstudio.LISTO_PARA_RETIRAR,
        EstadoEstudio.EN_CAMINO_AL_LABORATORIO_CENTRAL,
        EstadoEstudio.EN_LABORATORIO_CENTRAL,
        EstadoEstudio.EN_VIAJE_A_COREA,
    ):
        repo.cambiar_estado(3, estado, AHORA)
    repo.cambiar_estado(1, EstadoEstudio.PAGADO, AHORA)

    (en_corea,) = repo.listar_por_estados([EstadoEstudio.EN_VIAJE_A_COREA])
    assert (en_corea.id, en_corea.dni) == (3, "33555666")
    assert [
        e.id for e in repo.listar_por_estados([EstadoEstudio.PAGADO, EstadoEstudio.CREADO])
    ] == [
        1,
        2,
    ]
    assert repo.listar_por_estados([]) == []
