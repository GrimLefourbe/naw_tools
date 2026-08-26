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


# ── Tests: Wrap-around carry, bounded modes (Demo D — clock_time) ───────────

def test_demo_d_scroll_up_past_max_wraps_and_carries(settings_page: Page) -> None:
    """Incrementing a bounded segment (clock_time/datetime, unlike duration)
    past its max must wrap to its min AND carry 1 into the next segment —
    scrolling seconds up from 59 goes to 00 and bumps minutes, not just wrap
    seconds in place."""
    page = settings_page
    _enter_edit_mode(page, "ti_demo_d")
    mins_seg = _seg(page, "ti_demo_d", "minutes")
    secs_seg = _seg(page, "ti_demo_d", "seconds")
    expect(mins_seg).to_have_text("00")
    expect(secs_seg).to_have_text("00")

    secs_seg.click()
    page.keyboard.press("5")
    page.keyboard.press("9")
    expect(secs_seg).to_have_text("59")

    secs_seg.click()
    page.keyboard.press("ArrowUp")

    expect(secs_seg).to_have_text("00")
    expect(mins_seg).to_have_text("01")


def test_demo_d_scroll_down_past_min_wraps_and_borrows(settings_page: Page) -> None:
    """Symmetric case: decrementing a bounded segment below its min wraps to
    its max and borrows 1 from the next segment."""
    page = settings_page
    _enter_edit_mode(page, "ti_demo_d")
    mins_seg = _seg(page, "ti_demo_d", "minutes")
    secs_seg = _seg(page, "ti_demo_d", "seconds")

    mins_seg.click()
    page.keyboard.press("0")
    page.keyboard.press("1")
    expect(mins_seg).to_have_text("01")
    expect(secs_seg).to_have_text("00")

    secs_seg.click()
    page.keyboard.press("ArrowDown")

    expect(secs_seg).to_have_text("59")
    expect(mins_seg).to_have_text("00")


def test_demo_e_datetime_day_carries_into_month(settings_page: Page) -> None:
    """Same wrap-and-carry contract, exercised on datetime's day→month pair
    (not just clock_time's seconds→minutes) — a fresh page load starts at
    day=01/month=01, so wrapping day down from there must borrow from
    month."""
    page = settings_page
    # Demo E's 3 quick-fill pills + copy + clear make for a wide .ti-btns
    # overlay that covers the default (centered) click point on .ti-display
    # — click its left edge instead, which the reserved right-padding always
    # keeps clear (see --ti-btns-reserve in style.css).
    page.locator("#ti_demo_e .ti-display").click(position={"x": 5, "y": 5})
    page.locator("#ti_demo_e .ti-field").wait_for(state="visible")
    day_seg = _seg(page, "ti_demo_e", "day")
    month_seg = _seg(page, "ti_demo_e", "month")
    expect(day_seg).to_have_text("01")
    expect(month_seg).to_have_text("01")

    day_seg.click()
    page.keyboard.press("ArrowDown")

    expect(day_seg).to_have_text("31")
    expect(month_seg).to_have_text("12")


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


# ── Tests: interactive toggle ────────────────────────────────────────────

def test_interactive_toggle_makes_segments_read_only(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_a")
    seg = _seg(page, "ti_demo_a", "hours")
    expect(seg).to_have_attribute("tabindex", "0")

    page.locator("#ti_demo_a_interactive").get_by_role("checkbox").uncheck()
    page.wait_for_timeout(200)

    expect(page.locator("#ti_demo_a .ti-widget")).to_have_attribute("data-interactive", "false")
    expect(seg).to_have_attribute("tabindex", "-1")


def test_interactive_toggle_preserves_value(settings_page: Page) -> None:
    page = settings_page
    _enter_edit_mode(page, "ti_demo_a")
    _seg(page, "ti_demo_a", "hours").click()
    page.keyboard.press("ArrowUp")
    # Wait for the change event to fire and update the output
    expect(_output(page, "ti_demo_a")).to_have_value(re.compile("."), timeout=5_000)
    before = _output(page, "ti_demo_a").input_value()

    page.locator("#ti_demo_a_interactive").get_by_role("checkbox").uncheck()
    page.wait_for_timeout(200)
    page.locator("#ti_demo_a_interactive").get_by_role("checkbox").check()
    page.wait_for_timeout(200)

    assert _output(page, "ti_demo_a").input_value() == before


def test_interactive_toggle_hides_clear_button(settings_page: Page) -> None:
    """Demo A only has copy + clear (single format, no quick-fills) — clear
    must disappear once the field goes read-only; it can't do anything useful
    there."""
    page = settings_page
    expect(page.locator("#ti_demo_a .ti-clear")).to_be_visible()

    page.locator("#ti_demo_a_interactive").get_by_role("checkbox").uncheck()
    page.wait_for_timeout(200)

    expect(page.locator("#ti_demo_a .ti-clear")).to_be_hidden()


def test_interactive_toggle_keeps_copy_button_visible_and_working(settings_page: Page) -> None:
    page = settings_page
    page.locator("#ti_demo_a_interactive").get_by_role("checkbox").uncheck()
    page.wait_for_timeout(200)

    copy_btn = page.locator("#ti_demo_a .ti-copy")
    expect(copy_btn).to_be_visible()
    copy_btn.click()
    expect(copy_btn).to_have_text("✓", timeout=2_000)


def test_interactive_toggle_hides_toggle_button(settings_page: Page) -> None:
    """Demo B's own interactive state can't be flipped from the demo UI, so
    exercise the format-toggle button through the real Durées tab instead,
    where durees_duration_new (2 formats: HH:MM:SS/AJHMS) starts read-only in
    the default (Arrivée) mode."""
    page = settings_page
    page.get_by_role("tab", name="Durées").click()
    toggle = page.locator("#settings_time_input_toggle input[type='checkbox']")
    page.get_by_role("tab", name="Réglages").click()
    toggle.wait_for(state="visible")
    page.wait_for_timeout(500)
    if not toggle.is_checked():
        toggle.check()
    page.get_by_role("tab", name="Durées").click()
    expect(page.locator("#durees_start_time_new")).to_be_visible(timeout=5_000)

    # Default mode (Arrivée): duration is read-only.
    duration_widget = page.locator("#durees_duration_new .ti-widget")
    expect(duration_widget).to_have_attribute("data-interactive", "false")
    expect(page.locator("#durees_duration_new .ti-toggle")).to_be_hidden()
    expect(page.locator("#durees_duration_new .ti-copy")).to_be_visible()
