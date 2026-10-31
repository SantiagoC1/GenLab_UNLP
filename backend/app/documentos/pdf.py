"""Minimal PDF writer for the documents the platform generates (coupons, extraction order...).

One A4 page per call, Helvetica text and an optional QR drawn as vector squares. It has no
dependencies on purpose: adding a PDF library needs the team's approval.
"""

import textwrap
from dataclasses import dataclass

PAGE_WIDTH, PAGE_HEIGHT = 595, 842
MARGIN = 56
WRAP_COLUMNS = {10: 95, 12: 80, 20: 48}


@dataclass(frozen=True)
class Line:
    text: str
    size: int = 12
    gap: int = 0  # extra points of space before the line


def _escape(text: str) -> bytes:
    encoded = text.encode("cp1252", errors="replace")
    return encoded.replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")


def _qr_operations(modules: list[list[bool]], x: float, y_top: float, side: float) -> bytes:
    size = len(modules)
    cell = side / (size + 8)  # 4 modules of quiet zone on each side
    ops = [b"1 g %.2f %.2f %.2f %.2f re f 0 g" % (x, y_top - side, side, side)]
    for row, cells in enumerate(modules):
        for col, dark in enumerate(cells):
            if dark:
                ops.append(
                    b"%.2f %.2f %.2f %.2f re f"
                    % (
                        x + (col + 4) * cell,
                        y_top - (row + 5) * cell,
                        cell,
                        cell,
                    )
                )
    return b"\n".join(ops)


def build_pdf(lines: list[Line], qr: list[list[bool]] | None = None) -> bytes:
    """Builds a one-page PDF with the lines from the top and the QR (if any) below them."""
    content: list[bytes] = []
    y = PAGE_HEIGHT - MARGIN
    for line in lines:
        y -= line.gap
        columns = WRAP_COLUMNS.get(line.size, 80)
        for part in textwrap.wrap(line.text, columns) or [""]:
            y -= line.size + 4
            content.append(
                b"BT /F1 %d Tf %d %.2f Td (%s) Tj ET" % (line.size, MARGIN, y, _escape(part))
            )
    if qr is not None:
        content.append(_qr_operations(qr, MARGIN, y - 24, 150))
    stream = b"\n".join(content)

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>" % (PAGE_WIDTH, PAGE_HEIGHT),
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)
