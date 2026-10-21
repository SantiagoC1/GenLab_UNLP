from app.core.enums import Rol

PROVINCES = (
    "Buenos Aires",
    "Catamarca",
    "Chaco",
    "Chubut",
    "Ciudad Autónoma de Buenos Aires",
    "Córdoba",
    "Corrientes",
    "Entre Ríos",
    "Formosa",
    "Jujuy",
    "La Pampa",
    "La Rioja",
    "Mendoza",
    "Misiones",
    "Neuquén",
    "Río Negro",
    "Salta",
    "San Juan",
    "San Luis",
    "Santa Cruz",
    "Santa Fe",
    "Santiago del Estero",
    "Tierra del Fuego",
    "Tucumán",
)

# Roles que se registran solos (M1-RF1). El gerente médico y el transportista no (M1-RF6).
SELF_SIGNUP_ROLES = (
    Rol.MEDICO_TRATANTE.value,
    Rol.ADMINISTRATIVO_LABORATORIO.value,
    Rol.BIOINFORMATICO.value,
)

# Roles que da de alta el administrador general (M1-RF4): todos menos el paciente
# (lo registra el médico tratante) y el propio administrador general.
ADMIN_CREATABLE_ROLES = SELF_SIGNUP_ROLES + (
    Rol.TRANSPORTISTA.value,
    Rol.GERENTE_MEDICO.value,
)
