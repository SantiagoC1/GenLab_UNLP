"""Adaptador del módulo externo MA1: familiograma de un paciente."""

import base64
from abc import ABC, abstractmethod
from html import escape

import httpx

from app.core.config import get_settings

TIMEOUT_SECONDS = 10
PATIENT_KINSHIP_ID = 0
KINSHIPS = [
    {"id": 1, "parentesco": "progenitor"},
    {"id": 2, "parentesco": "hermano/a"},
    {"id": 3, "parentesco": "abuelo/a materno/a"},
    {"id": 4, "parentesco": "abuelo/a paterno/a"},
    {"id": 5, "parentesco": "tío/a materno/a"},
    {"id": 6, "parentesco": "tío/a paterno/a"},
    {"id": 7, "parentesco": "primo/a materno/a"},
    {"id": 8, "parentesco": "primo/a paterno/a"},
    {"id": 9, "parentesco": "hijo/a"},
    {"id": 10, "parentesco": "medio hermano/a materno/a"},
    {"id": 11, "parentesco": "medio hermano/a paterno/a"},
    {"id": 12, "parentesco": "pareja del paciente"},
    {"id": 13, "parentesco": "suegro/a"},
    {"id": 14, "parentesco": "sobrino/a"},
    {"id": 15, "parentesco": "nieto/a"},
]


class FamiliogramaInvalido(Exception):
    """El módulo rechazó los datos (422): trae el mensaje y los campos."""

    def __init__(self, mensaje: str, detalles: list):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.detalles = detalles


class FamiliogramaIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def listar_parentescos(self) -> list[dict]:
        """Devuelve los parentescos como {id, parentesco}, sin el paciente."""

    @abstractmethod
    def generar_familiograma(
        self, personas: list[dict], regla_sospecha: str = "desactivada"
    ) -> dict:
        """Devuelve {advertencias, svg_base64} del familiograma.

        Las personas llevan el parentesco por id y debe haber una sola
        con el del paciente (0). Si el módulo rechaza los datos, levanta
        FamiliogramaInvalido.
        """


class FamiliogramaSimulador(FamiliogramaIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def listar_parentescos(self) -> list[dict]:
        return KINSHIPS

    def generar_familiograma(
        self, personas: list[dict], regla_sospecha: str = "desactivada"
    ) -> dict:
        lines = [
            f'<text x="10" y="{20 * (number + 1)}">{escape(person["nombre"])} {escape(person["apellido"])}</text>'
            for number, person in enumerate(personas)
        ]
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">'
            + "".join(lines)
            + "</svg>"
        )
        return {
            "advertencias": [],
            "svg_base64": base64.b64encode(svg.encode()).decode(),
        }


class FamiliogramaReal(FamiliogramaIntegracion):
    """Cliente del módulo de familiograma, que se llama desde el servidor con una clave por grupo."""

    def _headers(self) -> dict:
        return {"x-api-key": get_settings().familiograma_apikey}

    def _base(self) -> str:
        return get_settings().familiograma_url.rstrip("/")

    def listar_parentescos(self) -> list[dict]:
        response = httpx.get(
            f"{self._base()}/parentescos",
            headers=self._headers(),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return [item for item in response.json() if item["id"] != PATIENT_KINSHIP_ID]

    def generar_familiograma(
        self, personas: list[dict], regla_sospecha: str = "desactivada"
    ) -> dict:
        response = httpx.post(
            self._base(),
            json={"personas": personas, "opciones": {"reglaSospecha": regla_sospecha}},
            headers=self._headers(),
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code == 422:
            error = response.json()["error"]
            raise FamiliogramaInvalido(error["mensaje"], error.get("detalles", []))
        response.raise_for_status()
        data = response.json()
        return {
            "advertencias": data["advertencias"],
            "svg_base64": data["imagen"]["base64"],
        }


def obtener_familiograma() -> FamiliogramaIntegracion:
    if get_settings().integracion_familiograma == "real":
        return FamiliogramaReal()
    return FamiliogramaSimulador()
