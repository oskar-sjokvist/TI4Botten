import enum

from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, create_engine, Integer, String, Enum, Boolean, JSON
from sqlalchemy.orm import Mapped, relationship, Mapped, DeclarativeBase, mapped_column, Session
from sqlalchemy.sql import func
from typing import Optional, List

class Base(DeclarativeBase):
    pass

class GameState(enum.Enum):
    LOBBY = "Lobby"
    DRAFT = "Draft"
    STARTED = "Started"
    FINISHED = "Finished"

class DraftingMode(enum.Enum):
    PICKS_ONLY = "Picks only"
    PICKS_AND_BANS = "Picks and bans"
    EXCLUSIVE_POOL = "Exclusive drafting pool"

class GamePlayer(Base):
    __tablename__ = "game_player"
    game_id: Mapped[int]  = mapped_column(ForeignKey("game.game_id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.player_id"), primary_key=True)
    faction: Mapped[Optional[str]] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int] = mapped_column(Integer, default=0)
    turn_order: Mapped[int] = mapped_column(Integer, default=0)

    # Used in exclusive pool mode.
    factions: Mapped[List[str]] = mapped_column(JSON, default=[])

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="game_players")
    player: Mapped["Player"] = relationship("Player", back_populates="game_players")


class Game(Base):
    __tablename__ = "game"
    game_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_state: Mapped[GameState] = mapped_column("type", Enum(GameState))
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())
    factions: Mapped[List[str]] = mapped_column(JSON, default=[])
    turn: Mapped[int] = mapped_column(Integer, default=0)

    game_players: Mapped[List["GamePlayer"]] = relationship("GamePlayer", back_populates="game")
    game_settings: Mapped["GameSettings"] = relationship("GameSettings", back_populates="game")

    @classmethod
    def latest_lobby(cls, session: Session):
        return session.query(cls).order_by(cls.game_id.desc()).filter(cls.game_state==GameState.LOBBY).first()



class GameSettings(Base):
    __tablename__ = "game_settings"
    game_settings_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[int]  = mapped_column(ForeignKey("game.game_id"))
    
    drafting_mode: Mapped[DraftingMode] = mapped_column("type", Enum(DraftingMode), default=DraftingMode.EXCLUSIVE_POOL)

    prophecy_of_kings: Mapped[bool] = mapped_column(Boolean, default=True)
    codex: Mapped[bool] = mapped_column(Boolean, default=True)
    discordant_stars: Mapped[bool] = mapped_column(Boolean, default=False)

    game: Mapped["Game"] = relationship("Game", back_populates="game_settings")

class Player(Base):
    __tablename__ = "player"
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)

    game_players: Mapped[List["GamePlayer"]] = relationship("GamePlayer", back_populates="player")

def get_engine():
    engine = create_engine('sqlite:///app.db', echo=True)
    Base.metadata.create_all(engine)
    return engine
