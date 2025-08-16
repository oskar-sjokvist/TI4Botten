import logging

from . import bettinglogic

from discord.ext import commands
from sqlalchemy import Engine

from typing import Optional


class Betting(commands.Cog):
    """Cog containing betting related commands."""

    def __init__(self, engine: Engine) -> None:
        self.logic = bettinglogic.BettingLogic(engine)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Betting cog loaded")

    @commands.command()
    async def balance(self, ctx: commands.Context) -> None:
        """Returns bettor's current balance."""
        await ctx.send(self.logic.balance(ctx.author.id, ctx.author.name))

    @commands.command()
    async def payout(self, ctx: commands.Context) -> None:
        hej = self.logic.payout(ctx.channel.id)
        print(hej)

    @commands.command()
    async def bet(
        self, ctx: commands.Context, bet_amount: Optional[int], winner: Optional[str]
    ) -> None:
        """Places a bet for bet amount on player. Usage !bet {amount} {player}"""
        await ctx.send(
            self.logic.bet(
                ctx.channel.id, bet_amount, winner, ctx.author.id, ctx.author.name
            )
        )
