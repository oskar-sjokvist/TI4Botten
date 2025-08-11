import enum

from datetime import datetime
from sqlalchemy import ForeignKey, DateTime, create_engine, Integer, String, Enum
from sqlalchemy.orm import Mapped, relationship, Mapped, DeclarativeBase, mapped_column
from sqlalchemy.sql import func
from typing import Optional, List

class Base(DeclarativeBase):
    pass

class GameState(enum.Enum):
    LOBBY = "Lobby"
    DRAFT = "Draft"
    STARTED = "Started"
    FINISHED = "Finished"

class GamePlayer(Base):
    __tablename__ = "game_player"
    game_id: Mapped[int]  = mapped_column(Integer, ForeignKey("game.game_id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("player.player_id"), primary_key=True)
    faction: Mapped[Optional[str]] = mapped_column(String)
    points: Mapped[int] = mapped_column(Integer, default=0)
    rank: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    game: Mapped["Game"] = relationship("Game", back_populates="game_players")
    player: Mapped["Player"] = relationship("Player", back_populates="game_players")


class Game(Base):
    __tablename__ = "game"
    game_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_state: Mapped[GameState] = mapped_column("type", Enum(GameState))
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp())

    game_players: Mapped[List["GamePlayer"]] = relationship("GamePlayer", back_populates="game")

class Player(Base):
    __tablename__ = "player"
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)

    game_players: Mapped[List["GamePlayer"]] = relationship("GamePlayer", back_populates="player")

def get_engine():
    engine = create_engine('sqlite:///app.db', echo=True)
    Base.metadata.create_all(engine)
    return engine
