from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from sqlalchemy.orm import Session, joinedload
from database import SessionLocal, engine, Base
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import subprocess, asyncio

import models, schemas

# --------------------------------------------------
# INIT
# --------------------------------------------------
Base.metadata.create_all(bind=engine)
scheduler = AsyncIOScheduler()

app = FastAPI(
    title="Cinema Aggregator API",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# DB DEPENDENCY
# --------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --------------------------------------------------
# SINGLE ENDPOINT: SEARCH SHOWTIMES BY MOVIE TITLE
# --------------------------------------------------

async def auto_scrape():
    subprocess.run(["python", "scraper/legend_scraper.py"])
    subprocess.run(["python", "scraper/prime_scraper.py"])
    subprocess.run(["python", "seed_from_json.py"])

scheduler.add_job(auto_scrape, "cron", hour=2)  # runs at 2am daily

@app.on_event("startup")
async def start_scheduler():
    scheduler.start()
    
@app.get(
    "/showtimes",
    response_model=List[schemas.ShowtimeRead],
    summary="Get movie showtimes by movie title"
)
def get_showtimes_by_movie_title(
    movie_title: str = Query(..., description="Movie title to search"),
    db: Session = Depends(get_db)
):
    showtimes = (
        db.query(models.Showtime)
        .join(models.Movie)
        .options(
            joinedload(models.Showtime.movie),
            joinedload(models.Showtime.cinema).joinedload(models.Cinema.provider),
            joinedload(models.Showtime.booking_links),
        )
        .filter(models.Movie.title.ilike(f"%{movie_title}%"))
        .all()
    )

    return showtimes
