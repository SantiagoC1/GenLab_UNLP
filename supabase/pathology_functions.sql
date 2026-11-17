-- ============================================================================
-- Guarda los síntomas que todavía no existen (no pisa el término de los que ya están).
create or replace function public.save_pathology_symptoms(p_cardinal jsonb, p_secondary jsonb)
returns void
language sql
security definer set search_path = ''
as $$
  insert into public.symptoms (code, term)
  select s ->> 'code', s ->> 'term'
  from (select p_cardinal as s union all select value from jsonb_array_elements(p_secondary)) all_symptoms
  on conflict (code) do nothing;
$$;

-- Vincula el cardinal y los secundarios con la patología.
create or replace function public.link_pathology_symptoms(
  p_pathology_id integer, p_cardinal jsonb, p_secondary jsonb
)
returns void
language sql
security definer set search_path = ''
as $$
  insert into public.pathology_symptoms (pathology_id, symptom_code, is_cardinal)
  values (p_pathology_id, p_cardinal ->> 'code', true);

  insert into public.pathology_symptoms (pathology_id, symptom_code, is_cardinal)
  select p_pathology_id, value ->> 'code', false from jsonb_array_elements(p_secondary);
$$;

-- Alta de la patología (escenario 5). Devuelve su id. Si el nombre ya existe, falla por el índice
-- único `pathologies_name_unique` (23505).
create or replace function public.create_pathology(
  p_name text, p_cardinal jsonb, p_secondary jsonb
)
returns integer
language plpgsql
security definer set search_path = ''
as $$
declare
  v_id integer;
begin
  perform public.save_pathology_symptoms(p_cardinal, p_secondary);
  insert into public.pathologies (name) values (trim(p_name)) returning id into v_id;
  perform public.link_pathology_symptoms(v_id, p_cardinal, p_secondary);
  return v_id;
end $$;

create or replace function public.replace_pathology_symptoms(
  p_pathology_id integer, p_cardinal jsonb, p_secondary jsonb
)
returns void
language plpgsql
security definer set search_path = ''
as $$
begin
  if not exists (select 1 from public.pathologies where id = p_pathology_id) then
    raise exception 'La patología no existe';
  end if;
  perform public.save_pathology_symptoms(p_cardinal, p_secondary);
  delete from public.pathology_symptoms where pathology_id = p_pathology_id;
  perform public.link_pathology_symptoms(p_pathology_id, p_cardinal, p_secondary);
end $$;

revoke execute on function
  public.save_pathology_symptoms(jsonb, jsonb),
  public.link_pathology_symptoms(integer, jsonb, jsonb),
  public.create_pathology(text, jsonb, jsonb),
  public.replace_pathology_symptoms(integer, jsonb, jsonb)
from public, anon, authenticated;

grant execute on function
  public.save_pathology_symptoms(jsonb, jsonb),
  public.link_pathology_symptoms(integer, jsonb, jsonb),
  public.create_pathology(text, jsonb, jsonb),
  public.replace_pathology_symptoms(integer, jsonb, jsonb)
to service_role;
