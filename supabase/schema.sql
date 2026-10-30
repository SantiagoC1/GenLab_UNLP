-- GenLab: esquema completo de la base. Ejecutar de una vez en el SQL Editor de Supabase
-- (pegar todo el archivo y "Run"). Se puede volver a ejecutar sin romper nada: todo es
-- "if not exists" / "on conflict do nothing".
--
-- Las contraseñas y los códigos por mail los maneja Supabase Auth (auth.users).
-- El backend usa la service role key, que no pasa por RLS: por eso RLS queda activada y sin
-- políticas en todas las tablas, y se le quitan los permisos a la anon key (que es pública).
--
-- Qué es definición del equipo y qué es propuesta (a confirmar con quien tenga cada módulo):
--   * Propuestas: los valores de estado de `batches`, `authorizations`, `appointments`,
--     `analyses` y `coupons`, el origen de `study_genes`, y que una cuenta (`users`) pueda tener
--     varios pacientes (hermanos menores con el mismo mail de los padres). Son columnas de texto
--     con CHECK: cambiar los valores es editar el CHECK, no migrar datos.
--   * Los estados del estudio son los de `EstadoEstudio` (backend/app/core/enums.py). No se
--     agregan ni se cambian sin avisar al equipo; `tests/test_schema.py` verifica que coincidan.
--     "Pompe urgente" es una marca (`studies.pompe_urgent`), no un estado.
--   * Pendientes de la especificación que NO se resuelven acá: P1, P2, P3, P4, P5, P6, P7, P8,
--     P11, P12, P13, P14, P15 y P16.
--
-- Primer administrador general (no se puede crear desde la aplicación):
--   1. Authentication > Users > "Add user" (con "Auto Confirm User"), con su mail y contraseña.
--   2. Copiar el UUID del usuario creado y ejecutar, completando los datos:
--        insert into public.users (id, email, first_name, last_name, phone, role)
--        values ('<UUID>', '<mail en minúsculas>', '<nombre>', '<apellido>', '<teléfono>',
--                'administrador_general');
--
-- Desbloquear una cuenta a mano, si hiciera falta (la aplicación tiene el botón del administrador):
--   update public.users set blocked = false, failed_attempts = 0 where email = '<mail>';


-- ============================================================================
-- 1. Acceso (M1)
-- ============================================================================

create table if not exists public.specialties (
    id   serial primary key,
    name text not null unique
);

create table if not exists public.users (
    id                   uuid primary key references auth.users (id) on delete cascade,
    email                text not null unique,
    first_name           text not null,
    last_name            text not null,
    phone                text not null,
    role                 text not null check (role in (
        'administrador_general', 'gerente_medico', 'medico_tratante', 'paciente',
        'administrativo_laboratorio', 'transportista', 'bioinformatico'
    )),
    province             text,
    license_number       text,
    must_change_password boolean not null default false,
    failed_attempts      integer not null default 0,
    blocked              boolean not null default false,
    created_at           timestamptz not null default now()
);

-- M1-RF5: un solo transportista por provincia
create unique index if not exists users_one_carrier_per_province
    on public.users (province) where role = 'transportista';

create table if not exists public.user_specialties (
    user_id      uuid    not null references public.users (id) on delete cascade,
    specialty_id integer not null references public.specialties (id),
    primary key (user_id, specialty_id)
);

-- M1-RF8: dispositivos desde los que ya se verificó un código. Se guarda el hash (sha256) del
-- identificador del navegador, nunca el identificador.
create table if not exists public.trusted_devices (
    user_id     uuid        not null references public.users (id) on delete cascade,
    device_hash text        not null,
    created_at  timestamptz not null default now(),
    primary key (user_id, device_hash)
);

-- Catálogo de ejemplo: ajustarlo con el que defina la cátedra
insert into public.specialties (name) values
    ('Genética médica'), ('Pediatría'), ('Neurología'), ('Cardiología'),
    ('Nefrología'), ('Hematología'), ('Endocrinología'), ('Clínica médica')
on conflict (name) do nothing;


-- ============================================================================
-- 2. Configuración médica (M2) y pacientes (M3)
-- ============================================================================

