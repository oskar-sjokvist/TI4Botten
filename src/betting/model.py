from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from .. import models


class GameBettor(models.Base):
    __tablename__ = "game_bettor"
    game_id: Mapped[int]  = mapped_column(ForeignKey("game.game_id", ondelete="CASCADE"), primary_key=True)

    # One bet per game per bettor. Could relax this to allow hedging.
    bettor_id: Mapped[int] = mapped_column(ForeignKey("bettor.bettor_id"), primary_key=True)

    winner: Mapped[Optional[int]] = mapped_column(ForeignKey("player.player_id"))
    bet: Mapped[int] = mapped_column(Integer, default=0)


class Bettor(models.Base):
    __tablename__ = "bettor"
    bettor_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[int] = mapped_column(String)

    balance: Mapped[int] = mapped_column(Integer, default=1000)

