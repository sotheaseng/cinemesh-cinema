import re
import json
import asyncio
from datetime import date
from urllib.parse import urljoin
from playwright.async_api import async_playwright

BASE_URL = "https://www.legend.com.kh"

MONTH = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

TIME_RE = re.compile(r"\d{1,2}:\d{2}\s?(AM|PM)", re.I)

# -----------------------------------------------------

def parse_date(text):
    d = re.search(r"\b(\d{1,2})\b", text)
    m = re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", text)
    if not d or not m:
        return None
    return date(date.today().year, MONTH[m.group(1)], int(d.group(1))).isoformat()

def clean_title(text):
    return text.splitlines()[-1].strip()

# -----------------------------------------------------

async def get_movies(page):
    await page.goto(BASE_URL)
    await page.wait_for_timeout(3000)
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await page.wait_for_timeout(2000)

    movies = []
    seen = set()

    for a in await page.locator("a[href*='/movies/']").all():
        href = await a.get_attribute("href")
        title = (await a.inner_text()).strip()
        if href:
            url = urljoin(BASE_URL, href.split("?", 1)[0])
            if url not in seen:
                seen.add(url)
                movies.append((title, url))

    print(f"🎬 Found {len(movies)} movies")
    return movies

# -----------------------------------------------------

async def parse_sessions(panel):
    sessions = []

    blocks = await panel.locator("div.my-10").all()
    for block in blocks:
        version = await block.locator("img[alt]").first.get_attribute("alt")

        hall = audio = sub = None
        for img in await block.locator("div.mb-6 img").all():
            alt = (await img.get_attribute("alt") or "").lower()
            if "screenx" in alt:
                hall = "ScreenX"
            elif "gold" in alt:
                hall = "Gold"
            elif "regular" in alt:
                hall = "Regular"
            if "lang" in alt:
                audio = "EN" if "eng" in alt else "KH"
            if "sub" in alt:
                sub = "EN" if "eng" in alt else "KH"

        times = []
        for t in await block.locator("a,button").all():
            txt = (await t.inner_text()).strip()
            if TIME_RE.match(txt):
                times.append(txt)

        if version and hall and audio and sub and times:
            sessions.append({
                "version_label": version,
                "hall": hall,
                "audio_language": audio,
                "subtitle_language": sub,
                "times": times
            })

    return sessions

# -----------------------------------------------------

async def scrape_movie(browser, movie, sem):
    async with sem:
        raw_title, url = movie
        print("🎞", raw_title)

        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(url)
            await page.wait_for_timeout(2000)

            title = clean_title(
                await page.get_by_role("heading").first.inner_text()
            )

            movie_data = {
                "booking_link": url,
                "movie_title": title,
                "dates": []
            }

            date_tabs = await page.locator("div[role='tab']").all()

            for tab in date_tabs:
                label = (await tab.inner_text()).strip()
                iso = parse_date(label)
                if not iso:
                    continue

                await tab.click()
                await page.wait_for_timeout(1200)

                date_entry = {
                    "date_label": iso,
                    "cinemas": []
                }

                headers = await page.locator("button[id^='headlessui-disclosure-button']").all()
                panels = await page.locator("div[id^='headlessui-disclosure-panel']").all()

                for h, p in zip(headers, panels):
                    cinema = (await h.inner_text()).strip()
                    sessions = await parse_sessions(p)

                    if sessions:
                        date_entry["cinemas"].append({
                            "cinema_name": cinema,
                            "sessions": sessions
                        })

                if date_entry["cinemas"]:
                    movie_data["dates"].append(date_entry)

            return movie_data

        finally:
            try:
                await context.close()
            except:
                pass

# -----------------------------------------------------

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        page = await browser.new_page()
        movies = await get_movies(page)
        await page.close()

        sem = asyncio.Semaphore(3)
        tasks = [scrape_movie(browser, m, sem) for m in movies]

        results = []
        for r in await asyncio.gather(*tasks, return_exceptions=True):
            if isinstance(r, dict):
                results.append(r)
            elif isinstance(r, Exception):
                print("⚠️ Movie failed:", repr(r))
        await browser.close()

    with open("legend.json", "w", encoding="utf-8") as f:
        json.dump({"base_url": BASE_URL, "movies": results}, f, indent=2, ensure_ascii=False)

    print("✅ Saved legend.json | Movies:", len(results))

if __name__ == "__main__":
    asyncio.run(main())