create table if not exists public.pathologies (
    id         serial primary key,
    name       text        not null,
    created_at timestamptz not null default now()
);

-- M2-RF3: no se puede duplicar una patología (sin distinguir mayúsculas)
create unique index if not exists pathologies_name_unique
    on public.pathologies (lower(name));

-- Síntomas elegidos con el buscador de SNOMED (MA2): se guarda el código y el término
create table if not exists public.symptoms (
    code text primary key,
    term text not null
);

create table if not exists public.pathology_symptoms (
    pathology_id integer not null references public.pathologies (id) on delete cascade,
    symptom_code text    not null references public.symptoms (code),
    is_cardinal  boolean not null default false,
    primary key (pathology_id, symptom_code)
);

-- M2-RF1: cada patología tiene un solo síntoma cardinal
create unique index if not exists pathology_one_cardinal
    on public.pathology_symptoms (pathology_id) where is_cardinal;

-- Configuración general. Hoy guarda la estrategia del CDSS (M2-RF5): quién la cambia (el gerente
-- médico) y el valor por defecto son la propuesta para la decisión 4, a confirmar.
create table if not exists public.app_settings (
    key        text primary key,
    value      text        not null,
    updated_by uuid references public.users (id),
    updated_at timestamptz not null default now(),
    constraint cdss_strategy_valid check (key <> 'cdss_strategy' or value in (
        'sintomas_coincidentes', 'sintomas_cardinales_coincidentes', 'menor_diferencia'
    ))
);

insert into public.app_settings (key, value) values
    ('cdss_strategy', 'sintomas_cardinales_coincidentes')
on conflict (key) do nothing;

-- Un paciente tiene su propia identidad (DNI, nombre, fecha de nacimiento) y una cuenta de
-- acceso (`account_user_id`): la suya, o la de su padre o madre si es menor. Así dos hermanos
-- comparten el mail de los padres (M3-RF2) sin chocar con el mail único de Auth.
create table if not exists public.patients (
    id               uuid primary key default gen_random_uuid(),
    account_user_id  uuid        not null references public.users (id),
    dni              text        not null unique,
    first_name       text        not null,
    last_name        text        not null,
    birth_date       date        not null,
    phone            text        not null,
    clinical_summary text        not null,
    suspicion_type   text        not null check (suspicion_type in ('clinica', 'familiar')),
    family_tree_path text,
    registered_by    uuid        not null references public.users (id),
    created_at       timestamptz not null default now()
);

create index if not exists patients_account_idx on public.patients (account_user_id);

-- Diagnósticos presuntivos (M3-RF3)
create table if not exists public.patient_pathologies (
    patient_id   uuid    not null references public.patients (id) on delete cascade,
    pathology_id integer not null references public.pathologies (id),
    primary key (patient_id, pathology_id)
);

-- Síntomas del paciente. Son independientes de los de la patología: modificar una patología
-- no cambia lo ya registrado (P13).
create table if not exists public.patient_symptoms (
    patient_id   uuid not null references public.patients (id) on delete cascade,
    symptom_code text not null references public.symptoms (code),
    primary key (patient_id, symptom_code)
);

-- Familiares para el familiograma (M3-RF9)
create table if not exists public.relatives (
    id         serial primary key,
    patient_id uuid        not null references public.patients (id) on delete cascade,
    kinship    text        not null,
    name       text        not null,
    diagnosis  text,
    created_at timestamptz not null default now()
);

create index if not exists relatives_patient_idx on public.relatives (patient_id);

create table if not exists public.relative_symptoms (
    relative_id  integer not null references public.relatives (id) on delete cascade,
    symptom_code text    not null references public.symptoms (code),
    primary key (relative_id, symptom_code)
);


-- ============================================================================
-- 3. Laboratorios de extracción y lotes (M6 y M7)
-- ============================================================================

create table if not exists public.extraction_labs (
    id         serial primary key,
    name       text        not null,
    address    text        not null,
    province   text        not null,
    latitude   numeric(9, 6),
    longitude  numeric(9, 6),
    created_at timestamptz not null default now()
);

create index if not exists extraction_labs_province_idx on public.extraction_labs (province);

