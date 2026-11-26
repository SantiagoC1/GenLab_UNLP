"""Storage of the coupons the platform manages (generated, assigned to doctors and patients).

The creation, validity and use of a coupon belong to the external coupons module (MA3); here we
only keep who holds each coupon.

The real implementations are in repositorio_supabase.py (table `coupons`, reading `users` and
`patients`). The ones in memory (repositorio_memoria.py) only serve `DEV_AUTH=true` and the tests.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.core import dev_auth


@dataclass(frozen=True)
class Medico:
    contacto: str  # e-mail, which also identifies the account
    nombre: str
    matricula: str


@dataclass(frozen=True)
class Paciente:
    contacto: str  # e-mail of the patient's account
    nombre: str
    medico: str  # contact of the treating doctor


@dataclass
class Cupon:
    codigo: str
    descuento: int
    estado: str
    generado_en: datetime
    medico: str | None = None  # contact (e-mail) of the doctor who holds it
    paciente: str | None = None  # contact (e-mail) of the patient it was given to


class RepositorioCupones(ABC):
    @abstractmethod
    def guardar_nuevos(self, cupones: list[Cupon]) -> None: ...

    @abstractmethod
    def listar(self) -> list[Cupon]:
        """Todos los cupones, del más nuevo al más viejo."""

    @abstractmethod
    def obtener(self, codigo: str) -> Cupon | None: ...

    @abstractmethod
    def asignar_a_medico(self, codigos: list[str], contacto_medico: str) -> list[Cupon]: ...

    @abstractmethod
    def listar_de_medico(self, contacto_medico: str) -> list[Cupon]:
        """Cupones que el médico tiene y todavía no le dio a ningún paciente."""

    @abstractmethod
    def listar_de_paciente(self, contacto_paciente: str) -> list[Cupon]: ...

    @abstractmethod
    def asignar_a_paciente(self, codigo: str, contacto_paciente: str) -> Cupon: ...

    @abstractmethod
    def marcar_usado(self, codigo: str) -> None:
        """Refleja acá que el módulo de cupones lo marcó como usado (si lo conocemos)."""


class RepositorioPacientes(ABC):
    """Patients of each treating doctor.

    They come from the patients table (module owned by Integrante A), read only.
    """

    @abstractmethod
    def listar_de_medico(self, contacto_medico: str) -> list[Paciente]: ...

    @abstractmethod
    def obtener(self, contacto: str, contacto_medico: str | None = None) -> Paciente | None:
        """The patient of that account; with several (siblings) the doctor's one comes first."""


class RepositorioMedicos(ABC):
    """Treating doctors that coupons can be assigned to.

    The doctors are users with role `medico_tratante` (module owned by Integrante A), read only.
    """

    @abstractmethod
    def buscar(self, texto: str) -> list[Medico]:
        """Doctors whose name or license number contain the text."""

    @abstractmethod
    def obtener(self, contacto: str) -> Medico | None: ...


def obtener_repositorio() -> RepositorioCupones:
    if dev_auth.is_enabled():
        from app.modules.cupones.repositorio_memoria import cupones_en_memoria

        return cupones_en_memoria()
    from app.modules.cupones.repositorio_supabase import RepositorioCuponesSupabase

    return RepositorioCuponesSupabase()


def obtener_repositorio_medicos() -> RepositorioMedicos:
    if dev_auth.is_enabled():
        from app.modules.cupones.repositorio_memoria import medicos_en_memoria

        return medicos_en_memoria()
    from app.modules.cupones.repositorio_supabase import RepositorioMedicosSupabase

    return RepositorioMedicosSupabase()


def obtener_repositorio_pacientes() -> RepositorioPacientes:
    if dev_auth.is_enabled():
        from app.modules.cupones.repositorio_memoria import pacientes_en_memoria

        return pacientes_en_memoria()
    from app.modules.cupones.repositorio_supabase import RepositorioPacientesSupabase

    return RepositorioPacientesSupabase()
