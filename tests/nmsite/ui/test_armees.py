import pytest
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.ui


@pytest.fixture()
def armees_page(live_page) -> Page:
    return live_page("Armées", "#armees_tdp_mode")


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_armees_tab_renders(armees_page: Page) -> None:
    page = armees_page
    expect(page.get_by_role("button", name="+")).to_be_visible()
    expect(page.get_by_role("button", name="All")).to_be_visible()
    expect(page.get_by_label("TDP")).to_be_visible()
    expect(page.get_by_label("Quête Alliance")).to_be_visible()
    expect(page.get_by_label("Durée")).to_be_visible()
    expect(page.locator("#armees_tdp_mode").get_by_role("button", name="Durée")).to_be_visible()
    expect(page.locator("#armees_tdp_mode").get_by_role("button", name="TDP")).to_be_visible()


@pytest.mark.skip(reason="TODO")
def test_add_row(armees_page: Page) -> None:
    pass


@pytest.mark.skip(reason="TODO")
def test_delete_row(armees_page: Page) -> None:
    pass


@pytest.mark.skip(reason="TODO")
def test_repartir(armees_page: Page) -> None:
    pass


@pytest.mark.skip(reason="TODO")
def test_total_updates(armees_page: Page) -> None:
    pass


@pytest.mark.skip(reason="TODO")
def test_tdp_mode_computes_duration(armees_page: Page) -> None:
    pass


@pytest.mark.skip(reason="TODO")
def test_duration_mode_computes_tdp(armees_page: Page) -> None:
    pass
