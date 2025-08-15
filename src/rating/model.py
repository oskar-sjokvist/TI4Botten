from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Enum, Float, String, Integer
from sqlalchemy.orm import Mapped, mapped_column

from .. import models


# Bookkeeping table.
class OutcomeLedger(models.Base):
    __tablename__ = "outcome_ledger"
    game_id: Mapped[int] = mapped_column(
        ForeignKey("game.game_id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.player_id"), primary_key=True
    )

    match_time: Mapped[datetime] = mapped_column(DateTime)

    rating_before: Mapped[int] = mapped_column(Integer)
    rating_after: Mapped[int] = mapped_column(Integer)
    rating_delta: Mapped[int] = mapped_column(Integer)


class MatchPlayer(models.Base):
    __tablename__ = "match_player"
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.player_id"), primary_key=True
    )

    name: Mapped[str] = mapped_column(String)

    rating: Mapped[float] = mapped_column(Float, default=1500)
