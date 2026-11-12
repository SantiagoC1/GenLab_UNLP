
"""Development-only logistics delivery and batch simulator.

All studies and patients are fictional. Data resets on restart.
"""

from datetime import date, datetime, timezone
from threading import Lock

from fastapi import HTTPException

from app.modules.logistics import mock_ministry, mock_repository

from app.modules.logistics import mock_fedex


_delivery_lock = Lock()
_deliveries: dict[tuple[str, str], dict] = {}
_batches: list[dict] = []
_next_batch_id = 1

_MOCK_STUDIES = {
    101: [1001, 1002, 1003, 1004],
    102: [1005, 1006, 1007],
    103: [1008, 1009, 1010, 1011, 1012],
}

# The priority is assigned when the study is created.
# This fictional study represents a Pompe case under four months.
_MOCK_URGENT_STUDIES = {1008}
_study_states: dict[int, str] = {}
_raw_study_files: dict[int, dict] = {}
_bioinformatics_notifications: list[dict] = []
BATCH_CAPACITY = 10


def _get_route(carrier_id: str, route_date: date) -> dict:
    route = mock_repository.get_daily_route(
        carrier_id,
        route_date.isoformat(),
    )

    if route is None:
        raise HTTPException(
            status_code=404,
            detail="No route found for the selected date.",
        )

    return route


def _get_route_stops(route_id: int) -> list[dict]:
    return mock_repository.get_route_stops(route_id)


def _create_batch() -> dict:
    global _next_batch_id

    batch = {
        "id": _next_batch_id,
        "state": "Abierto",
        "study_ids": [],
        "is_urgent": False,
        "closed_at": None,
        "authorized_at": None,
        "csv_content": None,
        "permit_content": None,
        "authorization_error": None,
        "scheduled_pickup_at": None,
        "collected_at": None,
        "fedex_url": None,
    }

    _next_batch_id += 1
    _batches.append(batch)
    return batch


def _get_open_batch() -> dict:
    for batch in _batches:
        if batch["state"] == "Abierto":
            return batch

    return _create_batch()


def _authorize_closed_batch(batch: dict) -> None:
    try:
        result = mock_ministry.request_authorization(
            batch_id=batch["id"],
            study_ids=list(batch["study_ids"]),
        )

        batch["csv_content"] = result["csv_content"]
        batch["permit_content"] = result["permit_content"]
        batch["authorized_at"] = result["authorized_at"]
        batch["authorization_error"] = result["error"]

        if result["authorized"] and result["permit_content"]:
            batch["state"] = "Autorizado"
        else:
            batch["state"] = "Cerrado"

    except Exception:
        batch["state"] = "Cerrado"
        batch["authorization_error"] = (
            "No se pudo completar la solicitud al Ministerio."
        )


def _close_batch(
    batch: dict,
    closed_at: datetime,
    is_urgent: bool = False,
) -> None:
    batch["state"] = "Cerrado"
    batch["closed_at"] = closed_at
    batch["is_urgent"] = is_urgent

    _authorize_closed_batch(batch)

    # Ensure subsequent studies enter a different open batch.
    _get_open_batch()


def get_delivery_status(
    carrier_id: str,
    route_date: date,
) -> dict:
    route = _get_route(carrier_id, route_date)
    stops = _get_route_stops(route["id"])

    pending_stops = [
        stop for stop in stops
        if stop["picked_up_at"] is None
    ]

    delivery_key = (carrier_id, route_date.isoformat())

    with _delivery_lock:
        delivery = _deliveries.get(delivery_key)

        return {
            "route_id": route["id"],
            "date": route_date,
            "total_stops": len(stops),
            "completed_stops": len(stops) - len(pending_stops),
            "can_deliver": (
                len(stops) > 0
                and not pending_stops
                and delivery is None
            ),
            "delivered_at": (
                delivery["delivered_at"] if delivery else None
            ),
            "study_count": (
                delivery["study_count"] if delivery else None
            ),
        }


