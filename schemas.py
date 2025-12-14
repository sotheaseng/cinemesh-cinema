from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


# -----------------------------
# Provider
# -----------------------------
class ProviderBase(BaseModel):
    name: str
    website_url: Optional[str] = None


class ProviderRead(ProviderBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Mini Provider (for showtimes)
# -----------------------------
class ProviderMini(BaseModel):
    id: int
    name: str
    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Cinema
# -----------------------------
class CinemaBase(BaseModel):
    provider_id: int
    external_id: str
    name: str
    city: Optional[str] = None
    country: Optional[str] = None


class CinemaRead(CinemaBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Mini Cinema (for showtimes)
# -----------------------------
class CinemaMini(BaseModel):
    id: int
    name: str
    provider: ProviderMini   # <-- provider attached
    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Movie
# -----------------------------
class MovieBase(BaseModel):
    core_movie_id: Optional[int] = None
    provider_id: int
    external_id: str
    title: str


class MovieRead(MovieBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Booking Links
# -----------------------------
class BookingLinkRead(BaseModel):
    id: int
    showtime_id: int
    url: str

    model_config = ConfigDict(from_attributes=True)


# -----------------------------
# Showtime
# -----------------------------
class ShowtimeBase(BaseModel):
    cinema_id: int
    movie_id: int
    start_time: datetime
    version_label: Optional[str] = None
    hall_type: Optional[str] = None
    audio_language: Optional[str] = None
    subtitle_language: Optional[str] = None


class ShowtimeRead(ShowtimeBase):
    id: int
    cinema: CinemaMini               # <-- REQUIRED ORDER
    booking_links: List[BookingLinkRead] = []

    model_config = ConfigDict(from_attributes=True)
