
"""Development-only Ministry of Health authorization simulator.

Documents and patient records are fictional.
Never use this module for real patient information.
"""

import csv
import io
from datetime import datetime, timezone


def generate_patient_csv(study_ids: list[int]) -> bytes:
    """Create a fictional patient CSV for development testing."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "study_id",
        "dni",
        "first_name",
        "last_name",
        "birth_date",
    ])

    for study_id in study_ids:
        writer.writerow([
            study_id,
            str(30000000 + study_id),
            f"Paciente{study_id}",
            "Simulado",
            "2000-01-01",
        ])

    return output.getvalue().encode("utf-8-sig")


def generate_test_pdf(batch_id: int) -> bytes:
    """Generate a minimal valid PDF containing a fictional permit."""
    message = (
        f"SIMULACION - Permiso de prueba - Lote {batch_id}"
    )

    stream = (
        "BT /F1 14 Tf 50 760 Td "
        f"({message}) Tj ET"
    ).encode("ascii")

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

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for index, content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(content)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)

    pdf.extend(
        f"xref\n0 {len(offsets)}\n".encode("ascii")
    )
    pdf.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        pdf.extend(
            f"{offset:010d} 00000 n \n".encode("ascii")
        )

    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(offsets)} /Root 1 0 R >>\n"
            "startxref\n"
            f"{xref_offset}\n"
            "%%EOF\n"
        ).encode("ascii")
    )

    return bytes(pdf)


def request_authorization(
    batch_id: int,
    study_ids: list[int],
) -> dict:
    """Simulate a Ministry request with optional failure testing."""
    patient_csv = generate_patient_csv(study_ids)


    permit_pdf = generate_test_pdf(batch_id)

    return {
        "authorized": True,
        "csv_content": patient_csv,
        "permit_content": permit_pdf,
        "authorized_at": datetime.now(timezone.utc),
        "error": None,
    }
