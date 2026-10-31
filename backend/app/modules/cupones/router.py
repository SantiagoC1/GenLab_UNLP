from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.core.enums import Rol
from app.core.security import require_role
from app.integrations.avisos import AvisosIntegracion, obtener_avisos
from app.integrations.cupones import CuponesIntegracion, obtener_cupones
from app.modules.cupones.repositorio import (
    RepositorioCupones,
    RepositorioMedicos,
    obtener_repositorio,
    obtener_repositorio_medicos,
)
from app.modules.cupones.schemas import (
    AsignacionSalida,
    AsignarAMedicoEntrada,
    CuponSalida,
    GenerarCuponesEntrada,
    MedicoSalida,
)
from app.modules.cupones.servicio import CuponesServicio

# Generar y asignar a médicos: gerente médico. Asignar a pacientes: médico tratante.
exigir_gerente = require_role(Rol.GERENTE_MEDICO)


def obtener_servicio(
    repositorio: Annotated[RepositorioCupones, Depends(obtener_repositorio)],
    cupones: Annotated[CuponesIntegracion, Depends(obtener_cupones)],
    avisos: Annotated[AvisosIntegracion, Depends(obtener_avisos)],
    medicos: Annotated[RepositorioMedicos, Depends(obtener_repositorio_medicos)],
) -> CuponesServicio:
    return CuponesServicio(repositorio, cupones, avisos, medicos)


Servicio = Annotated[CuponesServicio, Depends(obtener_servicio)]

# M5. Cupones de descuento
router = APIRouter(prefix="/cupones", tags=["cupones"])


@router.get("/ping")
def ping() -> dict[str, str]:
    """Prueba de humo del router. Se borra cuando el paquete tenga endpoints reales."""
    return {"modulo": "cupones"}


@router.post("/generar", status_code=201, dependencies=[Depends(exigir_gerente)])
def generar_cupones(datos: GenerarCuponesEntrada, servicio: Servicio) -> list[CuponSalida]:
    """Pide los cupones al módulo de cupones y los devuelve Vigentes, con su PDF y su QR."""
    return servicio.generar(datos.descuento, datos.cantidad)


@router.get("", dependencies=[Depends(exigir_gerente)])
def listar_cupones(servicio: Servicio) -> list[CuponSalida]:
    return servicio.listar()


@router.get("/medicos", dependencies=[Depends(exigir_gerente)])
def buscar_medicos(
    q: Annotated[str, Query(min_length=1, max_length=80)], servicio: Servicio
) -> list[MedicoSalida]:
    """Médicos tratantes buscados por nombre o matrícula."""
    return servicio.buscar_medicos(q)


@router.post("/asignar-a-medico", dependencies=[Depends(exigir_gerente)])
def asignar_a_medico(datos: AsignarAMedicoEntrada, servicio: Servicio) -> AsignacionSalida:
    """Asigna cupones Vigentes al médico tratante y le avisa."""
    return servicio.asignar_a_medico(datos.contacto_medico, datos.codigos)


@router.get("/{codigo}/pdf", dependencies=[Depends(exigir_gerente)])
def descargar_pdf(codigo: str, servicio: Servicio) -> Response:
    return Response(
        servicio.pdf(codigo),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cupon-{codigo}.pdf"'},
    )
