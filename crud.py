# crud.py
from sqlalchemy.orm import Session
from models import Provider, Cinema, Movie, Showtime, BookingLink
from datetime import datetime
from typing import Optional, List

# Providers
def get_provider_by_name(db: Session, name: str):
    return db.query(Provider).filter(Provider.name == name).first()

def create_provider_if_not_exists(db: Session, name: str, website_url: Optional[str] = None):
    p = get_provider_by_name(db, name)
    if p:
        return p
    p = Provider(name=name, website_url=website_url)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p

# Cinemas
def get_or_create_cinema(db: Session, provider: Provider, external_id: str, name: str, city: Optional[str]=None, country: Optional[str]=None):
    c = db.query(Cinema).filter(Cinema.provider_id == provider.id, Cinema.external_id == external_id).first()
    if c:
        return c
    c = Cinema(provider_id=provider.id, external_id=external_id, name=name, city=city, country=country)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c

# Movies
def get_or_create_movie(db: Session, provider: Provider, external_id: str, title: str, poster: Optional[str]=None, core_movie_id: Optional[int]=None, raw_data: Optional[str]=None):
    m = db.query(Movie).filter(Movie.provider_id == provider.id, Movie.external_id == external_id).first()
    if m:
        # optionally update title / poster
        updated = False
        if poster and m.poster != poster:
            m.poster = poster
            updated = True
        if title and m.title != title:
            m.title = title
            updated = True
        if raw_data:
            m.raw_data = raw_data
            updated = True
        if updated:
            db.add(m)
            db.commit()
            db.refresh(m)
        return m
    m = Movie(
        core_movie_id=core_movie_id,
        provider_id=provider.id,
        external_id=external_id,
        title=title,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m

# Showtimes
def create_showtime_if_not_exists(db: Session, cinema: Cinema, movie: Movie, start_time: datetime, version_label: Optional[str]=None, hall_type: Optional[str]=None, audio_language: Optional[str]=None, subtitle_language: Optional[str]=None):
    s = db.query(Showtime).filter(Showtime.cinema_id==cinema.id, Showtime.movie_id==movie.id, Showtime.start_time==start_time).first()
    if s:
        return s
    s = Showtime(cinema_id=cinema.id, movie_id=movie.id, start_time=start_time,
                 version_label=version_label, hall_type=hall_type,
                 audio_language=audio_language, subtitle_language=subtitle_language)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

# Booking links
def create_booking_link_if_not_exists(db: Session, showtime: Showtime, url: str):
    existing = db.query(BookingLink).filter(BookingLink.showtime_id==showtime.id, BookingLink.url==url).first()
    if existing:
        return existing
    bl = BookingLink(showtime_id=showtime.id, url=url)
    db.add(bl)
    db.commit()
    db.refresh(bl)
    return bl
