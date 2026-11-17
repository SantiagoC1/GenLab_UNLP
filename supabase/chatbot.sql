-- ============================================================================
-- GenLab - Módulo del chatbot (M11) sobre Supabase.
--
-- Estado que el servicio necesita entre una consulta y otra. La Edge Function `chat`
-- (supabase/functions/chat) no guarda nada en memoria, así que todo vive acá.
--
-- Idempotente: se pega entero en el SQL Editor y se puede ejecutar cuantas veces haga
-- falta. Es independiente de schema.sql (no usa sus tablas) y no borra datos.
--
-- Seguridad (ver docs/Chatbot_Supabase.md):
--   * Todas las tablas tienen RLS activado y ninguna política: la API de datos (anon y
--     authenticated) no puede leerlas ni escribirlas.
--   * Toda la lógica va por funciones `security definer`, que solo puede ejecutar la
--     service role (la Edge Function). Ni anon ni authenticated.
--   * El token de cada consumidor se guarda como hash SHA-256; el token en claro se
--     muestra una sola vez al emitirlo.
-- ============================================================================

create extension if not exists pgcrypto with schema extensions;

-- ---------------------------------------------------------------------------
-- Tablas
-- ---------------------------------------------------------------------------

-- Quién puede consumir el chatbot (un grupo, el backend de la plataforma, etc.)
create table if not exists public.chatbot_consumers (
  id          text primary key,
  token_hash  text not null unique,
  active      boolean not null default true,
  created_at  timestamptz not null default now()
);

-- Conversaciones, separadas por consumidor: el mismo id usado por dos consumidores no se mezcla
create table if not exists public.chatbot_conversations (
  consumer_id text not null references public.chatbot_consumers (id) on delete cascade,
  id          text not null,
  updated_at  timestamptz not null default now(),
  primary key (consumer_id, id)
);

create table if not exists public.chatbot_messages (
  id              bigint generated always as identity primary key,
  consumer_id     text not null,
  conversation_id text not null,
  role            text not null check (role in ('user', 'assistant')),
  content         text not null,
  created_at      timestamptz not null default now(),
  foreign key (consumer_id, conversation_id)
    references public.chatbot_conversations (consumer_id, id) on delete cascade
);
create index if not exists chatbot_messages_conversation_idx
  on public.chatbot_messages (consumer_id, conversation_id, id);

-- Límite de consultas: un contador por consumidor y por minuto
create table if not exists public.chatbot_rate_limit (
  consumer_id  text not null,
  window_start timestamptz not null,
  hits         integer not null default 0,
  primary key (consumer_id, window_start)
);

-- Caché de respuestas a consultas repetidas (solo primer mensaje de una conversación)
create table if not exists public.chatbot_cache (
  question_key text primary key,
  answer       text not null,
  kind         text not null
    check (kind in ('respuesta', 'fuera_de_alcance', 'sin_informacion')),
  created_at   timestamptz not null default now(),
  expires_at   timestamptz not null
);
create index if not exists chatbot_cache_created_idx on public.chatbot_cache (created_at);

-- Proveedores de IA a los que hay que saltear un rato (cuota agotada o caídos)
create table if not exists public.chatbot_provider_status (
  provider   text primary key,
  down_until timestamptz not null
);

-- Registro de consultas para evaluar la calidad (M11-RF7). Ya viene con los datos tapados.
create table if not exists public.chatbot_queries (
  id              bigint generated always as identity primary key,
  consumer_id     text not null,
  conversation_id text not null,
  kind            text not null
    check (kind in ('respuesta', 'fuera_de_alcance', 'derivar_medico', 'sin_informacion')),
  provider        text not null,
  question        text not null,
  answer          text not null,
  created_at      timestamptz not null default now()
);
create index if not exists chatbot_queries_created_idx on public.chatbot_queries (created_at);

-- ---------------------------------------------------------------------------
-- RLS: activado y sin políticas = nadie entra por la API de datos
-- ---------------------------------------------------------------------------

alter table public.chatbot_consumers       enable row level security;
alter table public.chatbot_conversations   enable row level security;
alter table public.chatbot_messages        enable row level security;
alter table public.chatbot_rate_limit      enable row level security;
alter table public.chatbot_cache           enable row level security;
alter table public.chatbot_provider_status enable row level security;
alter table public.chatbot_queries         enable row level security;

revoke all on public.chatbot_consumers, public.chatbot_conversations, public.chatbot_messages,
  public.chatbot_rate_limit, public.chatbot_cache, public.chatbot_provider_status,
  public.chatbot_queries
  from public, anon, authenticated;

