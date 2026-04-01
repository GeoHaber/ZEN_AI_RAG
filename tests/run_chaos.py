import os
import random
import time
from playwright.sync_api import sync_playwright


def run_chaos():
    """Run chaos."""
    port = os.environ.get("NICEGUI_SCREEN_TEST_PORT", "8080")
    url = f"http://localhost:{port}"
    print(f"🐒 Unleashing Chaos Monkey on {url}...")
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch()
        page = browser.new_page()

        try:
            page.goto(url, timeout=10000)
        except Exception:
            print(f"❌ App not reachable: {e}")
            return

        # Prepare for chaos
        page.wait_for_timeout(2000)

        selectors = ["button", "input[class*='q-field__native']", ".q-toggle", ".q-btn"]

        interactions = 25
        errors = []

        print("⚡ Starting frenzy...")
        for i in range(interactions):
            try:
                # Find interactables
                candidates = []
                for sel in selectors:
                    elements = page.locator(sel).all()
                    for el in elements:
                        if el.is_visible():
                            candidates.append(el)

                if not candidates:
                    page.wait_for_timeout(200)
                    continue

                target = random.choice(candidates)

                try:
                    tag = target.evaluate("el => el.tagName.toLowerCase()")
                    if tag == "input":
                        text = "".join(random.choices("xyz", k=3))
                        target.fill(text, timeout=200)
                    else:
                        target.click(timeout=200, no_wait_after=True)
                except Exception:
                    pass

                # Check crash
                if page.locator("text='Connection lost'").is_visible():
                    print(f"🚨 CRASH DETECTED at step {i}")
                    errors.append("Connection Lost")
                    break

                page.wait_for_timeout(50)

            except Exception as e:
                print(f"⚠️ Warning: {e}")
                pass

        if errors:
            print("❌ Test Failed: Application Crashed")
            sys.exit(1)
        else:
            print("✅ Application Survived! (Sync Chaos Test Passed)")

        browser.close()


if __name__ == "__main__":
    import sys

    run_chaos()
