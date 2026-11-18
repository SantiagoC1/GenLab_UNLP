import base64
from datetime import UTC, datetime

from app.core.enums import Rol
from app.core.errors import BusinessRuleError, InvalidIntegration
from app.documentos import qr as qr_code
from app.documentos.pdf import Line, build_pdf
from app.integrations.avisos import AvisosIntegracion
from app.integrations.cupones import CuponesError, CuponesIntegracion
from app.modules.cupones.repositorio import (
    Cupon,
    Medico,
    RepositorioCupones,
    RepositorioMedicos,
    RepositorioPacientes,
)
from app.modules.cupones.schemas import (
    AsignacionAPacienteSalida,
    AsignacionSalida,
    CuponSalida,
    MedicoSalida,
    MisCuponesMedicoSalida,
    PacienteSalida,
)

INTEGRACION = "cupones"
CANAL_AVISO = "email"
VIGENTE = "Vigente"


def qr_de(codigo: str) -> list[list[bool]] | None:
    try:
        return qr_code.encode(codigo)
    except ValueError:
        return None


class CuponesServicio:
    def __init__(
        self,
        repositorio: RepositorioCupones,
        cupones: CuponesIntegracion,
        avisos: AvisosIntegracion,
        medicos: RepositorioMedicos,
        pacientes: RepositorioPacientes,
    ):
        self.repositorio = repositorio
        self.cupones = cupones
        self.avisos = avisos
        self.medicos = medicos
        self.pacientes = pacientes

    # --- M5-RF1 and M5-RF5: generate coupons -------------------------------------------------

    def generar(self, descuento: int, cantidad: int) -> list[CuponSalida]:
        try:
            nuevos = self.cupones.obtener_cupones(descuento, cantidad)
        except CuponesError as error:
            raise BusinessRuleError(
                f"El módulo de cupones rechazó la solicitud: {error}",
                status_code=502,
                code="cupones_rechazados",
            ) from None
        except Exception:
            raise InvalidIntegration(INTEGRACION) from None

        ahora = datetime.now(UTC)
        guardados = [
            Cupon(c["codigo"], c.get("descuento", descuento), c["estado"], ahora) for c in nuevos
        ]
        # Only what the module accepted is shown: a rejection above leaves nothing stored.
        self.repositorio.guardar_nuevos(guardados)
        return [self.salida(c) for c in guardados]

    def listar(self) -> list[CuponSalida]:
        return [self.salida(c) for c in self.repositorio.listar()]

    # --- M5-RF2: assign coupons to a treating doctor -----------------------------------------

    def buscar_medicos(self, texto: str) -> list[MedicoSalida]:
        return [MedicoSalida(**vars(m)) for m in self.medicos.buscar(texto)]

    def asignar_a_medico(self, contacto_medico: str, codigos: list[str]) -> AsignacionSalida:
        medico = self.medicos.obtener(contacto_medico)
        if medico is None:
            raise BusinessRuleError("No existe el médico tratante.", status_code=404)

        cupones = []
        for codigo in codigos:
            cupon = self.repositorio.obtener(codigo)
            if cupon is None:
                raise BusinessRuleError(f"No existe el cupón {codigo}.", status_code=404)
            if cupon.medico is not None or cupon.paciente is not None:
                raise BusinessRuleError(
                    f"El cupón {codigo} ya está asignado.", code="cupon_ya_asignado"
                )
            cupones.append(cupon)
        # The validity belongs to the coupons module: nothing is assigned unless all are valid.
        for cupon in cupones:
            if self._estado_en_el_modulo(cupon.codigo) != VIGENTE:
                raise BusinessRuleError(
                    f"El cupón {cupon.codigo} no está Vigente.", code="cupon_no_vigente"
                )

        self.repositorio.asignar_a_medico(codigos, medico.contacto)
        return AsignacionSalida(
            medico=MedicoSalida(**vars(medico)),
            codigos=codigos,
            medico_avisado=self._avisar_al_medico(medico, len(codigos)),
        )

    # --- M5-RF3 and M5-RF4: the doctor gives a coupon to a patient ---------------------------

    def cupones_del_medico(self, contacto_medico: str) -> MisCuponesMedicoSalida:
        disponibles = self.repositorio.listar_de_medico(contacto_medico)
        return MisCuponesMedicoSalida(
            cantidad=len(disponibles), cupones=[self.salida(c) for c in disponibles]
        )

    def pacientes_del_medico(self, contacto_medico: str) -> list[PacienteSalida]:
        return [
            PacienteSalida(contacto=p.contacto, nombre=p.nombre)
            for p in self.pacientes.listar_de_medico(contacto_medico)
        ]

    def cupones_del_paciente(self, contacto_paciente: str) -> list[CuponSalida]:
        return [self.salida(c) for c in self.repositorio.listar_de_paciente(contacto_paciente)]

    def asignar_a_paciente(
        self, contacto_medico: str, contacto_paciente: str, codigo: str
    ) -> AsignacionAPacienteSalida:
        disponibles = self.repositorio.listar_de_medico(contacto_medico)
        if not disponibles:
            raise BusinessRuleError("No tenés cupones para asignar.", code="sin_cupones")
        cupon = next((c for c in disponibles if c.codigo == codigo), None)
        if cupon is None:
            raise BusinessRuleError(
                "Ese cupón no está entre tus cupones disponibles.", code="cupon_no_disponible"
            )
        paciente = self.pacientes.obtener(contacto_paciente)
        if paciente is None or paciente.medico != contacto_medico:
            raise BusinessRuleError("No existe el paciente.", status_code=404)
        if self._estado_en_el_modulo(cupon.codigo) != VIGENTE:
            raise BusinessRuleError(
                f"El cupón {cupon.codigo} no está Vigente.", code="cupon_no_vigente"
            )

        asignado = self.repositorio.asignar_a_paciente(cupon.codigo, paciente.contacto)
        return AsignacionAPacienteSalida(
            paciente=PacienteSalida(contacto=paciente.contacto, nombre=paciente.nombre),
            cupon=self.salida(asignado),
            disponibles=len(disponibles) - 1,
            paciente_avisado=self._avisar(
                paciente.contacto,
                f"Su médico le asignó un cupón de descuento del {asignado.descuento}% "
                "para el pago de su estudio.",
            ),
        )

    def _avisar(self, destinatario: str, mensaje: str) -> bool:
        try:
            return self.avisos.enviar_aviso(destinatario, CANAL_AVISO, mensaje)
        except Exception:
            return False

    def _estado_en_el_modulo(self, codigo: str) -> str:
        try:
            return self.cupones.validar_cupon(codigo)["estado"]
        except Exception:
            raise InvalidIntegration(INTEGRACION) from None

    def _avisar_al_medico(self, medico: Medico, cantidad: int) -> bool:
        mensaje = (
            f"El gerente médico le asignó {cantidad} "
            f"{'cupón' if cantidad == 1 else 'cupones'} de descuento para entregar a sus pacientes."
        )
        try:
            return self.avisos.enviar_aviso(medico.contacto, CANAL_AVISO, mensaje)
        except Exception:
            return False

    def pdf(self, codigo: str, usuario: dict) -> bytes:
        cupon = self.repositorio.obtener(codigo)
        # Whoever does not hold the coupon sees the same as a missing one.
        if cupon is None or not self._puede_ver(cupon, usuario):
            raise BusinessRuleError("No existe el cupón.", status_code=404)
        return documento_pdf(cupon)

    @staticmethod
    def _puede_ver(cupon: Cupon, usuario: dict) -> bool:
        rol, email = usuario["role"], usuario["email"]
        return (
            rol == Rol.GERENTE_MEDICO
            or (rol == Rol.MEDICO_TRATANTE and cupon.medico == email)
            or (rol == Rol.PACIENTE and cupon.paciente == email)
        )

    @staticmethod
    def salida(cupon: Cupon) -> CuponSalida:
        modules = qr_de(cupon.codigo)
        return CuponSalida(
            codigo=cupon.codigo,
            descuento=cupon.descuento,
            estado=cupon.estado,
            pdf_url=f"/cupones/{cupon.codigo}/pdf",
            qr=None
            if modules is None
            else "data:image/svg+xml;base64,"
            + base64.b64encode(qr_code.to_svg(modules).encode()).decode(),
            medico=cupon.medico,
            paciente=cupon.paciente,
        )


def documento_pdf(cupon: Cupon) -> bytes:
    return build_pdf(
        [
            Line("GenLab - Cupón de descuento", 20),
            Line(f"Código: {cupon.codigo}", 12, gap=24),
            Line(f"Descuento: {cupon.descuento}%", 12),
            Line(f"Estado: {cupon.estado}", 12),
            Line(
                "Presentá este cupón al pagar tu estudio: adjuntá este PDF o ingresá el código.",
                10,
                gap=16,
            ),
        ],
        qr=qr_de(cupon.codigo),
    )
