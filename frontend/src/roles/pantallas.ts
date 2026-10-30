import PublicoRegistroPantalla from './publico/RegistroPantalla'
import PublicoIngresarPantalla from './publico/IngresarPantalla'
import ChangePasswordScreen from './publico/ChangePasswordScreen'
import AdministradorGeneralAltaUsuarioPantalla from './administrador_general/AltaUsuarioPantalla'
import GerenteMedicoPatologiasPantalla from './gerente_medico/PatologiasPantalla'
import GerenteMedicoEstrategiaCdssPantalla from './gerente_medico/EstrategiaCdssPantalla'
import GerenteMedicoGenerarCuponesPantalla from './gerente_medico/GenerarCuponesPantalla'
import GerenteMedicoAsignarCuponesMedicosPantalla from './gerente_medico/AsignarCuponesMedicosPantalla'
import MedicoTratanteEstudiosPantalla from './medico_tratante/EstudiosPantalla'
import MedicoTratanteAltaPacientePantalla from './medico_tratante/AltaPacientePantalla'
import MedicoTratanteAltaEstudioPantalla from './medico_tratante/AltaEstudioPantalla'
import MedicoTratanteAsignarCuponPantalla from './medico_tratante/AsignarCuponPantalla'
import MedicoTratanteResultadoPantalla from './medico_tratante/ResultadoPantalla'
import MedicoTratanteReanalisisPantalla from './medico_tratante/ReanalisisPantalla'
import PacienteEstudiosPantalla from './paciente/EstudiosPantalla'
import PacienteCoberturaPantalla from './paciente/CoberturaPantalla'
import PacientePagoPantalla from './paciente/PagoPantalla'
import PacienteDemandaPantalla from './paciente/DemandaPantalla'
import PacienteTurnoPantalla from './paciente/TurnoPantalla'
import PacienteDocumentosPantalla from './paciente/DocumentosPantalla'
import PacienteTurnosPantalla from './paciente/TurnosPantalla'
import PacienteResultadoPantalla from './paciente/ResultadoPantalla'
import PacienteChatbotPantalla from './paciente/ChatbotPantalla'
import AdministrativoLaboratorioPresupuestosPantalla from './administrativo_laboratorio/PresupuestosPantalla'
import AdministrativoLaboratorioAutorizacionesPantalla from './administrativo_laboratorio/AutorizacionesPantalla'
import AdministrativoLaboratorioDatosCrudosPantalla from './administrativo_laboratorio/DatosCrudosPantalla'
import AdministrativoLaboratorioLotesPantalla from './administrativo_laboratorio/LotesPantalla'
import AdministrativoLaboratorioRetiroFedexPantalla from './administrativo_laboratorio/RetiroFedexPantalla'
import AdministrativoLaboratorioUbicacionMuestraPantalla from './administrativo_laboratorio/UbicacionMuestraPantalla'
import AdministrativoLaboratorioSimuladoresPantalla from './administrativo_laboratorio/SimuladoresPantalla'
import TransportistaOrdenDelDiaPantalla from './transportista/OrdenDelDiaPantalla'
import TransportistaRetiroDeMuestrasPantalla from './transportista/RetiroDeMuestrasPantalla'
import TransportistaEntregaDeMuestrasPantalla from './transportista/EntregaDeMuestrasPantalla'
import BioinformaticoEstudiosDisponiblesPantalla from './bioinformatico/EstudiosDisponiblesPantalla'
import BioinformaticoAnalisisPantalla from './bioinformatico/AnalisisPantalla'
import type { ComponentType } from 'react'

export type RolId =
  | 'publico'
  | 'administrador_general'
  | 'gerente_medico'
  | 'medico_tratante'
  | 'paciente'
  | 'administrativo_laboratorio'
  | 'transportista'
  | 'bioinformatico'

export interface Pantalla {
  rol: RolId
  ruta: string
  titulo: string
  componente: ComponentType
}

