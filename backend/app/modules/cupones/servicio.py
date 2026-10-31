import base64
from datetime import UTC, datetime

from app.core.errors import BusinessRuleError, InvalidIntegration
from app.documentos import qr as qr_code
from app.documentos.pdf import Line, build_pdf
from app.integrations.cupones import CuponesError, CuponesIntegracion
from app.modules.cupones.repositorio import Cupon, RepositorioCupones
from app.modules.cupones.schemas import CuponSalida

INTEGRACION = "cupones"


def qr_de(codigo: str) -> list[list[bool]] | None:
    try:
        return qr_code.encode(codigo)
    except ValueError:
        return None


class CuponesServicio:
    def __init__(self, repositorio: RepositorioCupones, cupones: CuponesIntegracion):
        self.repositorio = repositorio
        self.cupones = cupones

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

    def pdf(self, codigo: str) -> bytes:
        cupon = self.repositorio.obtener(codigo)
        if cupon is None:
            raise BusinessRuleError("No existe el cupón.", status_code=404)
        return documento_pdf(cupon)

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
