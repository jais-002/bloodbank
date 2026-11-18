import asyncio
from playwright.async_api import async_playwright

async def main():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            await page.goto('https://reactbits.dev/backgrounds/line-waves')
            await page.wait_for_selector('code', timeout=15000)
            codes = await page.query_selector_all('pre code')
            with open('scraped_waves.txt', 'w', encoding='utf-8') as f:
                for c in codes:
                    text = await c.inner_text()
                    f.write(text)
                    f.write('\n\n---NEXT---\n\n')
            await browser.close()
            print("Successfully extracted code.")
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
