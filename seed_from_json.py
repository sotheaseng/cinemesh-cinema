# seed_from_json.py
import json
import re
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime
import os

from database import SessionLocal, engine, Base
import models
from crud import (
    create_provider_if_not_exists,
    get_or_create_cinema,
    get_or_create_movie,
    create_showtime_if_not_exists,
    create_booking_link_if_not_exists,
)

# -------------------------------------------------------
# RESET DATABASE (DROP EVERYTHING)
# -------------------------------------------------------
def reset_database():
    print("⚠️ WARNING: Dropping ALL tables...")
    Base.metadata.drop_all(bind=engine)
    print("🗑️ All tables dropped.")

    print("📦 Recreating tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Tables recreated.\n")


# -------------------------------------------------------
# TIME PARSING HELPERS
# -------------------------------------------------------
def parse_time_str(text: str):
    m = re.search(r"(\d{1,2}:\d{2})(?:\s*(AM|PM|am|pm))?", text)
    if not m:
        return None

    hhmm = m.group(1)
    ampm = m.group(2)

    try:
        if ampm:
            return datetime.strptime(f"{hhmm} {ampm}", "%I:%M %p").time()
        return datetime.strptime(hhmm, "%H:%M").time()
    except:
        return None


def parse_date(date_str: str):
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None


def parse_showdate_from_url(href: str):
    if not href:
        return None

    parsed = urlparse(href)
    q = parse_qs(parsed.query)

    if "ShowDate" in q:
        raw = unquote(q["ShowDate"][0])
        for fmt in ("%d-%b-%Y %I:%M:%S %p", "%d-%b-%Y %I:%M %p"):
            try:
                return datetime.strptime(raw, fmt)
            except:
                continue

    return None


# -------------------------------------------------------
# SEEDER (NOW SUPPORTS PRIME, LEGEND, MAJOR)
# -------------------------------------------------------
def seed_file(file_path: str, provider_name: str):
    print(f"🌱 Seeding {file_path} ({provider_name})")

    db = SessionLocal()

    provider = create_provider_if_not_exists(
        db,
        provider_name,
        website_url=None
    )

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for m in data.get("movies", []):
        title = m.get("movie_title") or m.get("title") or "Unknown"

        # ✅ provider-scoped movie ID
        movie = get_or_create_movie(
            db,
            provider,
            external_id=f"{provider_name}:{title}",
            title=title
        )

        for date_entry in m.get("dates", []):
            date_label = date_entry.get("date_label")

            show_date = parse_date(date_label) or datetime.now().date()

            for c in date_entry.get("cinemas", []):
                cinema_name = c.get("cinema_name")

                cinema = get_or_create_cinema(
                    db,
                    provider,
                    external_id=cinema_name,
                    name=cinema_name
                )

                for sess in c.get("sessions", []):
                    version = sess.get("version_label")
                    hall = sess.get("hall")
                    audio = sess.get("audio_language")
                    sub = sess.get("subtitle_language")

                    for t in sess.get("times", []):
                        if isinstance(t, dict):
                            time_str = t.get("time")
                            booking_url = t.get("url")
                        else:
                            time_str = t
                            booking_url = None  # Major & Prime

                        dt = None
                        if booking_url:
                            dt = parse_showdate_from_url(booking_url)

                        if not dt:
                            time_val = parse_time_str(time_str)
                            if not time_val:
                                continue
                            dt = datetime.combine(show_date, time_val)

                        showtime = create_showtime_if_not_exists(
                            db,
                            cinema=cinema,
                            movie=movie,
                            start_time=dt,
                            version_label=version,
                            hall_type=hall,
                            audio_language=audio,
                            subtitle_language=sub
                        )

                        if booking_url:
                            create_booking_link_if_not_exists(
                                db,
                                showtime,
                                booking_url
                            )

    db.close()
    print(f"✅ Finished seeding {provider_name}\n")


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))

    prime_path = os.path.join(base_dir, "prime.json")
    legend_path = os.path.join(base_dir, "legend.json")
    major_path = os.path.join(base_dir, "major.json")

    reset_database()

    if os.path.exists(prime_path):
        seed_file(prime_path, "Prime Cineplex")

    if os.path.exists(legend_path):
        seed_file(legend_path, "Legend Cinema")

    if os.path.exists(major_path):
        seed_file(major_path, "Major Cineplex")

    print("🎉 Seeding complete.")
