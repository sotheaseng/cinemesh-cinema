import asyncio
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlparse, parse_qs

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

BASE_URL = "https://www.legend.com.kh"
OUTPUT_FILE = "legend.json"

# =========================
# Utilities
# =========================

TIME_RE = re.compile(r"\b\d{1,2}:\d{2}\s?(?:AM|PM)\b", re.I)


def clean_title(raw: str) -> str | None:
    """
    Extract only the movie name from noisy link text
    """
    lines = [l.strip() for l in raw.splitlines() if l.strip()]
    noise = {"Advance Ticket"}
    lines = [l for l in lines if l not in noise]

    return lines[-1] if lines else None


def extract_date_from_url(url: str) -> str:
    """
    Extract date from ?date=YYYY-MM-DDT...
    """
    qs = parse_qs(urlparse(url).query)
    if "date" in qs:
        return qs["date"][0][:10]
    return datetime.now().strftime("%Y-%m-%d")


async def block_resources(route):
    if route.request.resource_type in {"image", "media", "font"}:
        await route.abort()
    else:
        await route.continue_()


async def safe_goto(page, url, retries=3):
    for attempt in range(1, retries + 1):
        try:
            print(f"🌐 Navigating to {url} (attempt {attempt})")
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(2500)
            return
        except PlaywrightTimeout:
            if attempt == retries:
                raise
            print("⚠️ Timeout, retrying...")
            await asyncio.sleep(2)

# =========================
# Scraping Logic
# =========================

async def extract_movies(page):
    await safe_goto(page, BASE_URL)
    await page.wait_for_selector("a[href*='/movies']", timeout=20000)

    links = await page.locator("a[href*='/movies']").all()

    movies = []
    seen = set()

    for link in links:
        href = await link.get_attribute("href")
        raw_title = await link.inner_text()

        if not href or not raw_title:
            continue

        title = clean_title(raw_title)
        if not title:
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


async def extract_showtimes(page, movie):
    await safe_goto(page, movie["url"])
    await page.wait_for_timeout(3000)

    content = await page.locator("body").inner_text()

    times = sorted(set(TIME_RE.findall(content)))
    times = [t for t in times if ":" in t]

    if not times:
        return []

    date_label = extract_date_from_url(movie["url"])

    # Extract cinema names
    cinema_names = set()

    lines = content.splitlines()

    for line in lines:
        line = line.strip()

        if "Legend" in line and "Cinema" not in line:
            if "Legend" in line and len(line) < 60:
                cinema_names.add(line)

    if not cinema_names:
        cinema_names.add("Legend Cinema")

    cinemas = []

    for name in cinema_names:
        cinemas.append({
            "cinema_name": name,
            "sessions": [
                {
                    "version_label": None,
                    "hall": None,
                    "audio_language": None,
                    "subtitle_language": None,
                    "times": times,
                }
            ],
        })

    return [
        {
            "date_label": date_label,
            "cinemas": cinemas,
        }
    ]

# =========================
# Main
# =========================

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

        for movie in movies_raw:
            try:
                dates = await extract_showtimes(page, movie)
                if not dates:
                    continue

                movies_out.append({
                    "booking_link": movie["url"],
                    "movie_title": movie["title"],
                    "poster": None,
                    "format": None,
                    "dates": dates,
                })

            except Exception as e:
                print(f"❌ Failed movie {movie['title']}: {e}")

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