def register_delivery(
    carrier_id: str,
    route_date: date,
) -> dict:
    route = _get_route(carrier_id, route_date)
    delivery_key = (carrier_id, route_date.isoformat())

    with _delivery_lock:
        if delivery_key in _deliveries:
            raise HTTPException(
                status_code=409,
                detail="This delivery has already been registered.",
            )

        stops = sorted(
            _get_route_stops(route["id"]),
            key=lambda stop: stop["position"],
        )

        if not stops:
            raise HTTPException(
                status_code=409,
                detail="The route has no stops.",
            )

        if any(stop["picked_up_at"] is None for stop in stops):
            raise HTTPException(
                status_code=409,
                detail="All pickups must be completed first.",
            )

        study_ids = [
            study_id
            for stop in stops
            for study_id in _MOCK_STUDIES.get(stop["lab_id"], [])
        ]

        delivered_at = datetime.now(timezone.utc)
        assigned_batch_ids: list[int] = []

        for study_id in study_ids:
            batch = _get_open_batch()
            batch["study_ids"].append(study_id)
            _study_states[study_id] = "EnLaboratorioCentral"

            if batch["id"] not in assigned_batch_ids:
                assigned_batch_ids.append(batch["id"])

            is_urgent = study_id in _MOCK_URGENT_STUDIES
            is_full = len(batch["study_ids"]) == BATCH_CAPACITY

            if is_urgent or is_full:
                _close_batch(
                    batch=batch,
                    closed_at=delivered_at,
                    is_urgent=is_urgent,
                )

        delivery = {
            "route_id": route["id"],
            "date": route_date,
            "delivered_at": delivered_at,
            "study_count": len(study_ids),
            "batch_ids": assigned_batch_ids,
        }

        _deliveries[delivery_key] = delivery

        return dict(delivery)


def get_batches() -> list[dict]:
    with _delivery_lock:
        return [
            {
                "id": batch["id"],
                "state": batch["state"],
                "study_count": len(batch["study_ids"]),
                "is_urgent": batch["is_urgent"],
                "closed_at": batch["closed_at"],
                "authorized_at": batch["authorized_at"],
                "has_csv": batch["csv_content"] is not None,
                "has_permit": batch["permit_content"] is not None,
                "authorization_error": batch["authorization_error"],
                "can_schedule_pickup": (
                    batch["state"] == "Autorizado"
                    and batch["permit_content"] is not None
                    and batch["fedex_url"] is None
                ),
                "scheduled_pickup_at": batch["scheduled_pickup_at"],
                "collected_at": batch["collected_at"],
                "fedex_url": batch["fedex_url"],
            }
            for batch in _batches
        ]


def get_batch_document(
    batch_id: int,
    document_type: str,
) -> bytes:
    with _delivery_lock:
        batch = next(
            (item for item in _batches if item["id"] == batch_id),
            None,
        )

        if batch is None:
            raise HTTPException(404, "Batch not found.")

        if document_type == "csv":
            content = batch["csv_content"]
        elif document_type == "permit":
            content = batch["permit_content"]
        else:
            raise HTTPException(400, "Invalid document type.")

        if content is None:
            raise HTTPException(
                404,
                "Document is not available.",
            )

        return content


def schedule_batch_pickup(
    batch_id: int,
    scheduled_at: datetime,
) -> dict:
    with _delivery_lock:
        batch = next(
            (item for item in _batches if item["id"] == batch_id),
            None,
        )

        if batch is None:
            raise HTTPException(404, "No se encontró el lote.")

        if (
            batch["state"] != "Autorizado"
            or batch["permit_content"] is None
        ):
            raise HTTPException(
                409,
                "El lote necesita autorización del Ministerio.",
            )

        shipment = mock_fedex.schedule_pickup(
            batch_id=batch_id,
            scheduled_at=scheduled_at,
        )

        batch["state"] = "RetiroProgramado"
        batch["scheduled_pickup_at"] = shipment[
            "scheduled_pickup_at"
        ]
        batch["fedex_url"] = shipment["tracking_url"]

        return shipment


