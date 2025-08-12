from sqlalchemy.orm import Session
from typing import List

from . import model

def players_ordered_by_turn(session : Session, game : model.Game) -> List[model.GamePlayer]:
    return session.query(model.GamePlayer).with_parent(game).order_by(model.GamePlayer.turn_order.asc()).all()


def current_drafter(session : Session, game : model.Game) -> model.GamePlayer:
    current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()
    if current_drafter is None:
        raise LookupError("Current drafter not found for this game!")
    return current_drafter