-- Estados del lote (propuesta): Abierto > Cerrado (10 estudios o Pompe urgente) > Autorizado
-- (permiso del Ministerio de Salud) > RetiroProgramado (FedEx) > EnViajeACorea (sellado)
create table if not exists public.batches (
    id              serial primary key,
    state           text        not null default 'Abierto' check (state in (
        'Abierto', 'Cerrado', 'Autorizado', 'RetiroProgramado', 'EnViajeACorea'
    )),
    permit_pdf_path text,
    fedex_url       text,
    pickup_at       timestamptz,
    closed_at       timestamptz,
    created_at      timestamptz not null default now()
);

-- M7-RF6 y RF7: hay un solo lote abierto a la vez
create unique index if not exists batches_one_open
    on public.batches ((true)) where state = 'Abierto';


-- ============================================================================
-- 4. Estudios (M3, M4 y siguientes)
-- ============================================================================

create table if not exists public.studies (
    id                 serial primary key,
    patient_id         uuid    not null references public.patients (id),
    requested_by       uuid    not null references public.users (id),
    state              text    not null default 'Creado' check (state in (
        'Creado', 'Pagado', 'Autorizado', 'Rechazado', 'TurnoSacado', 'ListoParaRetirar',
        'EnCaminoAlLaboratorioCentral', 'EnLaboratorioCentral', 'EnViajeACorea',
        'EnElAreaDeBioinformatica', 'EnAnalisisPorUnBioinformatico', 'ResultadoDisponible'
    )),
    pompe_urgent       boolean not null default false,
    secondary_findings boolean not null default false,
    batch_id           integer references public.batches (id),
    created_at         timestamptz not null default now(),
    state_changed_at   timestamptz not null default now()
);

create index if not exists studies_state_idx        on public.studies (state);
create index if not exists studies_patient_idx      on public.studies (patient_id);
create index if not exists studies_batch_idx        on public.studies (batch_id);
create index if not exists studies_requested_by_idx on public.studies (requested_by);

-- Patologías sospechadas del estudio (M3-RF10). De acá sale la marca Pompe urgente.
create table if not exists public.study_pathologies (
    study_id     integer not null references public.studies (id) on delete cascade,
    pathology_id integer not null references public.pathologies (id),
    primary key (study_id, pathology_id)
);

-- Historial de cambios de estado: orden de llegada (M7-RF5 y M8-RF2), estado previo al cancelar
-- un turno (M6-RF7) y registro de quién hizo cada cambio. `changed_by` queda vacío cuando
-- cambia por una señal externa (laboratorio de extracción, FedEx).
create table if not exists public.study_state_history (
    id         bigserial primary key,
    study_id   integer     not null references public.studies (id) on delete cascade,
    from_state text check (from_state in (
        'Creado', 'Pagado', 'Autorizado', 'Rechazado', 'TurnoSacado', 'ListoParaRetirar',
        'EnCaminoAlLaboratorioCentral', 'EnLaboratorioCentral', 'EnViajeACorea',
        'EnElAreaDeBioinformatica', 'EnAnalisisPorUnBioinformatico', 'ResultadoDisponible'
    )),
    to_state   text        not null check (to_state in (
        'Creado', 'Pagado', 'Autorizado', 'Rechazado', 'TurnoSacado', 'ListoParaRetirar',
        'EnCaminoAlLaboratorioCentral', 'EnLaboratorioCentral', 'EnViajeACorea',
        'EnElAreaDeBioinformatica', 'EnAnalisisPorUnBioinformatico', 'ResultadoDisponible'
    )),
    changed_by uuid references public.users (id),
    changed_at timestamptz not null default now()
);

create index if not exists study_state_history_study_idx
    on public.study_state_history (study_id, changed_at);

-- Avisos dentro de la plataforma (M9). Organización, lectura y baja: pendiente P16.
create table if not exists public.notifications (
    id         serial primary key,
    user_id    uuid        not null references public.users (id) on delete cascade,
    study_id   integer references public.studies (id) on delete set null,
    message    text        not null,
    is_read    boolean     not null default false,
    created_at timestamptz not null default now()
);

create index if not exists notifications_user_idx on public.notifications (user_id, is_read);


-- ============================================================================
-- 5. Presupuesto, cobertura, pago y cupones (M4 y M5)
-- ============================================================================

