import datetime as dt
import pathlib

import nawminator as nm
import pytest
from playwright.sync_api import Page, expect

_PLAYERS_FIXTURE = (pathlib.Path(__file__).parent / "players_fixture.html").read_text()

pytestmark = [pytest.mark.ui, pytest.mark.parametrize("gradio_server", ["hybrid"], indirect=True)]


@pytest.fixture()
def durees_page(live_page) -> Page:
    return live_page("Durées", "#durees_target")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _fill_number(page: Page, elem_id: str, value: int | float) -> None:
    """Fill a gr.Number input by elem_id. Uses fill() to fire a single input event
    (avoids the race where Gradio's server response overwrites mid-keystroke typing)."""
    page.locator(f"#{elem_id} input").fill(str(value))


def _click_segment(page: Page, label: str) -> None:
    page.locator("#durees_target").get_by_role("button", name=label).click()


def _expected_duration(secs: float) -> str:
    return nm.utils.timedelta_to_ajhms(dt.timedelta(seconds=int(secs)))


def _expected_arrival(secs: float, start: str = "00:00:00") -> str:
    t = dt.datetime.strptime(start, "%H:%M:%S")
    return (t + dt.timedelta(seconds=secs)).strftime("%H:%M:%S")


# Scoped locators — gr.Number renders as <input>, gr.Text/Textbox as <textarea>
def _va(page: Page):
    return page.locator("#durees_va input")


def _duration(page: Page):
    return page.locator("#durees_duration").get_by_role("textbox")


def _start_time(page: Page):
    return page.locator("#durees_start_time").get_by_role("textbox")


def _arrival_time(page: Page):
    return page.locator("#durees_arrival_time").get_by_role("textbox")


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_durees_tab_renders(durees_page: Page) -> None:
    page = durees_page
    expect(page.locator("#durees_target").get_by_role("button", name="VA")).to_be_visible()
    expect(page.locator("#durees_target").get_by_role("button", name="Arrivée")).to_be_visible()
    expect(page.locator("#durees_target").get_by_role("button", name="Départ")).to_be_visible()
    expect(_va(page)).to_be_visible()
    expect(_duration(page)).to_be_visible()
    expect(_start_time(page)).to_be_visible()
    expect(_arrival_time(page)).to_be_visible()


def test_default_mode_interactivity(durees_page: Page) -> None:
    page = durees_page
    expect(_va(page)).to_be_editable()
    expect(_start_time(page)).to_be_editable()
    expect(_duration(page)).not_to_be_editable()
    expect(_arrival_time(page)).not_to_be_editable()


def test_switch_to_va_mode(durees_page: Page) -> None:
    page = durees_page
    _click_segment(page, "VA")
    expect(_duration(page)).to_be_editable(timeout=5_000)
    expect(_va(page)).not_to_be_editable()
    expect(_start_time(page)).to_be_editable()
    expect(_arrival_time(page)).to_be_editable()


def test_switch_to_depart_mode(durees_page: Page) -> None:
    page = durees_page
    _click_segment(page, "Départ")
    expect(_arrival_time(page)).to_be_editable(timeout=5_000)
    expect(_va(page)).to_be_editable()
    expect(_duration(page)).not_to_be_editable()
    expect(_start_time(page)).not_to_be_editable()


def test_arrivee_mode_computes_duration(durees_page: Page) -> None:
    page = durees_page
    secs = nm.formulas.duree_attaque(0, 0, 100, 0, 0)

    _fill_number(page, "durees_from_x", 0)
    _fill_number(page, "durees_from_y", 0)
    _fill_number(page, "durees_to_x", 100)
    _fill_number(page, "durees_to_y", 0)
    page.keyboard.press("Tab")

    expect(_duration(page)).to_have_value(_expected_duration(secs), timeout=10_000)
    expect(_arrival_time(page)).to_have_value(_expected_arrival(secs), timeout=10_000)


def test_arrivee_mode_va_changes_duration(durees_page: Page) -> None:
    page = durees_page
    secs0 = nm.formulas.duree_attaque(0, 0, 100, 0, 0)
    secs10 = nm.formulas.duree_attaque(0, 0, 100, 0, 10)

    _fill_number(page, "durees_from_x", 0)
    _fill_number(page, "durees_from_y", 0)
    _fill_number(page, "durees_to_x", 100)
    _fill_number(page, "durees_to_y", 0)

    # Wait for the VA=0 computation to settle before changing VA, so Gradio's
    # event queue is drained and the VA=10 fill fires into a clean queue.
    expect(_duration(page)).to_have_value(_expected_duration(secs0), timeout=10_000)

    _va(page).fill("10")
    page.keyboard.press("Tab")

    expect(_duration(page)).to_have_value(_expected_duration(secs10), timeout=10_000)
    expect(_arrival_time(page)).to_have_value(_expected_arrival(secs10), timeout=10_000)


