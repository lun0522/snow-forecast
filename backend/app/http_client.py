"""Shared HTTP JSON client with retries, timeouts, and SSL cert handling."""

from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_USER_AGENT = "snow-forecast-local/0.1 (personal ski weather dashboard)"


def _build_ssl_context() -> ssl.SSLContext:
    """Prefer certifi CA bundle when available for macOS Python reliability."""
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


_SSL_CONTEXT = _build_ssl_context()


class HttpFetchError(RuntimeError):
    """Raised when an upstream HTTP API request fails after retries."""


def get_text(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 25.0,
    retries: int = 3,
    backoff_seconds: float = 1.0,
    accept: str = "*/*",
) -> str:
    """Fetch UTF-8 text from an HTTP(S) endpoint with retry on transient errors."""
    full_url = url
    if params:
        encoded = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if "?" in url else "?"
        full_url = f"{url}{sep}{encoded}"

    req_headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": accept,
    }
    if headers:
        req_headers.update(headers)

    last_error: Exception | None = None
    for attempt in range(retries):
        request = urllib.request.Request(full_url, headers=req_headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout, context=_SSL_CONTEXT) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in (429, 500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(backoff_seconds * (2**attempt))
                continue
            body_preview = ""
            try:
                body_preview = exc.read().decode("utf-8", errors="replace")[:300]
            except Exception:
                pass
            raise HttpFetchError(f"HTTP {exc.code} fetching {full_url}: {body_preview}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(backoff_seconds * (2**attempt))
                continue
            raise HttpFetchError(f"Error fetching {full_url}: {exc}") from exc

    raise HttpFetchError(f"Failed fetching {full_url}: {last_error}")


def get_json(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 25.0,
    retries: int = 3,
    backoff_seconds: float = 1.0,
) -> Any:
    """Fetch JSON from an HTTP(S) endpoint with retry on transient errors."""
    raw = get_text(
        url=url,
        params=params,
        headers=headers,
        timeout=timeout,
        retries=retries,
        backoff_seconds=backoff_seconds,
        accept="application/json, application/geo+json",
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HttpFetchError(f"Invalid JSON from {url}: {exc}") from exc
