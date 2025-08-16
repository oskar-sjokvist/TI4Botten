from sqlalchemy import ForeignKey, String, Integer
from sqlalchemy.orm import Mapped, relationship, mapped_column
from typing import Optional

from .. import models
from ..game import model as game_model


class GameBet(models.Base):
    __tablename__ = "game_bet"
    game_id: Mapped[int] = mapped_column(
        ForeignKey("game.game_id", ondelete="CASCADE"), primary_key=True
    )

    # One bet per game per bettor. Could relax this to allow hedging.
    player_id: Mapped[int] = mapped_column(
        ForeignKey("bettor.player_id"), primary_key=True
    )

    winner: Mapped[Optional[int]] = mapped_column(ForeignKey("player.player_id"))
    bet: Mapped[int] = mapped_column(Integer, default=0)

    bettor: Mapped["Bettor"] = relationship("Bettor", back_populates="game_bet")


class Bettor(models.Base):
    __tablename__ = "bettor"
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.player_id", ondelete="CASCADE"), primary_key=True
    )

    balance: Mapped[int] = mapped_column(Integer, default=1000)
    
    player: Mapped[game_model.Player] = relationship(
        "Player",
    )

    game_bet: Mapped["GameBet"] = relationship("GameBet", back_populates="bettor")