"""Coupons, doctors and patients kept in memory, with example data.

Only for `DEV_AUTH=true` (nothing is written to the database) and as the test double of the
interfaces in repositorio.py. The real ones are in repositorio_supabase.py.
"""

from app.modules.cupones.repositorio import (
    Cupon,
    Medico,
    Paciente,
    RepositorioCupones,
    RepositorioMedicos,
    RepositorioPacientes,
)


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

    def obtener(self, contacto: str, contacto_medico: str | None = None) -> Paciente | None:
        return self.pacientes.get(contacto)


_cupones = RepositorioCuponesEnMemoria()
_medicos = RepositorioMedicosEnMemoria()
_pacientes = RepositorioPacientesEnMemoria()


def cupones_en_memoria() -> RepositorioCupones:
    return _cupones


def medicos_en_memoria() -> RepositorioMedicos:
    return _medicos


def pacientes_en_memoria() -> RepositorioPacientes:
    return _pacientes
