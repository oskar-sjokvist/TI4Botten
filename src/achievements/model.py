from __future__ import annotations
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, String, Integer, func, JSON, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, relationship, mapped_column

from .. import models

class Achievement(models.Base):
    __tablename__ = "achievement"

    achievement_id: Mapped[str] = mapped_column(String, primary_key=True)
    key: Mapped[str] = mapped_column(String, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    rule_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    active_from: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    active_to: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    __table_args__ = (
        UniqueConstraint("key", "version", name="uq_achievements_key_version"),
    )

    player_unlocks: Mapped[list["PlayerAchievement"]] = relationship(back_populates="achievement")

class PlayerAchievement(models.Base):
    __tablename__ = "player_achievement"

    player_id: Mapped[int] = mapped_column("player.player_id", primary_key=True)
    achievement_id: Mapped[str] = mapped_column(
        String(26), ForeignKey("achievement.achievement_id"), primary_key=True
    )
    unlocked_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    awarded_by: Mapped[str] = mapped_column(String, nullable=True)

    achievement: Mapped[Achievement] = relationship(back_populates="player_unlocks")

class PlayerProgress(models.Base):
    __tablename__ = "player_progress"

    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    counter_key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
