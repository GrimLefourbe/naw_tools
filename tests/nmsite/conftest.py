import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import Page

APP_PATH = str(pathlib.Path(__file__).parent.parent.parent / "src" / "nmsite" / "app.py")

# One fixed port + NMSITE_CONFIG preset per test mode. "legacy" isn't listed
# yet — nothing tests it via a live server yet (see TODO.md's TimeInput
# demo-harness item); add a DEV_LEGACY preset in config.py and an entry here
# if/when that changes.
_MODE_SERVERS = {
    "experimental": (17860, "DEV"),
    "hybrid": (17861, "DEV_HYBRID"),
}


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.2)
    raise TimeoutError(f"Gradio server did not start at {url} within {timeout}s")


def _start_server(port: int, preset: str) -> tuple[subprocess.Popen, str]:
    base_url = f"http://localhost:{port}"
    env = {
        **os.environ,
        "GRADIO_SERVER_PORT": str(port),
        "NMSITE_CONFIG": preset,
        "GRADIO_ANALYTICS_ENABLED": "False",
    }
    proc = subprocess.Popen(
        [sys.executable, APP_PATH],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_server(base_url)
    return proc, base_url


@pytest.fixture(scope="session")
def _server_pool():
    """Lazily-started, session-cached {mode: (proc, base_url)} — a mode's
    server only launches the first time a test actually requests it."""
    pool: dict[str, tuple[subprocess.Popen, str]] = {}
    yield pool
    for proc, _ in pool.values():
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


@pytest.fixture(scope="session")
def gradio_server(request, _server_pool):
    mode = getattr(request, "param", "experimental")
    if mode not in _MODE_SERVERS:
        raise ValueError(f"No test server configured for mode {mode!r} — add it to _MODE_SERVERS")
    if mode not in _server_pool:
        port, preset = _MODE_SERVERS[mode]
        _server_pool[mode] = _start_server(port, preset)
    return _server_pool[mode][1]


@pytest.fixture()
def live_page(gradio_server, page: Page):
    """Return a factory: call live_page(tab_name, ready_selector) to get a Page
    already navigated to the given tab. ready_selector, if given, is waited on
    before returning so the tab's content is fully rendered."""
    def _go(tab_name: str, ready_selector: str | None = None) -> Page:
        page.goto(gradio_server)
        page.get_by_role("tab", name=tab_name).click()
        if ready_selector:
            page.locator(ready_selector).wait_for(state="visible")
        return page
    return _go
