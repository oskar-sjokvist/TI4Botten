from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class GamePlayer(Base):
    __tablename__ = "game_player"
    game_id = Column(Integer, ForeignKey("game.game_id"), primary_key=True)
    player_id = Column(Integer, ForeignKey("player.player_id"), primary_key=True)
    faction = Column(String)
    points = Column(Integer)
    rank = Column(Integer)

    # Relationships
    game = relationship("Game", back_populates="game_players")
    player = relationship("Player", back_populates="game_players")


class Game(Base):
    __tablename__ = "game"
    game_id = Column(Integer, primary_key=True, autoincrement=True)
    game_state = Column(String)
    timestamp = Column(DateTime, server_default=func.current_timestamp())
    game_players = relationship("GamePlayer", back_populates="game")

class Player(Base):
    __tablename__ = "player"
    player_id = Column(Integer, primary_key=True)
    game_players = relationship("GamePlayer", back_populates="player")

def get_engine():
    engine = create_engine('sqlite://app.db', echo=True)
    Base.metadata.create_all(engine)
    return engine