-- Solo la service role (la Edge Function y el panel de Supabase) toca las tablas
grant all on public.chatbot_consumers, public.chatbot_conversations, public.chatbot_messages,
  public.chatbot_rate_limit, public.chatbot_cache, public.chatbot_provider_status,
  public.chatbot_queries
  to service_role;
grant usage, select on all sequences in schema public to service_role;

-- ---------------------------------------------------------------------------
-- Funciones. Las usa la Edge Function con la service role.
-- ---------------------------------------------------------------------------

-- Consumidores ---------------------------------------------------------------

-- Emite (o renueva) el token de un consumidor y lo devuelve EN CLARO, una sola vez.
-- Solo se guarda su hash. Si ya existía, el token anterior deja de servir.
-- Uso (SQL Editor):  select public.chatbot_issue_token('grupo-2');
create or replace function public.chatbot_issue_token(p_consumer text)
returns text
language plpgsql
security definer set search_path = ''
as $$
declare
  v_token text;
begin
  if p_consumer is null or length(trim(p_consumer)) = 0 then
    raise exception 'El nombre del consumidor no puede estar vacío';
  end if;
  v_token := encode(extensions.gen_random_bytes(32), 'hex');
  insert into public.chatbot_consumers (id, token_hash)
  values (trim(p_consumer), encode(extensions.digest(v_token, 'sha256'), 'hex'))
  on conflict (id) do update
    set token_hash = excluded.token_hash, active = true;
  return v_token;
end $$;

-- Deja de aceptar a un consumidor sin borrar su historial.
-- Uso:  select public.chatbot_revoke_consumer('grupo-2');
create or replace function public.chatbot_revoke_consumer(p_consumer text)
returns boolean
language plpgsql
security definer set search_path = ''
as $$
begin
  update public.chatbot_consumers set active = false where id = p_consumer;
  return found;
end $$;

-- Devuelve el id del consumidor dueño del token, o null si es inválido o está revocado.
create or replace function public.chatbot_authenticate(p_token text)
returns text
language sql
stable
security definer set search_path = ''
as $$
  select id
  from public.chatbot_consumers
  where active
    and token_hash = encode(extensions.digest(coalesce(p_token, ''), 'sha256'), 'hex');
$$;

-- Límite de consultas ---------------------------------------------------------

-- Registra una consulta. Devuelve 0 si puede seguir, o los segundos que faltan para poder
-- consultar de nuevo si ya pasó el límite del minuto en curso (M11-RF9).
create or replace function public.chatbot_check_rate_limit(p_consumer text, p_limit integer)
returns integer
language plpgsql
security definer set search_path = ''
as $$
declare
  v_window timestamptz := date_trunc('minute', now());
  v_hits   integer;
begin
  -- Limpieza de ventanas viejas
  delete from public.chatbot_rate_limit where window_start < now() - interval '10 minutes';

  insert into public.chatbot_rate_limit as r (consumer_id, window_start, hits)
  values (p_consumer, v_window, 1)
  on conflict (consumer_id, window_start) do update
    set hits = r.hits + 1
    where r.hits < p_limit
  returning r.hits into v_hits;

  if v_hits is null then
    -- La fila ya estaba en el límite: no se cuenta esta consulta
    return greatest(1, ceil(extract(epoch from (v_window + interval '1 minute' - now())))::integer);
  end if;
  return 0;
end $$;

-- Conversaciones --------------------------------------------------------------

-- Últimos mensajes de la conversación, del más viejo al más nuevo. Vacío si es nueva o venció.
create or replace function public.chatbot_get_history(
  p_consumer text, p_conversation text, p_ttl_minutes integer, p_max_messages integer
)
returns table (role text, content text)
language sql
stable
security definer set search_path = ''
as $$
  select m.role, m.content
  from (
    select mm.id, mm.role, mm.content
    from public.chatbot_messages mm
    join public.chatbot_conversations c
      on c.consumer_id = mm.consumer_id and c.id = mm.conversation_id
    where c.consumer_id = p_consumer
      and c.id = p_conversation
      and c.updated_at > now() - make_interval(mins => p_ttl_minutes)
    order by mm.id desc
    limit p_max_messages
  ) m
  order by m.id;
$$;

