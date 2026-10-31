"""Tarifa fija del presupuesto (M4-RF1). No es editable por el administrativo."""

IMPORTE_BASE_USD = 500
GENES_INCLUIDOS = 5
IMPORTE_GEN_ADICIONAL_USD = 30


def calcular_importe(cantidad_genes: int) -> int:
    """USD 500 hasta 5 genes y USD 30 por cada gen adicional (extracción y turno incluidos)."""
    if cantidad_genes < 0:
        raise ValueError("La cantidad de genes no puede ser negativa")
    adicionales = max(0, cantidad_genes - GENES_INCLUIDOS)
    return IMPORTE_BASE_USD + adicionales * IMPORTE_GEN_ADICIONAL_USD
