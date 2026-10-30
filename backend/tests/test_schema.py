"""Controles sobre supabase/schema.sql que no necesitan una base: que coincida con los enums del
backend y que ninguna tabla quede abierta."""

import re
from pathlib import Path

import pytest

from app.core.enums import EstadoEstudio, Rol

SCHEMA = (Path(__file__).resolve().parents[2] / "supabase" / "schema.sql").read_text(
    encoding="utf-8"
)


def _table(name: str) -> str:
    match = re.search(rf"create table if not exists public\.{name} \((.*?)\n\);", SCHEMA, re.S)
    assert match, f"No está la tabla {name}"
    return match.group(1)


def _allowed_values(table: str, column: str) -> set[str]:
    """Los valores que acepta el CHECK `column in (...)` de esa columna."""
    match = re.search(rf"{column}\s+text[^;,]*?check \({column} in \(([^)]*)\)\)", _table(table))
    assert match, f"{table}.{column} no tiene un CHECK de valores"
    return set(re.findall(r"'([^']+)'", match.group(1)))


def test_user_roles_match_the_enum():
    assert _allowed_values("users", "role") == {rol.value for rol in Rol}


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("studies", "state"),
        ("study_state_history", "from_state"),
        ("study_state_history", "to_state"),
    ],
)
def test_study_states_match_the_enum(table, column):
    assert _allowed_values(table, column) == {estado.value for estado in EstadoEstudio}


def test_pompe_urgent_is_a_mark_and_not_a_state():
    assert "pompe_urgent" in _table("studies")
    assert not any("pompe" in value.lower() for value in _allowed_values("studies", "state"))


def test_every_table_has_row_level_security_on():
    tables = re.findall(r"create table if not exists public\.(\w+)", SCHEMA)
    assert tables
    for table in tables:
        enabled = re.search(rf"alter table public\.{table}\s+enable row level security", SCHEMA)
        assert enabled, f"La tabla {table} no tiene RLS activada"


def test_the_public_keys_get_no_access_to_the_tables():
    assert re.search(
        r"revoke all on all tables\s+in schema public from anon, authenticated", SCHEMA
    )
