"""Startup-only optional update checker."""

from __future__ import annotations

import json
import re
import threading
from typing import Callable
from urllib.error import URLError
from urllib.request import Request, urlopen


DEFAULT_RELEASE_URL = "https://api.github.com/repos/spencermuller/psyker/releases/latest"
_VERSION_PART_PATTERN = re.compile(r"^\d+$")


def start_async_update_check(
    current_version: str,
    notify: Callable[[str], None],
    *,
    url: str = DEFAULT_RELEASE_URL,
    timeout_seconds: float = 1.5,
) -> threading.Thread:
    """Run a one-shot update check in a daemon thread and notify once if newer."""

    def _run() -> None:
        message = check_for_update_notice(
            current_version,
            url=url,
            timeout_seconds=timeout_seconds,
        )
        if message:
            notify(message)

    thread = threading.Thread(target=_run, name="psyker-update-check", daemon=True)
    thread.start()
    return thread


def check_for_update_notice(
    current_version: str,
    *,
    url: str = DEFAULT_RELEASE_URL,
    timeout_seconds: float = 1.5,
) -> str | None:
    """Return a single-line notice when a newer version is available."""
    latest_version = fetch_latest_version(url=url, timeout_seconds=timeout_seconds)
    if latest_version is None:
        return None
    if _is_newer_version(latest_version, current_version):
        return f"Update available: Psyker v{latest_version} (current v{current_version})"
    return None


def fetch_latest_version(*, url: str = DEFAULT_RELEASE_URL, timeout_seconds: float = 1.5) -> str | None:
    """Fetch latest release version from a JSON endpoint."""
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "psyker-update-check",
        },
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (OSError, TimeoutError, URLError, ValueError, json.JSONDecodeError):
        return None

    tag = str(payload.get("tag_name", "")).strip()
    if not tag:
        return None
    if tag.lower().startswith("v"):
        tag = tag[1:]
    return tag or None


def _is_newer_version(candidate: str, current: str) -> bool:
    candidate_parts = _parse_version_parts(candidate)
    current_parts = _parse_version_parts(current)
    if candidate_parts is None or current_parts is None:
        return False
    return candidate_parts > current_parts


def _parse_version_parts(value: str) -> tuple[int, ...] | None:
    text = value.strip()
    if text.lower().startswith("v"):
        text = text[1:]
    parts = text.split(".")
    parsed: list[int] = []
    for part in parts:
        if not _VERSION_PART_PATTERN.match(part):
            return None
        parsed.append(int(part))
    while parsed and parsed[-1] == 0:
        parsed.pop()
    return tuple(parsed)
