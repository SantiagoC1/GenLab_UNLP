
"""Development-only bioinformatics workflow.

All studies and users are fictional. Data resets on server restart.
Never use this module with real patient information.
"""

from datetime import datetime, timezone

from fastapi import HTTPException

from app.integrations.apigen import ApigenSimulador
from app.modules.logistics import mock_delivery

from io import BytesIO
from threading import Lock


MOCK_BIOINFORMATICIANS = {
    "analyst-1": "Bioinformático de prueba 1",
    "analyst-2": "Bioinformático de prueba 2",
}

# Fictional study metadata used only to exercise the external adapter.
# These are not real clinical associations or diagnostic results.
MOCK_STUDY_PATHOLOGIES = {
    1001: "Patología simulada A",
    1002: "Patología simulada B",
    1003: "Patología simulada C",
    1004: "Patología simulada A",
    1005: "Patología simulada B",
    1006: "Patología simulada C",
    1007: "Patología simulada A",
    1008: "Pompe",
    1009: "Patología simulada B",
    1010: "Patología simulada C",
    1011: "Patología simulada A",
    1012: "Patología simulada B",
}

_assignments: dict[int, dict] = {}

_analysis_records: dict[int, dict] = {}

# Development-only variant catalogue. These are not clinical findings.
_MOCK_VARIANT_CLASSES = {
    "Patogénica",
    "Benigna",
    "VUS",
}


def _find_study_batch(study_id: int) -> int | None:
    for batch in mock_delivery._batches:
        if study_id in batch["study_ids"]:
            return batch["id"]
    return None


def _get_arrival_time(study_id: int) -> datetime:
    uploaded_file = mock_delivery._raw_study_files.get(study_id)

    if uploaded_file is None:
        raise HTTPException(
            status_code=409,
            detail="El estudio todavía no tiene datos crudos cargados.",
        )

    return uploaded_file["uploaded_at"]


def _study_details(study_id: int, batch_id: int) -> dict:
    return {
        "id": study_id,
        "batch_id": batch_id,
        "state": mock_delivery._study_states[study_id],
        "pompe_urgent": (
            study_id in mock_delivery._MOCK_URGENT_STUDIES
        ),
        "arrived_at": _get_arrival_time(study_id),
        "pathology": MOCK_STUDY_PATHOLOGIES.get(
            study_id,
            "Patología simulada",
        ),
    }


def list_available_studies() -> list[dict]:
    """List unassigned studies, prioritizing urgent Pompe cases."""
    with mock_delivery._delivery_lock:
        studies = []

        for batch in mock_delivery._batches:
            for study_id in batch["study_ids"]:
                if (
                    mock_delivery._study_states.get(study_id)
                    != "EnElAreaDeBioinformatica"
                ):
                    continue

                studies.append(
                    _study_details(study_id, batch["id"])
                )

        return sorted(
            studies,
            key=lambda study: (
                not study["pompe_urgent"],
                study["arrived_at"],
                study["id"],
            ),
        )


def get_study_genes(study_id: int) -> dict:
    """Query the development Apigen adapter for an available study."""
    with mock_delivery._delivery_lock:
        if _find_study_batch(study_id) is None:
            raise HTTPException(
                status_code=404,
                detail="No se encontró el estudio.",
            )

        if (
            mock_delivery._study_states.get(study_id)
            != "EnElAreaDeBioinformatica"
        ):
            raise HTTPException(
                status_code=409,
                detail="El estudio ya no está disponible.",
            )

        pathology = MOCK_STUDY_PATHOLOGIES.get(
            study_id,
            "Patología simulada",
        )

    # The external adapter is a simulator, not a clinical gene catalogue.
    genes = ApigenSimulador().genes_por_patologia(pathology)

    return {
        "study_id": study_id,
        "pathology": pathology,
        "genes": genes,
        "simulated": True,
    }


def take_study(study_id: int, analyst_id: str) -> dict:
    """Atomically assign an available study to one fictional analyst."""
    if analyst_id not in MOCK_BIOINFORMATICIANS:
        raise HTTPException(
            status_code=400,
            detail="El bioinformático de prueba no es válido.",
        )

    with mock_delivery._delivery_lock:
        batch_id = _find_study_batch(study_id)

        if batch_id is None:
            raise HTTPException(
                status_code=404,
                detail="No se encontró el estudio.",
            )

        if (
            mock_delivery._study_states.get(study_id)
            != "EnElAreaDeBioinformatica"
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "El estudio ya no está disponible. "
                    "Actualizá la lista."
                ),
            )

        if study_id in _assignments:
            raise HTTPException(
                status_code=409,
                detail="El estudio ya fue asignado.",
            )

        assigned_at = datetime.now(timezone.utc)

        assignment = {
            "study_id": study_id,
            "batch_id": batch_id,
            "analyst_id": analyst_id,
            "analyst_name": MOCK_BIOINFORMATICIANS[analyst_id],
            "assigned_at": assigned_at,
            "state": "EnAnalisisPorUnBioinformatico",
        }

        _assignments[study_id] = assignment
        mock_delivery._study_states[
            study_id
        ] = "EnAnalisisPorUnBioinformatico"

        return dict(assignment)


