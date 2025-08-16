import logging

from . import ratinglogic

from discord.ext import commands
from sqlalchemy import Engine

from typing import Optional

class Rating(commands.Cog):
    """Cog containing rating related commands."""

    def __init__(self, engine: Engine) -> None:
        self.logic = ratinglogic.RatingLogic(engine)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Ratings cog loaded")

    @commands.command()
    async def stats(self, ctx: commands.Context, *, name: Optional[str]) -> None:
        """Returns stats for you."""
        if name:
            if id := self.logic.player_id_from_name(name):
                await ctx.send(self.logic.stats(id))
                return
            await ctx.send("Can't find anyone with that name")
        await ctx.send(self.logic.stats(ctx.author.id))

    @commands.command()
    async def wins(self, ctx: commands.Context) -> None:
        """Returns wins leaderboard."""
        await ctx.send(self.logic.wins())

    @commands.command()
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Returns ratings leaderboard."""
        await ctx.send(self.logic.ratings())
