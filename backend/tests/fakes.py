"""Fake adapters shared by the tests of the budget, coupon and appointment modules."""

from app.integrations.avisos import AvisosIntegracion
from app.integrations.obras_sociales import ObrasSocialesIntegracion


class AvisosEspia(AvisosIntegracion):
    """Records every notice instead of sending it."""

    def __init__(self):
        self.enviados: list[tuple[str, str, str]] = []

    def enviar_aviso(self, destinatario: str, canal: str, mensaje: str) -> bool:
        self.enviados.append((destinatario, canal, mensaje))
        return True

    def para(self, destinatario: str) -> list[str]:
        return [m for d, _, m in self.enviados if d == destinatario]


class AvisosCaido(AvisosIntegracion):
    def enviar_aviso(self, destinatario: str, canal: str, mensaje: str) -> bool:
        raise ConnectionError("sin servicio")


class ObrasSocialesFalsa(ObrasSocialesIntegracion):
    def __init__(self):
        self.altas: list[tuple[str, str]] = []

    def listar_obras_sociales(self) -> list[dict]:
        return [{"nombre": "OSDE", "cobertura": 80}, {"nombre": "Swiss Medical", "cobertura": 60}]

    def dar_de_alta_estudio(self, nombre: str, fecha: str) -> str:
        self.altas.append((nombre, fecha))
        return "OS-9001"

    def estado_autorizacion(self, identificador: str) -> str:
        return "Pendiente"
