from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from .. import models


class GameBettor(models.Base):
    __tablename__ = "game_player"
    game_id: Mapped[int]  = mapped_column(ForeignKey("game.game_id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.player_id"), primary_key=True)

    winner: Mapped[Optional[int]] = mapped_column(ForeignKey("player.player_id"))
    bet: Mapped[int] = mapped_column(Integer, default=0)

class Bettor(models.Base):
    __tablename__ = "bettor"
    player_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    balance: Mapped[int] = mapped_column(Integer, default=1000)

