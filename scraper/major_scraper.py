import requests
import json
from time import sleep

BASE = "https://majorcineplex.com.kh/api"

CINEMAS = [
    {"id": "0000008101", "name": "Major Aeon Mall Phnom Penh"},
    {"id": "0000008102", "name": "Major Cineplex Aeon Sen Sok"},
    {"id": "0000008103", "name": "Major Cineplex Aeon Mean Chey"},
    {"id": "0000008104", "name": "Major Cineplex Sorya"},
    {"id": "0000008105", "name": "Major Platinum Siem Reap"},
    {"id": "0000008106", "name": "Major Cineplex Big C Poipet"},
]

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://majorcineplex.com.kh/showtime",
}


# --------------------------------------------------
# API CALLS
# --------------------------------------------------
def get_dates(cinema_id):
    r = requests.get(
        f"{BASE}/date-show-movie",
        params={"cinema": cinema_id},
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


def get_showtimes(cinema_id, date):
    r = requests.get(
        f"{BASE}/show-movie",
        params={"cinema": cinema_id, "date": date},
        headers=HEADERS,
        timeout=10,
    )
    r.raise_for_status()
    return r.json()


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main():
    movies_index = {}

    for cinema in CINEMAS:
        print(f"🎬 Scraping {cinema['name']}")

        try:
            dates = get_dates(cinema["id"])
        except Exception as e:
            print("❌ Failed dates:", e)
            continue

        for raw_date in dates:
            date_label = raw_date.split("T")[0]
            print(f"   📅 {date_label}")

            try:
                payload = get_showtimes(cinema["id"], raw_date)
            except Exception as e:
                print("❌ Failed showtimes:", e)
                continue

            # 🔑 NORMALIZE PAYLOAD (dict OR list)
            if isinstance(payload, list):
                items = payload
            else:
                items = [payload]

            for item in items:
                theaters = item.get("theaters", [])

                for hall in theaters:
                    hall_name = hall.get("name")

                    for movie in hall.get("movies", []):
                        title = movie.get("title")
                        poster = movie.get("posterImage")
                        category = movie.get("category")
                        rating = movie.get("rating")

                        if not title:
                            continue

                        format_label = (
                            f"{category}-{rating}" if rating else category
                        )

                        movie_entry = movies_index.setdefault(
                            title,
                            {
                                "booking_link": "https://majorcineplex.com.kh/showtime",
                                "movie_title": title,
                                "poster": (
                                    f"https://majorcineplex.com.kh{poster}"
                                    if poster else None
                                ),
                                "format": format_label,
                                "dates": {},
                            }
                        )

                        date_bucket = movie_entry["dates"].setdefault(
                            date_label, {}
                        )
                        cinema_bucket = date_bucket.setdefault(
                            cinema["name"], {}
                        )

                        # ❗ sessions are inside movie["movies"]
                        for session in movie.get("movies", []):
                            show_time = session.get("showTime")
                            if not show_time:
                                continue

                            time_only = show_time.split("T")[1][:5]

                            key = (format_label, hall_name)
                            session_entry = cinema_bucket.setdefault(
                                key,
                                {
                                    "version_label": format_label,
                                    "hall": hall_name,
                                    "audio_language": None,
                                    "subtitle_language": None,
                                    "times": [],
                                }
                            )

                            if time_only not in session_entry["times"]:
                                session_entry["times"].append(time_only)

            sleep(0.25)

    # --------------------------------------------------
    # NORMALIZE TO PRIME FORMAT
    # --------------------------------------------------
    movies_output = []

    for movie in movies_index.values():
        dates_out = []

        for date_label, cinemas in movie["dates"].items():
            cinemas_out = []

            for cinema_name, sessions in cinemas.items():
                cinemas_out.append(
                    {
                        "cinema_name": cinema_name,
                        "sessions": list(sessions.values()),
                    }
                )

            dates_out.append(
                {
                    "date_label": date_label,
                    "cinemas": cinemas_out,
                }
            )

        movie["dates"] = dates_out
        movies_output.append(movie)

    with open("major.json", "w", encoding="utf-8") as f:
        json.dump(
            {
                "base_url": "https://majorcineplex.com.kh",
                "movies": movies_output,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"✅ Saved major.json | Movies: {len(movies_output)}")


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
if __name__ == "__main__":
    main()
