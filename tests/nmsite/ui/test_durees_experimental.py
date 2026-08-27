# tests/nmsite/ui/test_durees_experimental.py
"""E2E coverage for Durées in experimental mode (TimeInput fields only, no
dual-mount, no toggle) — runs against the default gradio_server (DEV, which
is time_input_mode="experimental")."""

import datetime as dt

import nawminator as nm
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


@pytest.fixture()
def durees_page(live_page) -> Page:
    return live_page("Durées", "#durees_target")


def _fill_number(page: Page, elem_id: str, value: int | float) -> None:
    page.locator(f"#{elem_id} input").fill(str(value))


def _expected_arrival(secs: float, start: str = "00:00:00") -> str:
    t = dt.datetime.strptime(start, "%H:%M:%S")
    return (t + dt.timedelta(seconds=secs)).strftime("%H:%M:%S")


def test_durees_tab_renders_timeinput_fields(durees_page: Page) -> None:
    page = durees_page
    expect(page.locator("#durees_duration .ti-widget")).to_be_visible()
    expect(page.locator("#durees_start_time .ti-widget")).to_be_visible()
    expect(page.locator("#durees_arrival_time .ti-widget")).to_be_visible()
    # No old-style textarea fields anywhere in this mode.
    expect(page.locator("#durees_duration").get_by_role("textbox")).to_have_count(0)


def test_arrivee_mode_computes_duration(durees_page: Page) -> None:
    page = durees_page
    secs = nm.formulas.duree_attaque(0, 0, 100, 0, 0)

    _fill_number(page, "durees_from_x", 0)
    _fill_number(page, "durees_from_y", 0)
    _fill_number(page, "durees_to_x", 100)
    _fill_number(page, "durees_to_y", 0)

    expect(page.locator("#durees_arrival_time .ti-display-value")).to_have_text(
        _expected_arrival(secs), timeout=10_000
    )


def test_editing_start_time_twice_does_not_close_the_editor(durees_page: Page) -> None:
    """Regression for the DureesHybrid loopback bug (see git history:
    'Fix three TimeInput component bugs' / 'Wire TimeInput as an opt-in
    toggle'), re-verified here since DureesExperimental reimplements the
    same skip= echo guard independently (no shared mirror step to reuse)."""
    page = durees_page
    page.locator("#durees_start_time .ti-display").click()
    page.locator("#durees_start_time .ti-field").wait_for(state="visible")
    hours_seg = page.locator("#durees_start_time .ti-seg[data-key='hours']")
    hours_seg.click()

    page.keyboard.press("ArrowUp")
    expect(hours_seg).to_have_text("01", timeout=5_000)
    page.wait_for_timeout(1_000)
    expect(page.locator("#durees_start_time .ti-field")).to_be_visible()

    page.keyboard.press("ArrowUp")
    expect(hours_seg).to_have_text("02", timeout=5_000)
