# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    website_url = Column(String(255))

    cinemas = relationship("Cinema", back_populates="provider")
    movies = relationship("Movie", back_populates="provider")


class Cinema(Base):
    __tablename__ = "cinemas"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    external_id = Column(String(100), nullable=False)
    name = Column(String(150), nullable=False)
    city = Column(String(100))
    country = Column(String(50))

    provider = relationship("Provider", back_populates="cinemas")
    showtimes = relationship("Showtime", back_populates="cinema")

    __table_args__ = (UniqueConstraint("provider_id", "external_id"),)


class Movie(Base):
    __tablename__ = "movies"

    id = Column(Integer, primary_key=True, index=True)

    # changed: nullable=True because scrapers do not provide this value
    core_movie_id = Column(Integer, nullable=True)

    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    external_id = Column(String(100), nullable=False)
    title = Column(String(255), nullable=False)

    provider = relationship("Provider", back_populates="movies")
    showtimes = relationship("Showtime", back_populates="movie")

    __table_args__ = (UniqueConstraint("core_movie_id", "provider_id"),)


class Showtime(Base):
    __tablename__ = "showtimes"

    id = Column(Integer, primary_key=True, index=True)
    cinema_id = Column(Integer, ForeignKey("cinemas.id"), nullable=False)
    movie_id = Column(Integer, ForeignKey("movies.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)

    version_label = Column(String(50))
    hall_type = Column(String(50))
    audio_language = Column(String(10))
    subtitle_language = Column(String(10))

    cinema = relationship("Cinema", back_populates="showtimes")
    movie = relationship("Movie", back_populates="showtimes")
    booking_links = relationship("BookingLink", back_populates="showtime")

    __table_args__ = (UniqueConstraint("cinema_id", "movie_id", "start_time"),)


class BookingLink(Base):
    __tablename__ = "booking_links"

    id = Column(Integer, primary_key=True, index=True)
    showtime_id = Column(Integer, ForeignKey("showtimes.id"), nullable=False)
    url = Column(String(255), nullable=False)

    showtime = relationship("Showtime", back_populates="booking_links")
