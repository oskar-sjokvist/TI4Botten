import logging

from . import ratinglogic

from discord.ext import commands
from sqlalchemy import Engine

from typing import Optional

class Rating(commands.Cog):
    """Cog containing rating related commands."""

    def __init__(self,  engine: Engine) -> None:
        self.logic = ratinglogic.RatingLogic(engine)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Ratings cog loaded")

    @commands.command()
    async def stats(self, ctx: commands.Context) -> None:
        """Returns everyone's stats."""
        await ctx.send(self.logic.ratings())
