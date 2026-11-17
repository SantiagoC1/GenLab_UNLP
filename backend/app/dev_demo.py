"""Small in-memory demo dataset, loaded on startup only when DEV_AUTH=true.

It uses the same in-memory repositories the screens read, so nothing is written to the database.
Each module adds its own seeder here as it gets in-memory data worth demonstrating.
"""

from datetime import UTC, datetime

from app.core import dev_auth
from app.modules.presupuesto_pago.repositorio import obtener_repositorio
from app.modules.presupuesto_pago.tarifa import calcular_importe


def seed_presupuestos() -> None:
    """The patients' studies already have a budget (study 3 stays in the administrative tray)."""
    estudios = obtener_repositorio()
    for estudio_id in (1, 2):
        estudio = estudios.obtener(estudio_id)
        if estudio is not None and not estudio.tiene_presupuesto:
            estudios.guardar_presupuesto(
                estudio_id, calcular_importe(len(estudio.genes)), datetime.now(UTC)
            )


def seed_demo() -> bool:
    """Loads the demo data if the bypass is enabled. Returns whether it did."""
    if not dev_auth.is_enabled():
        return False
    seed_presupuestos()
    return True
