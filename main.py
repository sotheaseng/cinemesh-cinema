from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from datetime import date

from sqlalchemy.orm import Session, joinedload

from database import SessionLocal, engine, Base
import models, schemas, crud

# --------------------------------------------------
# INIT
# --------------------------------------------------
Base.metadata.create_all(bind=engine)

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
# PROVIDERS
# --------------------------------------------------
@app.get("/providers", response_model=List[schemas.ProviderRead])
def list_providers(db: Session = Depends(get_db)):
    return db.query(models.Provider).all()


@app.post("/providers", response_model=schemas.ProviderRead)
def create_provider(
    provider: schemas.ProviderBase,
    db: Session = Depends(get_db)
):
    return crud.create_provider_if_not_exists(
        db,
        provider.name,
        provider.website_url
    )


# --------------------------------------------------
# CINEMAS
# --------------------------------------------------
@app.get("/cinemas", response_model=List[schemas.CinemaRead])
def list_cinemas(
    provider_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Cinema)

    if provider_id is not None:
        q = q.filter(models.Cinema.provider_id == provider_id)

    return q.all()


@app.post("/cinemas", response_model=schemas.CinemaRead)
def create_cinema(
    cinema: schemas.CinemaBase,
    db: Session = Depends(get_db)
):
    provider = db.query(models.Provider).get(cinema.provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")

    return crud.get_or_create_cinema(
        db,
        provider,
        external_id=cinema.external_id,
        name=cinema.name,
        city=cinema.city,
        country=cinema.country,
    )


# --------------------------------------------------
# MOVIES
# --------------------------------------------------
@app.get("/movies", response_model=List[schemas.MovieRead])
def list_movies(
    title: Optional[str] = Query(None, description="Search by movie title"),
    provider_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Movie)

    if title:
        q = q.filter(models.Movie.title.ilike(f"%{title}%"))

    if provider_id is not None:
        q = q.filter(models.Movie.provider_id == provider_id)

    return q.all()


@app.get("/movies/{movie_id}", response_model=schemas.MovieRead)
def get_movie_by_id(
    movie_id: int,
    db: Session = Depends(get_db)
):
    movie = db.query(models.Movie).get(movie_id)
    if not movie:
        raise HTTPException(404, "Movie not found")
    return movie


@app.post("/movies", response_model=schemas.MovieRead)
def create_movie(
    movie: schemas.MovieBase,
    db: Session = Depends(get_db)
):
    provider = db.query(models.Provider).get(movie.provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")

    return crud.get_or_create_movie(
        db,
        provider,
        external_id=movie.external_id,
        title=movie.title,
        core_movie_id=movie.core_movie_id,
    )


# --------------------------------------------------
# SHOWTIMES
# --------------------------------------------------
@app.get("/showtimes", response_model=List[schemas.ShowtimeRead])
def list_showtimes(
    movie_id: Optional[int] = None,
    movie_title: Optional[str] = None,
    provider_id: Optional[int] = None,
    cinema_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db)
):
    q = db.query(models.Showtime).options(
        joinedload(models.Showtime.movie),
        joinedload(models.Showtime.cinema).joinedload(models.Cinema.provider),
        joinedload(models.Showtime.booking_links),
    )

    if movie_id is not None:
        q = q.filter(models.Showtime.movie_id == movie_id)

    if movie_title:
        q = q.join(models.Movie).filter(models.Movie.title.ilike(f"%{movie_title}%"))

    if cinema_id is not None:
        q = q.filter(models.Showtime.cinema_id == cinema_id)

    if provider_id is not None:
        q = q.join(models.Cinema).filter(models.Cinema.provider_id == provider_id)

    if start_date:
        q = q.filter(models.Showtime.start_time >= start_date)

    if end_date:
        q = q.filter(models.Showtime.start_time <= end_date)

    return q.all()


@app.post("/showtimes", response_model=schemas.ShowtimeRead)
def create_showtime(
    show: schemas.ShowtimeBase,
    db: Session = Depends(get_db)
):
    cinema = db.query(models.Cinema).get(show.cinema_id)
    movie = db.query(models.Movie).get(show.movie_id)

    if not cinema or not movie:
        raise HTTPException(404, "Cinema or Movie not found")

    showtime = crud.create_showtime_if_not_exists(
        db,
        cinema,
        movie,
        start_time=show.start_time,
        version_label=show.version_label,
        hall_type=show.hall_type,
        audio_language=show.audio_language,
        subtitle_language=show.subtitle_language,
    )

    db.refresh(showtime)
    return showtime


# --------------------------------------------------
# BOOKING LINKS
# --------------------------------------------------
@app.get("/booking-links", response_model=List[schemas.BookingLinkRead])
def list_booking_links(db: Session = Depends(get_db)):
    return db.query(models.BookingLink).all()
