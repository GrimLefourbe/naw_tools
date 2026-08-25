"""UI tests for the TimeInput component (Settings tab demo instances)."""

import datetime as dt
import re

import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


@pytest.fixture()
def settings_page(live_page) -> Page:
    return live_page("Réglages", "#ti_demo_a .ti-widget")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seg(page: Page, elem_id: str, key: str):
    """Locate a segment span inside a TimeInput by elem_id and data-key."""
    return page.locator(f"#{elem_id} .ti-seg[data-key='{key}']")


def _output(page: Page, elem_id: str):
    """Locate the Python-repr output textbox paired with a demo instance."""
    return page.locator(f"#{elem_id}_out").get_by_role("textbox")


def _enter_edit_mode(page: Page, elem_id: str) -> None:
    """Click the display badge to reveal the editable segments (segments are
    hidden behind it until then — see .ti-widget's data-editing toggle)."""
    page.locator(f"#{elem_id} .ti-display").click()
    page.locator(f"#{elem_id} .ti-field").wait_for(state="visible")


def _seg_text(page: Page, elem_id: str, key: str) -> str:
    return _seg(page, elem_id, key).inner_text()


# ── Tests: Rendering ─────────────────────────────────────────────────────────

def test_demo_a_display_badge_visible_by_default(settings_page: Page) -> None:
    page = settings_page
    expect(page.locator("#ti_demo_a .ti-display")).to_be_visible()
    expect(page.locator("#ti_demo_a .ti-field")).to_be_hidden()


