-- Tablas del módulo de acceso (M1). Ejecutar en el SQL Editor de Supabase.
-- Las contraseñas y los códigos por mail los maneja Supabase Auth (auth.users).
-- El backend usa la service role key, que no pasa por RLS: por eso RLS queda activada
-- y sin políticas, así nadie accede a estas tablas con la anon key.

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

-- M1-RF6: un solo transportista por provincia
create unique index if not exists users_one_carrier_per_province
    on public.users (province) where role = 'transportista';

create table if not exists public.user_specialties (
    user_id      uuid    not null references public.users (id) on delete cascade,
    specialty_id integer not null references public.specialties (id),
    primary key (user_id, specialty_id)
);

alter table public.specialties      enable row level security;
alter table public.users            enable row level security;
alter table public.user_specialties enable row level security;

-- Catálogo de ejemplo: ajustarlo con el que defina la cátedra
insert into public.specialties (name) values
    ('Genética médica'), ('Pediatría'), ('Neurología'), ('Cardiología'),
    ('Nefrología'), ('Hematología'), ('Endocrinología'), ('Clínica médica')
on conflict (name) do nothing;