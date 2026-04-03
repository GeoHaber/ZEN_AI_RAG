import pytest
import asyncio
import os
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

# Constants
UI_URL = "http://localhost:8080"
TEST_DATA_DIR = Path("tests/data/rag_e2e_temp")


@pytest.mark.asyncio
async def test_rag_ui_website_ingestion():
    """
    E2E Test: Open RAG Dialog -> Enter URL -> Scan -> Verify Chat Response.
    """
    print("\n" + "=" * 60)
    print("TEST: RAG Website Ingestion (UI)")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # 1. Load Page
            print(f"  → Navigating to {UI_URL}")
            await page.goto(UI_URL)
            await page.wait_for_load_state("networkidle")

            # 2. Open settings/RAG dialog (Assuming there's a button or we trigger via script if needed)
            # Strategy: Look for the specific database/scanner icon or button
            # Based on ui/rag_interface.py it's wired to 'open_rag_dialog' in app_state
            # But we need a button in the UI to click.
            # In zena.py (audit check), usually there's a button in the sidebar or header.
            # Let's try to find a button with icon 'library_books' or 'database' or similar

            print("  → Opening RAG Dialog...")
            # Try specific selectors used in zena.py/layout
            # Fallback: We can try to evaluate JS to open it if the button is hidden,
            # but better to simulate user click.

            # Common selectors for RAG/Knowledge base
            rag_btn = page.locator("button:has-text('Knowledge Base'), button i:text('library_books')")

            if await rag_btn.count() > 0:
                await rag_btn.first.click()
            else:
                # If specifically hidden, we might need to click a menu first?
                # Assuming standard layout from prior audit
                print("  ⚠️ Could not find intuitive RAG button, checking specific IDs...")
                # Try finding any button that looks right
                await page.click("button >> i:has-text('library_books')")

            await page.wait_for_selector("text=Knowledge Base Scanner", timeout=5000)
            print("  ✅ RAG Dialog Opened")

            # 3. Select Website Tab (Default)
            # Input URL
            target_url = "https://example.com"
            print(f"  → Entering URL: {target_url}")
            # NiceGUI inputs often match by their label text
            url_input = page.locator("label:has-text('Website URL') input")
            await url_input.fill(target_url)

            # 4. Start Scan
            print("  → Clicking Start Scan...")
            await page.click("button:has-text('Start Scan')")

            # 5. Wait for Completion
            # We look for "Ingestion Complete" or success notification
            print("  → Waiting for ingestion...")
            await page.wait_for_selector("text=Ingestion Complete", timeout=30000)
            print("  ✅ Ingestion Validated (Visual confirmation)")

            # 6. Verify via Chat
            print("  → Closing Dialog...")
            await page.click("button:has-text('Start Chatting')")  # From rag_interface success view

            print("  → Sending Query...")
            chat_input = page.locator("input[type='text'], textarea")
            await chat_input.fill("What is this website about?")
            await chat_input.press("Enter")

            print("  → Waiting for response...")
            # Wait for response bubble containing key terms
            # example.com usually says "This domain is for use in illustrative examples"
            await page.wait_for_selector("text=illustrative examples", timeout=15000)
            print("  ✅ Chat response verified!")

            return True

        except Exception as e:
            print(f"  ❌ Website Test Failed: {e}")
            await page.screenshot(path="rag_website_fail.png")
            raise e
        finally:
            await browser.close()


@pytest.mark.asyncio
async def test_rag_ui_directory_ingestion():
    """
    E2E Test: Open RAG Dialog -> Local File Tab -> Scan Dir -> Verify Chat.
    """
    print("\n" + "=" * 60)
    print("TEST: RAG Directory Ingestion (UI)")
    print("=" * 60)

    # Prepare Test Data
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    secret_phrase = "The purple ostrich dances at dawn."
    (TEST_DATA_DIR / "secret.txt").write_text(f"CONFIDENTIAL: {secret_phrase}")
    abs_path = str(TEST_DATA_DIR.resolve())

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            # 1. Nav & Open Dialog
            await page.goto(UI_URL)
            await page.click("button >> i:has-text('library_books')")
            await page.wait_for_selector("text=Knowledge Base Scanner")

            # 2. Switch to Directory Tab
            print("  → Switching to Local Files...")
            await page.click("div[role='tab']:has-text('Local Files')")

            # 3. Enter Path
            print(f"  → Entering Path: {abs_path}")
            dir_input = page.locator("label:has-text('Directory Path') input")
            await dir_input.fill(abs_path)

            # 4. Start Scan
            await page.click("button:has-text('Start Scan')")

            # 5. Wait for Success
            await page.wait_for_selector("text=Ingestion Complete", timeout=10000)
            print("  ✅ Directory Ingestion Complete")

            # 6. Verify Chat
            await page.click("button:has-text('Start Chatting')")

            chat_input = page.locator("input[type='text'], textarea")
            await chat_input.fill("What does the purple ostrich do?")
            await chat_input.press("Enter")

            # Check response for "dances at dawn"
            print("  → Verifying secret phrase retrieval...")
            await page.wait_for_selector(f"text=dances at dawn", timeout=15000)
            print("  ✅ Secret phrase matched!")

            return True

        except Exception as e:
            print(f"  ❌ Directory Test Failed: {e}")
            await page.screenshot(path="rag_dir_fail.png")
            raise e
        finally:
            await browser.close()
            # Cleanup
            if TEST_DATA_DIR.exists():
                shutil.rmtree(TEST_DATA_DIR)


if __name__ == "__main__":
    # Allow running directly
    asyncio.run(test_rag_ui_website_ingestion())
    asyncio.run(test_rag_ui_directory_ingestion())
