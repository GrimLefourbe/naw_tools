"""Minimal E2E smoke test for Synchro in experimental mode (runs against the
default gradio_server, DEV)."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


def test_synchro_tab_shows_timeinput_only(gradio_server: str, page: Page) -> None:
    page.goto(gradio_server)
    page.get_by_role("tab", name="Synchro").click()
    page.locator("#synchro_time_input").wait_for(state="visible")
    expect(page.locator("#synchro_time_input .ti-widget")).to_be_visible()
    # No plain gr.DateTime field in this mode.
    expect(page.locator("#synchro_time_input input[type='text']")).to_have_count(0)
