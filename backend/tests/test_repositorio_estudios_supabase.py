"""The Supabase repository of the studies: reading, writing and the state history."""

from datetime import UTC, datetime

import pytest

from app.core.enums import EstadoEstudio, Rol
from app.core.errors import BusinessRuleError
from app.modules.presupuesto_pago.autorizacion import AutorizacionServicio
from app.modules.presupuesto_pago.paciente import PacienteServicio
from app.modules.presupuesto_pago.repositorio import AUTORIZADO, Cobertura, CuponAplicado
from app.modules.presupuesto_pago.repositorio_supabase import RepositorioEstudiosSupabase
from tests.fake_supabase import FakeSupabase
from tests.fakes import AvisosEspia, ObrasSocialesFalsa

LUCIA = "lucia.fernandez@example.com"
ADMIN_ID = "u-admin"
PATIENT_ACCOUNT_ID = "u-lucia"
GENES = ["GBA", "GLA", "IDUA", "IDS", "NPC1", "NPC2", "GAA"]
PDF = b"%PDF-1.4 demanda de prueba \x00\xff"


@pytest.fixture
def db(monkeypatch):
    fake = FakeSupabase(
        users=[
            {"id": ADMIN_ID, "email": "admin@example.com", "role": Rol.ADMINISTRATIVO_LABORATORIO},
            {"id": "u-doctor", "email": "ana.perez@example.com", "role": Rol.MEDICO_TRATANTE},
            {"id": PATIENT_ACCOUNT_ID, "email": LUCIA, "role": Rol.PACIENTE},
        ],
        patients=[
            {
                "id": "p-lucia",
                "account_user_id": PATIENT_ACCOUNT_ID,
                "first_name": "Lucía",
                "last_name": "Fernández",
                "dni": "30111222",
                "registered_by": "u-doctor",
            }
        ],
        studies=[
            {"id": 1, "patient_id": "p-lucia", "requested_by": "u-doctor", "state": "Creado"},
            {"id": 2, "patient_id": "p-lucia", "requested_by": "u-doctor", "state": "Creado"},
        ],
        study_genes=[{"study_id": 1, "gene": g} for g in GENES] + [{"study_id": 2, "gene": "GBA"}],
        study_state_history=[
            {"study_id": 1, "from_state": None, "to_state": "Creado", "changed_by": "u-doctor"},
            {"study_id": 2, "from_state": None, "to_state": "Creado", "changed_by": "u-doctor"},
        ],
    )
    # The repositories and `change_study_state` share the one client.
    monkeypatch.setattr("app.core.supabase_tables.supabase_admin", fake)
    monkeypatch.setattr("app.modules.consulta_medica.repository.supabase_admin", fake)
    return fake


@pytest.fixture
def repo(db) -> RepositorioEstudiosSupabase:
    return RepositorioEstudiosSupabase()


def ahora() -> datetime:
    return datetime.now(UTC)


# --- reading ------------------------------------------------------------------------------


def test_lists_the_studies_in_creado_without_budget_with_their_data(repo):
    estudio = repo.listar_creados_sin_presupuesto()[0]
    assert estudio.id == 1
    assert estudio.paciente == "Lucía Fernández"
    assert estudio.contacto_paciente == LUCIA
    assert estudio.contacto_medico == "ana.perez@example.com"
    assert estudio.genes == sorted(GENES)
    assert estudio.estado == EstadoEstudio.CREADO
    assert not estudio.tiene_presupuesto


def test_a_study_created_by_the_doctor_shows_up_in_the_budget_tray(repo, db):
    db.rows("studies").append(
        {"id": 3, "patient_id": "p-lucia", "requested_by": "u-doctor", "state": "Creado"}
    )
    assert [e.id for e in repo.listar_creados_sin_presupuesto()] == [1, 2, 3]


def test_lists_the_studies_of_a_patient_account_by_email(repo):
    assert [e.id for e in repo.listar_de_paciente(LUCIA)] == [1, 2]
    assert repo.listar_de_paciente("otra@example.com") == []


def test_obtener_returns_none_for_a_missing_study(repo):
    assert repo.obtener(99) is None


# --- budget -------------------------------------------------------------------------------


def test_publishing_the_budget_saves_it_and_takes_the_study_out_of_the_tray(repo, db):
    estudio = repo.guardar_presupuesto(1, 590, ahora(), ADMIN_ID)

    assert estudio.presupuesto_importe_usd == 590
    assert estudio.tiene_presupuesto
    fila = db.rows("budgets")[0]
    assert (fila["study_id"], fila["gene_count"], fila["issued_by"]) == (1, 7, ADMIN_ID)
    assert [e.id for e in repo.listar_creados_sin_presupuesto()] == [2]


def test_the_budget_needs_the_user_who_issues_it(repo, db):
    with pytest.raises(BusinessRuleError):
        repo.guardar_presupuesto(1, 590, ahora())
    assert db.rows("budgets") == []


