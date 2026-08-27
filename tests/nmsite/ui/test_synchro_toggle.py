"""UI tests for the opt-in TimeInput toggle applied to the Synchro tab's
departure time field."""

import datetime as dt

import nawminator as nm
import pytest
from playwright.sync_api import Page, expect

pytestmark = [pytest.mark.ui, pytest.mark.parametrize("gradio_server", ["hybrid"], indirect=True)]

# Two players, same alliance, tdc within calc_synchros's 0.5x-3x range of each
# other (unlike players_fixture.html's real data, which has no such pair —
# built minimally here rather than fixing that unrelated tdc-range edge case).
_TWO_PLAYERS_TEXT = "[4:156]\t1000000\tHomeGrim\tGrim\tSDS\n" "[5:148]\t1500000\tHomeHarley\tHarleyQueen\tSDS"


def _load_fixture_data(page: Page) -> None:
    page.get_by_role("tab", name="Réglages").click()
    page.get_by_label("Copiez les données depuis la page joueur ici.").fill(_TWO_PLAYERS_TEXT)
    page.get_by_role("button", name="Charger les données").click()
    page.get_by_text("2 joueurs chargés").first.wait_for(timeout=10_000)


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


def _old_time_input(page: Page):
    return page.locator("#synchro_time_input")


def _new_time_input(page: Page):
    return page.locator("#synchro_time_input_new")


def _seg(page: Page, key: str):
    return page.locator("#synchro_time_input_new .ti-seg[data-key='" + key + "']")


def _type_digits(page: Page, seg, digits: str) -> None:
    seg.click()
    for d in digits:
        page.keyboard.press(d)


def test_toggle_off_shows_old_datetime_input(gradio_server: str, page: Page) -> None:
    page.goto(gradio_server)
    page.get_by_role("tab", name="Synchro").click()
    page.locator("#synchro_time_input").wait_for(state="visible")
    expect(_old_time_input(page)).to_be_visible()
    expect(_new_time_input(page)).to_be_hidden()


def test_toggle_on_shows_new_time_input(gradio_server: str, page: Page) -> None:
    page.goto(gradio_server)
    _enable_time_input_toggle(page)
    page.get_by_role("tab", name="Synchro").click()
    page.locator("#synchro_time_input_new").wait_for(state="visible")
    expect(_new_time_input(page)).to_be_visible()
    expect(_old_time_input(page)).to_be_hidden()


def test_toggle_on_new_time_input_defaults_to_now_not_epoch(gradio_server: str, page: Page) -> None:
    """Regression: TimeInput's `value=lambda: dt.datetime.now()` default was
    silently discarded (double gr.HTML.postprocess()'d instead of resolved),
    so the field always rendered the mode's empty default — 01/01/1970 — no
    matter what was passed. It must show today's date on a fresh page load."""
    page.goto(gradio_server)
    _enable_time_input_toggle(page)
    page.get_by_role("tab", name="Synchro").click()
    display = _new_time_input(page).locator(".ti-display-value")
    expect(display).to_be_visible(timeout=5_000)
    assert dt.datetime.now().strftime("%d/%m/%Y") in display.inner_text()


def test_toggle_on_new_time_input_drives_synchro_computation(gradio_server: str, page: Page) -> None:
    page.goto(gradio_server)
    _load_fixture_data(page)
    _enable_time_input_toggle(page)

    page.get_by_role("tab", name="Synchro").click()
    page.locator("#synchro_time_input_new").wait_for(state="visible")

    page.get_by_label("Joueur à synchro").click()
    page.get_by_role("option").filter(has_text="Grim").click()

    page.get_by_label("Alliances Cibles").click()
    page.get_by_role("option").filter(has_text="SDS").click()
    page.keyboard.press("Escape")
    # Wait for the selection to commit server-side before proceeding — without
    # this, clicking Calculate can race the alliance-selection event and fire
    # with target_allis still empty.
    page.get_by_text("SDS", exact=True).wait_for(state="visible")

    # Enter edit mode, then type an explicit deterministic time (date segments
    # stay at their default — calc_synchros only ever reads .time() off the
    # resulting datetime, so the date part is irrelevant here).
    page.locator("#synchro_time_input_new .ti-display").click()
    page.locator("#synchro_time_input_new .ti-field").wait_for(state="visible")
    _type_digits(page, _seg(page, "hours"), "00")
    _type_digits(page, _seg(page, "minutes"), "05")
    _type_digits(page, _seg(page, "seconds"), "00")

    page.get_by_role("button", name="Calcule!").click()

    secs = nm.formulas.duree_attaque(5, 148, 4, 156, va=0)
    expected_horaire = (dt.datetime(1970, 1, 1, 0, 5, 0) + dt.timedelta(seconds=secs)).time().strftime("%H:%M:%S")

    expect(page.get_by_role("button", name=expected_horaire)).to_be_visible(timeout=10_000)
