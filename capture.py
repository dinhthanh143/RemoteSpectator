import sys
import os
import asyncio
from playwright.async_api import async_playwright

async def capture(url: str, output_path: str):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=15000)
        await page.screenshot(path=output_path, full_page=False)
        await browser.close()
    print(f"Captured: {output_path}")

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:3000"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "d:/BotTest/remoteSpectator/.spectator/last_capture.png"
    asyncio.run(capture(target_url, out_file))