-- Agrega la consulta y su respuesta y conserva solo los últimos mensajes (M11-RF6).
-- Si la conversación había vencido, empieza de cero.
create or replace function public.chatbot_add_turn(
  p_consumer text, p_conversation text, p_question text, p_answer text,
  p_ttl_minutes integer, p_max_messages integer
)
returns void
language plpgsql
security definer set search_path = ''
as $$
begin
  -- Vencimiento: borrar el contenido de una conversación sin actividad
  delete from public.chatbot_messages m
  using public.chatbot_conversations c
  where c.consumer_id = p_consumer
    and c.id = p_conversation
    and m.consumer_id = c.consumer_id
    and m.conversation_id = c.id
    and c.updated_at <= now() - make_interval(mins => p_ttl_minutes);

  insert into public.chatbot_conversations (consumer_id, id, updated_at)
  values (p_consumer, p_conversation, now())
  on conflict (consumer_id, id) do update set updated_at = now();

  insert into public.chatbot_messages (consumer_id, conversation_id, role, content)
  values (p_consumer, p_conversation, 'user', p_question),
         (p_consumer, p_conversation, 'assistant', p_answer);

  delete from public.chatbot_messages
  where consumer_id = p_consumer
    and conversation_id = p_conversation
    and id not in (
      select id from public.chatbot_messages
      where consumer_id = p_consumer and conversation_id = p_conversation
      order by id desc
      limit p_max_messages
    );

  -- Limpieza: conversaciones olvidadas hace más de un día
  delete from public.chatbot_conversations where updated_at < now() - interval '1 day';
end $$;

-- Caché -----------------------------------------------------------------------

create or replace function public.chatbot_cache_get(p_key text)
returns table (answer text, kind text)
language sql
stable
security definer set search_path = ''
as $$
  select c.answer, c.kind
  from public.chatbot_cache c
  where c.question_key = p_key and c.expires_at > now();
$$;

create or replace function public.chatbot_cache_put(
  p_key text, p_answer text, p_kind text, p_ttl_minutes integer, p_max_entries integer
)
returns void
language plpgsql
security definer set search_path = ''
as $$
begin
  if p_max_entries <= 0 or length(p_key) = 0 then
    return;
  end if;

  insert into public.chatbot_cache (question_key, answer, kind, created_at, expires_at)
  values (p_key, p_answer, p_kind, now(), now() + make_interval(mins => p_ttl_minutes))
  on conflict (question_key) do update
    set answer = excluded.answer, kind = excluded.kind,
        created_at = now(), expires_at = excluded.expires_at;

  delete from public.chatbot_cache where expires_at <= now();
  delete from public.chatbot_cache
  where question_key not in (
    select question_key from public.chatbot_cache order by created_at desc limit p_max_entries
  );
end $$;

-- Proveedores de IA -----------------------------------------------------------

-- Nombres de los proveedores que hay que saltear ahora
create or replace function public.chatbot_providers_down()
returns setof text
language sql
stable
security definer set search_path = ''
as $$
  select provider from public.chatbot_provider_status where down_until > now();
$$;

create or replace function public.chatbot_mark_provider_down(p_provider text, p_seconds integer)
returns void
language sql
security definer set search_path = ''
as $$
  insert into public.chatbot_provider_status (provider, down_until)
  values (p_provider, now() + make_interval(secs => p_seconds))
  on conflict (provider) do update set down_until = excluded.down_until;
$$;

-- Registro --------------------------------------------------------------------

create or replace function public.chatbot_log_query(
  p_consumer text, p_conversation text, p_kind text, p_provider text,
  p_question text, p_answer text
)
returns void
language sql
security definer set search_path = ''
as $$
  insert into public.chatbot_queries
    (consumer_id, conversation_id, kind, provider, question, answer)
  values (p_consumer, p_conversation, p_kind, p_provider, p_question, p_answer);
$$;

-- ---------------------------------------------------------------------------
-- Quién puede ejecutar qué: solo la service role (la Edge Function y el SQL Editor).
-- Por defecto Postgres da EXECUTE a todos: se lo sacamos a anon y authenticated.
-- ---------------------------------------------------------------------------

revoke execute on function
  public.chatbot_issue_token(text),
  public.chatbot_revoke_consumer(text),
  public.chatbot_authenticate(text),
  public.chatbot_check_rate_limit(text, integer),
  public.chatbot_get_history(text, text, integer, integer),
  public.chatbot_add_turn(text, text, text, text, integer, integer),
  public.chatbot_cache_get(text),
  public.chatbot_cache_put(text, text, text, integer, integer),
  public.chatbot_providers_down(),
  public.chatbot_mark_provider_down(text, integer),
  public.chatbot_log_query(text, text, text, text, text, text)
  from public, anon, authenticated;

grant execute on function
  public.chatbot_issue_token(text),
  public.chatbot_revoke_consumer(text),
  public.chatbot_authenticate(text),
  public.chatbot_check_rate_limit(text, integer),
  public.chatbot_get_history(text, text, integer, integer),
  public.chatbot_add_turn(text, text, text, text, integer, integer),
  public.chatbot_cache_get(text),
  public.chatbot_cache_put(text, text, text, integer, integer),
  public.chatbot_providers_down(),
  public.chatbot_mark_provider_down(text, integer),
  public.chatbot_log_query(text, text, text, text, text, text)
  to service_role;
