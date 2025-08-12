
from sqlalchemy import ForeignKey, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, Mapped, mapped_column

from .. import models


Base = declarative_base()

class MessageBox(models.Base):
    __tablename__ = "messagebox"
    
    game_id: Mapped[int]  = mapped_column(ForeignKey("game.game_id"), primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("player.player_id"), primary_key=True)
    win_message = mapped_column(String)
    lose_message = mapped_column(String)
