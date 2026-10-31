from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.enums import Rol
from app.core.security import require_role
from app.integrations.cupones import CuponesIntegracion, obtener_cupones
from app.modules.cupones.repositorio import RepositorioCupones, obtener_repositorio
from app.modules.cupones.schemas import CuponSalida, GenerarCuponesEntrada
from app.modules.cupones.servicio import CuponesServicio

# Generar y asignar a médicos: gerente médico. Asignar a pacientes: médico tratante.
exigir_gerente = require_role(Rol.GERENTE_MEDICO)


def obtener_servicio(
    repositorio: Annotated[RepositorioCupones, Depends(obtener_repositorio)],
    cupones: Annotated[CuponesIntegracion, Depends(obtener_cupones)],
) -> CuponesServicio:
    return CuponesServicio(repositorio, cupones)


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


@router.get("/{codigo}/pdf", dependencies=[Depends(exigir_gerente)])
def descargar_pdf(codigo: str, servicio: Servicio) -> Response:
    return Response(
        servicio.pdf(codigo),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="cupon-{codigo}.pdf"'},
    )
