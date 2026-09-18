"""Shared helpers for deciding how clients reach the game server."""

from typing import Optional

LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")


def is_local_host(host: str) -> bool:
    return host.strip().lower() in LOCAL_HOSTS


def resolve_ssl(host: str, use_ssl: Optional[bool]) -> bool:
    """Decide whether to use TLS.

    None (default) means auto: plain ws/http for localhost, wss/https for
    everything else. Pass True/False to override.
    """
    if use_ssl is None:
        return not is_local_host(host)
    return bool(use_ssl)


def ws_scheme(use_ssl: bool) -> str:
    return "wss" if use_ssl else "ws"


def http_scheme(use_ssl: bool) -> str:
    return "https" if use_ssl else "http"
