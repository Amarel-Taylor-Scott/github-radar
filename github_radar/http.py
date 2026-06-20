"""A tiny, dependency-free HTTP client tuned for GitHub.

Wraps ``urllib`` with the three things every github-radar source needs:

* a real User-Agent and optional ``Authorization`` header (GitHub rejects
  unauthenticated requests that omit a UA),
* rate-limit awareness — it reads ``X-RateLimit-Remaining`` / ``Retry-After``
  and backs off on ``403`` / ``429`` instead of hammering the API,
* typed exceptions so callers can ``except FetchError`` and *continue with the
  other sources* rather than crashing the whole run.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

LOGGER = logging.getLogger("github_radar.http")

DEFAULT_USER_AGENT = "github-radar/0.1 (+https://github.com/amareltaylor/github-radar)"


class FetchError(Exception):
    """Raised when a fetch ultimately fails after retries/back-off."""


class RateLimitError(FetchError):
    """Raised when GitHub signals rate-limiting and retries are exhausted."""


@dataclass
class Response:
    """A minimal HTTP response: status, decoded text body, and headers."""

    status: int
    body: str
    headers: dict[str, str]

    def json(self) -> Any:
        return json.loads(self.body)


class HttpClient:
    """Polite HTTP client with retry/back-off and rate-limit handling.

    Parameters
    ----------
    token:
        Optional GitHub token. When present it is sent as a Bearer token,
        raising the Search API limit from 10 to 30 requests/minute and the core
        limit from 60 to 5000 requests/hour. Never logged.
    max_retries:
        How many times to retry a transient failure (429/403-rate-limit/5xx)
        before giving up.
    timeout:
        Per-request socket timeout in seconds.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        *,
        user_agent: str = DEFAULT_USER_AGENT,
        max_retries: int = 3,
        timeout: float = 20.0,
        min_interval: float = 0.0,
        sleep=time.sleep,
    ) -> None:
        self.token = token
        self.user_agent = user_agent
        self.max_retries = max_retries
        self.timeout = timeout
        self.min_interval = min_interval
        self._sleep = sleep
        self._last_request = 0.0

    def _headers(self, accept: str, extra: Optional[dict[str, str]]) -> dict[str, str]:
        headers = {"User-Agent": self.user_agent, "Accept": accept}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            headers["X-GitHub-Api-Version"] = "2022-11-28"
        if extra:
            headers.update(extra)
        return headers

    def _throttle(self) -> None:
        """Enforce a minimum gap between requests to stay a good citizen."""
        if self.min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request
        if elapsed < self.min_interval:
            self._sleep(self.min_interval - elapsed)
        self._last_request = time.monotonic()

    def get(
        self,
        url: str,
        *,
        accept: str = "application/json",
        headers: Optional[dict[str, str]] = None,
    ) -> Response:
        """GET ``url`` with retry/back-off. Raises :class:`FetchError` on failure."""
        request = urllib.request.Request(
            url, headers=self._headers(accept, headers), method="GET"
        )
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as resp:
                    raw = resp.read()
                    charset = resp.headers.get_content_charset() or "utf-8"
                    return Response(
                        status=resp.status,
                        body=raw.decode(charset, errors="replace"),
                        headers={k.lower(): v for k, v in resp.headers.items()},
                    )
            except urllib.error.HTTPError as exc:  # noqa: PERF203
                last_exc = exc
                wait = self._backoff_for(exc, attempt)
                if wait is None:
                    raise self._classify(exc) from exc
                LOGGER.warning(
                    "GitHub returned %s for %s; backing off %.1fs (attempt %d/%d)",
                    exc.code, url, wait, attempt + 1, self.max_retries,
                )
                self._sleep(wait)
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                last_exc = exc
                if attempt >= self.max_retries:
                    raise FetchError(f"network error fetching {url}: {exc}") from exc
                wait = 2.0 * (2 ** attempt)
                LOGGER.warning(
                    "Network error for %s (%s); retrying in %.1fs", url, exc, wait
                )
                self._sleep(wait)
        raise FetchError(f"exhausted retries for {url}: {last_exc}")

    def _backoff_for(
        self, exc: urllib.error.HTTPError, attempt: int
    ) -> Optional[float]:
        """Return seconds to wait, or ``None`` if the error is not retryable."""
        if attempt >= self.max_retries:
            return None
        retry_after = exc.headers.get("Retry-After") if exc.headers else None
        remaining = exc.headers.get("X-RateLimit-Remaining") if exc.headers else None
        is_rate_limited = exc.code in (403, 429) and (
            retry_after is not None or remaining == "0"
        )
        if is_rate_limited:
            if retry_after is not None:
                try:
                    return min(float(retry_after), 120.0)
                except ValueError:
                    pass
            return min(2.0 * (2 ** attempt), 60.0)
        if exc.code in (500, 502, 503, 504):
            return 2.0 * (2 ** attempt)
        return None

    @staticmethod
    def _classify(exc: urllib.error.HTTPError) -> FetchError:
        if exc.code in (403, 429):
            return RateLimitError(f"rate-limited (HTTP {exc.code})")
        return FetchError(f"HTTP {exc.code}: {exc.reason}")
