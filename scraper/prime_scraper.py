# prime_scraper.py
import time
import json
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime

MONTH_MAP = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
    "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
}

def parse_real_date(label: str) -> str:
    try:
        parts = label.replace(",", "").split()
        day = int(parts[1])
        month = MONTH_MAP[parts[3]]
        year = datetime.now().year

        dt = datetime(year, month, day)
        return dt.strftime("%Y-%m-%d")
    except:
        return None


BASE_URL = "https://primecineplex.com/"


def make_driver():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Firefox(options=options)
    driver.set_window_size(1500, 1200)
    return driver


def wait_for_showtimes_button(driver, timeout=20):
    """
    Prime loads a 10-second intro animation. We wait until the showtimes anchor appears.
    """

    print("⏳ Waiting for intro animation to finish...")

    try:
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href='#tab_1']"))
        )
        print("✅ Intro finished — SHOWTIMES tab clickable")
        return True
    except:
        print("❌ Could not detect SHOWTIMES tab — intro still blocking or layout changed")
        return False


def scrape_prime():
    driver = make_driver()
    driver.get(BASE_URL)

    # 1️⃣ Wait for the intro animation
    if not wait_for_showtimes_button(driver):
        driver.quit()
        return

    # 2️⃣ Click SHOWTIMES (tab 1)
    try:
        print("👉 Clicking SHOWTIMES tab...")
        btn = driver.find_element(By.CSS_SELECTOR, "a[href='#tab_1']")
        driver.execute_script("arguments[0].click();", btn)
        time.sleep(2)
    except Exception as e:
        print("❌ Failed to click SHOWTIMES:", e)
        driver.quit()
        return

    # 3️⃣ FIND DATE TABS using the REAL selector
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a.ui-tabs-anchor[href^='#tab_']"))
        )
    except:
        print("❌ ERROR: Date tabs did not load")
        driver.quit()
        return

    tab_buttons = driver.find_elements(By.CSS_SELECTOR, "a.ui-tabs-anchor[href^='#tab_']")
    print(f"📌 Found {len(tab_buttons)} date tabs")

    results = []

    # 4️⃣ Loop through date tabs
    for tab in tab_buttons:
        tab_label = tab.text.strip()
        tab_id = tab.get_attribute("href").split("#")[-1]

        print(f"\n📅 Scraping Date: {tab_label} ({tab_id})")

        driver.execute_script("arguments[0].click();", tab)
        time.sleep(2)

        # movie cards are inside #tab_X
        movie_cards = driver.find_elements(
            By.CSS_SELECTOR,
            f"#{tab_id} .col-md-3[style*='min-height']"
        )
        print(f"  🎬 Found {len(movie_cards)} movies")

        for card in movie_cards:

            try:
                movie_format = card.find_element(By.CSS_SELECTOR, ".col-2.text-excerpt").text.strip()
            except:
                movie_format = None

            movie_title = card.find_element(By.CSS_SELECTOR, ".col-10.text-excerpt").text.strip()

            try:
                poster = card.find_element(By.CSS_SELECTOR, "img#samloadimage").get_attribute("src")
            except:
                poster = None

            # find existing movie entry or create new
            movie_entry = next((m for m in results if m["movie_title"] == movie_title), None)

            if not movie_entry:
                movie_entry = {
                    "booking_link": BASE_URL,
                    "movie_title": movie_title,
                    "poster": poster,
                    "format": movie_format,
                    "dates": []
                }
                results.append(movie_entry)

            date_entry = {
                "date_label": parse_real_date(tab_label),
                "cinemas": []
            }

            # 5️⃣ cinema branches & times
            branches = card.find_elements(By.CSS_SELECTOR, ".sambranchbg")

            for branch in branches:
                branch_name = branch.text.strip()

                time_block = branch.find_element(By.XPATH, "./../div[2]")
                time_elements = time_block.find_elements(By.TAG_NAME, "a")

                sessions = []

                for a in time_elements:
                    raw = a.text.strip()  # e.g. "20:40 H1"
                    if not raw:
                        continue

                    parts = raw.split()
                    time_str = parts[0]
                    hall = parts[1] if len(parts) > 1 else None

                    sessions.append({
                        "version_label": movie_format,
                        "hall": hall,
                        "audio_language": None,
                        "subtitle_language": None,
                        "times": [time_str]
                    })

                date_entry["cinemas"].append({
                    "cinema_name": f"Prime {branch_name}",
                    "sessions": sessions
                })

            movie_entry["dates"].append(date_entry)

    # 6️⃣ Save output
    out = {
        "base_url": BASE_URL,
        "movies": results
    }

    with open("prime.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("\n✅ Saved to prime.json")
    driver.quit()


if __name__ == "__main__":
    scrape_prime()
