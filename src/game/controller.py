from sqlalchemy import select
from sqlalchemy.orm import Session, with_parent

from .model import Game, GamePlayer

from typing import List


class GameController:

    def players_ordered_by_turn(
        self, session: Session, game: Game
    ) -> List[GamePlayer]:
        return (
            session.query(GamePlayer)
            .with_parent(game)
            .order_by(GamePlayer.turn_order.asc())
            .all()
        )


    def current_drafter(self, session: Session, game: Game) -> GamePlayer:
        current_drafter = session.execute(
            select(GamePlayer)
            .where(with_parent(game, Game.game_players))
            .filter_by(turn_order=game.turn)
        ).scalar()
        if current_drafter is None:
            raise LookupError("Current drafter not found for this game!")
        return current_drafter

    def players_ordered_by_points(
        self, session: Session, game: Game
    ) -> List[GamePlayer]:
        return (
            session.query(GamePlayer)
            .with_parent(game)
            .order_by(GamePlayer.points.desc())
            .all()
        )

    # Assumes only one winner
    def winner(self, session: Session, game: Game) -> GamePlayer:
        winner = session.execute(
            select(GamePlayer)
            .where(with_parent(game, Game.game_players))
            .order_by(GamePlayer.points.desc())
        ).scalar()
       
        if winner is None:
            raise LookupError("Winner not found for this game!")
        return winner