"""One polite HTTP client for every source.

Each host gets its own minimum gap between requests, so a hundred boards on one career system are read one
after another, about a second apart, never in a burst. A 429 or 503 is waited out, using the server's own
Retry-After when it sends one. Nothing here follows a link out of a response: adapters build every URL.
"""

from __future__ import annotations

import threading
import time
from typing import Any
from urllib.parse import urlsplit

import httpx

USER_AGENT = "intern-radar/0.1 (index of student roles at UAE employers; reads public career feeds once an hour)"


class SourceError(Exception):
    """A source could not be read. The message is safe to show on the site."""


class Client:
    def __init__(
        self,
        *,
        gap: float = 1.0,
        timeout: float = 25.0,
        retries: int = 2,
        transport: httpx.BaseTransport | None = None,
        sleep=time.sleep,
        clock=time.monotonic,
    ) -> None:
        self._http = httpx.Client(
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        )
        self._gap = gap
        # Hosts that punish bursts get a longer gap. Workable answered a quick series of calls with a day-long block.
        self._gaps = {"apply.workable.com": max(gap, 3.0)} if gap > 0 else {}
        self._retries = retries
        self._sleep = sleep
        self._clock = clock
        self._locks: dict[str, threading.Lock] = {}
        self._last: dict[str, float] = {}
        self._guard = threading.Lock()
        self.requests = 0

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _host_lock(self, host: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(host, threading.Lock())

    def _wait_turn(self, host: str) -> None:
        last = self._last.get(host)
        if last is not None:
            wait = self._gaps.get(host, self._gap) - (self._clock() - last)
            if wait > 0:
                self._sleep(wait)

    def request(self, method: str, url: str, *, json: Any = None, params: dict | None = None) -> Any:
        """Return the decoded JSON body, or raise SourceError."""
        host = urlsplit(url).netloc
        attempt = 0
        while True:
            with self._host_lock(host):
                self._wait_turn(host)
                try:
                    with self._guard:
                        self.requests += 1
                    resp = self._http.request(method, url, json=json, params=params)
                except httpx.HTTPError as exc:
                    resp = None
                    failure = f"{type(exc).__name__}"
                finally:
                    self._last[host] = self._clock()
            if resp is not None:
                if resp.status_code == 404:
                    raise SourceError("not found (404)")
                if resp.status_code in (429, 500, 502, 503, 504):
                    failure = f"HTTP {resp.status_code}"
                    retry_after = resp.headers.get("retry-after", "")
                    pause = min(float(retry_after), 30.0) if retry_after.isdigit() else 2.0 * (attempt + 1)
                elif resp.status_code >= 400:
                    raise SourceError(f"HTTP {resp.status_code}")
                else:
                    try:
                        return resp.json()
                    except ValueError as exc:
                        raise SourceError("the response was not JSON") from exc
            else:
                pause = 2.0 * (attempt + 1)
            attempt += 1
            if attempt > self._retries:
                raise SourceError(failure)
            self._sleep(pause)

    def get(self, url: str, *, params: dict | None = None) -> Any:
        return self.request("GET", url, params=params)

    def post(self, url: str, *, json: Any) -> Any:
        return self.request("POST", url, json=json)
