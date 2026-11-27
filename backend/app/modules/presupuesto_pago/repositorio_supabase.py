"""Studies for the budget, the coverage and the payment, stored in Supabase.

Reads the studies of module 3 (`studies`, `patients`, `study_genes`) and owns `budgets`,
`authorizations` and `payments`. State changes go through `change_study_state`, the only way to
change `studies.state`, so every change leaves its row in `study_state_history`.
"""

from collections.abc import Iterable
from datetime import datetime

from app.core.enums import EstadoEstudio
from app.core.errors import BusinessRuleError
from app.core.supabase_tables import select_in, table
from app.modules.consulta_medica import service as study_service
from app.modules.presupuesto_pago.repositorio import (
    AsientoFinanciero,
    CambioEstado,
    Cobertura,
    CuponAplicado,
    EstudioParaPresupuesto,
    RepositorioEstudios,
)

# Explicit columns everywhere: the court decision PDF (`demand_pdf`) never travels in a listing.
STUDY_COLUMNS = "id, patient_id, requested_by, state"
PATIENT_COLUMNS = "id, account_user_id, first_name, last_name, dni"
USER_COLUMNS = "id, email"
GENE_COLUMNS = "study_id, gene"
BUDGET_COLUMNS = "study_id, amount_usd, issued_at, applied_coupon_code, applied_coupon_pct"
AUTHORIZATION_COLUMNS = (
    "id, study_id, insurance_name, coverage_pct, status, rejection_reason, external_id, "
    "chosen_at, resolved_at, demand_name, demand_at, registered_by"
)
HISTORY_COLUMNS = "id, study_id, from_state, to_state, changed_at"
PAYMENT_COLUMNS = "id, study_id, amount_usd, method, coupon_code, paid_at"

HEX_PREFIX = "\\x"


