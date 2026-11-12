from app.core.enums import CdssStrategy
from app.core.errors import BusinessRuleError
from app.models import app_setting
from app.models import pathology as pathology_model

CDSS_STRATEGY_KEY = "cdss_strategy"
# Propuesta para la decisión 4: queda a confirmar con el PO y el equipo.
DEFAULT_CDSS_STRATEGY = CdssStrategy.MATCHING_CARDINAL_SYMPTOMS


def _clean(symptom: dict) -> dict:
    return {"code": symptom["code"].strip(), "term": symptom["term"].strip()}


def list_pathologies() -> list[dict]:
    return pathology_model.list_all()


def create_pathology(data: dict) -> dict:
    """Escenario 5: da de alta la patología con su cardinal y sus secundarios."""
    try:
        return pathology_model.create(
            data["name"].strip(),
            _clean(data["cardinal"]),
            [_clean(symptom) for symptom in data["secondary"]],
        )
    except pathology_model.NameTaken:
        # Otra alta con el mismo nombre ganó de mano entre la validación y el guardado
        raise BusinessRuleError("Ya existe una patología con ese nombre.") from None


def replace_symptoms(pathology_id: int, data: dict) -> dict:
    """Escenario 6: reemplaza los síntomas. Los pacientes ya registrados no cambian (P13)."""
    if pathology_model.find_by_id(pathology_id) is None:
        raise BusinessRuleError("La patología no existe.", 404)
    return pathology_model.replace_symptoms(
        pathology_id,
        _clean(data["cardinal"]),
        [_clean(symptom) for symptom in data["secondary"]],
    )


def get_cdss_strategy() -> str:
    """REUTILIZABLE: el alta de paciente (M3) le pasa esta estrategia al CDSS."""
    return app_setting.get(CDSS_STRATEGY_KEY) or DEFAULT_CDSS_STRATEGY.value


def set_cdss_strategy(strategy: str, user: dict) -> str:
    app_setting.save(CDSS_STRATEGY_KEY, strategy, user["id"])
    return strategy