def list_assigned_studies(analyst_id: str) -> list[dict]:
    """Return assignments with their current study states."""
    if analyst_id not in MOCK_BIOINFORMATICIANS:
        raise HTTPException(
            400,
            "El bioinformático de prueba no es válido.",
        )

    with mock_delivery._delivery_lock:
        return sorted(
            [
                {
                    **assignment,
                    "state": mock_delivery._study_states.get(
                        assignment["study_id"],
                        assignment["state"],
                    ),
                }
                for assignment in _assignments.values()
                if assignment["analyst_id"] == analyst_id
            ],
            key=lambda assignment: assignment["assigned_at"],
        )



def _validate_analysis_access(study_id: int, analyst_id: str) -> dict:
    """Call only while holding the delivery lock."""
    if analyst_id not in MOCK_BIOINFORMATICIANS:
        raise HTTPException(400, "El bioinformático de prueba no es válido.")

    assignment = _assignments.get(study_id)
    if assignment is None:
        raise HTTPException(404, "El estudio no está asignado.")

    if assignment["analyst_id"] != analyst_id:
        raise HTTPException(
            403,
            "El estudio está asignado a otro bioinformático.",
        )

    if mock_delivery._study_states.get(study_id) != "EnAnalisisPorUnBioinformatico":
        raise HTTPException(409, "El estudio ya no está en análisis.")

    return assignment


def _available_genes(study_id: int) -> list[str]:
    pathology = MOCK_STUDY_PATHOLOGIES.get(
        study_id, "Patología simulada"
    )
    return ApigenSimulador().genes_por_patologia(pathology)


def _variant_catalogue(gene: str) -> list[dict]:
    """Extend the shared adapter output with development-only test cases."""
    original = ApigenSimulador().variantes_por_gen(gene)

    variants = [
        {
            "gene": gene,
            "variant": item["variante"],
            "classification": item["clasificacion"],
        }
        for item in original
    ]

    variants.extend([
        {
            "gene": gene,
            "variant": f"{gene}:SIM-PAT",
            "classification": "Patogénica",
        },
        {
            "gene": gene,
            "variant": f"{gene}:SIM-BEN",
            "classification": "Benigna",
        },
    ])
    return variants


def get_analysis_genes(study_id: int, analyst_id: str) -> dict:
    with mock_delivery._delivery_lock:
        _validate_analysis_access(study_id, analyst_id)
        genes = _available_genes(study_id)

    return {
        "study_id": study_id,
        "genes": genes,
        "simulated": True,
    }


def get_gene_variants(
    study_id: int,
    analyst_id: str,
    gene: str,
) -> dict:
    with mock_delivery._delivery_lock:
        _validate_analysis_access(study_id, analyst_id)

        if gene not in _available_genes(study_id):
            raise HTTPException(
                400,
                "El gen no pertenece a este estudio.",
            )

        variants = _variant_catalogue(gene)

    return {
        "study_id": study_id,
        "gene": gene,
        "variants": variants,
        "simulated": True,
    }


def get_analysis(study_id: int, analyst_id: str) -> dict:
    with mock_delivery._delivery_lock:
        _validate_analysis_access(study_id, analyst_id)

        record = _analysis_records.get(study_id)

        return {
            "study_id": study_id,
            "variants": [
                dict(item)
                for item in record["variants"]
            ] if record else [],
        }


