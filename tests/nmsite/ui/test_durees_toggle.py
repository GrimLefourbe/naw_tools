"""UI tests for the opt-in TimeInput toggle applied to the Durées tab's
duration / start-time / arrival-time fields."""

import datetime as dt

import nawminator as nm
import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


@pytest.fixture()
def durees_page(live_page) -> Page:
    return live_page("Durées", "#durees_target")


def _enable_time_input_toggle(page: Page) -> None:
    page.get_by_role("tab", name="Réglages").click()
    toggle = page.locator("#settings_time_input_toggle input[type='checkbox']")
    toggle.wait_for(state="visible")
    # Let the page's own demo.load() restore chain (which also cascades to
    # every tab's visibility-toggle listener) drain before toggling — it can
    # otherwise complete after this check() and silently revert it.
    page.wait_for_timeout(500)
    if not toggle.is_checked():
        toggle.check()
        expect(toggle).to_be_checked()
    page.get_by_role("tab", name="Durées").click()
    page.locator("#durees_target").wait_for(state="visible")
    expect(page.locator("#durees_start_time_new")).to_be_visible(timeout=5_000)
    expect(page.locator("#durees_duration")).to_be_hidden(timeout=5_000)


def _fill_number(page: Page, elem_id: str, value: int | float) -> None:
    page.locator(f"#{elem_id} input").fill(str(value))


def _expected_arrival(secs: float, start: str = "00:00:00") -> str:
    t = dt.datetime.strptime(start, "%H:%M:%S")
    return (t + dt.timedelta(seconds=secs)).strftime("%H:%M:%S")


def _arrival_time_new_display(page: Page):
    # Gradio doesn't just CSS-hide a field's inner content when visible=False
    # — it isn't rendered into the DOM at all, so the old (hidden) field's
    # value can't be read here. Check the new field's own display badge
    # instead — it's the one actually visible with the toggle on.
    return page.locator("#durees_arrival_time_new .ti-display-value")


def test_toggle_off_shows_old_fields(durees_page: Page) -> None:
    page = durees_page
    expect(page.locator("#durees_duration")).to_be_visible()
    expect(page.locator("#durees_start_time")).to_be_visible()
    expect(page.locator("#durees_arrival_time")).to_be_visible()
    expect(page.locator("#durees_duration_new")).to_be_hidden()
    expect(page.locator("#durees_start_time_new")).to_be_hidden()
    expect(page.locator("#durees_arrival_time_new")).to_be_hidden()


def test_toggle_on_shows_new_fields(gradio_server: str, page: Page) -> None:
    page.goto(gradio_server)
    _enable_time_input_toggle(page)
    expect(page.locator("#durees_duration_new")).to_be_visible()
    expect(page.locator("#durees_start_time_new")).to_be_visible()
    expect(page.locator("#durees_arrival_time_new")).to_be_visible()
    expect(page.locator("#durees_duration")).to_be_hidden()
    expect(page.locator("#durees_start_time")).to_be_hidden()
    expect(page.locator("#durees_arrival_time")).to_be_hidden()


def _interactive(page: Page, elem_id: str) -> bool:
    widget = page.locator(f"#{elem_id} .ti-widget")
    return widget.get_attribute("data-interactive") == "true"


def test_toggle_on_mode_switch_updates_new_fields_interactivity(gradio_server: str, page: Page) -> None:
    """Switching VA/Arrivée/Départ must update which *_new (TimeInput) field
    is editable, exactly like it already does for the old fields — regression
    for a bug where on_choice(..., js=True, ...) instantly updates the old
    fields' interactive state but silently no-ops on TimeInput (a custom
    gr.HTML component), leaving the new fields stuck at their mount-time
    interactivity."""
    page.goto(gradio_server)
    _enable_time_input_toggle(page)

    # Default mode (Arrivée): duration/arrival read-only, start editable.
    assert _interactive(page, "durees_duration_new") is False
    assert _interactive(page, "durees_start_time_new") is True
    assert _interactive(page, "durees_arrival_time_new") is False

    page.locator("#durees_target").get_by_role("button", name="VA").click()
    page.wait_for_timeout(500)
    assert _interactive(page, "durees_duration_new") is True
    assert _interactive(page, "durees_start_time_new") is True
    assert _interactive(page, "durees_arrival_time_new") is True

    page.locator("#durees_target").get_by_role("button", name="Départ").click()
    page.wait_for_timeout(500)
    assert _interactive(page, "durees_duration_new") is False
    assert _interactive(page, "durees_start_time_new") is False
    assert _interactive(page, "durees_arrival_time_new") is True


def test_toggle_on_editing_new_start_time_drives_computation(gradio_server: str, page: Page) -> None:
    """Editing the new TimeInput start-time field (the only field editable by
    default, Arrivée mode) must sync into the old field and re-run _compute,
    same as editing the old field directly would."""
    page.goto(gradio_server)
    _enable_time_input_toggle(page)
    secs = nm.formulas.duree_attaque(0, 0, 100, 0, 0)

    _fill_number(page, "durees_to_x", 100)
    expect(_arrival_time_new_display(page)).to_have_text(_expected_arrival(secs), timeout=10_000)

    # Enter edit mode on the new start-time field and bump hours by 1 via ArrowUp.
    page.locator("#durees_start_time_new .ti-display").click()
    page.locator("#durees_start_time_new .ti-field").wait_for(state="visible")
    hours_seg = page.locator("#durees_start_time_new .ti-seg[data-key='hours']")
    hours_seg.click()
    page.keyboard.press("ArrowUp")
    # The display badge (and its .ti-display-value text) is hidden while a
    # field is in edit mode — check the segment directly instead.
    expect(hours_seg).to_have_text("01", timeout=5_000)

    expect(_arrival_time_new_display(page)).to_have_text(_expected_arrival(secs, start="01:00:00"), timeout=10_000)


def test_toggle_on_new_field_edit_does_not_echo_back_and_close(gradio_server: str, page: Page) -> None:
    """Regression: _mirror_to_new used to write back into the very field that
    triggered it (e.g. editing durees_start_time_new fed the recomputed value
    right back to durees_start_time_new itself). TimeInput can't distinguish
    that server echo from a genuine external change, so its `watch('value')`
    handler reacted by exiting edit mode and dropping focus — after every
    single wheel tick / arrow press, kicking the user out of the field they
    were mid-edit on. Two ArrowUp presses in a row (no re-click in between)
    must both land, and the field editor must stay open throughout."""
    page.goto(gradio_server)
    _enable_time_input_toggle(page)

    page.locator("#durees_start_time_new .ti-display").click()
    page.locator("#durees_start_time_new .ti-field").wait_for(state="visible")
    hours_seg = page.locator("#durees_start_time_new .ti-seg[data-key='hours']")
    hours_seg.click()

    page.keyboard.press("ArrowUp")
    expect(hours_seg).to_have_text("01", timeout=5_000)
    # Give any server round trip triggered by that edit time to land before
    # the second press — this is exactly the window the echo used to fire in.
    page.wait_for_timeout(1_000)
    expect(page.locator("#durees_start_time_new .ti-field")).to_be_visible()

    page.keyboard.press("ArrowUp")
    expect(hours_seg).to_have_text("02", timeout=5_000)
