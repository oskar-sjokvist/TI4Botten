import enum

from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Integer, String, Enum, Boolean, JSON
from sqlalchemy.orm import Mapped, relationship, Mapped, mapped_column, Session
from sqlalchemy.sql import func
from typing import Optional, List

from .. import models


class GameState(enum.Enum):
    LOBBY = "Lobby"
    BAN = "Ban"
    DRAFT = "Draft"
    STARTED = "Started"
    FINISHED = "Finished"


class DraftingMode(enum.Enum):
    PICKS_ONLY = "Picks only"
    PICKS_AND_BANS = "Picks and bans"
    EXCLUSIVE_POOL = "Exclusive drafting pool"
    MILTY_DRAFT = "Milty draft"


class GamePlayer(models.Base):
    __tablename__ = "game_player"
    game_id: Mapped[int] = mapped_column(ForeignKey("game.game_id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.player_id"), primary_key=True
    )
    faction: Mapped[Optional[str]] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer, default=0)
    turn_order: Mapped[int] = mapped_column(Integer, default=0)

    # Used in exclusive pool mode and Milty draft
    factions: Mapped[List[str]] = mapped_column(JSON, default=[])

    # Used in Milty draft
    position: Mapped[Optional[int]] = mapped_column(Integer)
    strategy_card: Mapped[Optional[str]] = mapped_column(String)

    # Used in picks and bans
    bans: Mapped[Optional[List[str]]] = mapped_column(JSON, default=[])

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="game_players")
    player: Mapped["Player"] = relationship("Player", back_populates="game_players")


class Game(models.Base):
    __tablename__ = "game"
    game_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_state: Mapped[GameState] = mapped_column("game_state", Enum(GameState))
    name: Mapped[str] = mapped_column("name")

    lobby_create_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )
    game_finish_time: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp()
    )

    turn: Mapped[int] = mapped_column(Integer, default=0)

    game_players: Mapped[List["GamePlayer"]] = relationship(
        "GamePlayer", back_populates="game", cascade="all"
    )
    game_settings: Mapped["GameSettings"] = relationship(
        "GameSettings", back_populates="game", cascade="all"
    )

    @classmethod
    def latest_lobby(cls, session: Session):
        return (
            session.query(cls)
            .order_by(cls.game_id.desc())
            .filter(cls.game_state == GameState.LOBBY)
            .first()
        )

    @classmethod
    def latest_ban(cls, session: Session):
        return (
            session.query(cls)
            .order_by(cls.game_id.desc())
            .filter(cls.game_state == GameState.BAN)
            .first()
        )

    @classmethod
    def latest_draft(cls, session: Session):
        return (
            session.query(cls)
            .order_by(cls.game_id.desc())
            .filter(cls.game_state == GameState.DRAFT)
            .first()
        )


class GameSettings(models.Base):
    __tablename__ = "game_settings"
    game_id: Mapped[int] = mapped_column(ForeignKey("game.game_id"), primary_key=True)

    drafting_mode: Mapped[DraftingMode] = mapped_column(
        "drafting_mode", Enum(DraftingMode), default=DraftingMode.EXCLUSIVE_POOL
    )

    base_game: Mapped[bool] = mapped_column(Boolean, default=True)
    prophecy_of_kings: Mapped[bool] = mapped_column(Boolean, default=True)
    codex: Mapped[bool] = mapped_column(Boolean, default=True)
    discordant_stars: Mapped[bool] = mapped_column(Boolean, default=True)

    factions_per_player: Mapped[int] = mapped_column(Integer, default=4)
    bans_per_player: Mapped[int] = mapped_column(Integer, default=2)

    game: Mapped["Game"] = relationship("Game", back_populates="game_settings")


class Player(models.Base):
    __tablename__ = "player"
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)

    game_players: Mapped[List["GamePlayer"]] = relationship(
        "GamePlayer", back_populates="player"
    )
