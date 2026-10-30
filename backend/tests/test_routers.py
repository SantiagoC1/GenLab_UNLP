import pytest

MODULOS = [
    "config_medica",
    "consulta_medica",
    "presupuesto_pago",
    "cupones",
    "turnos",
    "logistica",
    "bioinformatica",
    "avisos",
]


@pytest.mark.parametrize("modulo", MODULOS)
def test_router_registrado(client, modulo):
    r = client.get(f"/{modulo}/ping")
    assert r.status_code == 200
    assert r.json() == {"modulo": modulo}
