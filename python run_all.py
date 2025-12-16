import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRAPER_DIR = os.path.join(BASE_DIR, "scraper")

SCRAPERS = [
    "legend_scraper.py",
    "major_scraper.py",
    "prime_scraper.py",
]

SEEDER = "seed_from_json.py"


def run_script(path: str):
    print(f"\n▶ Running {os.path.basename(path)}")
    result = subprocess.run(
        [sys.executable, path],
        cwd=BASE_DIR,
    )
    if result.returncode != 0:
        print(f"❌ Failed: {path}")
        sys.exit(1)
    print(f"✅ Finished {os.path.basename(path)}")


def main():
    print("🚀 Starting cinema pipeline")

    for scraper in SCRAPERS:
        run_script(os.path.join(SCRAPER_DIR, scraper))

    run_script(os.path.join(BASE_DIR, SEEDER))

    print("\n🎉 All scrapers executed and database seeded successfully!")


if __name__ == "__main__":
    main()
