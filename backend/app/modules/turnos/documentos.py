"""The PDFs the patient prints to attend the appointment (M6-RF6)."""

from app.documentos.pdf import Line, build_pdf
from app.modules.presupuesto_pago.repositorio import EstudioParaPresupuesto
from app.modules.turnos.reglas import ARG
from app.modules.turnos.repositorio import Laboratorio, Turno

# [assumption] The previous instructions and the legal text are placeholders: the laboratory has
# to provide the final wording.
INDICACIONES = (
    "Presentate 10 minutos antes del horario del turno.",
    "Llevá tu DNI y el consentimiento informado impreso, completo y firmado.",
    "Seguí las indicaciones previas a la extracción que te dio tu médico tratante (por ejemplo, "
    "si corresponde un ayuno).",
    "Si no podés asistir, cancelá el turno desde la plataforma para liberarlo.",
)


def orden_de_extraccion(
    turno: Turno, estudio: EstudioParaPresupuesto, laboratorio: Laboratorio
) -> bytes:
    inicio = turno.inicio.astimezone(ARG)
    lineas = [
        Line("GenLab - Orden de extracción", 20),
        Line(f"Paciente: {estudio.paciente}", 12, gap=24),
        Line(f"Estudio de exoma clínico N° {estudio.id}", 12),
        Line(f"Fecha: {inicio:%d/%m/%Y}", 12, gap=12),
        Line(f"Hora: {inicio:%H:%M}", 12),
        Line(f"Laboratorio de extracción: {laboratorio.nombre}", 12),
        Line(f"Dirección: {laboratorio.direccion}", 12),
        Line("Indicaciones", 12, gap=18),
        *[Line(f"- {indicacion}", 10) for indicacion in INDICACIONES],
    ]
    return build_pdf(lineas)


def consentimiento_informado(estudio: EstudioParaPresupuesto) -> bytes:
    lineas = [
        Line("GenLab - Consentimiento informado", 20),
        Line("Estudio de exoma clínico", 12, gap=12),
        Line(f"Paciente: {estudio.paciente}", 12, gap=12),
        Line(f"Estudio N° {estudio.id}", 12),
        Line(
            "Declaro que fui informado/a sobre el estudio de exoma clínico, sus alcances y sus "
            "limitaciones, y que autorizo la extracción de la muestra de sangre y el análisis "
            "genético para el estudio indicado por mi médico tratante.",
            10,
            gap=18,
        ),
        Line(
            "Si el paciente es menor de edad, el consentimiento lo firman su madre, su padre o "
            "su tutor.",
            10,
            gap=8,
        ),
        Line("Firma: ______________________________", 12, gap=40),
        Line("Aclaración: _________________________", 12, gap=18),
        Line("DNI: _______________________________", 12, gap=18),
        Line("Fecha: ______ / ______ / ____________", 12, gap=18),
        Line(
            "Imprimí este documento, completalo y firmalo. Se entrega en papel en el laboratorio "
            "de extracción el día del turno: no se sube a la plataforma.",
            10,
            gap=30,
        ),
    ]
    return build_pdf(lineas)
