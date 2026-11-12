from enum import StrEnum


class EstadoEstudio(StrEnum):
    """Ciclo de vida del estudio. Es excluyente: el estudio está en un solo estado a la vez.

    Pompe urgente NO es un estado: es una marca de prioridad aparte (ver Estudio.pompe_urgente).
    """

    CREADO = "Creado"
    PAGADO = "Pagado"
    AUTORIZADO = "Autorizado"
    RECHAZADO = "Rechazado"
    TURNO_SACADO = "TurnoSacado"
    LISTO_PARA_RETIRAR = "ListoParaRetirar"
    EN_CAMINO_AL_LABORATORIO_CENTRAL = "EnCaminoAlLaboratorioCentral"
    EN_LABORATORIO_CENTRAL = "EnLaboratorioCentral"
    EN_VIAJE_A_COREA = "EnViajeACorea"
    EN_EL_AREA_DE_BIOINFORMATICA = "EnElAreaDeBioinformatica"
    EN_ANALISIS_POR_UN_BIOINFORMATICO = "EnAnalisisPorUnBioinformatico"
    RESULTADO_DISPONIBLE = "ResultadoDisponible"


class CdssStrategy(StrEnum):
    """Estrategias del CDSS (M2-RF5). Son los valores permitidos por `app_settings`."""

    MATCHING_SYMPTOMS = "sintomas_coincidentes"
    MATCHING_CARDINAL_SYMPTOMS = "sintomas_cardinales_coincidentes"
    SMALLEST_DIFFERENCE = "menor_diferencia"


class Rol(StrEnum):
    ADMINISTRADOR_GENERAL = "administrador_general"
    GERENTE_MEDICO = "gerente_medico"
    MEDICO_TRATANTE = "medico_tratante"
    PACIENTE = "paciente"
    ADMINISTRATIVO_LABORATORIO = "administrativo_laboratorio"
    TRANSPORTISTA = "transportista"
    BIOINFORMATICO = "bioinformatico"
