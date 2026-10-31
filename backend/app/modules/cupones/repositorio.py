"""Storage of the coupons the platform manages (generated, assigned to doctors and patients).

The creation, validity and use of a coupon belong to the external coupons module (MA3); here we
only keep who holds each coupon.

TODO: swap `RepositorioCuponesEnMemoria` for a database-backed implementation (table `coupons`)
without touching the service or the router.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


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

    TODO: they come from the patients table (module owned by Integrante A).
    """

    @abstractmethod
    def listar_de_medico(self, contacto_medico: str) -> list[Paciente]: ...

    @abstractmethod
    def obtener(self, contacto: str) -> Paciente | None: ...


class RepositorioMedicos(ABC):
    """Treating doctors that coupons can be assigned to.

    TODO: the doctors are users with role `medico_tratante` (module owned by Integrante A).
    """

    @abstractmethod
    def buscar(self, texto: str) -> list[Medico]:
        """Doctors whose name or license number contain the text."""

    @abstractmethod
    def obtener(self, contacto: str) -> Medico | None: ...


class RepositorioCuponesEnMemoria(RepositorioCupones):
    def __init__(self) -> None:
        self.cupones: dict[str, Cupon] = {}

    def guardar_nuevos(self, cupones: list[Cupon]) -> None:
        for cupon in cupones:
            self.cupones[cupon.codigo] = cupon

    def listar(self) -> list[Cupon]:
        return list(reversed(self.cupones.values()))

    def obtener(self, codigo: str) -> Cupon | None:
        return self.cupones.get(codigo)

    def asignar_a_medico(self, codigos: list[str], contacto_medico: str) -> list[Cupon]:
        asignados = [self.cupones[codigo] for codigo in codigos]
        for cupon in asignados:
            cupon.medico = contacto_medico
        return asignados

    def listar_de_medico(self, contacto_medico: str) -> list[Cupon]:
        return [
            c for c in self.cupones.values() if c.medico == contacto_medico and c.paciente is None
        ]

    def listar_de_paciente(self, contacto_paciente: str) -> list[Cupon]:
        return [c for c in self.cupones.values() if c.paciente == contacto_paciente]

    def asignar_a_paciente(self, codigo: str, contacto_paciente: str) -> Cupon:
        cupon = self.cupones[codigo]
        cupon.paciente = contacto_paciente
        return cupon

    def marcar_usado(self, codigo: str) -> None:
        if codigo in self.cupones:
            self.cupones[codigo].estado = "Usado"


def _medicos_de_ejemplo() -> list[Medico]:
    return [
        Medico("ana.perez@example.com", "Ana Pérez", "MP-12345"),
        Medico("carlos.rivas@example.com", "Carlos Rivas", "MP-23456"),
        Medico("elena.sosa@example.com", "Elena Sosa", "MP-34567"),
    ]


class RepositorioMedicosEnMemoria(RepositorioMedicos):
    def __init__(self) -> None:
        self.medicos = {m.contacto: m for m in _medicos_de_ejemplo()}

    def buscar(self, texto: str) -> list[Medico]:
        buscado = texto.strip().lower()
        return [
            m
            for m in self.medicos.values()
            if buscado in m.nombre.lower() or buscado in m.matricula.lower()
        ]

    def obtener(self, contacto: str) -> Medico | None:
        return self.medicos.get(contacto)


_repositorio = RepositorioCuponesEnMemoria()


class RepositorioPacientesEnMemoria(RepositorioPacientes):
    def __init__(self) -> None:
        pacientes = [
            Paciente("lucia.fernandez@example.com", "Lucía Fernández", "ana.perez@example.com"),
            Paciente("martin.gomez@example.com", "Martín Gómez", "ana.perez@example.com"),
            Paciente("sofia.ramirez@example.com", "Sofía Ramírez", "carlos.rivas@example.com"),
        ]
        self.pacientes = {p.contacto: p for p in pacientes}

    def listar_de_medico(self, contacto_medico: str) -> list[Paciente]:
        return [p for p in self.pacientes.values() if p.medico == contacto_medico]

    def obtener(self, contacto: str) -> Paciente | None:
        return self.pacientes.get(contacto)


_medicos = RepositorioMedicosEnMemoria()
_pacientes = RepositorioPacientesEnMemoria()


def obtener_repositorio() -> RepositorioCupones:
    return _repositorio


def obtener_repositorio_medicos() -> RepositorioMedicos:
    return _medicos


def obtener_repositorio_pacientes() -> RepositorioPacientes:
    return _pacientes
