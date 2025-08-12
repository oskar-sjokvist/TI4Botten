from . import model
from sqlalchemy.orm import Session
from typing import List

def players_ordered_by_turn(session : Session, game : model.Game) -> List[model.GamePlayer]:
    return session.query(model.GamePlayer).with_parent(game).order_by(model.GamePlayer.turn_order.asc()).all()
