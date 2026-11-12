
"""Development-only notification inbox.

Uses fictional identities and existing simulated events.
Does not send emails or modify study states.
"""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.modules.bioinformatica import mock_service as bioinformatics
from app.modules.logistics import mock_delivery


MOCK_ACTORS = {
    "medico_tratante": bioinformatics.MOCK_DOCTORS,
    "paciente": bioinformatics.MOCK_PATIENTS,
    "bioinformatico": bioinformatics.MOCK_BIOINFORMATICIANS,
}

RESULT_DESTINATIONS = {
    "medico_tratante": "/medico_tratante/resultado",
    "paciente": "/paciente/resultado",
}

ANALYST_DESTINATION = "/bioinformatico/estudios-disponibles"


def _validate_actor(role: str, actor_id: str) -> None:
    actors = MOCK_ACTORS.get(role)

    if actors is None:
        raise HTTPException(
            403,
            "Este rol no tiene avisos simulados disponibles.",
        )

    if actor_id not in actors:
        raise HTTPException(
            400,
            "El usuario de prueba no es válido.",
        )


def _build_notice(
    notice_id: str,
    study_id: int,
    title: str,
    message: str,
    created_at: datetime,
    destination: str | None,
) -> dict:
    return {
        "id": notice_id,
        "study_id": study_id,
        "title": title,
        "message": message,
        "created_at": created_at,
        "destination": destination,
        "pending": True,
        "simulated": True,
    }


def list_notices(role: str, actor_id: str) -> list[dict]:
    _validate_actor(role, actor_id)

    with mock_delivery._delivery_lock:
        events = list(mock_delivery._bioinformatics_notifications)
        notices = []

        for index, event in enumerate(events):
            study_id = event["study_id"]
            recipient_role = event["recipient_role"]

            if recipient_role != role:
                continue

            if role in ("medico_tratante", "paciente"):
                owners = bioinformatics.MOCK_STUDY_OWNERS.get(study_id)

                if owners is None:
                    continue

                owner_id = (
                    owners[0]
                    if role == "medico_tratante"
                    else owners[1]
                )

                if owner_id != actor_id:
                    continue

                if (
                    mock_delivery._study_states.get(study_id)
                    != "ResultadoDisponible"
                ):
                    continue

                notices.append(
                    _build_notice(
                        notice_id=f"result-{index}",
                        study_id=study_id,
                        title="Resultado disponible",
                        message=(
                            f"El resultado del estudio #{study_id} "
                            "está disponible para consultar."
                        ),
                        created_at=event["created_at"],
                        destination=RESULT_DESTINATIONS[role],
                    )
                )

            elif role == "bioinformatico":
                if (
                    mock_delivery._study_states.get(study_id)
                    != "EnElAreaDeBioinformatica"
                ):
                    continue

                notices.append(
                    _build_notice(
                        notice_id=f"raw-data-{index}",
                        study_id=study_id,
                        title="Datos crudos disponibles",
                        message=(
                            f"Se cargaron los datos crudos del "
                            f"estudio #{study_id}."
                        ),
                        created_at=event["created_at"],
                        destination=ANALYST_DESTINATION,
                    )
                )

        return sorted(
            notices,
            key=lambda notice: notice["created_at"],
            reverse=True,
        )


def get_notice_summary(role: str, actor_id: str) -> dict:
    notices = list_notices(role, actor_id)

    return {
        "total": len(notices),
        "pending_count": sum(
            1 for notice in notices if notice["pending"]
        ),
        "has_pending": any(
            notice["pending"] for notice in notices
        ),
        "simulated": True,
    }
