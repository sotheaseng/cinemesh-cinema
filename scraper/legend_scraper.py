import asyncio
import json
import re
from datetime import datetime
from urllib.parse import urljoin

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "https://www.legend.com.kh"
OUTPUT_FILE = "legend.json"


async def block_resources(route):
    if route.request.resource_type in {"image", "media", "font"}:
        await route.abort()
    else:
        await route.continue_()


async def safe_goto(page, url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            print(f"🌐 Navigating to {url} (attempt {attempt})")
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=60000,
            )
            await page.wait_for_timeout(3000)
            return
        except PlaywrightTimeout:
            if attempt == retries:
                raise
            print("⚠️ Timeout, retrying...")
            await asyncio.sleep(2)


async def extract_movies(page):
    await safe_goto(page, BASE_URL)

    await page.wait_for_selector("a[href*='/movies']", timeout=20000)

    links = await page.locator("a[href*='/movies']").all()

    movies = []
    seen = set()

    for link in links:
        href = await link.get_attribute("href")
        title = (await link.inner_text()).strip()

        if not href or not title:
            continue

        url = href if href.startswith("http") else urljoin(BASE_URL, href)

        if url in seen:
            continue

        seen.add(url)
        movies.append({
            "title": title,
            "url": url,
        })

    return movies


TIME_RE = re.compile(r"\d{1,2}:\d{2}\s?(AM|PM)?", re.I)


async def extract_showtimes(page, movie):
    await safe_goto(page, movie["url"])

    await page.wait_for_timeout(3000)

    content = await page.content()

    times = TIME_RE.findall(content)
    dates = []

    today = datetime.now().strftime("%Y-%m-%d")

    if times:
        dates.append({
            "date_label": today,
            "cinemas": [
                {
                    "cinema_name": "Legend Cinema",
                    "sessions": [
                        {
                            "version_label": None,
                            "hall": None,
                            "audio_language": None,
                            "subtitle_language": None,
                            "times": list(set(times)),
                        }
                    ],
                }
            ],
        })

    return dates


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )

        page = await context.new_page()
        await page.route("**/*", block_resources)

        print("🎬 Scraping Legend Cinema")

        movies_raw = await extract_movies(page)
        print(f"🎥 Found {len(movies_raw)} movies")

        movies_out = []

        for m in movies_raw:
            try:
                dates = await extract_showtimes(page, m)
                if not dates:
                    continue

                movies_out.append({
                    "booking_link": m["url"],
                    "movie_title": m["title"],
                    "poster": None,
                    "format": None,
                    "dates": dates,
                })
            except Exception as e:
                print(f"❌ Failed movie {m['title']}: {e}")

        await browser.close()

        output = {
            "base_url": BASE_URL,
            "movies": movies_out,
        }

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved {OUTPUT_FILE} | Movies: {len(movies_out)}")


if __name__ == "__main__":
    asyncio.run(main())
