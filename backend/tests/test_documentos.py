import re

import pytest

from app.documentos import qr
from app.documentos.pdf import Line, build_pdf


def test_los_bits_de_formato_del_qr_son_los_del_estandar():
    # Level L with mask 0 is 111011111000100 in ISO/IEC 18004.
    assert qr._format_bits() == 0b111011111000100


def test_el_qr_elige_la_version_segun_el_largo():
    assert len(qr.encode("CUP-0001")) == 21
    assert len(qr.encode("CUP-2026-ABCDEF-0000001")) == 25


def test_el_qr_rechaza_un_texto_demasiado_largo():
    with pytest.raises(ValueError):
        qr.encode("x" * (qr.MAX_BYTES + 1))


def test_el_qr_tiene_los_tres_cuadros_de_posicion():
    modules = qr.encode("CUP-0001")
    for x, y in ((0, 0), (14, 0), (0, 14)):
        assert all(modules[y][x + i] for i in range(7))
        assert all(modules[y + 6][x + i] for i in range(7))
        assert not modules[y + 1][x + 1]


def test_el_svg_del_qr_es_un_svg():
    svg = qr.to_svg(qr.encode("CUP-0001"))
    assert svg.startswith("<svg") and svg.endswith("</svg>")


def test_el_pdf_tiene_una_estructura_valida_y_el_texto():
    pdf = build_pdf(
        [Line("Orden (de) extracción", 20), Line("Texto \\ largo " * 20, 12)], qr.encode("A")
    )
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.rstrip().endswith(b"%%EOF")
    assert b"extracci\xf3n" in pdf  # WinAnsi accent
    startxref = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
    assert pdf[startxref : startxref + 4] == b"xref"
    entries = re.findall(rb"(\d{10}) 00000 n", pdf)
    for number, offset in enumerate(entries, start=1):
        assert pdf[int(offset) :].startswith(b"%d 0 obj" % number)
