import logging

from . import ratinglogic

from discord.ext import commands
from sqlalchemy import Engine

from ..typing import *
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
        id = ctx.author.id
        if name:
            id = self.logic.player_id_from_name(name)
            if not id:
                await ctx.send("Can't find anyone with that name")
                return

        match self.logic.stats(id):
            case Ok(s):
                await ctx.send(embed=s.card_view())
            case Err(s):
                await ctx.send(s)

    @commands.command()
    async def wins(self, ctx: commands.Context) -> None:
        """Returns wins leaderboard."""
        await ctx.send(self.logic.wins())

    @commands.command()
    async def leaderboard(self, ctx: commands.Context) -> None:
        """Returns ratings leaderboard."""
        await ctx.send(self.logic.ratings())

    @commands.command()
    async def picture(self, ctx: commands.Context, *, url: str) -> None:
        """Set a profile picture using an https url."""
        await ctx.send(self.logic.set_pic(ctx.author.id, url))

    @commands.command()
    async def description(self, ctx: commands.Context, *, description: str) -> None:
        """Set a profile description."""
        await ctx.send(self.logic.set_description(ctx.author.id, description))