def test_the_applied_coupon_is_kept_and_removed(repo):
    repo.guardar_presupuesto(1, 590, ahora(), ADMIN_ID)

    assert repo.guardar_cupon_aplicado(1, CuponAplicado("CUP-1", 20)).cupon_aplicado == (
        CuponAplicado("CUP-1", 20)
    )
    assert repo.obtener(1).cupon_aplicado == CuponAplicado("CUP-1", 20)
    assert repo.guardar_cupon_aplicado(1, None).cupon_aplicado is None


def test_a_coupon_cannot_be_applied_before_the_budget_exists(repo):
    with pytest.raises(BusinessRuleError):
        repo.guardar_cupon_aplicado(1, CuponAplicado("CUP-1", 20))


# --- coverage and court decision ----------------------------------------------------------


def test_the_coverage_is_inserted_then_updated_in_place(repo, db):
    elegida = ahora()
    cobertura = Cobertura("OSDE", 80, identificador_externo="OS-9001", elegida_en=elegida)
    guardado = repo.guardar_cobertura(1, cobertura)

    assert guardado.cobertura.obra_social == "OSDE"
    assert guardado.cobertura.identificador_externo == "OS-9001"
    assert guardado.cobertura.elegida_en == elegida
    assert [e.id for e in repo.listar_con_cobertura()] == [1]

    cobertura.estado, cobertura.motivo_rechazo = "Rechazado", "Sin cobertura"
    assert repo.guardar_cobertura(1, cobertura).cobertura.motivo_rechazo == "Sin cobertura"
    assert len(db.rows("authorizations")) == 1


def test_the_court_decision_is_stored_as_hex_and_read_back_as_bytes(repo, db):
    cobertura = Cobertura("OSDE", 80, demanda=PDF, demanda_nombre="demanda.pdf", demanda_en=ahora())
    repo.guardar_cobertura(1, cobertura)

    assert db.rows("authorizations")[0]["demand_pdf"] == "\\x" + PDF.hex()
    assert repo.obtener_demanda(1) == PDF
    assert repo.obtener(1).cobertura.tiene_demanda


def test_the_listings_never_ask_for_the_pdf_of_the_decision(repo, db):
    repo.guardar_cobertura(
        1, Cobertura("OSDE", 80, demanda=PDF, demanda_nombre="demanda.pdf", demanda_en=ahora())
    )
    db.selects.clear()

    repo.listar_con_cobertura()
    repo.listar_de_paciente(LUCIA)
    repo.listar_creados_sin_presupuesto()
    repo.obtener(1)

    assert "demand_pdf" not in db.columns_requested("authorizations")
    assert "*" not in {c for _, cols in db.selects for c in cols.split(",")}


def test_saving_a_coverage_read_from_a_listing_keeps_the_stored_pdf(repo):
    repo.guardar_cobertura(
        1, Cobertura("OSDE", 80, demanda=PDF, demanda_nombre="demanda.pdf", demanda_en=ahora())
    )
    leida = repo.listar_con_cobertura()[0].cobertura
    assert leida.demanda is None and leida.tiene_demanda

    leida.estado = "Rechazado"
    repo.guardar_cobertura(1, leida)

    assert repo.obtener_demanda(1) == PDF


def test_answering_the_decision_clears_the_pdf(repo):
    cobertura = Cobertura("OSDE", 80, demanda=PDF, demanda_nombre="demanda.pdf", demanda_en=ahora())
    repo.guardar_cobertura(1, cobertura)

    cobertura.demanda = cobertura.demanda_nombre = cobertura.demanda_en = None
    repo.guardar_cobertura(1, cobertura)

    assert repo.obtener_demanda(1) is None
    assert not repo.obtener(1).cobertura.tiene_demanda


# --- state changes and their history ------------------------------------------------------


def test_a_state_change_updates_the_study_and_leaves_its_row_in_the_history(repo, db):
    estudio = repo.cambiar_estado(1, EstadoEstudio.PAGADO, ahora(), ADMIN_ID)

    assert estudio.estado == EstadoEstudio.PAGADO
    assert db.rows("studies")[0]["state"] == "Pagado"
    ultimo = db.rows("study_state_history")[-1]
    assert (ultimo["study_id"], ultimo["from_state"], ultimo["to_state"]) == (1, "Creado", "Pagado")
    assert ultimo["changed_by"] == ADMIN_ID


def test_the_history_comes_back_in_order_with_each_visit_to_a_state(repo):
    repo.cambiar_estado(1, EstadoEstudio.PAGADO, ahora())
    repo.cambiar_estado(1, EstadoEstudio.TURNO_SACADO, ahora())
    repo.cambiar_estado(1, EstadoEstudio.PAGADO, ahora())
    repo.cambiar_estado(1, EstadoEstudio.TURNO_SACADO, ahora())

    pasos = [(c.desde, c.hacia) for c in repo.obtener(1).historial]
    assert pasos == [
        (None, EstadoEstudio.CREADO),
        (EstadoEstudio.CREADO, EstadoEstudio.PAGADO),
        (EstadoEstudio.PAGADO, EstadoEstudio.TURNO_SACADO),
        (EstadoEstudio.TURNO_SACADO, EstadoEstudio.PAGADO),
        (EstadoEstudio.PAGADO, EstadoEstudio.TURNO_SACADO),
    ]


