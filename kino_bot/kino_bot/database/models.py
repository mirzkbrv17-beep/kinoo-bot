"""SQLAlchemy 2.0 modellari — barcha jadvallar."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (BigInteger, Boolean, DateTime, Float, ForeignKey, Index,
                        Integer, String, Text, UniqueConstraint)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from utils.helpers import utcnow


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)  # Telegram ID
    username: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    full_name: Mapped[str] = mapped_column(String(256), default="")
    language: Mapped[str] = mapped_column(String(4), default="uz")
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)  # botni bloklamagan
    referrer_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"))
    pref_genres: Mapped[str] = mapped_column(String(256), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    last_active_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Genre(Base):
    __tablename__ = "genres"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_uz: Mapped[str] = mapped_column(String(64), unique=True)
    name_ru: Mapped[str] = mapped_column(String(64), default="")


class Movie(Base):
    __tablename__ = "movies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    kind: Mapped[str] = mapped_column(String(10), default="movie")  # movie | cartoon
    title: Mapped[str] = mapped_column(String(256))
    original_title: Mapped[Optional[str]] = mapped_column(String(256))
    search_key: Mapped[str] = mapped_column(String(600), default="", index=True)
    poster_file_id: Mapped[Optional[str]] = mapped_column(String(256))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    country: Mapped[Optional[str]] = mapped_column(String(128))
    genre_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("genres.id", ondelete="SET NULL"), index=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer)  # daqiqa
    age_limit: Mapped[Optional[str]] = mapped_column(String(16))
    imdb: Mapped[Optional[float]] = mapped_column(Float)
    description: Mapped[Optional[str]] = mapped_column(Text)
    video_file_id: Mapped[Optional[str]] = mapped_column(String(256))
    video_type: Mapped[str] = mapped_column(String(10), default="video")  # video | document
    watch_url: Mapped[Optional[str]] = mapped_column(String(512))
    trailer_url: Mapped[Optional[str]] = mapped_column(String(512))
    views: Mapped[int] = mapped_column(Integer, default=0)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (Index("ix_movies_kind_active", "kind", "is_active"),)


class Favorite(Base):
    __tablename__ = "favorites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[int] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint("user_id", "movie_id", name="uq_fav_user_movie"),)


class Series(Base):
    __tablename__ = "series"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    original_title: Mapped[Optional[str]] = mapped_column(String(256))
    search_key: Mapped[str] = mapped_column(String(600), default="", index=True)
    poster_file_id: Mapped[Optional[str]] = mapped_column(String(256))
    year: Mapped[Optional[int]] = mapped_column(Integer)
    country: Mapped[Optional[str]] = mapped_column(String(128))
    genre_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("genres.id", ondelete="SET NULL"))
    description: Mapped[Optional[str]] = mapped_column(Text)
    trailer_url: Mapped[Optional[str]] = mapped_column(String(512))
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Season(Base):
    __tablename__ = "seasons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    __table_args__ = (UniqueConstraint("series_id", "number", name="uq_season_series_number"),)


class Episode(Base):
    __tablename__ = "episodes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id", ondelete="CASCADE"), index=True)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), index=True)
    number: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    video_file_id: Mapped[Optional[str]] = mapped_column(String(256))
    video_type: Mapped[str] = mapped_column(String(10), default="video")
    watch_url: Mapped[Optional[str]] = mapped_column(String(512))
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint("season_id", "number", name="uq_episode_season_number"),)


class WatchHistory(Base):
    __tablename__ = "watch_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    movie_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"))
    episode_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"))
    times: Mapped[int] = mapped_column(Integer, default=1)
    first_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class MovieView(Base):
    """Har bir HAQIQIY ko'rish (30 daqiqalik dedupe bilan) — TOP statistika shu yerdan."""
    __tablename__ = "movie_views"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("movies.id", ondelete="CASCADE"))
    episode_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("episodes.id", ondelete="CASCADE"))
    viewed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (Index("ix_views_movie_time", "movie_id", "viewed_at"),
                      Index("ix_views_user_time", "user_id", "viewed_at"))


class MandatoryChannel(Base):
    __tablename__ = "mandatory_channels"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    title: Mapped[str] = mapped_column(String(256), default="")
    username: Mapped[Optional[str]] = mapped_column(String(64))
    invite_link: Mapped[Optional[str]] = mapped_column(String(256))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class VipSubscription(Base):
    __tablename__ = "vip_subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    source: Mapped[str] = mapped_column(String(16), default="admin")  # admin|promo|stars|referral


class PromoCode(Base):
    __tablename__ = "promo_codes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    vip_days: Mapped[int] = mapped_column(Integer, default=7)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PromoUsage(Base):
    __tablename__ = "promo_usages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    promo_id: Mapped[int] = mapped_column(Integer, ForeignKey("promo_codes.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    used_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    __table_args__ = (UniqueConstraint("promo_id", "user_id", name="uq_promo_user"),)


class Referral(Base):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    referred_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class MovieRequest(Base):
    __tablename__ = "movie_requests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(10), default="pending")  # pending|accepted|rejected
    handled_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class SupportMessage(Base):
    __tablename__ = "support_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    admin_reply: Mapped[Optional[str]] = mapped_column(Text)
    replied_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class Admin(Base):
    __tablename__ = "admins"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    role: Mapped[str] = mapped_column(String(12), default="moderator")  # admin | moderator
    added_by: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class BotSetting(Base):
    __tablename__ = "bot_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class CustomEmoji(Base):
    __tablename__ = "custom_emojis"
    key: Mapped[str] = mapped_column(String(32), primary_key=True)  # menyu kaliti
    emoji_id: Mapped[Optional[str]] = mapped_column(String(32))
    fallback: Mapped[str] = mapped_column(String(8), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
