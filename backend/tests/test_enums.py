from app.core.enums import EstadoEstudio, Rol


def test_estados_del_estudio():
    assert [e.value for e in EstadoEstudio] == [
        "Creado",
        "Pagado",
        "Autorizado",
        "Rechazado",
        "TurnoSacado",
        "ListoParaRetirar",
        "EnCaminoAlLaboratorioCentral",
        "EnLaboratorioCentral",
        "EnViajeACorea",
        "EnElAreaDeBioinformatica",
        "EnAnalisisPorUnBioinformatico",
        "ResultadoDisponible",
    ]


def test_pompe_urgente_no_es_un_estado():
    assert "PompeUrgente" not in {e.value for e in EstadoEstudio}


def test_roles():
    assert {r.value for r in Rol} == {
        "administrador_general",
        "gerente_medico",
        "medico_tratante",
        "paciente",
        "administrativo_laboratorio",
        "transportista",
        "bioinformatico",
    }
