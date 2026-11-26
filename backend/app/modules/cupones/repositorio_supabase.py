"""Coupons, doctors and patients read from and written to Supabase.

Only `coupons` is written. `users` and `patients` belong to the access and medical consultation
modules: here they are read only, and only the columns needed.
"""

from datetime import datetime

from app.core.enums import Rol
from app.core.errors import BusinessRuleError
from app.core.supabase_tables import select_in, table
from app.modules.cupones.repositorio import (
    Cupon,
    Medico,
    Paciente,
    RepositorioCupones,
    RepositorioMedicos,
    RepositorioPacientes,
)

COUPON_COLUMNS = "code, discount_pct, status, doctor_id, patient_id, created_at"
PATIENT_COLUMNS = "id, account_user_id, registered_by, first_name, last_name"
DOCTOR_COLUMNS = "id, email, first_name, last_name, license_number"
USED = "Usado"


def _user_id(email: str) -> str | None:
    rows = table("users").select("id").eq("email", email).limit(1).execute().data
    return rows[0]["id"] if rows else None


def _emails(user_ids) -> dict[str, str]:
    return {u["id"]: u["email"] for u in select_in("users", "id, email", "id", user_ids)}


class RepositorioCuponesSupabase(RepositorioCupones):
    def guardar_nuevos(self, cupones: list[Cupon]) -> None:
        if not cupones:
            return
        table("coupons").insert(
            [
                {
                    "code": c.codigo,
                    "discount_pct": c.descuento,
                    "status": c.estado,
                    "created_at": c.generado_en.isoformat(),
                }
                for c in cupones
            ]
        ).execute()

    def listar(self) -> list[Cupon]:
        rows = (
            table("coupons")
            .select(COUPON_COLUMNS)
            .order("created_at", desc=True)
            .order("id", desc=True)
            .execute()
            .data
        )
        return self._armar(rows)

    def obtener(self, codigo: str) -> Cupon | None:
        rows = table("coupons").select(COUPON_COLUMNS).eq("code", codigo).limit(1).execute().data
        armados = self._armar(rows)
        return armados[0] if armados else None

    def asignar_a_medico(self, codigos: list[str], contacto_medico: str) -> list[Cupon]:
        medico_id = _user_id(contacto_medico)
        if medico_id is None:
            raise BusinessRuleError("No existe el médico tratante.", status_code=404)
        table("coupons").update({"doctor_id": medico_id}).in_("code", codigos).execute()
        return self._armar(select_in("coupons", COUPON_COLUMNS, "code", codigos))

    def listar_de_medico(self, contacto_medico: str) -> list[Cupon]:
        medico_id = _user_id(contacto_medico)
        if medico_id is None:
            return []
        rows = (
            table("coupons")
            .select(COUPON_COLUMNS)
            .eq("doctor_id", medico_id)
            .is_("patient_id", "null")
            .order("id")
            .execute()
            .data
        )
        return self._armar(rows)

    def listar_de_paciente(self, contacto_paciente: str) -> list[Cupon]:
        cuenta_id = _user_id(contacto_paciente)
        if cuenta_id is None:
            return []
        pacientes = table("patients").select("id").eq("account_user_id", cuenta_id).execute().data
        rows = select_in("coupons", COUPON_COLUMNS, "patient_id", [p["id"] for p in pacientes])
        return self._armar(rows)

    def asignar_a_paciente(self, codigo: str, contacto_paciente: str) -> Cupon:
        cupon = (
            table("coupons").select("code, doctor_id").eq("code", codigo).limit(1).execute().data
        )
        cuenta_id = _user_id(contacto_paciente)
        if not cupon or cuenta_id is None:
            raise BusinessRuleError("No existe el paciente.", status_code=404)
        pacientes = (
            table("patients")
            .select("id, registered_by")
            .eq("account_user_id", cuenta_id)
            .order("created_at")
            .execute()
            .data
        )
        if not pacientes:
            raise BusinessRuleError("No existe el paciente.", status_code=404)
        # Siblings share the account: the coupon goes to the one this doctor registered.
        del_medico = [p for p in pacientes if p["registered_by"] == cupon[0]["doctor_id"]]
        elegido = (del_medico or pacientes)[0]
        table("coupons").update({"patient_id": elegido["id"]}).eq("code", codigo).execute()
        return self.obtener(codigo)

    def marcar_usado(self, codigo: str) -> None:
        table("coupons").update({"status": USED}).eq("code", codigo).execute()

    @staticmethod
    def _armar(rows: list[dict]) -> list[Cupon]:
        """Coupons with the e-mail of the doctor and of the patient's account."""
        if not rows:
            return []
        pacientes = {
            p["id"]: p["account_user_id"]
            for p in select_in(
                "patients", "id, account_user_id", "id", [r["patient_id"] for r in rows]
            )
        }
        correos = _emails([r["doctor_id"] for r in rows] + list(pacientes.values()))
        return [
            Cupon(
                codigo=r["code"],
                descuento=r["discount_pct"],
                estado=r["status"],
                generado_en=datetime.fromisoformat(r["created_at"]),
                medico=correos.get(r["doctor_id"]),
                paciente=correos.get(pacientes.get(r["patient_id"])),
            )
            for r in rows
        ]


def _medico(row: dict) -> Medico:
    return Medico(
        contacto=row["email"],
        nombre=f"{row['first_name']} {row['last_name']}",
        matricula=row["license_number"] or "",
    )


class RepositorioMedicosSupabase(RepositorioMedicos):
    @staticmethod
    def _medicos() -> list[dict]:
        return (
            table("users")
            .select(DOCTOR_COLUMNS)
            .eq("role", Rol.MEDICO_TRATANTE.value)
            .order("last_name")
            .execute()
            .data
        )

    def buscar(self, texto: str) -> list[Medico]:
        buscado = texto.strip().lower()
        return [
            _medico(m)
            for m in self._medicos()
            if buscado in f"{m['first_name']} {m['last_name']}".lower()
            or buscado in (m["license_number"] or "").lower()
        ]

    def obtener(self, contacto: str) -> Medico | None:
        return next((_medico(m) for m in self._medicos() if m["email"] == contacto), None)


class RepositorioPacientesSupabase(RepositorioPacientes):
    def listar_de_medico(self, contacto_medico: str) -> list[Paciente]:
        medico_id = _user_id(contacto_medico)
        if medico_id is None:
            return []
        rows = (
            table("patients")
            .select(PATIENT_COLUMNS)
            .eq("registered_by", medico_id)
            .order("last_name")
            .execute()
            .data
        )
        correos = _emails([r["account_user_id"] for r in rows])
        return [
            Paciente(
                contacto=correos[r["account_user_id"]],
                nombre=f"{r['first_name']} {r['last_name']}",
                medico=contacto_medico,
            )
            for r in rows
        ]

    def obtener(self, contacto: str, contacto_medico: str | None = None) -> Paciente | None:
        cuenta_id = _user_id(contacto)
        if cuenta_id is None:
            return None
        rows = (
            table("patients")
            .select(PATIENT_COLUMNS)
            .eq("account_user_id", cuenta_id)
            .order("created_at")
            .execute()
            .data
        )
        if not rows:
            return None
        medico_id = None if contacto_medico is None else _user_id(contacto_medico)
        elegido = next((r for r in rows if r["registered_by"] == medico_id), rows[0])
        medico = _emails([elegido["registered_by"]]).get(elegido["registered_by"], "")
        return Paciente(contacto, f"{elegido['first_name']} {elegido['last_name']}", medico)
