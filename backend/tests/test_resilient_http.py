"""A stale connection to PostgREST must not turn into a 500 (httpx `Server disconnected`).

The retry of our transport is tested on its own, counting its attempts. Through the whole
postgrest client the tests only check that a failed read is survived: the client of postgrest
2.34 and later retries by itself, so the total number of attempts depends on its version.
"""

import httpx
import pytest
from supabase import create_client

from app import database
from app.core import resilient_http, supabase_tables
from app.core.resilient_http import (
    KEEPALIVE_EXPIRY_SECONDS,
    RetryOnStaleConnection,
    harden_postgrest,
)

ROWS = [{"id": 4, "state": "Creado"}]
URL = "http://localhost:54321/rest/v1/studies"


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


def disconnected() -> httpx.RemoteProtocolError:
    return httpx.RemoteProtocolError("Server disconnected")


def send(transport: RetryOnStaleConnection, method: str = "GET") -> httpx.Response:
    return transport.handle_request(httpx.Request(method, URL))


# --- our transport, on its own: it counts its own attempts -------------------------------------


def test_a_read_that_fails_on_a_stale_connection_is_retried_once():
    inner = FlakyTransport(disconnected())

    assert send(RetryOnStaleConnection(inner, retries=1)).status_code == 200
    assert inner.methods == ["GET", "GET"]


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_reads_are_retried_exactly_the_configured_number_of_times(method):
    inner = FlakyTransport(*[disconnected() for _ in range(5)])

    with pytest.raises(httpx.RemoteProtocolError):
        send(RetryOnStaleConnection(inner, retries=1), method)
    assert inner.methods == [method, method]


def test_without_retries_a_read_is_tried_once():
    inner = FlakyTransport(disconnected())

    with pytest.raises(httpx.RemoteProtocolError):
        send(RetryOnStaleConnection(inner, retries=0))
    assert inner.methods == ["GET"]


@pytest.mark.parametrize(
    "error", [httpx.ReadError("closed"), httpx.ConnectError("refused")], ids=["read", "connect"]
)
def test_the_other_stale_connection_errors_are_retried_too(error):
    inner = FlakyTransport(error)

    assert send(RetryOnStaleConnection(inner, retries=1)).status_code == 200
    assert inner.methods == ["GET", "GET"]


@pytest.mark.parametrize("method", ["POST", "PATCH", "DELETE", "PUT"])
def test_a_write_is_never_retried(method):
    inner = FlakyTransport(disconnected())

    with pytest.raises(httpx.RemoteProtocolError):
        send(RetryOnStaleConnection(inner, retries=3), method)
    assert inner.methods == [method]


def test_an_error_that_is_not_a_stale_connection_is_not_retried():
    inner = FlakyTransport(httpx.ReadTimeout("slow"))

    with pytest.raises(httpx.ReadTimeout):
        send(RetryOnStaleConnection(inner, retries=3))
    assert inner.methods == ["GET"]


@pytest.mark.parametrize(
    ("version", "retries"),
    [("2.10.0", 1), ("2.33.0", 1), ("2.34.0", 0), ("2.34.1", 0), ("2.40.2", 0), ("3.0.0", 0)],
)
def test_it_retries_once_unless_postgrest_already_retries(monkeypatch, version, retries):
    monkeypatch.setattr(resilient_http.metadata, "version", lambda name: version)

    assert RetryOnStaleConnection(FlakyTransport()).retries == retries


def test_without_postgrest_information_it_retries_once(monkeypatch):
    def missing(name):
        raise resilient_http.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(resilient_http.metadata, "version", missing)

    assert RetryOnStaleConnection(FlakyTransport()).retries == 1


# --- through the whole postgrest client: only "a failed read is survived" -----------------------


@pytest.fixture
def no_waiting(monkeypatch):
    """The postgrest client waits before it retries: the tests do not need to."""
    monkeypatch.setattr("postgrest._sync.request_builder.time.sleep", lambda seconds: None)


def client_over(transport: httpx.BaseTransport):
    client = create_client("http://localhost:54321", "test-service-role-key")
    harden_postgrest(client, inner=transport)
    return client


def test_a_single_disconnect_is_survived_by_a_read(no_waiting):
    client = client_over(FlakyTransport(disconnected()))

    assert client.table("studies").select("id, state").execute().data == ROWS


def test_the_repository_helpers_survive_a_single_disconnect(no_waiting, monkeypatch):
    monkeypatch.setattr(
        supabase_tables, "supabase_admin", client_over(FlakyTransport(disconnected()))
    )

    assert supabase_tables.select_in("studies", "id, state", "id", [4]) == ROWS


def test_a_write_that_loses_its_connection_is_not_hidden(no_waiting):
    client = client_over(FlakyTransport(disconnected()))

    with pytest.raises(httpx.RemoteProtocolError):
        client.table("studies").insert({"state": "Creado"}).execute()


def test_the_shared_clients_use_the_resilient_session_with_a_short_keepalive():
    for shared in (database.supabase, database.supabase_admin):
        session = shared.postgrest.session
        assert isinstance(session._transport, RetryOnStaleConnection)
        pool = session._transport.inner._pool
        assert pool._http2 is False
        assert pool._keepalive_expiry == KEEPALIVE_EXPIRY_SECONDS