-- M4-RF1: importe fijo según la cantidad de genes (USD 500 hasta 5, más USD 30 por cada uno)
create table if not exists public.budgets (
    id         serial primary key,
    study_id   integer       not null unique references public.studies (id) on delete cascade,
    gene_count integer       not null check (gene_count >= 0),
    amount_usd numeric(10, 2) not null check (amount_usd >= 0),
    issued_by  uuid          not null references public.users (id),
    issued_at  timestamptz   not null default now()
);

-- Respuesta de la obra social (M4-RF3, RF7 y RF8). Un estudio puede tener más de una si se
-- pide la reautorización con una demanda.
create table if not exists public.authorizations (
    id               serial primary key,
    study_id         integer     not null references public.studies (id) on delete cascade,
    insurance_name   text        not null,
    coverage_pct     integer     not null check (coverage_pct between 0 and 100),
    status           text        not null default 'Pendiente' check (status in (
        'Pendiente', 'Autorizado', 'Rechazado'
    )),
    rejection_reason text,
    demand_pdf_path  text,
    registered_by    uuid references public.users (id),
    created_at       timestamptz not null default now(),
    resolved_at      timestamptz
);

create index if not exists authorizations_study_idx on public.authorizations (study_id);

-- Los cupones los crea y valida el módulo MA3: acá solo los asignados (M5-RF2 y RF3)
create table if not exists public.coupons (
    id           serial primary key,
    code         text        not null unique,
    discount_pct integer     not null check (discount_pct between 1 and 100),
    status       text        not null default 'Vigente' check (status in (
        'Vigente', 'Utilizado', 'Vencido'
    )),
    doctor_id    uuid references public.users (id),
    patient_id   uuid references public.patients (id),
    created_at   timestamptz not null default now()
);

-- Registro financiero del pago particular simulado (M4-RF5)
create table if not exists public.payments (
    id         serial primary key,
    study_id   integer        not null references public.studies (id),
    amount_usd numeric(10, 2) not null check (amount_usd >= 0),
    coupon_id  integer references public.coupons (id),
    paid_at    timestamptz    not null default now()
);

create index if not exists payments_study_idx on public.payments (study_id);


-- ============================================================================
-- 6. Turnos, extracción y orden del día (M6 y M7)
-- ============================================================================

-- Los turnos libres se generan por regla (15 minutos, lunes a viernes de 9 a 18); acá solo
-- están los reservados. Estados (propuesta): Programado, Cancelado, Ausente, Realizado.
create table if not exists public.appointments (
    id         serial primary key,
    study_id   integer     not null references public.studies (id),
    lab_id     integer     not null references public.extraction_labs (id),
    starts_at  timestamptz not null,
    status     text        not null default 'Programado' check (status in (
        'Programado', 'Cancelado', 'Ausente', 'Realizado'
    )),
    created_at timestamptz not null default now()
);

-- M6-RF5: un turno no se puede reservar dos veces; un estudio tiene un solo turno vigente
create unique index if not exists appointments_one_per_slot
    on public.appointments (lab_id, starts_at) where status <> 'Cancelado';
create unique index if not exists appointments_one_active_per_study
    on public.appointments (study_id) where status = 'Programado';
create index if not exists appointments_study_idx on public.appointments (study_id);

-- Muestra de sangre informada por el laboratorio de extracción (M6-RF9: desde 2 ml)
create table if not exists public.samples (
    id         serial primary key,
    study_id   integer       not null references public.studies (id),
    volume_ml  numeric(5, 2) not null check (volume_ml > 0),
    taken_at   timestamptz   not null,
    created_at timestamptz   not null default now()
);

create index if not exists samples_study_idx on public.samples (study_id);

-- Orden del día del transportista (M7-RF1). `arrived_at` es la llegada al laboratorio central.
create table if not exists public.daily_routes (
    id         serial primary key,
    carrier_id uuid        not null references public.users (id),
    day        date        not null,
    province   text        not null,
    arrived_at timestamptz,
    created_at timestamptz not null default now(),
    unique (carrier_id, day)
);

