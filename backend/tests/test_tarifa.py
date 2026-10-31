import pytest

from app.modules.presupuesto_pago.tarifa import calcular_importe


@pytest.mark.parametrize(
    ("genes", "importe"),
    [(0, 500), (1, 500), (5, 500), (6, 530), (10, 650)],
)
def test_calcular_importe(genes, importe):
    assert calcular_importe(genes) == importe


def test_calcular_importe_rechaza_cantidad_negativa():
    with pytest.raises(ValueError):
        calcular_importe(-1)
