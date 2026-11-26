"""Storage of the resamplings (M6-RF10): the table `resamplings`.

A resampling asks for a new sample of the same study, at no cost. It is pending until the patient
books the new appointment. Appointments and samples are still in memory (N2); only this table is
persisted, so the repository is chosen by `DEV_AUTH` like the ones of the budget module.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.config import get_settings


@dataclass
class Remuestreo:
    """A new sample is needed for the same study, at no cost (M6-RF10)."""

    id: int
    estudio_id: int
    motivo: str
    detalle: str
    registrado_en: datetime
    pedido_por: str | None = None  # id of the user who asked; None when the lab or a system did
    resuelto: bool = False  # True once the patient books the new appointment


class RepositorioRemuestreos(ABC):
    @abstractmethod
    def registrar(
        self,
        estudio_id: int,
        motivo: str,
        detalle: str,
        registrado_en: datetime,
        pedido_por: str | None = None,
    ) -> Remuestreo: ...

    @abstractmethod
    def pendiente(self, estudio_id: int) -> Remuestreo | None:
        """El remuestreo del estudio al que el paciente todavía no le sacó turno."""

    @abstractmethod
    def resolver(self, estudio_id: int, resuelto_en: datetime) -> None: ...

    @abstractmethod
    def listar(self, estudio_id: int) -> list[Remuestreo]:
        """Todos los remuestreos del estudio, del primero al último."""


class RepositorioRemuestreosEnMemoria(RepositorioRemuestreos):
    def __init__(self) -> None:
        self.remuestreos: list[Remuestreo] = []

    def registrar(
        self,
        estudio_id: int,
        motivo: str,
        detalle: str,
        registrado_en: datetime,
        pedido_por: str | None = None,
    ) -> Remuestreo:
        remuestreo = Remuestreo(
            len(self.remuestreos) + 1, estudio_id, motivo, detalle, registrado_en, pedido_por
        )
        self.remuestreos.append(remuestreo)
        return remuestreo

    def pendiente(self, estudio_id: int) -> Remuestreo | None:
        return next(
            (
                r
                for r in reversed(self.remuestreos)
                if r.estudio_id == estudio_id and not r.resuelto
            ),
            None,
        )

    def resolver(self, estudio_id: int, resuelto_en: datetime) -> None:
        for remuestreo in self.remuestreos:
            if remuestreo.estudio_id == estudio_id:
                remuestreo.resuelto = True

    def listar(self, estudio_id: int) -> list[Remuestreo]:
        return [r for r in self.remuestreos if r.estudio_id == estudio_id]


_COLUMNAS = "id, study_id, reason, detail, requested_by, created_at, resolved_at"


def _fila_a_remuestreo(fila: dict) -> Remuestreo:
    return Remuestreo(
        id=fila["id"],
        estudio_id=fila["study_id"],
        motivo=fila["reason"],
        detalle=fila["detail"],
        registrado_en=datetime.fromisoformat(fila["created_at"]),
        pedido_por=fila["requested_by"],
        resuelto=fila["resolved_at"] is not None,
    )


class RepositorioRemuestreosSupabase(RepositorioRemuestreos):
    """Reads and writes `public.resamplings` with the server (admin) client."""

    def __init__(self, tabla=None) -> None:
        if tabla is None:
            from app.database import supabase_admin

            tabla = supabase_admin.table
        self._tabla = tabla

    def registrar(
        self,
        estudio_id: int,
        motivo: str,
        detalle: str,
        registrado_en: datetime,
        pedido_por: str | None = None,
    ) -> Remuestreo:
        fila = {
            "study_id": estudio_id,
            "reason": motivo,
            "detail": detalle,
            "requested_by": pedido_por,
            "created_at": registrado_en.astimezone(UTC).isoformat(),
        }
        creada = self._tabla("resamplings").insert(fila).execute().data[0]
        return _fila_a_remuestreo(creada)

    def pendiente(self, estudio_id: int) -> Remuestreo | None:
        filas = (
            self._tabla("resamplings")
            .select(_COLUMNAS)
            .eq("study_id", estudio_id)
            .is_("resolved_at", "null")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return _fila_a_remuestreo(filas[0]) if filas else None

    def resolver(self, estudio_id: int, resuelto_en: datetime) -> None:
        (
            self._tabla("resamplings")
            .update({"resolved_at": resuelto_en.astimezone(UTC).isoformat()})
            .eq("study_id", estudio_id)
            .is_("resolved_at", "null")
            .execute()
        )

    def listar(self, estudio_id: int) -> list[Remuestreo]:
        filas = (
            self._tabla("resamplings")
            .select(_COLUMNAS)
            .eq("study_id", estudio_id)
            .order("created_at")
            .execute()
            .data
        )
        return [_fila_a_remuestreo(fila) for fila in filas]


_en_memoria = RepositorioRemuestreosEnMemoria()
_supabase: RepositorioRemuestreosSupabase | None = None


def obtener_repositorio() -> RepositorioRemuestreos:
    """In memory only with `DEV_AUTH=true` (the demo data); otherwise the real table."""
    global _supabase
    if get_settings().dev_auth:
        return _en_memoria
    if _supabase is None:
        _supabase = RepositorioRemuestreosSupabase()
    return _supabase
