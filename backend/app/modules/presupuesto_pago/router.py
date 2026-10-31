from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.enums import Rol
from app.core.security import require_role
from app.integrations.avisos import AvisosIntegracion, obtener_avisos
from app.modules.presupuesto_pago.repositorio import RepositorioEstudios, obtener_repositorio
from app.modules.presupuesto_pago.schemas import (
    DetalleEstudioSalida,
    EstudioPendienteSalida,
    PresupuestoEmitidoSalida,
)
from app.modules.presupuesto_pago.servicio import PresupuestoServicio

# Solo el administrativo del laboratorio opera los presupuestos.
exigir_administrativo = require_role(Rol.ADMINISTRATIVO_LABORATORIO)


administrativo = [Depends(exigir_administrativo)]


def obtener_servicio(
    repositorio: Annotated[RepositorioEstudios, Depends(obtener_repositorio)],
    avisos: Annotated[AvisosIntegracion, Depends(obtener_avisos)],
) -> PresupuestoServicio:
    return PresupuestoServicio(repositorio, avisos)


Servicio = Annotated[PresupuestoServicio, Depends(obtener_servicio)]

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
