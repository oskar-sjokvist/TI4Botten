import logging
from . import model as betting_model
from ..game import model as game_model

from sqlalchemy.orm import Session
from sqlalchemy import Engine, select

from typing import Optional


class BettingLogic:
    """Cog containing betting related commands."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    @staticmethod
    def _balance(session: Session, bettor: betting_model.Bettor) -> int:
        session.flush()
        stmt = select(betting_model.GameBet).filter_by(player_id=bettor.player_id)
        debts = session.execute(stmt).all()
        total_debt = sum([debt.bet for debt in debts])

        return bettor.balance - total_debt

    def balance(self, id: int, name) -> str:
        """Returns bettor's current balance."""
        with Session(self.engine) as session:
            bettor = session.get(betting_model.Bettor, id)
            if not bettor:
                player = session.get(game_model.Player, id)
                if not player:
                    player = game_model.Player(player_id=id, name=name)
                    session.add(player)
                bettor = betting_model.Bettor(player_id=id)
                session.add(bettor)
                session.commit()
            return f"{bettor.player.name} has {self._balance(session, bettor)} Jake coins."

    def payout(self, game_id: int) -> str:
        try:
            with Session(self.engine) as session:
                game = session.get(game_model.Game, game_id)
                if not game:
                    return "Game not found."
                if game.game_state != game_model.GameState.FINISHED:
                    return "Game is not yet finished! Can't pay anyone out."

                stmt = select(betting_model.GameBet).filter_by(game_id=game.game_id)
                bets = session.scalars(stmt).all()
                winner = (
                    session.query(game_model.GamePlayer)
                    .with_parent(game)
                    .order_by(game_model.GamePlayer.points.desc())
                    .first()
                )
                if not bets:
                    return "No bets placed"
                if winner is None:
                    return "Something went wrong"
                lines = []
                for game_bet in bets:
                    if game_bet.winner == winner.player_id:
                        bettor = game_bet.bettor
                        bettor.balance += game_bet.bet
                        lines.append(f"{bettor.player.name} won {game_bet.bet} Jake coins!")
                    else:
                        bettor.balance -= game_bet.bet
                        lines.append(f"{bettor.player.name} lost {game_bet.bet} Jake coins!")

                    session.merge(bettor)
                    session.delete(game_bet)

                session.commit()
                return "\n".join(lines)
        except Exception as e:
            logging.error(f"payout: {e}")
            return "Something went wrong"

    def bet(
        self,
        game_id: int,
        bet_amount: Optional[int],
        winner: Optional[str],
        id: int,
        name: str,
    ) -> str:
        """Places a bet on game_id, for bet amount on player id."""
        with Session(self.engine) as session:
            bettor = session.get(betting_model.Bettor, id)
            if not bettor:
                player = session.get(game_model.Player, id)
                if not player:
                    player = game_model.Player(player_id=id, name=name)
                    session.add(player)
                bettor = betting_model.Bettor(player_id=id)
                session.add(bettor)
            session.commit()

            game = session.get(game_model.Game, game_id)
            if not game:
                return "Game not found."

            if bet_amount is None and winner is None:
                bets = session.scalars(select(betting_model.GameBet).filter_by(game_id=game.game_id)).all()
                lines = []
                for game_bet in bets:
                    predicted_winner = session.get(
                        game_model.Player, game_bet.winner
                    )
                    if not predicted_winner:
                        return "Something went wrong"
                    lines.append(
                        f"{bettor.player.name} bets {game_bet.bet} Jake coins on {predicted_winner.name} to win the game."
                    )
                if lines:
                    return "\n".join(lines)

            if game.game_state != game_model.GameState.DRAFT:
                return "You can only place bets on games in draft state"

            existing_bet = session.get(
                betting_model.GameBet, (game_id, bettor.player_id)
            )

            if existing_bet:
                predicted_winner = session.get(game_model.Player, existing_bet.winner)
                if not predicted_winner:
                    return "Something went wrong."
                return f"You have a bet placed on {predicted_winner.name} for {existing_bet.bet} Jake coins to win this game."

            if not bet_amount:
                return "Place a bet amount."

            if not winner:
                return "Choose a winner."

            if bet_amount > self._balance(session, bettor):
                return "You are trying to bet more than you have."

            if bet_amount <= 0:
                return "Nice try"

            stmt = select(game_model.GamePlayer).filter_by(game_id=game.game_id)
            players = session.scalars(stmt).all()
            for player in players:
                if winner == player.player.name:
                    gm = betting_model.GameBet(
                        game_id=game.game_id,
                        player_id=bettor.player_id,
                        winner=player.player_id,
                        bet=bet_amount,
                    )
                    session.add(gm)
                    session.merge(bettor)
                    session.commit()
                    return f"You placed a bet on {player.player.name} for {gm.bet} Jake coins to win this game."
                    
            return "Player not found."
