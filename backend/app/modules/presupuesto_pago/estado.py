"""Lifecycle of a study: which state changes are valid.

A study is always in exactly one state, and any change that is not listed here is rejected.
TODO: the study state model belongs to Integrante A (task T1). When it lands in `core/`, this
table moves there and the modules keep calling `validate_transition`.
"""

from app.core.enums import EstadoEstudio as E
from app.core.errors import BusinessRuleError

TRANSITIONS: dict[E, frozenset[E]] = {
    E.CREADO: frozenset({E.PAGADO, E.AUTORIZADO, E.RECHAZADO}),
    E.RECHAZADO: frozenset({E.AUTORIZADO}),
    E.PAGADO: frozenset({E.TURNO_SACADO}),
    E.AUTORIZADO: frozenset({E.TURNO_SACADO}),
    # Cancelling returns the study to its previous state; a resampling keeps it in TurnoSacado.
    E.TURNO_SACADO: frozenset({E.PAGADO, E.AUTORIZADO, E.LISTO_PARA_RETIRAR, E.TURNO_SACADO}),
    E.LISTO_PARA_RETIRAR: frozenset({E.EN_CAMINO_AL_LABORATORIO_CENTRAL}),
    E.EN_CAMINO_AL_LABORATORIO_CENTRAL: frozenset({E.EN_LABORATORIO_CENTRAL}),
    E.EN_LABORATORIO_CENTRAL: frozenset({E.EN_VIAJE_A_COREA}),
    E.EN_VIAJE_A_COREA: frozenset({E.EN_EL_AREA_DE_BIOINFORMATICA}),
    E.EN_EL_AREA_DE_BIOINFORMATICA: frozenset({E.EN_ANALISIS_POR_UN_BIOINFORMATICO}),
    E.EN_ANALISIS_POR_UN_BIOINFORMATICO: frozenset({E.RESULTADO_DISPONIBLE, E.TURNO_SACADO}),
    E.RESULTADO_DISPONIBLE: frozenset(),
}


def can_transition(current: E, new: E) -> bool:
    return new in TRANSITIONS[current]


def validate_transition(current: E, new: E) -> None:
    if not can_transition(current, new):
        raise BusinessRuleError(
            f"El estudio no puede pasar de {current.value} a {new.value}.",
            code="transicion_invalida",
        )
