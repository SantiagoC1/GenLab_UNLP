
"""Development-only reanalysis requests.

All identities, pathologies and gene associations are fictional.
Requests do not trigger payment, state changes or automatic analysis.
"""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.modules.bioinformatica import mock_service
from app.modules.logistics import mock_delivery


# Fictional associations for workflow testing only.
# These genes must not be interpreted as clinical recommendations.
MOCK_REANALYSIS_PATHOLOGIES = {
    "Patología simulada D": ["GEN-SIM-01", "GEN-SIM-02"],
    "Patología simulada E": ["GEN-SIM-02", "GEN-SIM-03"],
    "Patología simulada F": ["GLA", "GEN-SIM-04"],
    "Patología simulada G": ["GLA"],
}

_reanalysis_requests: dict[int, dict] = {}
_next_request_id = 1


def _validate_doctor(study_id: int, doctor_id: str) -> None:
    """Validate ownership while holding the shared delivery lock."""
    mock_service._validate_result_access(
        study_id,
        "medico_tratante",
        doctor_id,
    )


def _validate_completed_study(study_id: int) -> dict:
    """Validate the original result while holding the shared lock."""
    if mock_delivery._study_states.get(study_id) != "ResultadoDisponible":
        raise HTTPException(
            409,
            "El estudio todavía no tiene un resultado disponible.",
        )

    original = mock_service._analysis_records.get(study_id)

    if (
        original is None
        or original.get("completed_at") is None
        or original.get("pdf") is None
    ):
        raise HTTPException(
            409,
            "El estudio no tiene un análisis original finalizado.",
        )

    if study_id not in mock_delivery._raw_study_files:
        raise HTTPException(
            409,
            "No se encontraron los datos crudos originales.",
        )

    return original


def _analyzed_genes(study_id: int) -> set[str]:
    """Determine covered genes, including genes with no variants.

    The 8.3 simulator does not persist analyzed genes separately.
    Its completed original analysis covers the entire gene catalogue
    returned for the original study pathology.
    """
    original = mock_service._analysis_records.get(study_id)

    if original is None or original.get("completed_at") is None:
        return set()

    genes = set(mock_service._available_genes(study_id))

    # Preserve genes covered by earlier simulated requests if present.
    for request in _reanalysis_requests.values():
        if (
            request["study_id"] == study_id
            and request["status"] == "Completed"
        ):
            genes.update(request["pending_genes"])

    return genes


def list_pathologies() -> list[dict]:
    return [
        {"name": name, "simulated": True}
        for name in sorted(MOCK_REANALYSIS_PATHOLOGIES)
    ]


def preview_reanalysis(
    study_id: int,
    doctor_id: str,
    pathology: str,
) -> dict:
    with mock_delivery._delivery_lock:
        _validate_doctor(study_id, doctor_id)
        _validate_completed_study(study_id)

        candidate_genes = MOCK_REANALYSIS_PATHOLOGIES.get(pathology)

        if candidate_genes is None:
            raise HTTPException(
                400,
                "La patología de prueba seleccionada no es válida.",
            )

        analyzed = _analyzed_genes(study_id)
        pending = sorted(set(candidate_genes) - analyzed)
        excluded = sorted(set(candidate_genes) & analyzed)

        existing = _reanalysis_requests.get(study_id)

        return {
            "study_id": study_id,
            "pathology": pathology,
            "candidate_genes": sorted(set(candidate_genes)),
            "analyzed_genes": sorted(analyzed),
            "pending_genes": pending,
            "excluded_genes": excluded,
            "can_request": bool(pending) and existing is None,
            "has_pending_request": existing is not None,
            "simulated": True,
        }


def request_reanalysis(
    study_id: int,
    doctor_id: str,
    pathology: str,
) -> dict:
    global _next_request_id

    with mock_delivery._delivery_lock:
        _validate_doctor(study_id, doctor_id)
        _validate_completed_study(study_id)

        candidate_genes = MOCK_REANALYSIS_PATHOLOGIES.get(pathology)

        if candidate_genes is None:
            raise HTTPException(
                400,
                "La patología de prueba seleccionada no es válida.",
            )

        if study_id in _reanalysis_requests:
            raise HTTPException(
                409,
                "Ya existe una solicitud de reanálisis para este estudio.",
            )

        analyzed = _analyzed_genes(study_id)
        pending = sorted(set(candidate_genes) - analyzed)

        if not pending:
            raise HTTPException(
                409,
                "No hay genes nuevos para analizar.",
            )

        original = mock_service._analysis_records[study_id]
        requested_at = datetime.now(timezone.utc)

        request = {
            "id": _next_request_id,
            "study_id": study_id,
            "doctor_id": doctor_id,
            "pathology": pathology,
            "candidate_genes": sorted(set(candidate_genes)),
            "excluded_genes": sorted(
                set(candidate_genes) & analyzed
            ),
            "pending_genes": pending,
            "requested_at": requested_at,
            "status": "PendingDefinition",
            "original_completed_at": original["completed_at"],
            "uses_existing_raw_data": True,
            "payment_required": None,
            "simulated": True,
        }

        _next_request_id += 1
        _reanalysis_requests[study_id] = request

        return dict(request)


def get_reanalysis_request(
    study_id: int,
    doctor_id: str,
) -> dict | None:
    with mock_delivery._delivery_lock:
        _validate_doctor(study_id, doctor_id)

        request = _reanalysis_requests.get(study_id)

        return dict(request) if request is not None else None
