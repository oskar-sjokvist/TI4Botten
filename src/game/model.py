import enum

from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, Integer, String, Enum, Boolean, JSON
from sqlalchemy.orm import Mapped, relationship, mapped_column
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
    PICKS_ONLY = "PICKS_ONLY"
    PICKS_AND_BANS = "PICKS_AND_BANS"
    EXCLUSIVE_POOL = "EXCLUSIVE_POOL"
    HOMEBREW_DRAFT = "HOMEBREW_DRAFT"


class GamePlayer(models.Base):
    __tablename__ = "game_player"
    game_id: Mapped[int] = mapped_column(ForeignKey("game.game_id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.player_id"), primary_key=True
    )
    faction: Mapped[Optional[str]] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer, default=0)
    turn_order: Mapped[int] = mapped_column(Integer, default=0)

    # Used in exclusive pool mode and Homebrew draft
    factions: Mapped[List[str]] = mapped_column(JSON, default=[])

    # Used in Homebrew draft
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

class GameSettings(models.Base):
    __tablename__ = "game_settings"
    game_id: Mapped[int] = mapped_column(ForeignKey("game.game_id"), primary_key=True)

    drafting_mode: Mapped[DraftingMode] = mapped_column(
        "drafting_mode", Enum(DraftingMode), default=DraftingMode.EXCLUSIVE_POOL
    )

    base_game_factions: Mapped[bool] = mapped_column(Boolean, default=True)
    prophecy_of_kings_factions: Mapped[bool] = mapped_column(Boolean, default=True)
    codex_factions: Mapped[bool] = mapped_column(Boolean, default=True)
    discordant_stars_factions: Mapped[bool] = mapped_column(Boolean, default=True)

    factions_per_player: Mapped[int] = mapped_column(Integer, default=4)
    bans_per_player: Mapped[int] = mapped_column(Integer, default=1)

    game: Mapped["Game"] = relationship("Game", back_populates="game_settings")


class SettingsPoll(models.Base):
    __tablename__ = "settings_poll"
    game_id: Mapped[int] = mapped_column(ForeignKey("game.game_id", ondelete="CASCADE"), primary_key=True)
    message_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    thread_id: Mapped[int] = mapped_column(Integer, primary_key=True)


class Player(models.Base):
    __tablename__ = "player"
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)

    game_players: Mapped[List["GamePlayer"]] = relationship(
        "GamePlayer", back_populates="player"
    )
