"""The Supabase repositories of the coupons, the doctors and the patients."""

from datetime import UTC, datetime

import pytest

from app.core.enums import Rol
from app.core.errors import BusinessRuleError
from app.modules.cupones.repositorio import Cupon
from app.modules.cupones.repositorio_supabase import (
    RepositorioCuponesSupabase,
    RepositorioMedicosSupabase,
    RepositorioPacientesSupabase,
)
from tests.fake_supabase import FakeSupabase

ANA = "ana.perez@example.com"
CARLOS = "carlos.rivas@example.com"
LUCIA = "lucia.fernandez@example.com"
FAMILIA = "familia.gomez@example.com"


def nuevo(codigo: str, descuento: int = 20) -> Cupon:
    return Cupon(codigo, descuento, "Vigente", datetime.now(UTC))


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase(
        users=[
            {
                "id": "u-ana",
                "email": ANA,
                "first_name": "Ana",
                "last_name": "Pérez",
                "license_number": "MP-12345",
                "role": Rol.MEDICO_TRATANTE.value,
            },
            {
                "id": "u-carlos",
                "email": CARLOS,
                "first_name": "Carlos",
                "last_name": "Rivas",
                "license_number": None,
                "role": Rol.MEDICO_TRATANTE.value,
            },
            {
                "id": "u-gerente",
                "email": "gerente@example.com",
                "first_name": "Gerardo",
                "last_name": "Medina",
                "license_number": None,
                "role": Rol.GERENTE_MEDICO.value,
            },
            {"id": "u-lucia", "email": LUCIA, "role": Rol.PACIENTE.value},
            {"id": "u-familia", "email": FAMILIA, "role": Rol.PACIENTE.value},
        ],
        patients=[
            {
                "id": "p-lucia",
                "account_user_id": "u-lucia",
                "registered_by": "u-ana",
                "first_name": "Lucía",
                "last_name": "Fernández",
            },
            # Two siblings share their parents' account, each with a different doctor.
            {
                "id": "p-hijo1",
                "account_user_id": "u-familia",
                "registered_by": "u-ana",
                "first_name": "Tomás",
                "last_name": "Gómez",
            },
            {
                "id": "p-hijo2",
                "account_user_id": "u-familia",
                "registered_by": "u-carlos",
                "first_name": "Julia",
                "last_name": "Gómez",
            },
        ],
    )
    monkeypatch.setattr("app.core.supabase_tables.supabase_admin", fake)
    return fake


# --- coupons ------------------------------------------------------------------------------


def test_new_coupons_are_stored_and_listed_newest_first(db):
    repo = RepositorioCuponesSupabase()
    repo.guardar_nuevos([nuevo("CUP-1"), nuevo("CUP-2", 50)])

    assert [c.codigo for c in repo.listar()] == ["CUP-2", "CUP-1"]
    assert repo.obtener("CUP-2").descuento == 50
    assert repo.obtener("CUP-2").estado == "Vigente"
    assert repo.obtener("NOPE") is None


def test_assigning_to_a_doctor_shows_the_coupons_in_his_list_by_email(db):
    repo = RepositorioCuponesSupabase()
    repo.guardar_nuevos([nuevo("CUP-1"), nuevo("CUP-2")])

    asignados = repo.asignar_a_medico(["CUP-1"], ANA)

    assert [(c.codigo, c.medico) for c in asignados] == [("CUP-1", ANA)]
    assert [c.codigo for c in repo.listar_de_medico(ANA)] == ["CUP-1"]
    assert repo.listar_de_medico(CARLOS) == []


def test_assigning_to_a_missing_doctor_is_a_404(db):
    repo = RepositorioCuponesSupabase()
    repo.guardar_nuevos([nuevo("CUP-1")])
    with pytest.raises(BusinessRuleError) as error:
        repo.asignar_a_medico(["CUP-1"], "nadie@example.com")
    assert error.value.status_code == 404