/** Una entrada por pantalla. La ruta completa es `/${rol}/${ruta}`. */
export const PANTALLAS: Pantalla[] = [
  { rol: 'publico', ruta: 'registro', titulo: 'Registrarse', componente: PublicoRegistroPantalla },
  {
    rol: 'publico',
    ruta: 'ingresar',
    titulo: 'Ingresar al sistema',
    componente: PublicoIngresarPantalla,
  },
  {
    rol: 'publico',
    ruta: 'cambiar-contrasena',
    titulo: 'Cambiar la contraseña',
    componente: ChangePasswordScreen,
  },
  {
    rol: 'administrador_general',
    ruta: 'alta-usuario',
    titulo: 'Dar de alta a un usuario',
    componente: AdministradorGeneralAltaUsuarioPantalla,
  },
  {
    rol: 'gerente_medico',
    ruta: 'patologias',
    titulo: 'Patologías lisosomales',
    componente: GerenteMedicoPatologiasPantalla,
  },
  {
    rol: 'gerente_medico',
    ruta: 'estrategia-cdss',
    titulo: 'Estrategia del CDSS',
    componente: GerenteMedicoEstrategiaCdssPantalla,
  },
  {
    rol: 'gerente_medico',
    ruta: 'generar-cupones',
    titulo: 'Generar cupones de descuento',
    componente: GerenteMedicoGenerarCuponesPantalla,
  },
  {
    rol: 'gerente_medico',
    ruta: 'asignar-cupones-medicos',
    titulo: 'Asignar cupones al médico tratante',
    componente: GerenteMedicoAsignarCuponesMedicosPantalla,
  },
  {
    rol: 'medico_tratante',
    ruta: 'estudios',
    titulo: 'Mis estudios',
    componente: MedicoTratanteEstudiosPantalla,
  },
  {
    rol: 'medico_tratante',
    ruta: 'alta-paciente',
    titulo: 'Dar de alta al paciente',
    componente: MedicoTratanteAltaPacientePantalla,
  },
  {
    rol: 'medico_tratante',
    ruta: 'alta-estudio',
    titulo: 'Dar de alta el estudio',
    componente: MedicoTratanteAltaEstudioPantalla,
  },
  {
    rol: 'medico_tratante',
    ruta: 'asignar-cupon',
    titulo: 'Asignar un cupón de descuento al paciente',
    componente: MedicoTratanteAsignarCuponPantalla,
  },
  {
    rol: 'medico_tratante',
    ruta: 'resultado',
    titulo: 'Resultado del estudio',
    componente: MedicoTratanteResultadoPantalla,
  },
  {
    rol: 'medico_tratante',
    ruta: 'reanalisis',
    titulo: 'Solicitar el reanálisis de un estudio',
    componente: MedicoTratanteReanalisisPantalla,
  },
  {
    rol: 'paciente',
    ruta: 'estudios',
    titulo: 'Mis estudios',
    componente: PacienteEstudiosPantalla,
  },
  {
    rol: 'paciente',
    ruta: 'cobertura',
    titulo: 'Elegir la cobertura por obra social',
    componente: PacienteCoberturaPantalla,
  },
  { rol: 'paciente', ruta: 'pago', titulo: 'Pagar el estudio', componente: PacientePagoPantalla },
  {
    rol: 'paciente',
    ruta: 'demanda',
    titulo: 'Solicitar la reautorización con una demanda',
    componente: PacienteDemandaPantalla,
  },
  {
    rol: 'paciente',
    ruta: 'turno',
    titulo: 'Sacar turno de extracción',
    componente: PacienteTurnoPantalla,
  },
  {
    rol: 'paciente',
    ruta: 'documentos',
    titulo: 'Orden de extracción y consentimiento informado',
    componente: PacienteDocumentosPantalla,
  },
  { rol: 'paciente', ruta: 'turnos', titulo: 'Mis turnos', componente: PacienteTurnosPantalla },
  {
    rol: 'paciente',
    ruta: 'resultado',
    titulo: 'Descargar el resultado del estudio',
    componente: PacienteResultadoPantalla,
  },
  {
    rol: 'paciente',
    ruta: 'chatbot',
    titulo: 'Consultar al chatbot',
    componente: PacienteChatbotPantalla,
  },
  {
    rol: 'administrativo_laboratorio',
    ruta: 'presupuestos',
    titulo: 'Emitir el presupuesto',
    componente: AdministrativoLaboratorioPresupuestosPantalla,
  },
  {
    rol: 'administrativo_laboratorio',
    ruta: 'autorizaciones',
    titulo: 'Registrar la autorización de la obra social',
    componente: AdministrativoLaboratorioAutorizacionesPantalla,
  },
  {
    rol: 'administrativo_laboratorio',
    ruta: 'datos-crudos',
    titulo: 'Cargar los datos crudos de un estudio',
    componente: AdministrativoLaboratorioDatosCrudosPantalla,
  },
  {
    rol: 'administrativo_laboratorio',
    ruta: 'lotes',
    titulo: 'Lotes',
    componente: AdministrativoLaboratorioLotesPantalla,
  },
  {
    rol: 'administrativo_laboratorio',
    ruta: 'retiro-fedex',
    titulo: 'Programar el retiro de un lote con FedEx',
    componente: AdministrativoLaboratorioRetiroFedexPantalla,
  },
  {
    rol: 'administrativo_laboratorio',
    ruta: 'ubicacion-muestra',
    titulo: 'Ubicación de una muestra en traslado',
    componente: AdministrativoLaboratorioUbicacionMuestraPantalla,
  },
  {
    rol: 'administrativo_laboratorio',
    ruta: 'simuladores',
    titulo: 'Simuladores de actores externos',
    componente: AdministrativoLaboratorioSimuladoresPantalla,
  },
  {
    rol: 'transportista',
    ruta: 'orden-del-dia',
    titulo: 'Orden del día',
    componente: TransportistaOrdenDelDiaPantalla,
  },
  {
    rol: 'transportista',
    ruta: 'retiro-de-muestras',
    titulo: 'Retirar muestras en un laboratorio de extracción',
    componente: TransportistaRetiroDeMuestrasPantalla,
  },
  {
    rol: 'transportista',
    ruta: 'entrega-de-muestras',
    titulo: 'Entregar las muestras en el laboratorio central',
    componente: TransportistaEntregaDeMuestrasPantalla,
  },
  {
    rol: 'bioinformatico',
    ruta: 'estudios-disponibles',
    titulo: 'Estudios disponibles',
    componente: BioinformaticoEstudiosDisponiblesPantalla,
  },
  {
    rol: 'bioinformatico',
    ruta: 'analisis',
    titulo: 'Registrar variantes y finalizar el análisis',
    componente: BioinformaticoAnalisisPantalla,
  },
]

const INITIAL_SCREEN: Partial<Record<RolId, string>> = {
  paciente: 'estudios',
}

export function initialScreen(rol: RolId): string | undefined {
  return INITIAL_SCREEN[rol] ?? PANTALLAS.find((p) => p.rol === rol)?.ruta
}
