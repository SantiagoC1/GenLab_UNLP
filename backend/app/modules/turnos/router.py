from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.enums import Rol
from app.core.security import require_role
from app.integrations.avisos import AvisosIntegracion, obtener_avisos
from app.modules.presupuesto_pago.repositorio import RepositorioEstudios
from app.modules.presupuesto_pago.repositorio import obtener_repositorio as obtener_estudios
from app.modules.turnos import reglas
from app.modules.turnos.repositorio import RepositorioTurnos, obtener_repositorio
from app.modules.turnos.schemas import (
    CancelacionSalida,
    EstudioHabilitadoSalida,
    LaboratorioSalida,
    ReservarEntrada,
    TurnoSalida,
    TurnosLibresSalida,
)
from app.modules.turnos.servicio import TurnosServicio

# Turnos y documentos: el paciente, sobre sus propios estudios.
exigir_paciente = require_role(Rol.PACIENTE)
UsuarioPaciente = Annotated[dict, Depends(exigir_paciente)]


def obtener_servicio(
    turnos: Annotated[RepositorioTurnos, Depends(obtener_repositorio)],
    estudios: Annotated[RepositorioEstudios, Depends(obtener_estudios)],
    avisos: Annotated[AvisosIntegracion, Depends(obtener_avisos)],
    ahora: Annotated[datetime, Depends(reglas.ahora)],
) -> TurnosServicio:
    return TurnosServicio(turnos, estudios, avisos, ahora)


Servicio = Annotated[TurnosServicio, Depends(obtener_servicio)]

# M6. Turno y extracción
router = APIRouter(prefix="/turnos", tags=["turnos"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "turnos"}


@router.get("/laboratorios", dependencies=[Depends(exigir_paciente)])
def listar_laboratorios(
    servicio: Servicio, provincia: Annotated[str | None, Query(max_length=60)] = None
) -> list[LaboratorioSalida]:
    """Los laboratorios de extracción del país, con el próximo turno libre de cada uno."""
    return servicio.listar_laboratorios(provincia)


@router.get("/laboratorios/{laboratorio_id}/turnos-libres", dependencies=[Depends(exigir_paciente)])
def listar_turnos_libres(
    laboratorio_id: int, fecha: date, servicio: Servicio
) -> TurnosLibresSalida:
    """Turnos libres de un laboratorio en un día, generados por la regla (M6-RF2)."""
    return servicio.turnos_libres(laboratorio_id, fecha)


@router.get("/habilitados")
def listar_estudios_habilitados(
    usuario: UsuarioPaciente, servicio: Servicio
) -> list[EstudioHabilitadoSalida]:
    """Estudios del paciente que pueden sacar turno (M6-RF3)."""
    return servicio.estudios_habilitados(usuario["email"])


@router.post("/reservas", status_code=201)
def reservar_turno(
    datos: ReservarEntrada, usuario: UsuarioPaciente, servicio: Servicio
) -> TurnoSalida:
    """Reserva el turno, pasa el estudio a Turno sacado y programa el recordatorio por mail."""
    return servicio.reservar(usuario["email"], datos.estudio_id, datos.laboratorio_id, datos.inicio)


@router.get("/mis-turnos")
def listar_mis_turnos(usuario: UsuarioPaciente, servicio: Servicio) -> list[TurnoSalida]:
    return servicio.mis_turnos(usuario["email"])


def _pdf(contenido: bytes, nombre: str) -> Response:
    return Response(
        contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/{turno_id}/orden-extraccion")
def descargar_orden_de_extraccion(
    turno_id: int, usuario: UsuarioPaciente, servicio: Servicio
) -> Response:
    """Orden de extracción: fecha, hora, laboratorio e indicaciones previas."""
    return _pdf(
        servicio.orden_de_extraccion(usuario["email"], turno_id), f"orden-extraccion-{turno_id}.pdf"
    )


@router.get("/{turno_id}/consentimiento-informado")
def descargar_consentimiento_informado(
    turno_id: int, usuario: UsuarioPaciente, servicio: Servicio
) -> Response:
    """Consentimiento informado para imprimir. El firmado se entrega en papel."""
    return _pdf(
        servicio.consentimiento_informado(usuario["email"], turno_id),
        "consentimiento-informado.pdf",
    )


@router.post("/{turno_id}/cancelar")
def cancelar_turno(
    turno_id: int, usuario: UsuarioPaciente, servicio: Servicio
) -> CancelacionSalida:
    """Cancela un turno futuro sin costo y devuelve el estudio al estado previo."""
    return servicio.cancelar(usuario["email"], turno_id)
