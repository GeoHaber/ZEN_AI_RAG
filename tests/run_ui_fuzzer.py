import asyncio
import random
import sys
from playwright.async_api import async_playwright

# Standalone UI Chaos / Fuzzer Test
# Usage: python tests/run_ui_fuzzer.py


async def run_chaos_monkey():
    """Run chaos monkey."""
    port = "8080"  # Default NiceGUI port
    url = f"http://localhost:{port}"

    print(f"🐒 Initializing UI Chaos Monkey...")
    async with async_playwright() as p:
        # Launch browser (headless=False to see the chaos)
        try:
            browser = await p.chromium.launch(headless=False)
        except Exception as e:
            print(
                f"❌ Failed to launch browser: {e}. Please install playwright: pip install playwright && playwright install"
            )
            return

        context = await browser.new_context()
        page = await context.new_page()

        # 1. Connect to App
        try:
            print(f"🔌 Connecting to {url}...")
            await page.goto(url, timeout=5000)
            await page.wait_for_selector("body", timeout=5000)
        except Exception:
            print(f"⚠️ App not running at {url}. Please start 'python start_llm.py' first.")
            await browser.close()
            sys.exit(1)

        print("\n🚀 App connected! Unleashing the monkey in 3 seconds...")
        await asyncio.sleep(3)

        # Elements to interact with
        selectors = [
            "button",
            ".q-btn",
            "input[type='text']",
            "textarea",
            ".q-toggle",
            ".q-checkbox",
            ".q-item",
            ".q-expansion-item",
        ]

        interactions = 50
        errors = []

        for i in range(interactions):
            try:
                # 🐒 15% chance for special "High-Value" actions
                dice = random.random()
                if dice < 0.05:
                    print(f"[{i + 1}] 🌗 Monkey is toggling Theme...")
                    theme_toggle = page.locator(".q-toggle").first
                    if await theme_toggle.is_visible():
                        await theme_toggle.click()
                elif dice < 0.10:
                    print(f"[{i + 1}] ☰ Monkey is exploring the Drawer...")
                    menu_btn = page.locator("button:has-text('menu')").first
                    if await menu_btn.is_visible():
                        await menu_btn.click()
                        await asyncio.sleep(0.5)
                        # Try to click a random item in the expansion menus
                        items = await page.locator(".q-item").all()
                        if items:
                            await random.choice(items).click()
                elif dice < 0.15:
                    print(f"[{i + 1}] 🎙️ Monkey is checking the Voice Lab...")
                    voice_lab_btn = page.locator("button:has-text('Voice Lab')")
                    if await voice_lab_btn.is_visible():
                        await voice_lab_btn.click()
                        await asyncio.sleep(1)  # Wait for navigation
                        # We might be in a new tab now if it opened a new one
                        # Let's stay on the main page for now or switch back

                # Re-scan DOM for all interactable candidates
                candidates = []
                for sel in selectors:
                    elements = await page.locator(sel).all()
                    for el in elements:
                        try:
                            if await el.is_visible() and await el.is_enabled():
                                candidates.append(el)
                        except Exception:
                            continue

                if not candidates:
                    await asyncio.sleep(0.2)
                    continue

                target = random.choice(candidates)

                try:
                    tag_name = await target.evaluate("el => el.tagName.toLowerCase()", timeout=500)
                    type_attr = await target.get_attribute("type") or ""
                    await target.inner_text() or ""

                    # Highlight target
                    await target.evaluate(
                        "el => { el.style.outline = '3px solid #ff4444'; el.style.outlineOffset = '-3px'; }"
                    )
                    await asyncio.sleep(0.1)
                    await target.evaluate("el => el.style.outline = ''")

                    if tag_name in ["input", "textarea"] or "text" in type_attr:
                        text = "".join(random.choices("abcdef123!@# ", k=5))
                        await target.fill(text, timeout=500)
                    else:
                        # Click with a bit of randomness in position
                        await target.click(timeout=500, no_wait_after=True)

                except Exception:
                    pass

                # Specific check for RAG Dialog
                if await page.locator(".q-dialog").is_visible():
                    print(f"[{i + 1}] 🧠 Monkey is in the RAG Dialog!")
                    close_btn = page.locator(".q-dialog button:has-text('close')").first
                    if random.random() < 0.2 and await close_btn.is_visible():
                        await close_btn.click()

                # Check for critical failures
                if await page.locator("text='Connection lost'").is_visible():
                    errors.append(f"❌ Connection Lost detected at step {i}")
                    break

                if await page.locator("text='500'").is_visible() or await page.locator("text='Error'").count() > 10:
                    errors.append(f"❌ Potential Crash/Error loop detected at step {i}")
                    break

                await asyncio.sleep(0.2)

            except Exception:
                pass

            # Progress items
            print(f"\r[{i + 1}/{interactions}] Actions completed...", end="")
        print("\n")
        if errors:
            print(f"❌ TEST FAILED: Application Crashed!")
            for err in errors:
                print(err)
                pass
            sys.exit(1)

        print(f"✅ TEST PASSED: Application Survived {interactions} interactions!")
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(run_chaos_monkey())
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