def test_a_coupon_given_to_a_patient_leaves_the_doctors_available_list(db):
    repo = RepositorioCuponesSupabase()
    repo.guardar_nuevos([nuevo("CUP-1"), nuevo("CUP-2")])
    repo.asignar_a_medico(["CUP-1", "CUP-2"], ANA)

    asignado = repo.asignar_a_paciente("CUP-1", LUCIA)

    assert (asignado.medico, asignado.paciente) == (ANA, LUCIA)
    assert [c.codigo for c in repo.listar_de_medico(ANA)] == ["CUP-2"]
    assert [c.codigo for c in repo.listar_de_paciente(LUCIA)] == ["CUP-1"]
    assert repo.listar_de_paciente(FAMILIA) == []


def test_with_siblings_the_coupon_goes_to_the_patient_of_that_doctor(db):
    repo = RepositorioCuponesSupabase()
    repo.guardar_nuevos([nuevo("CUP-1")])
    repo.asignar_a_medico(["CUP-1"], CARLOS)

    repo.asignar_a_paciente("CUP-1", FAMILIA)

    assert db.rows("coupons")[0]["patient_id"] == "p-hijo2"


def test_marking_a_coupon_as_used_updates_its_state(db):
    repo = RepositorioCuponesSupabase()
    repo.guardar_nuevos([nuevo("CUP-1")])

    repo.marcar_usado("CUP-1")

    assert repo.obtener("CUP-1").estado == "Usado"


def test_marking_an_unknown_coupon_as_used_changes_nothing(db):
    repo = RepositorioCuponesSupabase()
    repo.marcar_usado("EXTERNO-9")
    assert db.rows("coupons") == []


# --- doctors and patients (read only) -----------------------------------------------------


def test_doctors_are_searched_by_name_or_license_and_only_treating_doctors(db):
    repo = RepositorioMedicosSupabase()

    assert [m.contacto for m in repo.buscar("pérez")] == [ANA]
    assert [m.matricula for m in repo.buscar("mp-123")] == ["MP-12345"]
    assert repo.buscar("gerardo") == []
    assert repo.obtener(CARLOS).nombre == "Carlos Rivas"
    assert repo.obtener(CARLOS).matricula == ""
    assert repo.obtener("gerente@example.com") is None


def test_the_patients_of_a_doctor_come_with_their_account_email(db):
    repo = RepositorioPacientesSupabase()

    pacientes = repo.listar_de_medico(ANA)

    assert {(p.contacto, p.nombre) for p in pacientes} == {
        (LUCIA, "Lucía Fernández"),
        (FAMILIA, "Tomás Gómez"),
    }
    assert all(p.medico == ANA for p in pacientes)


def test_a_patient_is_found_by_account_preferring_the_doctors_own(db):
    repo = RepositorioPacientesSupabase()

    assert repo.obtener(LUCIA).medico == ANA
    assert repo.obtener(FAMILIA, CARLOS).nombre == "Julia Gómez"
    assert repo.obtener(FAMILIA, CARLOS).medico == CARLOS
    assert repo.obtener(FAMILIA).nombre == "Tomás Gómez"
    assert repo.obtener("nadie@example.com") is None


def test_the_repositories_only_ask_for_explicit_columns(db):
    cupones, medicos, pacientes = (
        RepositorioCuponesSupabase(),
        RepositorioMedicosSupabase(),
        RepositorioPacientesSupabase(),
    )
    cupones.guardar_nuevos([nuevo("CUP-1")])
    cupones.listar()
    medicos.buscar("a")
    pacientes.listar_de_medico(ANA)

    pedidas = {c for _, columnas in db.selects for c in columnas.split(",")}
    assert "*" not in pedidas
    # The sensitive columns of the tables owned by others are never read.
    assert db.columns_requested("patients").isdisjoint({"clinical_summary", "dni", "phone"})
    assert db.columns_requested("users").isdisjoint({"phone", "failed_attempts", "blocked"})
