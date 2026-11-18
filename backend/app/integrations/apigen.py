"""Adaptador del módulo externo MA5."""

from abc import ABC, abstractmethod

import httpx

from app.core.config import get_settings

TIMEOUT_SECONDS = 5
GENE_SEARCH_LIMIT = 20
_TODO = "TODO: la parte de variantes y diagnóstico la usa bioinformática."


class ApigenIntegracion(ABC):
    """Interfaz que usa el resto del sistema. El contrato real puede cambiar sin tocar a los demás."""

    @abstractmethod
    def genes_por_patologia(
        self, patologia: str, con_hallazgos_secundarios: bool = False
    ) -> list[str]:
        """Devuelve los genes de la patología, por su código (POMPE).

        Con hallazgos secundarios suma los genes de la lista ACMG.
        """

    @abstractmethod
    def listar_patologias(self) -> list[dict]:
        """Devuelve las patologías de Apigen como {codigo, nombre}."""

    @abstractmethod
    def buscar_genes(self, prefijo: str) -> list[str]:
        """Devuelve los símbolos de los genes que empiezan con el prefijo."""

    @abstractmethod
    def variantes_por_gen(self, gen: str) -> list[dict]:
        """Devuelve: variantes con su clasificación (patogénica, benigna o VUS)."""

    @abstractmethod
    def confirmar_diagnostico(self, patologia: str, variantes: list[str]) -> bool:
        """Devuelve: si las variantes confirman el diagnóstico."""


class ApigenSimulador(ApigenIntegracion):
    """Devuelve datos de ejemplo para desarrollar y demostrar sin depender de otro grupo."""

    def genes_por_patologia(
        self, patologia: str, con_hallazgos_secundarios: bool = False
    ) -> list[str]:
        return ["GLA"] + (["ACMG-1"] if con_hallazgos_secundarios else [])

    def listar_patologias(self) -> list[dict]:
        return [
            {"codigo": "ASMD", "nombre": "Deficiencia de esfingomielinasa ácida"},
            {"codigo": "FABRY", "nombre": "Enfermedad de Fabry"},
            {"codigo": "GAUCHER", "nombre": "Enfermedad de Gaucher"},
            {"codigo": "MPS1", "nombre": "Mucopolisacaridosis tipo 1"},
            {"codigo": "MPS2", "nombre": "Mucopolisacaridosis tipo 2"},
            {"codigo": "POMPE", "nombre": "Enfermedad de Pompe"},
        ]

    def buscar_genes(self, prefijo: str) -> list[str]:
        genes = ["GAA", "GBA1", "GLA", "IDS", "IDUA", "SMPD1"]
        return [gen for gen in genes if gen.startswith(prefijo.upper())]

    def variantes_por_gen(self, gen: str) -> list[dict]:
        return [{"variante": f"{gen}:c.1A>G", "clasificacion": "VUS"}]

    def confirmar_diagnostico(self, patologia: str, variantes: list[str]) -> bool:
        return bool(variantes)


class ApigenReal(ApigenIntegracion):
    """Cliente de Apigen, que expone PostgREST de Supabase.

    Los genes se piden acá; las variantes y el diagnóstico los usa
    bioinformática y todavía no están conectados.
    """

    def _headers(self) -> dict:
        return {"apikey": get_settings().apigen_apikey}

    def _base(self) -> str:
        return get_settings().apigen_url.rstrip("/")

    def genes_por_patologia(
        self, patologia: str, con_hallazgos_secundarios: bool = False
    ) -> list[str]:
        response = httpx.post(
            f"{self._base()}/rpc/genes_por_patologia",
            json={"p_patologia": patologia},
            headers=self._headers(),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        genes = response.json()
        if not con_hallazgos_secundarios:
            return genes

        response = httpx.get(
            f"{self._base()}/genes_hallazgos_secundarios",
            params={"select": "gen"},
            headers=self._headers(),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return genes + [row["gen"] for row in response.json() if row["gen"] not in genes]

    def listar_patologias(self) -> list[dict]:
        response = httpx.post(
            f"{self._base()}/rpc/listar_patologias",
            json={},
            headers=self._headers(),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return [{"codigo": row["codigo"], "nombre": row["nombre"]} for row in response.json()]

    def buscar_genes(self, prefijo: str) -> list[str]:
        response = httpx.get(
            f"{self._base()}/gen",
            params={
                "simbolo": f"ilike.{prefijo}*",
                "select": "simbolo",
                "limit": GENE_SEARCH_LIMIT,
            },
            headers=self._headers(),
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return [row["simbolo"] for row in response.json()]

    def variantes_por_gen(self, gen: str) -> list[dict]:
        raise NotImplementedError(_TODO)

    def confirmar_diagnostico(self, patologia: str, variantes: list[str]) -> bool:
        raise NotImplementedError(_TODO)


def obtener_apigen() -> ApigenIntegracion:
    if get_settings().integracion_apigen == "real":
        return ApigenReal()
    return ApigenSimulador()
