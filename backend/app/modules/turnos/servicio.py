from datetime import date, datetime, time, timedelta

from app.core.enums import EstadoEstudio
from app.core.errors import BusinessRuleError
from app.integrations.avisos import AvisosIntegracion
from app.modules.presupuesto_pago.paciente import avisar
from app.modules.presupuesto_pago.repositorio import EstudioParaPresupuesto, RepositorioEstudios
from app.modules.turnos import documentos, reglas
from app.modules.turnos.reglas import ARG
from app.modules.turnos.remuestreos import RepositorioRemuestreos
from app.modules.turnos.repositorio import (
    AUSENTE,
    CANCELADO,
    PROGRAMADO,
    REALIZADO,
    Laboratorio,
    Recordatorio,
    RepositorioTurnos,
    Turno,
    TurnoOcupado,
)
from app.modules.turnos.schemas import (
    AgendaSalida,
    CancelacionSalida,
    EstudioHabilitadoSalida,
    EstudioRemuestreableSalida,
    InasistenciaSalida,
    LaboratorioSalida,
    MuestraRecibidaSalida,
    RemuestreoPendienteSalida,
    RemuestreoSalida,
    TurnoSalida,
    TurnosLibresSalida,
)

ANTICIPO_RECORDATORIO = timedelta(hours=24)
# N5 / M6-RF10: the states from which the administrative user can ask for a resampling.
ESTADOS_PARA_REMUESTREO_ADMINISTRATIVO = frozenset(
    {EstadoEstudio.EN_VIAJE_A_COREA, EstadoEstudio.EN_EL_AREA_DE_BIOINFORMATICA}
)
# What the doctor and the patient are told for each reason.
CAUSAS_DE_REMUESTREO = {
    reglas.MOTIVO_CALIDAD: "la muestra llegó con mala calidad",
    reglas.MOTIVO_ADN: "el ADN de la muestra no alcanzó para el análisis",
}


