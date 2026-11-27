"""The repository of the table `resamplings`, against a fake PostgREST client (no database)."""

from datetime import UTC, datetime

import pytest

from app.core.enums import EstadoEstudio as E
from app.modules.presupuesto_pago.estado import can_transition
from app.modules.turnos import remuestreos
from app.modules.turnos.reglas import ARG, MOTIVO_ADN, MOTIVO_CALIDAD
from app.modules.turnos.remuestreos import (
    RepositorioRemuestreosEnMemoria,
    RepositorioRemuestreosSupabase,
)

AHORA = datetime(2026, 11, 2, 10, 7, tzinfo=ARG)
DESPUES = datetime(2026, 11, 3, 9, 15, tzinfo=ARG)


class _Consulta:
    """Just enough of the postgrest query builder for this repository."""

    def __init__(self, filas: list[dict]):
        self.filas = filas
        self._filtros: list = []
        self._orden: tuple[str, bool] | None = None
        self._limite: int | None = None
        self._insertar: dict | None = None
        self._actualizar: dict | None = None

    def select(self, columnas: str):
        self.columnas = columnas
        return self

    def insert(self, fila: dict):
        self._insertar = fila
        return self

    def update(self, cambios: dict):
        self._actualizar = cambios
        return self

    def eq(self, columna, valor):
        self._filtros.append(lambda f: f[columna] == valor)
        return self

    def is_(self, columna, valor):
        assert valor == "null"
        self._filtros.append(lambda f: f[columna] is None)
        return self

    def order(self, columna, desc=False):
        self._orden = (columna, desc)
        return self

    def limit(self, cantidad):
        self._limite = cantidad
        return self

    def execute(self):
        if self._insertar is not None:
            fila = {
                "id": len(self.filas) + 1,
                "detail": "",
                "requested_by": None,
                "resolved_at": None,
                **self._insertar,
            }
            self.filas.append(fila)
            return _Respuesta([fila])
        elegidas = [f for f in self.filas if all(c(f) for c in self._filtros)]
        if self._actualizar is not None:
            for fila in elegidas:
                fila.update(self._actualizar)
            return _Respuesta(elegidas)
        if self._orden:
            columna, desc = self._orden
            elegidas.sort(key=lambda f: f[columna], reverse=desc)
        return _Respuesta(elegidas[: self._limite])


class _Respuesta:
    def __init__(self, data: list[dict]):
        self.data = data


@pytest.fixture
def filas() -> list[dict]:
    return []


@pytest.fixture
def repositorio(filas):
    return RepositorioRemuestreosSupabase(tabla=lambda nombre: _Consulta(filas))


def test_registrar_guarda_la_fila_con_los_nombres_de_la_tabla(repositorio, filas):
    creado = repositorio.registrar(1, MOTIVO_CALIDAD, "Hemolizada", AHORA, "user-1")

    assert filas == [
        {
            "id": 1,
            "study_id": 1,
            "reason": MOTIVO_CALIDAD,
            "detail": "Hemolizada",
            "requested_by": "user-1",
            "created_at": AHORA.astimezone(UTC).isoformat(),
            "resolved_at": None,
        }
    ]
    assert (creado.id, creado.estudio_id, creado.motivo, creado.detalle) == (
        1,
        1,
        MOTIVO_CALIDAD,
        "Hemolizada",
    )
    assert creado.pedido_por == "user-1"
    assert creado.registrado_en == AHORA
    assert creado.resuelto is False


def test_pendiente_devuelve_el_ultimo_sin_resolver(repositorio):
    repositorio.registrar(1, MOTIVO_ADN, "Primero", AHORA)
    repositorio.resolver(1, AHORA)
    repositorio.registrar(1, MOTIVO_CALIDAD, "Segundo", DESPUES)
    repositorio.registrar(2, MOTIVO_ADN, "De otro estudio", DESPUES)

    pendiente = repositorio.pendiente(1)
    assert pendiente is not None and pendiente.detalle == "Segundo"
    assert repositorio.pendiente(3) is None


def test_resolver_marca_solo_los_pendientes_del_estudio(repositorio, filas):
    repositorio.registrar(1, MOTIVO_CALIDAD, "Uno", AHORA)
    repositorio.registrar(2, MOTIVO_CALIDAD, "Dos", AHORA)

    repositorio.resolver(1, DESPUES)

    assert filas[0]["resolved_at"] == DESPUES.astimezone(UTC).isoformat()
    assert filas[1]["resolved_at"] is None
    assert repositorio.pendiente(1) is None
    assert repositorio.pendiente(2) is not None


def test_listar_devuelve_los_del_estudio_del_primero_al_ultimo(repositorio):
    repositorio.registrar(1, MOTIVO_ADN, "Uno", AHORA)
    repositorio.registrar(1, MOTIVO_CALIDAD, "Dos", DESPUES)
    repositorio.registrar(2, MOTIVO_CALIDAD, "Otro", DESPUES)

    assert [r.detalle for r in repositorio.listar(1)] == ["Uno", "Dos"]


def test_con_dev_auth_se_usa_la_memoria_y_sin_dev_auth_la_tabla(monkeypatch):
    monkeypatch.setattr(remuestreos, "_supabase", RepositorioRemuestreosSupabase(tabla=object))

    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: True)
    assert isinstance(remuestreos.obtener_repositorio(), RepositorioRemuestreosEnMemoria)

    monkeypatch.setattr("app.core.dev_auth.is_enabled", lambda: False)
    assert isinstance(remuestreos.obtener_repositorio(), RepositorioRemuestreosSupabase)


# --- the new transition of the state model (needs the approval of Integrante A) ----------------


@pytest.mark.parametrize("desde", [E.EN_VIAJE_A_COREA, E.EN_EL_AREA_DE_BIOINFORMATICA])
def test_desde_corea_y_bioinformatica_se_puede_volver_a_turno_sacado(desde):
    assert can_transition(desde, E.TURNO_SACADO)


@pytest.mark.parametrize(
    "desde", [E.LISTO_PARA_RETIRAR, E.EN_LABORATORIO_CENTRAL, E.RESULTADO_DISPONIBLE]
)
def test_desde_los_demas_estados_no_se_agrega_la_vuelta(desde):
    assert not can_transition(desde, E.TURNO_SACADO)
