from app.core.enums import CdssStrategy
from app.core.errors import BusinessRuleError
from app.modules.config_medica import repository

CDSS_STRATEGY_KEY = "cdss_strategy"
# Propuesta para la decisión 4: queda a confirmar con el PO y el equipo.
DEFAULT_CDSS_STRATEGY = CdssStrategy.MATCHING_CARDINAL_SYMPTOMS


def _clean(symptom: dict) -> dict:
    return {"code": symptom["code"].strip(), "term": symptom["term"].strip()}


def list_pathologies() -> list[dict]:
    return repository.list_all()


def create_pathology(data: dict) -> dict:
    """Da de alta la patología con su cardinal y sus secundarios."""
    try:
        return repository.create(
            repository.normalize_name(data["name"]),
            _clean(data["cardinal"]),
            [_clean(symptom) for symptom in data["secondary"]],
        )
    except repository.NameTaken:
        # Otra alta con el mismo nombre ganó de mano entre la validación y el guardado
        raise BusinessRuleError("Ya existe una patología con ese nombre.") from None


def replace_symptoms(pathology_id: int, data: dict) -> dict:
    """Reemplaza los síntomas de la patología.

    Los pacientes ya registrados no cambian (P13).
    """
    if repository.find_by_id(pathology_id) is None:
        raise BusinessRuleError("La patología no existe.", 404)
    return repository.replace_symptoms(
        pathology_id,
        _clean(data["cardinal"]),
        [_clean(symptom) for symptom in data["secondary"]],
    )


def get_cdss_strategy() -> str:
    """El alta de paciente se la pasa al CDSS."""
    return repository.get_setting(CDSS_STRATEGY_KEY) or DEFAULT_CDSS_STRATEGY.value


def set_cdss_strategy(strategy: str, user: dict) -> str:
    repository.save_setting(CDSS_STRATEGY_KEY, strategy, user["id"])
    return strategy
