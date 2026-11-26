"""Small helpers for the repositories that read and write Supabase with the service role."""

from collections.abc import Iterable
from typing import Any

from app.database import supabase_admin


def table(name: str):
    """The table of the admin client (the backend always writes with the service role)."""
    return supabase_admin.table(name)


def select_in(
    name: str, columns: str, column: str, values: Iterable[Any], order: str | None = "id"
) -> list[dict]:
    """Rows whose `column` is one of `values`, in a single query. Always list the columns."""
    unique = sorted({v for v in values if v is not None}, key=str)
    if not unique:
        return []
    query = table(name).select(columns).in_(column, unique)
    if order:
        query = query.order(order)
    return query.execute().data