create table if not exists public.route_stops (
    route_id     integer not null references public.daily_routes (id) on delete cascade,
    lab_id       integer not null references public.extraction_labs (id),
    position     integer not null check (position > 0),
    picked_up_at timestamptz,
    primary key (route_id, lab_id),
    unique (route_id, position)
);


-- ============================================================================
-- 7. Bioinformática y resultados (M8)
-- ============================================================================

create table if not exists public.raw_data (
    id          serial primary key,
    study_id    integer     not null references public.studies (id),
    file_path   text        not null,
    attached_by uuid        not null references public.users (id),
    created_at  timestamptz not null default now()
);

create index if not exists raw_data_study_idx on public.raw_data (study_id);

-- Un reanálisis agrega un análisis nuevo al mismo estudio (M8-RF8).
-- Resultado (propuesta): Negativo, ConVariantes o ADNInsuficiente (M6-RF10).
create table if not exists public.analyses (
    id                  serial primary key,
    study_id            integer     not null references public.studies (id),
    bioinformatician_id uuid        not null references public.users (id),
    outcome             text check (outcome in ('Negativo', 'ConVariantes', 'ADNInsuficiente')),
    result_pdf_path     text,
    started_at          timestamptz not null default now(),
    finished_at         timestamptz
);

-- M8-RF3: un estudio tiene un solo análisis abierto; si otro lo tomó antes, falla el segundo
create unique index if not exists analyses_one_open_per_study
    on public.analyses (study_id) where finished_at is null;
create index if not exists analyses_study_idx on public.analyses (study_id);

-- La clasificación la informa Apigen y no se edita (M8-RF4). P5: cómo se informa una VUS.
create table if not exists public.variants (
    id             serial primary key,
    analysis_id    integer not null references public.analyses (id) on delete cascade,
    gene           text    not null,
    variant        text    not null,
    classification text    not null check (classification in ('Patogénica', 'Benigna', 'VUS'))
);

create index if not exists variants_analysis_idx on public.variants (analysis_id);

-- Genes del estudio (M3-RF10 y RF11). Origen (propuesta): de la patología, hallazgo secundario
-- o agregado a mano por el médico. `analysis_id` marca qué análisis ya los cubrió, para que un
-- reanálisis solo tome los genes todavía no analizados (P6, P15).
create table if not exists public.study_genes (
    study_id    integer not null references public.studies (id) on delete cascade,
    gene        text    not null,
    origin      text    not null default 'patologia' check (origin in (
        'patologia', 'hallazgo_secundario', 'manual'
    )),
    analysis_id integer references public.analyses (id),
    primary key (study_id, gene)
);


-- ============================================================================
-- Seguridad: RLS activada y sin políticas en todas las tablas (solo entra el backend con la
-- service role key), y sin permisos para la anon key ni para los usuarios de Auth.
-- ============================================================================

alter table public.specialties          enable row level security;
alter table public.users                enable row level security;
alter table public.user_specialties     enable row level security;
alter table public.trusted_devices      enable row level security;
alter table public.pathologies          enable row level security;
alter table public.symptoms             enable row level security;
alter table public.pathology_symptoms   enable row level security;
alter table public.app_settings         enable row level security;
alter table public.patients             enable row level security;
alter table public.patient_pathologies  enable row level security;
alter table public.patient_symptoms     enable row level security;
alter table public.relatives            enable row level security;
alter table public.relative_symptoms    enable row level security;
alter table public.extraction_labs      enable row level security;
alter table public.batches              enable row level security;
alter table public.studies              enable row level security;
alter table public.study_pathologies    enable row level security;
alter table public.study_state_history  enable row level security;
alter table public.notifications        enable row level security;
alter table public.budgets              enable row level security;
alter table public.authorizations       enable row level security;
alter table public.coupons              enable row level security;
alter table public.payments             enable row level security;
alter table public.appointments         enable row level security;
alter table public.samples              enable row level security;
alter table public.daily_routes         enable row level security;
alter table public.route_stops          enable row level security;
alter table public.raw_data             enable row level security;
alter table public.analyses             enable row level security;
alter table public.variants             enable row level security;
alter table public.study_genes          enable row level security;

revoke all on all tables    in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
alter default privileges in schema public revoke all on tables    from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
