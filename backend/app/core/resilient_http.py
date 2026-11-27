"""A sturdier HTTP session for the shared Supabase (PostgREST) clients.

The client of supabase-py talks to PostgREST over HTTP/2 and keeps its connections open. The
server closes idle connections, so the next request on a stale one fails with
`httpx.RemoteProtocolError: Server disconnected` and the API answers 500. Two small measures:

* HTTP/1.1 and a short keep-alive, so a pooled connection is dropped before the server does it.
* A single retry of the reads (GET and HEAD) that fail on a stale connection. Writes are never
  retried: a repeated insert or update could be applied twice.
"""

import httpx

# Shorter than the idle time after which the server closes a connection.
KEEPALIVE_EXPIRY_SECONDS = 5.0
LIMITS = httpx.Limits(
    max_connections=100, max_keepalive_connections=20, keepalive_expiry=KEEPALIVE_EXPIRY_SECONDS
)
# What a stale pooled connection raises. The retry opens a new connection.
STALE_CONNECTION_ERRORS = (httpx.RemoteProtocolError, httpx.ReadError, httpx.ConnectError)
IDEMPOTENT_METHODS = frozenset({"GET", "HEAD"})


class RetryOnStaleConnection(httpx.BaseTransport):
    """Sends the requests through `inner` and retries a failed read once."""

    def __init__(self, inner: httpx.BaseTransport | None = None):
        self.inner = inner or httpx.HTTPTransport(http2=False, limits=LIMITS)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        try:
            return self.inner.handle_request(request)
        except STALE_CONNECTION_ERRORS:
            if request.method not in IDEMPOTENT_METHODS:
                raise
            return self.inner.handle_request(request)

    def close(self) -> None:
        self.inner.close()


def harden_postgrest(client, inner: httpx.BaseTransport | None = None) -> None:
    """Swaps the HTTP session of the PostgREST part of a supabase-py client.

    The base URL, the headers and the timeout are the ones the client already had. The auth
    and storage parts of the client are not touched. `inner` is only for the tests.
    """
    postgrest = client.postgrest
    old = postgrest.session
    postgrest.session = httpx.Client(
        base_url=old.base_url,
        headers=old.headers,
        timeout=old.timeout,
        follow_redirects=True,
        transport=RetryOnStaleConnection(inner),
    )
    old.close()
