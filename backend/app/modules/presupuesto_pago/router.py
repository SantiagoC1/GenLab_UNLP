from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.core.enums import Rol
from app.core.security import require_role
from app.integrations.avisos import AvisosIntegracion, obtener_avisos
from app.integrations.cupones import CuponesIntegracion, obtener_cupones
from app.integrations.obras_sociales import ObrasSocialesIntegracion, obtener_obras_sociales
from app.modules.cupones.repositorio import RepositorioCupones
from app.modules.cupones.repositorio import obtener_repositorio as obtener_repositorio_cupones
from app.modules.presupuesto_pago.autorizacion import AutorizacionServicio
from app.modules.presupuesto_pago.paciente import PacienteServicio
from app.modules.presupuesto_pago.repositorio import RepositorioEstudios, obtener_repositorio
from app.modules.presupuesto_pago.schemas import (
    AplicarCuponEntrada,
    AsientoFinancieroSalida,
    AutorizacionPendienteSalida,
    AutorizacionRegistradaSalida,
    CuponAplicadoSalida,
    DetalleEstudioSalida,
    ElegirCoberturaEntrada,
    EstudioDelPacienteSalida,
    EstudioPendienteSalida,
    ObraSocialSalida,
    PagarEntrada,
    PagoSalida,
    PresupuestoEmitidoSalida,
    RespuestaObraSocialEntrada,
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
    avisos: Annotated[AvisosIntegracion, Depends(obtener_avisos)],
    cupones: Annotated[CuponesIntegracion, Depends(obtener_cupones)],
    repositorio_cupones: Annotated[RepositorioCupones, Depends(obtener_repositorio_cupones)],
) -> PacienteServicio:
    return PacienteServicio(repositorio, obras_sociales, avisos, cupones, repositorio_cupones)


ServicioPaciente = Annotated[PacienteServicio, Depends(obtener_servicio_paciente)]


def obtener_servicio_autorizacion(
    repositorio: Annotated[RepositorioEstudios, Depends(obtener_repositorio)],
    avisos: Annotated[AvisosIntegracion, Depends(obtener_avisos)],
) -> AutorizacionServicio:
    return AutorizacionServicio(repositorio, avisos)


ServicioAutorizacion = Annotated[AutorizacionServicio, Depends(obtener_servicio_autorizacion)]

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


@router.post("/mis-estudios/{estudio_id}/pago", status_code=201)
def pagar_estudio(
    estudio_id: int, datos: PagarEntrada, usuario: UsuarioPaciente, servicio: ServicioPaciente
) -> PagoSalida:
    """Pago particular simulado: asienta el pago y pasa el estudio a Pagado."""
    return servicio.pagar(usuario["email"], estudio_id, datos.metodo)


@router.get("/registro-financiero", dependencies=administrativo)
def ver_registro_financiero(
    repositorio: Annotated[RepositorioEstudios, Depends(obtener_repositorio)],
) -> list[AsientoFinancieroSalida]:
    """Todas las operaciones asentadas: importe, paciente, estudio, método, fecha y cupón."""
    return [AsientoFinancieroSalida(**vars(a)) for a in repositorio.listar_asientos()]


@router.post("/mis-estudios/{estudio_id}/cupon")
def aplicar_cupon(
    estudio_id: int,
    datos: AplicarCuponEntrada,
    usuario: UsuarioPaciente,
    servicio: ServicioPaciente,
) -> CuponAplicadoSalida:
    """Consulta al módulo de cupones si está Vigente y devuelve el nuevo importe."""
    return servicio.aplicar_cupon(usuario["email"], estudio_id, datos.codigo)


@router.post("/mis-estudios/{estudio_id}/cupon-pdf")
async def aplicar_cupon_con_pdf(
    estudio_id: int,
    request: Request,
    usuario: UsuarioPaciente,
    servicio: ServicioPaciente,
) -> CuponAplicadoSalida:
    """Igual que el anterior, pero adjuntando el PDF del cupón (cuerpo `application/pdf`)."""
    return servicio.aplicar_cupon_con_pdf(usuario["email"], estudio_id, await request.body())


@router.delete("/mis-estudios/{estudio_id}/cupon")
def quitar_cupon(
    estudio_id: int, usuario: UsuarioPaciente, servicio: ServicioPaciente
) -> EstudioDelPacienteSalida:
    """Vuelve al importe original."""
    return servicio.quitar_cupon(usuario["email"], estudio_id)


@router.get("/autorizaciones-pendientes", dependencies=administrativo)
def listar_autorizaciones_pendientes(
    servicio: ServicioAutorizacion,
) -> list[AutorizacionPendienteSalida]:
    """Bandeja: estudios con la autorización de la obra social pendiente."""
    return servicio.listar_pendientes()


@router.post("/estudios/{estudio_id}/autorizacion", dependencies=administrativo)
def registrar_autorizacion(
    estudio_id: int,
    datos: RespuestaObraSocialEntrada,
    servicio: ServicioAutorizacion,
) -> AutorizacionRegistradaSalida:
    """Registra la respuesta de la obra social (Autorizado o Rechazado con motivo)."""
    return servicio.registrar_respuesta(estudio_id, datos.resultado, datos.motivo)
