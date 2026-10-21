export const ROLES = [
  'administrador_general',
  'gerente_medico',
  'medico_tratante',
  'paciente',
  'administrativo_laboratorio',
  'transportista',
  'bioinformatico',
] as const
export type Rol = (typeof ROLES)[number]

/** Nombres visibles según el glosario LEL. */
export const ETIQUETA_ROL: Record<Rol, string> = {
  administrador_general: 'Administrador general',
  gerente_medico: 'Gerente médico',
  medico_tratante: 'Médico tratante',
  paciente: 'Paciente',
  administrativo_laboratorio: 'Administrativo del laboratorio',
  transportista: 'Transportista',
  bioinformatico: 'Bioinformático',
}
