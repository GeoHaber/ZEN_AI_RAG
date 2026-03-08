import pytest
import os
import random
from playwright.async_api import Page, expect


# Minimal navigation fixture relying on pytest-playwright to handle loop
@pytest.fixture(autouse=True)
async def navigate_to_app(page: Page):
    """Navigate to app."""
    port = os.environ.get("NICEGUI_SCREEN_TEST_PORT", "8080")
    url = f"http://localhost:{port}"
    try:
        await page.goto(url, timeout=10000)
    except Exception as e:
        pytest.skip(f"App not running at {url}: {e}")
    yield


@pytest.mark.asyncio
def _do_test_chaos_monkey_setup():
    """Helper: setup phase for test_chaos_monkey."""

    print("\n🐒 Unleashing Chaos Monkey...")

    selectors = ["button", "input[class*='q-field__native']", ".q-toggle", ".q-btn"]

    interactions = 25
    errors = []

    return errors, interactions, selectors


async def test_chaos_monkey(page: Page):
    """Test chaos monkey."""
    errors, interactions, selectors = _do_test_chaos_monkey_setup()
    # Wait for app to be ready
    await page.wait_for_timeout(2000)

    for i in range(interactions):
        try:
            # Re-scan DOM each time
            candidates = []
            for sel in selectors:
                elements = await page.locator(sel).all()
                for el in elements:
                    if await el.is_visible():
                        candidates.append(el)

            if not candidates:
                await page.wait_for_timeout(200)
                continue

            # Pick random victim
            target = random.choice(candidates)

            try:
                tag_name = await target.evaluate("el => el.tagName.toLowerCase()", timeout=200)

                if tag_name == "input":
                    text = "".join(random.choices("abcdef", k=3))
                    await target.fill(text, timeout=200)
                else:
                    await target.click(timeout=200, no_wait_after=True)
            except Exception:
                pass

            # Check for crash
            if await page.locator("text='Connection lost'").is_visible():
                errors.append(f"Connection Lost detected at step {i}")
                break

            await page.wait_for_timeout(50)

        except Exception:
            pass

    if errors:
        pytest.fail(f"❌ Application Crashed: {errors}")

    assert True
    print("✅ Application Survived!")
