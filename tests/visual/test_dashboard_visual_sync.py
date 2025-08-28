import pytest

@pytest.mark.playwright
def test_dashboard_loads_and_screenshots(page, base_url):
    url = base_url + "/"
    page.goto(url)
    page.wait_for_selector('h3.section-title')
    page.screenshot(path="dashboard_screenshot.png", full_page=True)
    assert page.query_selector('h3.section-title') is not None
