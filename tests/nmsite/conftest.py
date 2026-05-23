import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest
from playwright.sync_api import Page

TEST_PORT = 17860
BASE_URL = f"http://localhost:{TEST_PORT}"
APP_PATH = str(pathlib.Path(__file__).parent.parent.parent / "src" / "nmsite" / "app.py")


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


@pytest.fixture(scope="session")
def gradio_server():
    env = {
        **os.environ,
        "GRADIO_SERVER_PORT": str(TEST_PORT),
        "NMSITE_CONFIG": "DEV",
        "GRADIO_ANALYTICS_ENABLED": "False",
    }
    proc = subprocess.Popen(
        [sys.executable, APP_PATH],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_server(BASE_URL)
        yield BASE_URL
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


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
