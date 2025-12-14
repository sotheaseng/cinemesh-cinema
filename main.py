from fastapi import FastAPI, Depends, HTTPException
from typing import List, Optional, Union
from sqlalchemy.orm import Session, joinedload

from database import SessionLocal, engine, Base
import models, schemas, crud

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Cinema Aggregator API", version="1.0.0")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow Next.js to access FastAPI
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# Dependency: DB Session
# ---------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------
# PROVIDERS
# ---------------------------
@app.post("/providers", response_model=schemas.ProviderRead)
def create_provider_api(provider: schemas.ProviderBase, db: Session = Depends(get_db)):
    return crud.create_provider_if_not_exists(db, provider.name, provider.website_url)


@app.get("/providers", response_model=List[schemas.ProviderRead])
def list_providers_api(db: Session = Depends(get_db)):
    return db.query(models.Provider).all()


# ---------------------------
# CINEMAS
# ---------------------------
@app.post("/cinemas", response_model=schemas.CinemaRead)
def create_cinema_api(cinema: schemas.CinemaBase, db: Session = Depends(get_db)):
    provider = db.query(models.Provider).filter(models.Provider.id == cinema.provider_id).first()
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


@app.get("/cinemas", response_model=List[schemas.CinemaRead])
def list_cinemas_api(db: Session = Depends(get_db)):
    return db.query(models.Cinema).all()


# ---------------------------
# MOVIES
# ---------------------------
@app.post("/movies", response_model=schemas.MovieRead)
def create_movie_api(movie: schemas.MovieBase, db: Session = Depends(get_db)):
    provider = db.query(models.Provider).filter(models.Provider.id == movie.provider_id).first()
    if not provider:
        raise HTTPException(404, "Provider not found")

    return crud.get_or_create_movie(
        db,
        provider,
        external_id=movie.external_id,
        title=movie.title,
        core_movie_id=movie.core_movie_id,
    )


@app.get("/movie", response_model=schemas.MovieRead)
def get_movie_api(
    db: Session = Depends(get_db),
    movie_id: Optional[int] = None,
    movie_title: Optional[str] = None,
):
    """Allow lookup by numeric movie_id OR movie_title."""
    if movie_id is not None:
        movie = db.query(models.Movie).filter(models.Movie.id == movie_id).first()
        if not movie:
            raise HTTPException(404, "Movie not found")
        return movie

    if movie_title is not None:
        movie = (
            db.query(models.Movie)
            .filter(models.Movie.title.ilike(f"%{movie_title}%"))
            .first()
        )
        if not movie:
            raise HTTPException(404, "Movie not found")
        return movie

    raise HTTPException(400, "You must provide either movie_id or movie_title")


# ---------------------------
# SHOWTIMES
# ---------------------------
@app.post("/showtimes", response_model=schemas.ShowtimeRead)
def create_showtime_api(show_in: schemas.ShowtimeBase, db: Session = Depends(get_db)):
    cinema = db.query(models.Cinema).filter(models.Cinema.id == show_in.cinema_id).first()
    movie = db.query(models.Movie).filter(models.Movie.id == show_in.movie_id).first()

    if not cinema or not movie:
        raise HTTPException(404, "Cinema or Movie not found")

    showtime = crud.create_showtime_if_not_exists(
        db,
        cinema,
        movie,
        start_time=show_in.start_time,
        version_label=show_in.version_label,
        hall_type=show_in.hall_type,
        audio_language=show_in.audio_language,
        subtitle_language=show_in.subtitle_language,
    )

    db.refresh(showtime)
    return showtime


@app.get("/showtimes", response_model=List[schemas.ShowtimeRead])
def list_showtimes_api(
    db: Session = Depends(get_db),
    movie_id: Optional[int] = None,
    movie_title: Optional[str] = None,
):
    q = db.query(models.Showtime).options(
        joinedload(models.Showtime.cinema).joinedload(models.Cinema.provider),
        joinedload(models.Showtime.movie),
        joinedload(models.Showtime.booking_links),
    )

    if movie_id:
        q = q.filter(models.Showtime.movie_id == movie_id)

    if movie_title:
        q = q.join(models.Movie).filter(models.Movie.title.ilike(f"%{movie_title}%"))

    return q.all()


# ---------------------------
# BOOKING LINKS
# ---------------------------
@app.get("/booking-links", response_model=List[schemas.BookingLinkRead])
def list_booking_links_api(db: Session = Depends(get_db)):
    return db.query(models.BookingLink).all()