def register_variant(
    study_id: int,
    analyst_id: str,
    gene: str,
    variant: str,
) -> dict:
    with mock_delivery._delivery_lock:
        _validate_analysis_access(study_id, analyst_id)

        if gene not in _available_genes(study_id):
            raise HTTPException(
                400,
                "El gen no pertenece a este estudio.",
            )

        selected = next(
            (
                item for item in _variant_catalogue(gene)
                if item["variant"] == variant
            ),
            None,
        )

        if selected is None:
            raise HTTPException(
                400,
                "La variante no pertenece al catálogo del gen.",
            )

        if selected["classification"] not in _MOCK_VARIANT_CLASSES:
            raise HTTPException(
                502,
                "Apigen devolvió una clasificación no válida.",
            )

        record = _analysis_records.setdefault(
            study_id,
            {"variants": [], "completed_at": None, "pdf": None},
        )

        if any(
            item["gene"] == gene and item["variant"] == variant
            for item in record["variants"]
        ):
            raise HTTPException(
                409,
                "La variante ya está registrada.",
            )

        record["variants"].append(dict(selected))
        return dict(selected)


def remove_variant(
    study_id: int,
    analyst_id: str,
    gene: str,
    variant: str,
) -> dict:
    with mock_delivery._delivery_lock:
        _validate_analysis_access(study_id, analyst_id)
        record = _analysis_records.get(study_id)

        if record is None:
            raise HTTPException(404, "La variante no está registrada.")

        match = next(
            (
                item for item in record["variants"]
                if item["gene"] == gene and item["variant"] == variant
            ),
            None,
        )

        if match is None:
            raise HTTPException(404, "La variante no está registrada.")

        record["variants"].remove(match)
        return {"removed": True}


