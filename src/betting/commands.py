import logging

from . import model as betting_model
from ..game import model as game_model
from ..game import controller as game_controller

from sqlalchemy.orm import Session
from discord.ext import commands
from sqlalchemy import Engine, select

from typing import Optional

class Betting(commands.Cog):
    """Cog containing betting related commands."""

    def __init__(self,  engine: Engine) -> None:
        self.engine = engine

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Betting cog loaded")


    @commands.command()
    async def balance(self, ctx: commands.Context) -> None:
        """Returns bettor's current balance."""
        with Session(self.engine) as session:
            bettor = session.get(betting_model.Bettor, ctx.author.id)
            if not bettor:
                bettor = betting_model.Bettor(bettor_id=ctx.author.id, name=ctx.author.name)
                session.add(bettor)
            session.commit()
            await ctx.send(f"{bettor.name} has {bettor.balance} Jake coins.")

    @commands.command()
    async def payout(self, ctx: commands.Context, game_id: int) -> None:
        with Session(self.engine) as session:
            game = session.get(game_model.Game, game_id)
            if not game:
                await ctx.send("Game not found.")
                return
            if game.game_state != game_model.GameState.FINISHED:
                await ctx.send("Game is not yet finished! Can't pay anyone out.")
                return

            stmt = select(betting_model.GameBettor).filter_by(game_id=game.game_id)
            bettors = session.execute(stmt).scalars().all()
            winner = game_controller.winner(session, game)
            lines = []
            for game_bettor in bettors:
                if game_bettor.winner == winner.player_id:
                    bettor = session.get(betting_model.Bettor, game_bettor.bettor_id)
                    if bettor is None:
                        await ctx.send("Something went wrong")
                        return
                    bettor.balance += game_bettor.bet * 2
                    lines.append(f"{bettor.name} won {game_bettor.bet} Jake coins!")
                    session.merge(bettor)
                else:
                    lines.append(f"{bettor.name} lost {game_bettor.bet} Jake coins!")
                    
                session.delete(game_bettor)

            session.commit()
            await ctx.send("\n".join(lines))
            

    @commands.command()
    async def bet(self, ctx: commands.Context, game_id: int, bet_amount: Optional[int], winner: Optional[str]) -> None:
        """Places a bet on game_id, for bet amount on player id."""
        with Session(self.engine) as session:
            bettor = session.get(betting_model.Bettor, ctx.author.id)
            if not bettor:
                bettor = betting_model.Bettor(bettor_id=ctx.author.id, name=ctx.author.name)
                session.add(bettor)
            session.commit()

            game = session.get(game_model.Game, game_id)
            if not game:
                await ctx.send("Game not found.")
                return

            if bet_amount is None and winner is None:
                stmt = select(betting_model.GameBettor).filter_by(game_id=game.game_id)
                bettors = session.execute(stmt).scalars().all()
                lines = []
                for game_bettor in bettors:
                    predicted_winner = session.get(game_model.Player, game_bettor.winner)
                    if not predicted_winner:
                        await ctx.send("Something went wrong")
                        return
                    lines.append(f"{player.name} bets {game_bettor.bet} Jake coins on {predicted_winner.name} to win the game.")
                if lines:
                    await ctx.send("\n".join(lines))
                    return

            if game.game_state != game_model.GameState.DRAFT:
                await ctx.send("You can only place bets on games in draft state")
                return

            existing_bet = session.get(betting_model.GameBettor, (game_id, bettor.player_id))
            if existing_bet:
                await ctx.send(f"You have a bet placed on {existing_bet.winner} for {existing_bet.bet} Jake coins to win game {game.name} #{game.game_id}")
                return

            if not bet_amount:
                await ctx.send("Place a bet amount.")
                return

            if not winner:
                await ctx.send("Choose a winner.")
                return

            if bet_amount > bettor.balance:
                await ctx.send("You are trying to bet more than you have.")
                return

            if bet_amount <= 0:
                await ctx.send("Nice try")
                return

            stmt = select(game_model.GamePlayer).filter_by(game_id=game.game_id)
            players = session.execute(stmt).scalars().all()
            for player in players:
                if winner == player.player.name:
                    gm = betting_model.GameBettor(
                        game_id=game.game_id,
                        player_id=bettor.player_id,
                        winner=player.player_id,
                        bet=bet_amount,
                    )
                    session.add(gm)
                    bettor.balance -= bet_amount
                    session.merge(bettor)
                    session.commit()
                    await ctx.send(f"You placed a bet on {player.player.name} for {gm.bet} Jake coins to win game {game.name} #{game.game_id}")
                    return


            


