"""UI tests for the global TimeInput opt-in toggle (Settings tab)."""

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


@pytest.fixture()
def settings_page(live_page) -> Page:
    return live_page("Réglages", "#settings_time_input_toggle")


def _toggle(page: Page):
    return page.locator("#settings_time_input_toggle input[type='checkbox']")


def test_time_input_toggle_off_by_default(settings_page: Page) -> None:
    page = settings_page
    expect(_toggle(page)).not_to_be_checked()


def test_time_input_toggle_persists_across_reload(gradio_server: str, page: Page) -> None:
    page.goto(gradio_server)
    page.get_by_role("tab", name="Réglages").click()
    page.locator("#settings_time_input_toggle").wait_for(state="visible")

    _toggle(page).check()
    expect(_toggle(page)).to_be_checked()

    page.reload()
    page.get_by_role("tab", name="Réglages").click()
    page.locator("#settings_time_input_toggle").wait_for(state="visible")
    expect(_toggle(page)).to_be_checked(timeout=5_000)