def _when(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _usd(value) -> int:
    """`numeric(10, 2)` comes back as a number: the amounts are whole dollars."""
    return int(round(float(value)))


def _to_bytea(content: bytes) -> str:
    """PostgREST takes a bytea as a hex string."""
    return HEX_PREFIX + content.hex()


def _from_bytea(value: str) -> bytes:
    """PostgREST returns a bytea as the hex string `\\x...`."""
    return bytes.fromhex(value[len(HEX_PREFIX) :] if value.startswith(HEX_PREFIX) else value)


def _cobertura(row: dict) -> Cobertura:
    return Cobertura(
        obra_social=row["insurance_name"],
        porcentaje=row["coverage_pct"],
        estado=row["status"],
        identificador_externo=row["external_id"],
        motivo_rechazo=row["rejection_reason"],
        elegida_en=_when(row["chosen_at"]),
        resuelta_en=_when(row["resolved_at"]),
        registrada_por=row["registered_by"],
        demanda_nombre=row["demand_name"],
        demanda_en=_when(row["demand_at"]),
    )


class RepositorioEstudiosSupabase(RepositorioEstudios):
    # --- reading --------------------------------------------------------------------------

    def listar_creados_sin_presupuesto(self) -> list[EstudioParaPresupuesto]:
        rows = (
            table("studies")
            .select(STUDY_COLUMNS)
            .eq("state", EstadoEstudio.CREADO.value)
            .order("id")
            .execute()
            .data
        )
        return [e for e in self._armar(rows) if not e.tiene_presupuesto]

    def listar_con_cobertura(self) -> list[EstudioParaPresupuesto]:
        con_cobertura = table("authorizations").select("study_id").execute().data
        ids = {row["study_id"] for row in con_cobertura}
        return self._armar(select_in("studies", STUDY_COLUMNS, "id", ids))

    def listar_por_estados(self, estados: Iterable[EstadoEstudio]) -> list[EstudioParaPresupuesto]:
        rows = select_in("studies", STUDY_COLUMNS, "state", [e.value for e in estados])
        return self._armar(rows)

    def listar_de_paciente(self, contacto: str) -> list[EstudioParaPresupuesto]:
        cuentas = table("users").select("id").eq("email", contacto).limit(1).execute().data
        if not cuentas:
            return []
        pacientes = (
            table("patients").select("id").eq("account_user_id", cuentas[0]["id"]).execute().data
        )
        rows = select_in("studies", STUDY_COLUMNS, "patient_id", [p["id"] for p in pacientes])
        return self._armar(rows)

    def obtener(self, estudio_id: int) -> EstudioParaPresupuesto | None:
        rows = table("studies").select(STUDY_COLUMNS).eq("id", estudio_id).limit(1).execute().data
        estudios = self._armar(rows)
        return estudios[0] if estudios else None

    def obtener_demanda(self, estudio_id: int) -> bytes | None:
        rows = (
            table("authorizations")
            .select("demand_pdf")
            .eq("study_id", estudio_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
            .data
        )
        if not rows or rows[0]["demand_pdf"] is None:
            return None
        return _from_bytea(rows[0]["demand_pdf"])

    # --- writing --------------------------------------------------------------------------

    def guardar_presupuesto(
        self,
        estudio_id: int,
        importe_usd: int,
        emitido_en: datetime,
        emitido_por: str | None = None,
    ) -> EstudioParaPresupuesto:
        if emitido_por is None:
            raise BusinessRuleError("Falta el usuario que emite el presupuesto.", 500)
        genes = table("study_genes").select(GENE_COLUMNS).eq("study_id", estudio_id).execute()
        table("budgets").insert(
            {
                "study_id": estudio_id,
                "gene_count": len(genes.data),
                "amount_usd": importe_usd,
                "issued_by": emitido_por,
                "issued_at": _iso(emitido_en),
            }
        ).execute()
        return self._obtener_existente(estudio_id)

    def guardar_cobertura(self, estudio_id: int, cobertura: Cobertura) -> EstudioParaPresupuesto:
        fila = {
            "insurance_name": cobertura.obra_social,
            "coverage_pct": cobertura.porcentaje,
            "status": cobertura.estado,
            "rejection_reason": cobertura.motivo_rechazo,
            "external_id": cobertura.identificador_externo,
            "chosen_at": _iso(cobertura.elegida_en),
            "resolved_at": _iso(cobertura.resuelta_en),
            "demand_name": cobertura.demanda_nombre,
            "demand_at": _iso(cobertura.demanda_en),
        }
        if cobertura.registrada_por is not None:
            fila["registered_by"] = cobertura.registrada_por
        if cobertura.demanda is not None:
            fila["demand_pdf"] = _to_bytea(cobertura.demanda)
        elif cobertura.demanda_nombre is None:
            # The decision was answered: the PDF goes away with its name.
            fila["demand_pdf"] = None
        # Otherwise the PDF is already stored and this object only knows its name: keep it.

        actual = self._id_de_cobertura(estudio_id)
        if actual is None:
            table("authorizations").insert({"study_id": estudio_id, **fila}).execute()
        else:
            table("authorizations").update(fila).eq("id", actual).execute()
        return self._obtener_existente(estudio_id)

    def guardar_cupon_aplicado(
        self, estudio_id: int, cupon: CuponAplicado | None
    ) -> EstudioParaPresupuesto:
        cambios = {
            "applied_coupon_code": None if cupon is None else cupon.codigo,
            "applied_coupon_pct": None if cupon is None else cupon.descuento,
        }
        actualizado = table("budgets").update(cambios).eq("study_id", estudio_id).execute().data
        if not actualizado:
            raise BusinessRuleError("El estudio todavía no tiene el presupuesto emitido.")
        return self._obtener_existente(estudio_id)

    def cambiar_estado(
        self,
        estudio_id: int,
        nuevo: EstadoEstudio,
        en: datetime,
        cambiado_por: str | None = None,
    ) -> EstudioParaPresupuesto:
        # The moment is the database's: `change_study_state` stamps the history itself.
        study_service.change_study_state(estudio_id, nuevo, cambiado_por)
        return self._obtener_existente(estudio_id)

    def registrar_asiento(
        self,
        estudio: EstudioParaPresupuesto,
        importe_usd: int,
        metodo: str,
        fecha: datetime,
        cupon: str | None = None,
    ) -> AsientoFinanciero:
        cupon_id = None
        if cupon is not None:
            conocido = table("coupons").select("id").eq("code", cupon).limit(1).execute().data
            cupon_id = conocido[0]["id"] if conocido else None
        fila = (
            table("payments")
            .insert(
                {
                    "study_id": estudio.id,
                    "amount_usd": importe_usd,
                    "coupon_id": cupon_id,
                    "coupon_code": cupon,
                    "method": metodo,
                    "paid_at": _iso(fecha),
                }
            )
            .execute()
            .data[0]
        )
        return AsientoFinanciero(
            fila["id"], estudio.id, estudio.paciente, importe_usd, metodo, fecha, cupon
        )

    def listar_asientos(self) -> list[AsientoFinanciero]:
        filas = (
            table("payments")
            .select(PAYMENT_COLUMNS)
            .order("paid_at", desc=True)
            .order("id", desc=True)
            .execute()
            .data
        )
        estudios = select_in("studies", "id, patient_id", "id", [f["study_id"] for f in filas])
        pacientes = {
            p["id"]: f"{p['first_name']} {p['last_name']}"
            for p in select_in(
                "patients", PATIENT_COLUMNS, "id", [e["patient_id"] for e in estudios]
            )
        }
        paciente_de = {e["id"]: pacientes.get(e["patient_id"], "") for e in estudios}
        return [
            AsientoFinanciero(
                f["id"],
                f["study_id"],
                paciente_de.get(f["study_id"], ""),
                _usd(f["amount_usd"]),
                f["method"],
                _when(f["paid_at"]),
                f["coupon_code"],
            )
            for f in filas
        ]

    # --- helpers --------------------------------------------------------------------------

    def _obtener_existente(self, estudio_id: int) -> EstudioParaPresupuesto:
        estudio = self.obtener(estudio_id)
        if estudio is None:
            raise BusinessRuleError("No existe el estudio.", status_code=404)
        return estudio

    @staticmethod
    def _id_de_cobertura(estudio_id: int) -> int | None:
        rows = (
            table("authorizations")
            .select("id")
            .eq("study_id", estudio_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
            .data
        )
        return rows[0]["id"] if rows else None

    @staticmethod
    def _armar(estudios: list[dict]) -> list[EstudioParaPresupuesto]:
        """Builds the studies with their patient, genes, budget, coverage and state history."""
        if not estudios:
            return []
        ids = [e["id"] for e in estudios]
        pacientes = {
            p["id"]: p
            for p in select_in(
                "patients", PATIENT_COLUMNS, "id", [e["patient_id"] for e in estudios]
            )
        }
        cuentas = [p["account_user_id"] for p in pacientes.values()]
        pedidos = [e["requested_by"] for e in estudios]
        correos = {
            u["id"]: u["email"] for u in select_in("users", USER_COLUMNS, "id", cuentas + pedidos)
        }

        genes: dict[int, list[str]] = {}
        for fila in select_in("study_genes", GENE_COLUMNS, "study_id", ids, order="gene"):
            genes.setdefault(fila["study_id"], []).append(fila["gene"])
        presupuestos = {
            b["study_id"]: b
            for b in select_in("budgets", BUDGET_COLUMNS, "study_id", ids, order="study_id")
        }
        # One coverage per study is kept up to date; with several rows the last one rules.
        coberturas = {
            a["study_id"]: a
            for a in select_in("authorizations", AUTHORIZATION_COLUMNS, "study_id", ids)
        }
        historial: dict[int, list[CambioEstado]] = {}
        for fila in select_in(
            "study_state_history", HISTORY_COLUMNS, "study_id", ids, order="changed_at"
        ):
            desde = None if fila["from_state"] is None else EstadoEstudio(fila["from_state"])
            historial.setdefault(fila["study_id"], []).append(
                CambioEstado(desde, EstadoEstudio(fila["to_state"]), _when(fila["changed_at"]))
            )

        armados = []
        for e in estudios:
            paciente = pacientes[e["patient_id"]]
            presupuesto = presupuestos.get(e["id"])
            cobertura = coberturas.get(e["id"])
            codigo = None if presupuesto is None else presupuesto["applied_coupon_code"]
            armados.append(
                EstudioParaPresupuesto(
                    id=e["id"],
                    paciente=f"{paciente['first_name']} {paciente['last_name']}",
                    contacto_paciente=correos[paciente["account_user_id"]],
                    genes=genes.get(e["id"], []),
                    estado=EstadoEstudio(e["state"]),
                    presupuesto_importe_usd=None
                    if presupuesto is None
                    else _usd(presupuesto["amount_usd"]),
                    presupuesto_emitido_en=None
                    if presupuesto is None
                    else _when(presupuesto["issued_at"]),
                    contacto_medico=correos.get(e["requested_by"], ""),
                    dni=paciente.get("dni") or "",
                    cobertura=None if cobertura is None else _cobertura(cobertura),
                    cupon_aplicado=None
                    if codigo is None
                    else CuponAplicado(codigo, presupuesto["applied_coupon_pct"]),
                    historial=historial.get(e["id"], []),
                )
            )
        return armados
