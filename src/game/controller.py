from sqlalchemy.orm import Session

from . import model


class GameController:

    def current_drafter(self, session : Session, game : model.Game) -> model.GamePlayer:
        current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()
        if current_drafter is None:
            raise LookupError("Current drafter not found for this game!")
        return current_drafter

