from sqlalchemy import select
from sqlalchemy.orm import Session, with_parent

from .model import Game, GamePlayer

from typing import Sequence


class GameController:

    def player_from_game(self, session: Session, game:Game, player_id: int) -> GamePlayer|None:
        return session.scalar(
            select(GamePlayer)
            .where(
                with_parent(game, Game.game_players),
                GamePlayer.player_id==player_id,
            )
        )

    def players_ordered_by_turn(
        self, session: Session, game: Game
    ) -> Sequence[GamePlayer]:
        return session.scalars(
            select(GamePlayer)
            .where(with_parent(game, Game.game_players))
            .order_by(GamePlayer.turn_order.asc())
        ).all()


    def current_drafter(self, session: Session, game: Game) -> GamePlayer:
        current_drafter = session.scalar(
            select(GamePlayer)
            .where(
                with_parent(game, Game.game_players),
                GamePlayer.turn_order == game.turn,
            )
        )
        if current_drafter is None:
            raise LookupError("Current drafter not found for this game!")
        return current_drafter

    def players_ordered_by_points(
        self, session: Session, game: Game
    ) -> Sequence[GamePlayer]:
        return session.scalars(
            select(GamePlayer)
            .where(with_parent(game, Game.game_players))
            .order_by(GamePlayer.points.desc())
        ).all()

    # Assumes only one winner
    def winner(self, session: Session, game: Game) -> GamePlayer:
        winner = session.scalar(
            select(GamePlayer)
            .where(with_parent(game, Game.game_players))
            .order_by(GamePlayer.points.desc())
        )
       
        if winner is None:
            raise LookupError("Winner not found for this game!")
        return winner