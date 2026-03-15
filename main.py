from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from sqlalchemy.orm import Session, joinedload
from database import SessionLocal, engine, Base
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import subprocess, asyncio

import models, schemas
from sqlalchemy.exc import IntegrityError

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


# --------------------------------------------------
# RESERVATIONS
# --------------------------------------------------

@app.post(
    "/reservations",
    response_model=schemas.ReservationRead,
    summary="Create a reservation for a showtime seat",
)
def create_reservation(
    payload: schemas.ReservationCreate,
    db: Session = Depends(get_db),
):
    try:
        reservation = models.Reservation(
            showtime_id=payload.showtime_id,
            core_user_id=payload.core_user_id,
            seat_label=payload.seat_label,
            booking_link_id=payload.booking_link_id,
        )
        db.add(reservation)
        db.commit()
        db.refresh(reservation)
        return reservation
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Seat already reserved")


@app.get(
    "/showtimes/{showtime_id}/reserved-seats",
    response_model=List[str],
    summary="List reserved seats for a showtime",
)
def get_reserved_seats(
    showtime_id: int,
    db: Session = Depends(get_db),
):
    rows = (
        db.query(models.Reservation.seat_label)
        .filter(
            models.Reservation.showtime_id == showtime_id,
            models.Reservation.status.in_(["booked", "confirmed"]),
        )
        .all()
    )
    return [r[0] for r in rows]


@app.get(
    "/users/{core_user_id}/reservations",
    response_model=List[schemas.ReservationRead],
    summary="List reservations for a core user",
)
def list_user_reservations(
    core_user_id: int,
    db: Session = Depends(get_db),
):
    reservations = (
        db.query(models.Reservation)
        .filter(models.Reservation.core_user_id == core_user_id)
        .all()
    )
    return reservations


@app.get(
    "/reservations",
    response_model=List[schemas.ReservationRead],
    summary="List all reservations (admin use)",
)
def list_all_reservations(
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Reservation)
        .options(
            joinedload(models.Reservation.showtime)
            .joinedload(models.Showtime.cinema)
            .joinedload(models.Cinema.provider),
            joinedload(models.Reservation.showtime).joinedload(models.Showtime.movie),
            joinedload(models.Reservation.showtime).joinedload(
                models.Showtime.booking_links
            ),
        )
        .all()
    )