def test_demo_a_click_reveals_hms_segments(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_a")
    expect(_seg(page, "ti_demo_a", "hours")).to_be_visible()
    expect(_seg(page, "ti_demo_a", "minutes")).to_be_visible()
    expect(_seg(page, "ti_demo_a", "seconds")).to_be_visible()
    expect(page.locator("#ti_demo_a .ti-display")).to_be_hidden()


def test_demo_b_format_toggle_visible_without_editing(settings_page: Page) -> None:
    page = settings_page
    # The toolbar (including the format toggle) overlays the display badge
    # and stays reachable regardless of edit state.
    expect(page.locator("#ti_demo_b .ti-toggle")).to_be_visible()


def test_demo_b_days_segment_visible_after_entering_edit_mode(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_b")
    # Days segment is visible (AJHMS format by default)
    expect(_seg(page, "ti_demo_b", "days")).to_be_visible()


def test_demo_c_renders_quick_fill_button(settings_page: Page) -> None:
    page = settings_page
    expect(page.locator("#ti_demo_c .ti-pill[data-fill='now']")).to_be_visible()


def test_demo_d_renders_current_time_pill(settings_page: Page) -> None:
    page = settings_page
    expect(page.locator("#ti_demo_d .ti-pill[data-fill='current_time']")).to_be_visible()


def test_copy_button_present_on_all_demos(settings_page: Page) -> None:
    page = settings_page
    for demo_id in ["ti_demo_a", "ti_demo_b", "ti_demo_c", "ti_demo_d", "ti_demo_e"]:
        expect(page.locator(f"#{demo_id} .ti-copy")).to_be_visible()


# ── Tests: Keyboard editing ───────────────────────────────────────────────────

def test_demo_a_arrow_up_increments_hours(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_a")
    hours_seg = _seg(page, "ti_demo_a", "hours")
    hours_seg.click()
    initial = int(hours_seg.inner_text())
    page.keyboard.press("ArrowUp")
    expect(hours_seg).to_have_text(str(initial + 1).zfill(2))


def test_demo_a_arrow_down_decrements_minutes(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_a")
    # First set minutes to a known value via ArrowUp
    mins_seg = _seg(page, "ti_demo_a", "minutes")
    mins_seg.click()
    for _ in range(5):
        page.keyboard.press("ArrowUp")
    val_after_up = int(mins_seg.inner_text())
    assert val_after_up == 5

    page.keyboard.press("ArrowDown")
    expect(mins_seg).to_have_text("04")


def test_demo_a_digit_entry_two_digits(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_a")
    secs_seg = _seg(page, "ti_demo_a", "seconds")
    secs_seg.click()
    page.keyboard.press("3")
    page.keyboard.press("0")
    # After two digits, auto-commits and advances; wait for render
    expect(secs_seg).to_have_text("30", timeout=3_000)


def test_demo_a_normalization_on_large_seconds(settings_page: Page) -> None:
    """Typing a value >= 60 into seconds carries the overflow into minutes,
    immediately on the segment's 2-digit auto-commit (not deferred to Tab)."""
    page = settings_page
    _enter_edit_mode(page, "ti_demo_a")
    mins_seg = _seg(page, "ti_demo_a", "minutes")
    secs_seg = _seg(page, "ti_demo_a", "seconds")

    # Fresh page load -> every segment starts at 0.
    expect(mins_seg).to_have_text("00")
    expect(secs_seg).to_have_text("00")

    # Typing a 2-digit value >= 60 into seconds auto-commits immediately
    # (no Tab needed) and normalize() carries the overflow into minutes:
    # 90 seconds -> 1 minute, 30 seconds.
    secs_seg.click()
    page.keyboard.press("9")
    page.keyboard.press("0")

    expect(mins_seg).to_have_text("01")
    expect(secs_seg).to_have_text("30")


# ── Tests: Format toggle (Demo B) ────────────────────────────────────────────

def test_demo_b_format_toggle_switches_display(settings_page: Page) -> None:
    page = settings_page
    toggle = page.locator("#ti_demo_b .ti-toggle")
    initial_label = toggle.inner_text()

    toggle.click()
    page.wait_for_timeout(300)

    new_label = toggle.inner_text()
    assert new_label != initial_label, "Toggle should cycle the format label"


def test_demo_b_toggle_back_to_ajhms(settings_page: Page) -> None:
    page = settings_page
    toggle = page.locator("#ti_demo_b .ti-toggle")
    first_label = toggle.inner_text()
    toggle.click()
    page.wait_for_timeout(200)
    toggle.click()
    page.wait_for_timeout(200)
    # After two clicks should be back to original
    assert toggle.inner_text() == first_label


# ── Tests: Quick-fill (Demo D — clock_time) ──────────────────────────────────

def test_demo_d_current_time_fill_updates_segments(settings_page: Page) -> None:
    page = settings_page

    pill = page.locator("#ti_demo_d .ti-pill[data-fill='current_time']")
    pill.click()
    page.wait_for_timeout(500)

    hours_text = int(_seg(page, "ti_demo_d", "hours").inner_text())
    now = dt.datetime.now()
    # Allow ±1 minute tolerance for test timing
    assert abs(hours_text - now.hour) <= 1, f"Hours {hours_text} too far from now {now.hour}"


# ── Tests: Python value output ────────────────────────────────────────────────

def test_demo_a_change_emits_timedelta(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_a")
    hours_seg = _seg(page, "ti_demo_a", "hours")
    hours_seg.click()
    page.keyboard.press("ArrowUp")
    page.keyboard.press("Tab")

    # A <textarea>'s dynamically-set .value isn't part of its rendered text
    # content, so to_have_value (not to_contain_text) is the correct check.
    expect(_output(page, "ti_demo_a")).to_have_value(re.compile("timedelta"), timeout=5_000)


def test_demo_d_change_emits_time(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_d")
    hours_seg = _seg(page, "ti_demo_d", "hours")
    hours_seg.click()
    page.keyboard.press("ArrowUp")
    page.keyboard.press("Tab")

    expect(_output(page, "ti_demo_d")).to_have_value(re.compile("datetime.time"), timeout=5_000)


def test_demo_e_change_emits_datetime(settings_page: Page) -> None:
    page = settings_page
    # Click "Maintenant" to fill demo E — the toolbar is reachable without
    # entering edit mode, so no _enter_edit_mode() call needed here.
    page.locator("#ti_demo_e .ti-pill[data-fill='now']").click()
    page.wait_for_timeout(500)

    expect(_output(page, "ti_demo_e")).to_have_value(re.compile("datetime.datetime"), timeout=5_000)
