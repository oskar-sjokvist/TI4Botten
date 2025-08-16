from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Float, String, Integer
from sqlalchemy.orm import Mapped, relationship, mapped_column

from .. import models
from ..game import model as game_model


# Bookkeeping table.
class OutcomeLedger(models.Base):
    __tablename__ = "outcome_ledger"
    game_id: Mapped[int] = mapped_column(
        ForeignKey("game.game_id", ondelete="CASCADE"), primary_key=True
    )
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.player_id", ondelete="CASCADE"), primary_key=True
    )

    match_time: Mapped[datetime] = mapped_column(DateTime)

    rating_before: Mapped[int] = mapped_column(Integer)
    rating_after: Mapped[int] = mapped_column(Integer)
    rating_delta: Mapped[int] = mapped_column(Integer)

class MatchPlayer(models.Base):
    __tablename__ = "match_player"
    player_id: Mapped[int] = mapped_column(
        ForeignKey("player.player_id", ondelete="CASCADE"), primary_key=True
    )

    rating: Mapped[float] = mapped_column(Float, default=1500)
    thumbnail_url: Mapped[str] = mapped_column(String, default="")
    description: Mapped[str] = mapped_column(String, default="")
    
    player: Mapped[game_model.Player] = relationship(
        "Player",
    )
    


class WinnerHeadToHead(models.Base):
    __tablename__ = "winner_head_to_head"
    game_id: Mapped[int] = mapped_column(
        ForeignKey("game.game_id", ondelete="CASCADE"), primary_key=True
    )

    winner_id: Mapped[int] = mapped_column(
        ForeignKey("match_player.player_id", ondelete="CASCADE"), primary_key=True
    )
    loser_id: Mapped[int] = mapped_column(
        ForeignKey("match_player.player_id", ondelete="CASCADE"), primary_key=True
    )

    winner: Mapped[MatchPlayer] = relationship(
        "MatchPlayer",
        foreign_keys=[winner_id],
    )
    player_high = relationship(
        "MatchPlayer",
        foreign_keys=[loser_id],
    )