def test_player_dropdown_fills_coordinates(gradio_server: str, page: Page) -> None:
    # Load player data via the Settings tab
    page.goto(gradio_server)
    page.get_by_role("tab", name="Réglages").click()
    page.get_by_label("Copiez les données depuis la page joueur ici.").fill(_PLAYERS_FIXTURE)
    page.get_by_role("button", name="Charger les données").click()
    page.get_by_text("3 joueurs chargés").first.wait_for(timeout=10_000)

    # Navigate to Durées — the dropdowns should now be populated and visible
    page.get_by_role("tab", name="Durées").click()
    page.locator("#durees_target").wait_for(state="visible")
    expect(page.locator("#durees_src_player")).to_be_visible(timeout=5_000)

    # Select Grim as source
    src = page.locator("#durees_src_player")
    src.click()
    src.get_by_role("option").filter(has_text="Grim:").click()
    expect(page.locator("#durees_from_x input")).to_have_value("4", timeout=5_000)
    expect(page.locator("#durees_from_y input")).to_have_value("156", timeout=5_000)

    # Select HarleyQueen as target
    tgt = page.locator("#durees_tgt_player")
    tgt.click()
    tgt.get_by_role("option").filter(has_text="HarleyQueen:").click()
    expect(page.locator("#durees_to_x input")).to_have_value("5", timeout=5_000)
    expect(page.locator("#durees_to_y input")).to_have_value("148", timeout=5_000)

    # Duration should be computed from the selected coordinates
    secs = nm.formulas.duree_attaque(4, 156, 5, 148, 0)
    expect(_duration(page)).to_have_value(_expected_duration(secs), timeout=10_000)
    expect(_arrival_time(page)).to_have_value(_expected_arrival(secs), timeout=10_000)


def test_va_mode_computes_va_from_times(durees_page: Page) -> None:
    page = durees_page
    base_secs = nm.formulas.duree_attaque(0, 0, 100, 0, 0)
    target_secs = nm.formulas.duree_attaque(0, 0, 100, 0, 10)

    _click_segment(page, "VA")
    expect(_va(page)).not_to_be_editable(timeout=5_000)
    # not_to_be_editable fires instantly (js=True); wait for the server chain
    # (_apply_time_defaults → _compute) to finish so it can't overwrite arrival.
    page.wait_for_timeout(500)

    # Set arrival first (before coords) so the queue is clear when we trigger
    # the coord fill — that compute runs with VA mode + the correct arrival.
    _arrival_time(page).fill(_expected_arrival(target_secs))
    _arrival_time(page).press("Tab")

    _fill_number(page, "durees_to_x", 100)
    page.keyboard.press("Tab")

    expected_va = nm.formulas.from_va(target_secs / base_secs)
    expect(_va(page)).to_have_value(str(expected_va), timeout=10_000)
    expect(_duration(page)).to_have_value(_expected_duration(target_secs), timeout=10_000)


def test_depart_mode_computes_start_time(durees_page: Page) -> None:
    """Realistic workflow: compute arrival in Arrivée mode, then switch to Départ to
    find when to leave. The Départ chain picks up the existing arrival value and
    back-computes start_time without needing to fill arrival in Départ mode."""
    page = durees_page
    secs = nm.formulas.duree_attaque(0, 0, 100, 0, 0)

    # Set coords in Arrivée mode — compute fills arrival with the trip end time
    _fill_number(page, "durees_to_x", 100)
    expect(_arrival_time(page)).to_have_value(_expected_arrival(secs), timeout=10_000)

    # Switch to Départ: the mode-switch chain runs _compute with the existing
    # arrival value → start_time = _shift_time(arrival, -secs) = "00:00:00"
    _click_segment(page, "Départ")
    expect(_start_time(page)).to_have_value("00:00:00", timeout=10_000)
    expect(_duration(page)).to_have_value(_expected_duration(secs), timeout=10_000)


def test_mode_switch_applies_time_defaults(durees_page: Page) -> None:
    page = durees_page

    # Case 1: fresh page has arrival="" — switching to Départ fills it to 00:00:00
    _click_segment(page, "Départ")
    expect(_arrival_time(page)).to_have_value("00:00:00", timeout=5_000)

    # Case 2: clear start in VA mode, switch to Arrivée → start refills to 00:00:00
    _click_segment(page, "VA")
    expect(_start_time(page)).to_be_editable(timeout=5_000)
    # Wait for the full VA chain (_apply_time_defaults + _compute) to complete before
    # clearing start. not_to_be_editable only catches the js=True interactivity step
    # (instant); the trailing _compute would push "23:10:00" back and overwrite our fill("").
    page.wait_for_timeout(500)

    _start_time(page).fill("")
    _start_time(page).press("Tab")

    _click_segment(page, "Arrivée")
    expect(_start_time(page)).to_have_value("00:00:00", timeout=5_000)


def test_va_mode_overnight_wraps_midnight(durees_page: Page) -> None:
    """_times_to_secs adds 86 400 s when arrival clock time is before start (next-day arrival)."""
    page = durees_page
    secs = nm.formulas.duree_attaque(0, 0, 10, 0, 0)
    start = "23:00:00"
    arrival = (dt.datetime(2000, 1, 1, 23, 0, 0) + dt.timedelta(seconds=secs)).strftime("%H:%M:%S")

    # Pre-fill coords and switch to VA mode
    _fill_number(page, "durees_to_x", 10)
    _click_segment(page, "VA")
    expect(_va(page)).not_to_be_editable(timeout=5_000)

    _start_time(page).fill(start)
    _arrival_time(page).fill(arrival)
    page.keyboard.press("Tab")

    # Duration must match the full trip length, proving the midnight wrap was applied
    expect(_duration(page)).to_have_value(_expected_duration(secs), timeout=10_000)