def register_fedex_collection(batch_id: int) -> dict:
    """Confirm collection and update all studies in the batch."""
    with _delivery_lock:
        batch = next(
            (item for item in _batches if item["id"] == batch_id),
            None,
        )

        if batch is None:
            raise HTTPException(
                status_code=404,
                detail="No se encontró el lote.",
            )

        if batch["state"] != "RetiroProgramado":
            raise HTTPException(
                status_code=409,
                detail="El lote no está pendiente de retiro.",
            )

        shipment = mock_fedex.simulate_collection(batch_id)

        batch["state"] = "EnViajeACorea"
        batch["collected_at"] = shipment["collected_at"]

        for study_id in batch["study_ids"]:
            _study_states[study_id] = "EnViajeACorea"

        return shipment

def get_batch_studies(batch_id: int) -> list[dict]:
    """Return fictional studies and their current states."""
    with _delivery_lock:
        batch = next(
            (item for item in _batches if item["id"] == batch_id),
            None,
        )

        if batch is None:
            raise HTTPException(
                status_code=404,
                detail="No se encontró el lote.",
            )

        return [
            {
                "id": study_id,
                "batch_id": batch_id,
                "state": _study_states[study_id],
                "pompe_urgent": study_id in _MOCK_URGENT_STUDIES,
            }
            for study_id in batch["study_ids"]
        ]



def get_studies_awaiting_raw_data() -> list[dict]:
    """List fictional studies whose raw data can be uploaded."""
    with _delivery_lock:
        return [
            {
                "id": study_id,
                "batch_id": batch["id"],
                "state": _study_states.get(study_id),
                "pompe_urgent": study_id in _MOCK_URGENT_STUDIES,
            }
            for batch in _batches
            for study_id in batch["study_ids"]
            if _study_states.get(study_id) == "EnViajeACorea"
        ]


def upload_study_raw_data(
    study_id: int,
    filename: str,
    content: bytes,
) -> dict:
    """Attach raw data to one fictional study and notify analysts."""
    with _delivery_lock:
        study_exists = any(
            study_id in batch["study_ids"]
            for batch in _batches
        )

        if not study_exists:
            raise HTTPException(
                status_code=404,
                detail="No se encontró el estudio.",
            )

        if _study_states.get(study_id) != "EnViajeACorea":
            raise HTTPException(
                status_code=409,
                detail=(
                    "Solo se pueden cargar datos crudos de estudios "
                    "en viaje a Corea."
                ),
            )

        if not content:
            raise HTTPException(
                status_code=400,
                detail="El archivo no puede estar vacío.",
            )

        if not filename.strip():
            raise HTTPException(
                status_code=400,
                detail="El archivo debe tener un nombre.",
            )

        uploaded_at = datetime.now(timezone.utc)

        # Development-only storage. Never use this for real patient data.
        _raw_study_files[study_id] = {
            "filename": filename,
            "content": content,
            "uploaded_at": uploaded_at,
        }

        _study_states[study_id] = "EnElAreaDeBioinformatica"

        _bioinformatics_notifications.append(
            {
                "study_id": study_id,
                "recipient_role": "bioinformatico",
                "channel": "email",
                "status": "Simulado",
                "created_at": uploaded_at,
            }
        )

        return {
            "study_id": study_id,
            "state": _study_states[study_id],
            "filename": filename,
            "file_size": len(content),
            "uploaded_at": uploaded_at,
            "notification_status": "Simulado",
        }


def get_bioinformatics_notifications() -> list[dict]:
    """Expose simulated notification events for development tests."""
    with _delivery_lock:
        return [
            dict(notification)
            for notification in _bioinformatics_notifications
        ]
