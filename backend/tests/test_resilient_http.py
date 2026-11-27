"""A stale connection to PostgREST must not turn into a 500 (httpx `Server disconnected`).

The real supabase-py client is used with a fake transport underneath: the failure happens in the
HTTP layer, below where `FakeSupabase` replaces the client.
"""

import httpx
import pytest
from supabase import create_client

from app import database
from app.core import supabase_tables
from app.core.resilient_http import (
    KEEPALIVE_EXPIRY_SECONDS,
    RetryOnStaleConnection,
    harden_postgrest,
)

ROWS = [{"id": 4, "state": "Creado"}]


class FlakyTransport(httpx.BaseTransport):
    """Fails with the given errors, one per call, and then answers with the rows."""

    def __init__(self, *errors: Exception):
        self.errors = list(errors)
        self.methods: list[str] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.methods.append(request.method)
        if self.errors:
            raise self.errors.pop(0)
        return httpx.Response(200, json=ROWS, request=request)


def client_over(transport: httpx.BaseTransport):
    client = create_client("http://localhost:54321", "test-service-role-key")
    harden_postgrest(client, inner=transport)
    return client


def disconnected() -> httpx.RemoteProtocolError:
    return httpx.RemoteProtocolError("Server disconnected")


def test_a_read_on_a_stale_connection_is_retried_once_and_succeeds():
    transport = FlakyTransport(disconnected())
    client = client_over(transport)

    rows = client.table("studies").select("id, state").execute().data

    assert rows == ROWS
    assert transport.methods == ["GET", "GET"]


@pytest.mark.parametrize(
    "error", [httpx.ReadError("closed"), httpx.ConnectError("refused")], ids=["read", "connect"]
)
def test_the_other_stale_connection_errors_are_retried_too(error):
    transport = FlakyTransport(error)
    client = client_over(transport)

    assert client.table("studies").select("id").execute().data == ROWS
    assert transport.methods == ["GET", "GET"]


def test_the_repository_helpers_survive_a_stale_connection(monkeypatch):
    transport = FlakyTransport(disconnected())
    monkeypatch.setattr(supabase_tables, "supabase_admin", client_over(transport))

    assert supabase_tables.select_in("studies", "id, state", "id", [4]) == ROWS
    assert transport.methods == ["GET", "GET"]


def test_a_read_is_retried_only_once():
    transport = FlakyTransport(disconnected(), disconnected())
    client = client_over(transport)

    with pytest.raises(httpx.RemoteProtocolError):
        client.table("studies").select("id").execute()
    assert transport.methods == ["GET", "GET"]


@pytest.mark.parametrize(
    "write",
    [
        lambda t: t.insert({"state": "Creado"}),
        lambda t: t.update({"state": "Pagado"}).eq("id", 4),
        lambda t: t.delete().eq("id", 4),
    ],
    ids=["insert", "update", "delete"],
)
def test_a_write_is_never_retried(write):
    transport = FlakyTransport(disconnected())
    client = client_over(transport)

    with pytest.raises(httpx.RemoteProtocolError):
        write(client.table("studies")).execute()
    assert len(transport.methods) == 1


def test_an_error_that_is_not_a_stale_connection_is_not_retried():
    transport = FlakyTransport(httpx.ReadTimeout("slow"))
    client = client_over(transport)

    with pytest.raises(httpx.ReadTimeout):
        client.table("studies").select("id").execute()
    assert len(transport.methods) == 1


def test_the_shared_clients_use_the_resilient_session_with_a_short_keepalive():
    for shared in (database.supabase, database.supabase_admin):
        session = shared.postgrest.session
        assert isinstance(session._transport, RetryOnStaleConnection)
        pool = session._transport.inner._pool
        assert pool._http2 is False
        assert pool._keepalive_expiry == KEEPALIVE_EXPIRY_SECONDS
