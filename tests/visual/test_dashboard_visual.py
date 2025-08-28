import pytest

@pytest.mark.parametrize("path", ["/"])
async def test_dashboard_loads_and_screenshots(page, base_url, path):
    url = base_url + path
    await page.goto(url)
    await page.wait_for_selector('h3.section-title')
    # take a full page screenshot
    await page.screenshot(path="dashboard_screenshot.png", full_page=True)
    assert await page.query_selector('h3.section-title') is not None