def _pdf_escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def _create_mock_pdf(study_id: int, variants: list[dict]) -> bytes:
    """Build a simple valid PDF using only the Python standard library."""
    lines = [
        "GENLAB - RESULTADO SIMULADO",
        f"Estudio: {study_id}",
        "Documento ficticio - sin validez clinica",
        f"Variantes registradas: {len(variants)}",
    ]

    if not variants:
        lines.append("Sin variantes registradas")
    else:
        for item in variants:
            classification = {
                "Patogénica": "Patogenica",
                "Benigna": "Benigna",
                "VUS": "VUS",
            }[item["classification"]]
            lines.append(
                f"{item['gene']} | {item['variant']} | {classification}"
            )

    commands = ["BT", "/F1 11 Tf", "50 790 Td", "15 TL"]
    for index, line in enumerate(lines):
        if index:
            commands.append("T*")
        commands.append(f"({_pdf_escape(line)}) Tj")
    commands.append("ET")

    stream = "\n".join(commands).encode("ascii", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 595 842] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
            + stream
            + b"\nendstream"
        ),
    ]

    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    offsets = [0]

    for index, obj in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f"{index} 0 obj\n".encode("ascii"))
        output.write(obj)
        output.write(b"\nendobj\n")

    xref_offset = output.tell()
    output.write(f"xref\n0 {len(offsets)}\n".encode("ascii"))
    output.write(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        output.write(f"{offset:010d} 00000 n \n".encode("ascii"))

    output.write(
        (
            f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )

    return output.getvalue()


def complete_analysis(study_id: int, analyst_id: str) -> dict:
    with mock_delivery._delivery_lock:
        _validate_analysis_access(study_id, analyst_id)

        record = _analysis_records.setdefault(
            study_id,
            {"variants": [], "completed_at": None, "pdf": None},
        )

        variants = [dict(item) for item in record["variants"]]
        completed_at = datetime.now(timezone.utc)
        pdf = _create_mock_pdf(study_id, variants)

        record["completed_at"] = completed_at
        record["pdf"] = pdf

        mock_delivery._study_states[study_id] = "ResultadoDisponible"

        # These are simulated events, not actual emails.
        notifications = [
            {
                "study_id": study_id,
                "recipient_role": role,
                "channel": "email",
                "status": "Simulado",
                "created_at": completed_at,
            }
            for role in ("medico_tratante", "paciente")
        ]

        mock_delivery._bioinformatics_notifications.extend(notifications)

        return {
            "study_id": study_id,
            "state": "ResultadoDisponible",
            "variant_count": len(variants),
            "negative": len(variants) == 0,
            "completed_at": completed_at,
            "pdf_available": True,
            "notification_count": len(notifications),
        }


def get_result_pdf(study_id: int, analyst_id: str) -> bytes:
    with mock_delivery._delivery_lock:
        assignment = _assignments.get(study_id)

        if assignment is None:
            raise HTTPException(404, "No se encontró el estudio.")

        if assignment["analyst_id"] != analyst_id:
            raise HTTPException(403, "No tenés permiso para este resultado.")

        record = _analysis_records.get(study_id)

        if record is None or record["pdf"] is None:
            raise HTTPException(404, "El resultado todavía no está disponible.")

        return record["pdf"]



# Fictional identities and study ownership for development only.
MOCK_DOCTORS = {
    "doctor-1": "Médico tratante de prueba 1",
    "doctor-2": "Médico tratante de prueba 2",
}

MOCK_PATIENTS = {
    "patient-1": "Paciente de prueba 1",
    "patient-2": "Paciente de prueba 2",
}

# Each study has exactly one requesting doctor and one patient.
# This mapping is only for the isolated development environment.
MOCK_STUDY_OWNERS = {
    1001: ("doctor-1", "patient-1"),
    1002: ("doctor-1", "patient-1"),
    1003: ("doctor-1", "patient-2"),
    1004: ("doctor-2", "patient-2"),
    1005: ("doctor-2", "patient-1"),
    1006: ("doctor-1", "patient-2"),
    1007: ("doctor-2", "patient-2"),
    1008: ("doctor-1", "patient-1"),
    1009: ("doctor-2", "patient-1"),
    1010: ("doctor-1", "patient-2"),
    1011: ("doctor-2", "patient-2"),
    1012: ("doctor-1", "patient-1"),
}


def _validate_result_access(
    study_id: int,
    role: str,
    actor_id: str,
) -> None:
    """Call only while holding the delivery lock."""
    owners = MOCK_STUDY_OWNERS.get(study_id)

    if owners is None or _find_study_batch(study_id) is None:
        raise HTTPException(404, "No se encontró el estudio.")

    if role == "medico_tratante":
        if actor_id not in MOCK_DOCTORS:
            raise HTTPException(400, "El médico de prueba no es válido.")
        authorized = owners[0] == actor_id
    elif role == "paciente":
        if actor_id not in MOCK_PATIENTS:
            raise HTTPException(400, "El paciente de prueba no es válido.")
        authorized = owners[1] == actor_id
    else:
        raise HTTPException(403, "El rol no tiene acceso al resultado.")

    if not authorized:
        raise HTTPException(
            403,
            "No tenés permiso para consultar este estudio.",
        )


def list_results(role: str, actor_id: str) -> list[dict]:
    with mock_delivery._delivery_lock:
        if role == "medico_tratante":
            if actor_id not in MOCK_DOCTORS:
                raise HTTPException(400, "El médico de prueba no es válido.")
            owner_index = 0
        elif role == "paciente":
            if actor_id not in MOCK_PATIENTS:
                raise HTTPException(400, "El paciente de prueba no es válido.")
            owner_index = 1
        else:
            raise HTTPException(403, "El rol no tiene acceso al resultado.")

        results = []

        for study_id, owners in MOCK_STUDY_OWNERS.items():
            if owners[owner_index] != actor_id:
                continue

            if mock_delivery._study_states.get(study_id) != "ResultadoDisponible":
                continue

            record = _analysis_records.get(study_id)

            if record is None or record["pdf"] is None:
                continue

            results.append({
                "study_id": study_id,
                "state": "ResultadoDisponible",
                "variant_count": len(record["variants"]),
                "negative": len(record["variants"]) == 0,
                "completed_at": record["completed_at"],
            })

        return sorted(
            results,
            key=lambda result: (
                result["completed_at"],
                result["study_id"],
            ),
            reverse=True,
        )


def get_result(
    study_id: int,
    role: str,
    actor_id: str,
) -> dict:
    with mock_delivery._delivery_lock:
        _validate_result_access(study_id, role, actor_id)

        if mock_delivery._study_states.get(study_id) != "ResultadoDisponible":
            raise HTTPException(
                409,
                "El resultado todavía no está disponible.",
            )

        record = _analysis_records.get(study_id)

        if record is None or record["pdf"] is None:
            raise HTTPException(
                404,
                "No se encontró el resultado.",
            )

        result = {
            "study_id": study_id,
            "state": "ResultadoDisponible",
            "variant_count": len(record["variants"]),
            "negative": len(record["variants"]) == 0,
            "completed_at": record["completed_at"],
            "pdf_available": True,
        }

        if role == "medico_tratante":
            result["variants"] = [
                dict(item) for item in record["variants"]
            ]

        return result


def get_result_pdf_for_actor(
    study_id: int,
    role: str,
    actor_id: str,
) -> bytes:
    with mock_delivery._delivery_lock:
        _validate_result_access(study_id, role, actor_id)

        if mock_delivery._study_states.get(study_id) != "ResultadoDisponible":
            raise HTTPException(
                409,
                "El resultado todavía no está disponible.",
            )

        record = _analysis_records.get(study_id)

        if record is None or record["pdf"] is None:
            raise HTTPException(
                404,
                "No se encontró el resultado.",
            )

        return record["pdf"]