def test_an_invalid_transition_changes_nothing_and_writes_no_history(repo, db):
    antes = len(db.rows("study_state_history"))

    with pytest.raises(BusinessRuleError) as error:
        repo.cambiar_estado(1, EstadoEstudio.LISTO_PARA_RETIRAR, ahora(), ADMIN_ID)

    assert error.value.code == "transicion_invalida"
    assert db.rows("studies")[0]["state"] == "Creado"
    assert len(db.rows("study_state_history")) == antes


def test_a_change_on_a_missing_study_is_a_404(repo):
    with pytest.raises(BusinessRuleError) as error:
        repo.cambiar_estado(99, EstadoEstudio.PAGADO, ahora())
    assert error.value.status_code == 404


# --- financial record ---------------------------------------------------------------------


def test_the_financial_record_lists_the_newest_first_with_patient_and_coupon(repo, db):
    db.rows("coupons").append({"id": 7, "code": "CUP-1"})
    estudio = repo.obtener(1)
    repo.registrar_asiento(estudio, 500, "tarjeta_credito", ahora())
    asiento = repo.registrar_asiento(estudio, 400, "transferencia", ahora(), "CUP-1")

    assert asiento.paciente == "Lucía Fernández"
    assert db.rows("payments")[-1]["coupon_id"] == 7
    registro = repo.listar_asientos()
    assert [(a.importe_usd, a.metodo, a.cupon) for a in registro] == [
        (400, "transferencia", "CUP-1"),
        (500, "tarjeta_credito", None),
    ]
    assert registro[0].paciente == "Lucía Fernández"


# --- through the services, over the Supabase repository -----------------------------------


def test_paying_changes_the_state_through_the_history_and_answers_with_the_new_one(repo, db):
    repo.guardar_presupuesto(1, 590, ahora(), ADMIN_ID)
    servicio = PacienteServicio(repo, ObrasSocialesFalsa(), AvisosEspia(), None, None)

    pago = servicio.pagar(LUCIA, 1, "tarjeta_credito", PATIENT_ACCOUNT_ID)

    assert pago.estado == EstadoEstudio.PAGADO
    assert pago.importe_usd == 590
    assert db.rows("studies")[0]["state"] == "Pagado"
    ultimo = db.rows("study_state_history")[-1]
    assert (ultimo["to_state"], ultimo["changed_by"]) == ("Pagado", PATIENT_ACCOUNT_ID)
    assert db.rows("payments")[0]["method"] == "tarjeta_credito"


def test_authorizing_answers_with_the_new_state_and_records_the_entry(repo, db):
    repo.guardar_presupuesto(1, 590, ahora(), ADMIN_ID)
    PacienteServicio(repo, ObrasSocialesFalsa(), AvisosEspia(), None, None).elegir_cobertura(
        LUCIA, 1, "OSDE"
    )

    respuesta = AutorizacionServicio(repo, AvisosEspia()).registrar_respuesta(
        1, AUTORIZADO, None, ADMIN_ID
    )

    assert respuesta.estado == EstadoEstudio.AUTORIZADO
    assert db.rows("studies")[0]["state"] == "Autorizado"
    assert db.rows("study_state_history")[-1]["changed_by"] == ADMIN_ID
    assert db.rows("payments")[0]["method"] == "obra_social (OSDE)"
    assert db.rows("authorizations")[0]["registered_by"] == ADMIN_ID
    assert repo.obtener(1).cobertura.registrada_por == ADMIN_ID
    assert repo.obtener(1).cobertura.estado == AUTORIZADO


def test_lists_the_studies_in_the_given_states_with_the_dni_of_the_patient(repo, db):
    db.rows("studies")[1]["state"] = "EnViajeACorea"

    (estudio,) = repo.listar_por_estados([EstadoEstudio.EN_VIAJE_A_COREA])

    assert (estudio.id, estudio.paciente, estudio.dni) == (2, "Lucía Fernández", "30111222")
    assert estudio.estado == EstadoEstudio.EN_VIAJE_A_COREA


def test_the_states_are_a_filter_and_the_studies_come_in_order(repo, db):
    db.rows("studies")[0]["state"] = "EnElAreaDeBioinformatica"
    db.rows("studies")[1]["state"] = "EnViajeACorea"

    estados = [EstadoEstudio.EN_VIAJE_A_COREA, EstadoEstudio.EN_EL_AREA_DE_BIOINFORMATICA]

    assert [e.id for e in repo.listar_por_estados(estados)] == [1, 2]
    assert [e.id for e in repo.listar_por_estados([EstadoEstudio.PAGADO])] == []
    assert repo.listar_por_estados([]) == []
