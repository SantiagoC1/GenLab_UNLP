"""A sturdier HTTP session for the shared Supabase (PostgREST) clients.

The client of supabase-py talks to PostgREST over HTTP/2 and keeps its connections open. The
server closes idle connections, so the next request on a stale one fails with
`httpx.RemoteProtocolError: Server disconnected` and the API answers 500. Two measures:

* HTTP/1.1 and a short keep-alive, so a pooled connection is dropped before the server does it.
* One retry of the reads (GET and HEAD) that fail on a stale connection. Writes are never
  retried: a repeated insert or update could be applied twice.

From postgrest 2.34 the client retries those reads by itself (up to three times, with a wait).
Then our retry is switched off: a read must never be retried by two layers at once.
"""

import re
from importlib import metadata

import httpx

# Shorter than the idle time after which the server closes a connection.
KEEPALIVE_EXPIRY_SECONDS = 5.0
LIMITS = httpx.Limits(
    max_connections=100, max_keepalive_connections=20, keepalive_expiry=KEEPALIVE_EXPIRY_SECONDS
)
# What a stale pooled connection raises. The retry opens a new connection.
STALE_CONNECTION_ERRORS = (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError)
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD"})
# The first postgrest release that retries the reads that fail at the network level.
POSTGREST_RETRIES_FROM = (2, 34)


def postgrest_retries_network_errors() -> bool:
    """True if the installed postgrest client retries a read that lost its connection."""
    try:
        version = metadata.version("postgrest")
    except metadata.PackageNotFoundError:
        return False
    major_minor = tuple(int(part) for part in re.findall(r"\d+", version)[:2])
    return major_minor >= POSTGREST_RETRIES_FROM


class RetryOnStaleConnection(httpx.BaseTransport):
    """Sends the requests through `inner` and retries a failed read `retries` times.

    By default it retries once, or never if the postgrest client already does it.
    """

    def __init__(self, inner: httpx.BaseTransport | None = None, retries: int | None = None):
        self.inner = inner or httpx.HTTPTransport(http2=False, limits=LIMITS)
        self.retries = (
            (0 if postgrest_retries_network_errors() else 1) if retries is None else retries
        )

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        retries_left = self.retries if request.method in IDEMPOTENT_METHODS else 0
        while True:
            try:
                return self.inner.handle_request(request)
            except STALE_CONNECTION_ERRORS:
                if retries_left <= 0:
                    raise
                retries_left -= 1

    def close(self) -> None:
        self.inner.close()


def harden_postgrest(
    client, inner: httpx.BaseTransport | None = None, retries: int | None = None
) -> None:
    """Swaps the HTTP session of the PostgREST part of a supabase-py client.

    The base URL, the headers and the timeout are the ones the client already had. The auth
    and storage parts of the client are not touched. `inner` and `retries` are for the tests.
    """
    postgrest = client.postgrest
    old = postgrest.session
    postgrest.session = httpx.Client(
        base_url=old.base_url,
        headers=old.headers,
        timeout=old.timeout,
        follow_redirects=True,
        transport=RetryOnStaleConnection(inner, retries),
    )
    old.close()