class TurnosServicio:
    def __init__(
        self,
        turnos: RepositorioTurnos,
        estudios: RepositorioEstudios,
        avisos: AvisosIntegracion,
        ahora: datetime,
        remuestreos: RepositorioRemuestreos,
    ):
        self.turnos = turnos
        self.remuestreos = remuestreos
        self.estudios = estudios
        self.avisos = avisos
        self.ahora = ahora

    # --- M6-RF1: the map of labs and their free appointments ---------------------------------

    def listar_laboratorios(self, provincia: str | None = None) -> list[LaboratorioSalida]:
        laboratorios = self.turnos.listar_laboratorios(provincia)
        return [self._laboratorio(lab, con_proximo_turno=True) for lab in laboratorios]

    def turnos_libres(self, laboratorio_id: int, dia: date) -> TurnosLibresSalida:
        self._laboratorio_existente(laboratorio_id)
        hoy = self.ahora.astimezone(ARG).date()
        if dia < hoy or dia > reglas.ultimo_dia_reservable(hoy):
            raise BusinessRuleError(
                f"Solo se pueden reservar turnos desde hoy y hasta {reglas.HORIZONTE_DIAS} días "
                "adelante.",
                status_code=422,
                code="fecha_fuera_de_rango",
            )
        libres = self._libres_del_dia(laboratorio_id, dia)
        motivo = reglas.motivo_sin_turnos(dia)
        if motivo is None and not libres:
            motivo = "El laboratorio no tiene turnos libres ese día."
        return TurnosLibresSalida(
            laboratorio_id=laboratorio_id, fecha=dia, turnos=libres, motivo=motivo
        )

    # --- M6-RF3: which studies can book -------------------------------------------------------

    def estudios_habilitados(self, contacto: str) -> list[EstudioHabilitadoSalida]:
        habilitados = []
        for estudio in self.estudios.listar_de_paciente(contacto):
            motivo = self._motivo_habilitado(estudio)
            if motivo is not None:
                habilitados.append(
                    EstudioHabilitadoSalida(
                        estudio_id=estudio.id,
                        estado=estudio.estado,
                        motivo=motivo,
                        inasistencias=self.turnos.contar_inasistencias(estudio.id),
                        remuestreo_motivo=self._motivo_remuestreo_pendiente(estudio.id),
                    )
                )
        return habilitados

    # --- M6-RF4 and M6-RF5: book ---------------------------------------------------------------

    def reservar(
        self, contacto: str, estudio_id: int, laboratorio_id: int, inicio: datetime
    ) -> TurnoSalida:
        estudio = self.estudio_del_paciente(contacto, estudio_id)
        if self.turnos.turno_vigente_de_estudio(estudio.id) is not None:
            raise BusinessRuleError("El estudio ya tiene un turno.", code="ya_tiene_turno")
        if self._motivo_habilitado(estudio) is None:
            raise BusinessRuleError(
                f"El estudio está {estudio.estado.value}: solo puede sacar turno un estudio "
                "Pagado o Autorizado, o uno con una nueva reserva habilitada.",
                code="estudio_no_habilitado",
            )
        laboratorio = self._laboratorio_existente(laboratorio_id)
        self._exigir_turno_valido(inicio)

        recordatorio = Recordatorio(enviar_en=max(self.ahora, inicio - ANTICIPO_RECORDATORIO))
        try:
            turno = self.turnos.crear_turno(
                estudio.id, laboratorio.id, inicio, self.ahora, recordatorio
            )
        except TurnoOcupado:
            raise BusinessRuleError(
                "Ese turno se ocupó antes de que lo reserves. Elegí uno de los turnos libres "
                "actualizados.",
                code="turno_ocupado",
            ) from None

        if estudio.estado != EstadoEstudio.TURNO_SACADO:
            estudio = self.estudios.cambiar_estado(
                estudio.id, EstadoEstudio.TURNO_SACADO, self.ahora
            )
        # The patient booked the new appointment: the resampling stops being pending.
        self.remuestreos.resolver(estudio.id, self.ahora)
        avisar(
            self.avisos,
            estudio.contacto_paciente,
            f"Reservó su turno de extracción en {laboratorio.nombre} para el "
            f"{inicio.astimezone(ARG):%d/%m/%Y a las %H:%M}. Va a recibir un recordatorio por mail.",
        )
        return self._turno_salida(turno, laboratorio)

    # --- M6-RF7: cancel ------------------------------------------------------------------------

    def cancelar(self, contacto: str, turno_id: int) -> CancelacionSalida:
        turno = self.turnos.obtener_turno(turno_id)
        if turno is None:
            raise BusinessRuleError("No existe el turno.", status_code=404)
        estudio = self.estudio_del_paciente(contacto, turno.estudio_id)
        if turno.estado != PROGRAMADO:
            raise BusinessRuleError(
                f"El turno está {turno.estado}: no se puede cancelar.", code="turno_no_vigente"
            )
        if turno.inicio <= self.ahora:
            raise BusinessRuleError(
                "El horario del turno ya pasó: no se puede cancelar. Si no asistió, el laboratorio "
                "lo registra como inasistencia.",
                code="turno_pasado",
            )

        # The state returns before the appointment is released, so an invalid change leaves
        # everything as it was.
        anterior = self._estado_previo_al_turno(estudio)
        if anterior is not None:
            estudio = self.estudios.cambiar_estado(estudio.id, anterior, self.ahora)
        # The appointment is released (it leaves the book) and its reminder is cancelled.
        cancelado = self.turnos.marcar_turno(turno.id, CANCELADO, anular_recordatorio=True)
        avisar(
            self.avisos,
            estudio.contacto_paciente,
            f"Canceló su turno de extracción del {turno.inicio.astimezone(ARG):%d/%m/%Y a las %H:%M}. "
            "Puede sacar uno nuevo cuando quiera, sin costo.",
        )
        return CancelacionSalida(
            turno=self._turno_salida(cancelado, self._laboratorio_existente(turno.laboratorio_id)),
            estudio_estado=estudio.estado,
        )

    @staticmethod
    def _estado_previo_al_turno(estudio: EstudioParaPresupuesto) -> EstadoEstudio | None:
        """Pagado or Autorizado if that is where the study came from; None if it has to stay in
        TurnoSacado (a resampling rebooking), where cancelling just enables a new booking."""
        entradas = [c for c in estudio.historial if c.hacia == EstadoEstudio.TURNO_SACADO]
        if entradas and entradas[-1].desde in (EstadoEstudio.PAGADO, EstadoEstudio.AUTORIZADO):
            return entradas[-1].desde
        return None

    # --- M6-RF8: absences ------------------------------------------------------------------------

    def agenda(self) -> list[AgendaSalida]:
        agenda = []
        for turno in self.turnos.listar_programados():
            estudio = self.estudios.obtener(turno.estudio_id)
            laboratorio = self._laboratorio_existente(turno.laboratorio_id)
            agenda.append(
                AgendaSalida(
                    turno_id=turno.id,
                    estudio_id=turno.estudio_id,
                    paciente=estudio.paciente if estudio else "",
                    laboratorio=laboratorio.nombre,
                    inicio=turno.inicio,
                    ya_paso=turno.inicio <= self.ahora,
                    inasistencias=self.turnos.contar_inasistencias(turno.estudio_id),
                )
            )
        return agenda

    def registrar_inasistencia(self, turno_id: int) -> InasistenciaSalida:
        turno = self.turnos.obtener_turno(turno_id)
        if turno is None:
            raise BusinessRuleError("No existe el turno.", status_code=404)
        if turno.estado != PROGRAMADO:
            raise BusinessRuleError(
                f"El turno está {turno.estado}: no se puede registrar una inasistencia.",
                code="turno_no_vigente",
            )
        if turno.inicio > self.ahora:
            raise BusinessRuleError(
                "El horario del turno todavía no pasó: no se puede registrar una inasistencia.",
                code="turno_futuro",
            )
        estudio = self.estudios.obtener(turno.estudio_id)

        # The study stays in TurnoSacado and, with no valid appointment left, a new booking is
        # enabled (M6-RF3). The slot was already in the past, so there is nothing to free.
        ausente = self.turnos.marcar_turno(turno.id, AUSENTE, anular_recordatorio=True)
        cantidad = self.turnos.contar_inasistencias(estudio.id)
        alcanzado = cantidad >= reglas.LIMITE_INASISTENCIAS
        palabra = "inasistencia" if cantidad == 1 else "inasistencias"
        mensaje = (
            "Registramos que no asistió a su turno de extracción del "
            f"{turno.inicio.astimezone(ARG):%d/%m/%Y a las %H:%M}. "
            f"Acumula {cantidad} {palabra}."
        )
        if alcanzado:
            mensaje += f" Llegó al límite de {reglas.LIMITE_INASISTENCIAS} inasistencias."
        mensaje += " Puede reprogramar su turno desde la plataforma."
        avisado = avisar(self.avisos, estudio.contacto_paciente, mensaje)
        return InasistenciaSalida(
            turno=self._turno_salida(ausente, self._laboratorio_existente(turno.laboratorio_id)),
            estudio_estado=estudio.estado,
            inasistencias=cantidad,
            limite=reglas.LIMITE_INASISTENCIAS,
            limite_alcanzado=alcanzado,
            paciente_avisado=avisado,
        )

    # --- M6-RF9: the sample notification ---------------------------------------------------------

    def recibir_muestra(self, estudio_id: int, volumen_ml: float) -> MuestraRecibidaSalida:
        estudio = self.estudios.obtener(estudio_id)
        if estudio is None:
            raise BusinessRuleError("No existe el estudio.", status_code=404)
        turno = self.turnos.turno_vigente_de_estudio(estudio.id)
        if turno is None or estudio.estado != EstadoEstudio.TURNO_SACADO:
            raise BusinessRuleError(
                "El estudio no tiene un turno de extracción vigente: no se espera una muestra.",
                code="sin_turno_vigente",
            )

        # Every sample is kept. The volume is only recorded: it decides nothing (N5), so a
        # received sample always continues the process.
        muestra = self.turnos.registrar_muestra(estudio.id, volumen_ml, self.ahora)
        self.turnos.marcar_turno(turno.id, REALIZADO, anular_recordatorio=True)
        estudio = self.estudios.cambiar_estado(
            estudio.id, EstadoEstudio.LISTO_PARA_RETIRAR, self.ahora
        )
        return MuestraRecibidaSalida(
            estudio_id=estudio.id,
            estado=estudio.estado,
            muestra_id=muestra.id,
            volumen_ml=volumen_ml,
            listo_para_retirar=True,
        )

    # --- M6-RF10: resampling ---------------------------------------------------------------------

    def solicitar_remuestreo_por_adn(
        self, estudio_id: int, detalle: str | None
    ) -> RemuestreoSalida:
        """The bioinformatician found the DNA insufficient (denatured) while analysing."""
        estudio = self.estudios.obtener(estudio_id)
        if estudio is None:
            raise BusinessRuleError("No existe el estudio.", status_code=404)
        if estudio.estado != EstadoEstudio.EN_ANALISIS_POR_UN_BIOINFORMATICO:
            raise BusinessRuleError(
                f"El estudio está {estudio.estado.value}: el ADN insuficiente solo se informa "
                "durante el análisis.",
                code="estudio_no_en_analisis",
            )
        return self._habilitar_remuestreo(
            estudio,
            reglas.MOTIVO_ADN,
            (detalle or "").strip() or "ADN desnaturalizado",
            CAUSAS_DE_REMUESTREO[reglas.MOTIVO_ADN],
        )

    def estudios_remuestreables(self) -> list[EstudioRemuestreableSalida]:
        """The studies on which the administrative user can ask for a resampling."""
        salida = []
        for estudio in self.estudios.listar_por_estados(ESTADOS_PARA_REMUESTREO_ADMINISTRATIVO):
            pendiente = self.remuestreos.pendiente(estudio.id)
            salida.append(
                EstudioRemuestreableSalida(
                    estudio_id=estudio.id,
                    paciente=estudio.paciente,
                    dni=estudio.dni,
                    estado=estudio.estado,
                    remuestreo_pendiente=None
                    if pendiente is None
                    else RemuestreoPendienteSalida(
                        remuestreo_id=pendiente.id,
                        motivo=pendiente.motivo,
                        detalle=pendiente.detalle,
                        pedido_en=pendiente.registrado_en,
                    ),
                )
            )
        return salida

    def solicitar_remuestreo_por_administrativo(
        self, estudio_id: int, motivo: str, detalle: str, usuario_id: str | None
    ) -> RemuestreoSalida:
        """The administrative user asks for a new sample, for one of the two reasons."""
        detalle = detalle.strip()
        if not detalle:
            raise BusinessRuleError(
                "Indicá el detalle del remuestreo.", status_code=422, code="detalle_obligatorio"
            )
        if motivo not in CAUSAS_DE_REMUESTREO:
            raise BusinessRuleError(
                "El motivo del remuestreo no es válido.", status_code=422, code="motivo_invalido"
            )
        estudio = self.estudios.obtener(estudio_id)
        if estudio is None:
            raise BusinessRuleError("No existe el estudio.", status_code=404)
        if estudio.estado not in ESTADOS_PARA_REMUESTREO_ADMINISTRATIVO:
            raise BusinessRuleError(
                f"El estudio está {estudio.estado.value}: el remuestreo solo se pide cuando la "
                "muestra está en viaje a Corea o en el área de bioinformática.",
                code="estudio_sin_remuestreo_posible",
            )
        if self.remuestreos.pendiente(estudio.id) is not None:
            raise BusinessRuleError(
                "El estudio ya tiene un remuestreo pendiente: el paciente todavía no sacó el "
                "nuevo turno.",
                code="remuestreo_pendiente",
            )
        return self._habilitar_remuestreo(
            estudio, motivo, detalle, CAUSAS_DE_REMUESTREO[motivo], usuario_id
        )

    def _habilitar_remuestreo(
        self,
        estudio: EstudioParaPresupuesto,
        motivo: str,
        detalle: str,
        causa: str,
        pedido_por: str | None = None,
    ) -> RemuestreoSalida:
        # Same study, no new charge and no new study: it goes back to TurnoSacado and, with no
        # valid appointment, the patient can book again. The previous sample and the history of
        # the study are kept.
        # TODO (coordinate with C): the study must leave its batch here (`studies.batch_id`) and
        # the batch must forget it. Batches are not persisted yet, so nothing is done about it.
        estudio = self.estudios.cambiar_estado(estudio.id, EstadoEstudio.TURNO_SACADO, self.ahora)
        remuestreo = self.remuestreos.registrar(estudio.id, motivo, detalle, self.ahora, pedido_por)
        medico_avisado = bool(estudio.contacto_medico) and avisar(
            self.avisos,
            estudio.contacto_medico,
            f"El estudio {estudio.id} de {estudio.paciente} necesita una nueva muestra: {causa}. "
            "Es el mismo estudio y no tiene costo; el paciente va a sacar un nuevo turno.",
        )
        paciente_avisado = avisar(
            self.avisos,
            estudio.contacto_paciente,
            f"Hace falta una nueva muestra para su estudio: {causa}. Es el mismo estudio y no "
            "tiene costo. Saque un nuevo turno de extracción desde la plataforma.",
        )
        return RemuestreoSalida(
            remuestreo_id=remuestreo.id,
            estudio_id=estudio.id,
            estado=estudio.estado,
            motivo=motivo,
            detalle=detalle,
            medico_avisado=medico_avisado,
            paciente_avisado=paciente_avisado,
        )

    def _motivo_remuestreo_pendiente(self, estudio_id: int) -> str | None:
        pendiente = self.remuestreos.pendiente(estudio_id)
        return pendiente.motivo if pendiente else None

    def mis_turnos(self, contacto: str) -> list[TurnoSalida]:
        ids = [e.id for e in self.estudios.listar_de_paciente(contacto)]
        return [
            self._turno_salida(t, self.turnos.obtener_laboratorio(t.laboratorio_id))
            for t in self.turnos.listar_de_estudios(ids)
        ]

    # --- M6-RF6: the documents to print ------------------------------------------------------

    def orden_de_extraccion(self, contacto: str, turno_id: int) -> bytes:
        turno, estudio, laboratorio = self._turno_vigente_del_paciente(contacto, turno_id)
        return documentos.orden_de_extraccion(turno, estudio, laboratorio)

    def consentimiento_informado(self, contacto: str, turno_id: int) -> bytes:
        _, estudio, _ = self._turno_vigente_del_paciente(contacto, turno_id)
        return documentos.consentimiento_informado(estudio)

    def _turno_vigente_del_paciente(
        self, contacto: str, turno_id: int
    ) -> tuple[Turno, EstudioParaPresupuesto, Laboratorio]:
        turno = self.turnos.obtener_turno(turno_id)
        if turno is None:
            raise BusinessRuleError("No existe el turno.", status_code=404)
        estudio = self.estudio_del_paciente(contacto, turno.estudio_id)
        if turno.estado != PROGRAMADO:
            raise BusinessRuleError(
                "El turno ya no está vigente: sus documentos dejaron de estar disponibles.",
                code="turno_no_vigente",
            )
        return turno, estudio, self._laboratorio_existente(turno.laboratorio_id)

    # --- helpers --------------------------------------------------------------------------

    def estudio_del_paciente(self, contacto: str, estudio_id: int) -> EstudioParaPresupuesto:
        estudio = self.estudios.obtener(estudio_id)
        # Someone else's study looks the same as a missing one.
        if estudio is None or estudio.contacto_paciente != contacto:
            raise BusinessRuleError("No existe el estudio.", status_code=404)
        return estudio

    def _motivo_habilitado(self, estudio: EstudioParaPresupuesto) -> str | None:
        if estudio.estado == EstadoEstudio.PAGADO:
            return "pagado"
        if estudio.estado == EstadoEstudio.AUTORIZADO:
            return "autorizado"
        # Still TurnoSacado but without an appointment: a cancellation was not it (that goes back
        # to Pagado or Autorizado), so it is an absence or a resampling.
        if (
            estudio.estado == EstadoEstudio.TURNO_SACADO
            and self.turnos.turno_vigente_de_estudio(estudio.id) is None
        ):
            return "nueva_reserva"
        return None

    def _laboratorio_existente(self, laboratorio_id: int) -> Laboratorio:
        laboratorio = self.turnos.obtener_laboratorio(laboratorio_id)
        if laboratorio is None:
            raise BusinessRuleError("No existe el laboratorio de extracción.", status_code=404)
        return laboratorio

    def _exigir_turno_valido(self, inicio: datetime) -> None:
        hoy = self.ahora.astimezone(ARG).date()
        if (
            not reglas.es_turno_valido(inicio)
            or inicio <= self.ahora
            or inicio.astimezone(ARG).date() > reglas.ultimo_dia_reservable(hoy)
        ):
            raise BusinessRuleError(
                "Ese horario no es un turno válido: son de 15 minutos, de lunes a viernes de 9 a "
                "18, sin feriados, y a futuro.",
                status_code=422,
                code="turno_invalido",
            )

    def _libres_del_dia(self, laboratorio_id: int, dia: date) -> list[datetime]:
        desde = datetime.combine(dia, time.min, tzinfo=ARG)
        ocupados = self.turnos.ocupados(laboratorio_id, desde, desde + timedelta(days=1))
        return [t for t in reglas.turnos_del_dia(dia) if t > self.ahora and t not in ocupados]

    def _proximo_turno(self, laboratorio_id: int) -> datetime | None:
        hoy = self.ahora.astimezone(ARG).date()
        for adelante in range(reglas.HORIZONTE_DIAS + 1):
            libres = self._libres_del_dia(laboratorio_id, hoy + timedelta(days=adelante))
            if libres:
                return libres[0]
        return None

    def _laboratorio(self, lab: Laboratorio, con_proximo_turno: bool = False) -> LaboratorioSalida:
        return LaboratorioSalida(
            **vars(lab),
            proximo_turno=self._proximo_turno(lab.id) if con_proximo_turno else None,
        )

    def _turno_salida(self, turno: Turno, laboratorio: Laboratorio) -> TurnoSalida:
        return TurnoSalida(
            id=turno.id,
            estudio_id=turno.estudio_id,
            laboratorio=self._laboratorio(laboratorio),
            inicio=turno.inicio,
            estado=turno.estado,
            recordatorio_para=None if turno.recordatorio.anulado else turno.recordatorio.enviar_en,
            puede_cancelar=turno.estado == PROGRAMADO and turno.inicio > self.ahora,
            orden_extraccion_url=f"/turnos/{turno.id}/orden-extraccion"
            if turno.estado == PROGRAMADO
            else None,
            consentimiento_url=f"/turnos/{turno.id}/consentimiento-informado"
            if turno.estado == PROGRAMADO
            else None,
        )
