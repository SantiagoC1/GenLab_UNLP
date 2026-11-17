"""Rules of the extraction appointment books (M6-RF2).

The extraction labs do not work inside the platform, so their free appointments are generated
with one rule: 15 minutes each, for one person, Monday to Friday from 9:00 to 18:00, never on a
holiday. A booked appointment is the only thing that is stored.
"""

from datetime import date, datetime, time, timedelta, timezone

# Argentina has no daylight saving time, so a fixed offset is enough.
ARG = timezone(timedelta(hours=-3), "ART")

DURACION = timedelta(minutes=15)
APERTURA = time(9, 0)
CIERRE = time(18, 0)
# M6-RF8: at this many absences the patient is told; nothing is blocked until P2 is resolved.
LIMITE_INASISTENCIAS = 5
# M6-RF9: the blood sample needs at least this volume to continue the process.
VOLUMEN_MINIMO_ML = 2.0
# Reasons of a resampling (M6-RF10).
MOTIVO_VOLUMEN = "volumen_menor_2ml"
MOTIVO_ADN = "adn_desnaturalizado"
# [assumption] How far ahead an appointment can be booked.
HORIZONTE_DIAS = 60

# [assumption] National holidays of 2026 (including the moved ones and the bridge days), to be
# checked against the official calendar. Outside the listed years no day is a holiday until the
# list is extended.
FERIADOS = frozenset(
    {
        date(2026, 1, 1),
        date(2026, 2, 16),
        date(2026, 2, 17),
        date(2026, 3, 23),
        date(2026, 3, 24),
        date(2026, 4, 2),
        date(2026, 4, 3),
        date(2026, 5, 1),
        date(2026, 5, 25),
        date(2026, 6, 15),
        date(2026, 6, 20),
        date(2026, 7, 9),
        date(2026, 7, 10),
        date(2026, 8, 17),
        date(2026, 10, 12),
        date(2026, 11, 23),
        date(2026, 12, 7),
        date(2026, 12, 8),
        date(2026, 12, 25),
    }
)


def ahora() -> datetime:
    """The current time in Argentina. A dependency, so the tests can fix the clock."""
    return datetime.now(ARG)


def motivo_sin_turnos(dia: date) -> str | None:
    """Why there are no appointments that day, or None if the lab works."""
    if dia.weekday() >= 5:
        return "Los laboratorios atienden de lunes a viernes."
    if dia in FERIADOS:
        return "Ese día es feriado."
    return None


def turnos_del_dia(dia: date) -> list[datetime]:
    """Every appointment start of the day (empty on weekends and holidays)."""
    if motivo_sin_turnos(dia) is not None:
        return []
    inicio = datetime.combine(dia, APERTURA, tzinfo=ARG)
    cierre = datetime.combine(dia, CIERRE, tzinfo=ARG)
    turnos = []
    while inicio + DURACION <= cierre:
        turnos.append(inicio)
        inicio += DURACION
    return turnos


def es_turno_valido(inicio: datetime) -> bool:
    """True if the start is one of the slots the rule generates."""
    local = inicio.astimezone(ARG)
    return local in turnos_del_dia(local.date())


def ultimo_dia_reservable(hoy: date) -> date:
    return hoy + timedelta(days=HORIZONTE_DIAS)
