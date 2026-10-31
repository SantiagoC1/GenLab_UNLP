from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.enums import Rol
from app.core.security import require_role
from app.integrations.avisos import AvisosIntegracion, obtener_avisos
from app.integrations.obras_sociales import ObrasSocialesIntegracion, obtener_obras_sociales
from app.modules.presupuesto_pago.paciente import PacienteServicio
from app.modules.presupuesto_pago.repositorio import RepositorioEstudios, obtener_repositorio
from app.modules.presupuesto_pago.schemas import (
    DetalleEstudioSalida,
    ElegirCoberturaEntrada,
    EstudioDelPacienteSalida,
    EstudioPendienteSalida,
    ObraSocialSalida,
    PresupuestoEmitidoSalida,
)
from app.modules.presupuesto_pago.servicio import PresupuestoServicio

# Solo el administrativo del laboratorio opera los presupuestos.
exigir_administrativo = require_role(Rol.ADMINISTRATIVO_LABORATORIO)


administrativo = [Depends(exigir_administrativo)]

# Cobertura, pago y demanda: el paciente, sobre sus propios estudios.
exigir_paciente = require_role(Rol.PACIENTE)
UsuarioPaciente = Annotated[dict, Depends(exigir_paciente)]


def obtener_servicio(
    repositorio: Annotated[RepositorioEstudios, Depends(obtener_repositorio)],
    avisos: Annotated[AvisosIntegracion, Depends(obtener_avisos)],
) -> PresupuestoServicio:
    return PresupuestoServicio(repositorio, avisos)


Servicio = Annotated[PresupuestoServicio, Depends(obtener_servicio)]


def obtener_servicio_paciente(
    repositorio: Annotated[RepositorioEstudios, Depends(obtener_repositorio)],
    obras_sociales: Annotated[ObrasSocialesIntegracion, Depends(obtener_obras_sociales)],
) -> PacienteServicio:
    return PacienteServicio(repositorio, obras_sociales)


ServicioPaciente = Annotated[PacienteServicio, Depends(obtener_servicio_paciente)]

# M4. Presupuesto, cobertura y pago
router = APIRouter(prefix="/presupuesto_pago", tags=["presupuesto_pago"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "presupuesto_pago"}


@router.get("/estudios-pendientes", dependencies=administrativo)
def listar_estudios_pendientes(
    servicio: Servicio,
) -> list[EstudioPendienteSalida]:
    """Bandeja: estudios Creados sin presupuesto."""
    return servicio.listar_pendientes()


@router.get("/estudios/{estudio_id}", dependencies=administrativo)
def ver_detalle_del_estudio(estudio_id: int, servicio: Servicio) -> DetalleEstudioSalida:
    """Lista de genes del estudio e importe calculado con la tarifa fija."""
    return servicio.detalle(estudio_id)


@router.post("/estudios/{estudio_id}/presupuesto", dependencies=administrativo, status_code=201)
def emitir_presupuesto(estudio_id: int, servicio: Servicio) -> PresupuestoEmitidoSalida:
    """Publica el presupuesto y avisa al paciente. El importe no se recibe: lo fija la tarifa."""
    return servicio.emitir(estudio_id)


@router.get("/mis-estudios")
def listar_mis_estudios(
    usuario: UsuarioPaciente, servicio: ServicioPaciente
) -> list[EstudioDelPacienteSalida]:
    """Los estudios del paciente con su presupuesto, su estado y su cobertura."""
    return servicio.listar_estudios(usuario["email"])


@router.get("/obras-sociales", dependencies=[Depends(exigir_paciente)])
def listar_obras_sociales(servicio: ServicioPaciente) -> list[ObraSocialSalida]:
    """Lista de obras sociales con su porcentaje de cobertura (módulo adicional 6)."""
    return servicio.listar_obras_sociales()


@router.post("/mis-estudios/{estudio_id}/cobertura", status_code=201)
def elegir_cobertura(
    estudio_id: int,
    datos: ElegirCoberturaEntrada,
    usuario: UsuarioPaciente,
    servicio: ServicioPaciente,
) -> EstudioDelPacienteSalida:
    """Deja el estudio a la espera de la autorización de la obra social."""
    return servicio.elegir_cobertura(usuario["email"], estudio_id, datos.obra_social)
