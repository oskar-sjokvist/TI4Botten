import logging
import Levenshtein

from . import gamelogic
from . import factions

from typing import Optional
from discord.ext import commands
from sqlalchemy import Engine

class Game(commands.Cog):
    """Cog containing game related commands."""

    def __init__(self,  engine: Engine) -> None:
        """Initialize the Commands cog with factions."""
        self.factions = factions.read_factions()
        self.logic = gamelogic.GameLogic(engine)


    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Game cog loaded")


    @commands.command(name="factions")
    async def random_factions(self, ctx: commands.Context, number: int = 8, *, sources: str = "") -> None:
        """Returns a specified number of random factions."""
        if number <= 0:
            await ctx.send("Please specify a positive number of factions.")
            return

        random_factions = [str(faction) for faction in self.factions.get_random_factions(number, sources)]

        if not random_factions:
            await ctx.send("No factions found matching the criteria.")
            return
        await ctx.send(f"Here are {number} random factions:\n{'\n'.join(random_factions)}")

    @commands.command()
    async def faction(self, ctx: commands.Context, faction: str) -> None:
        """Returns info about the given faction."""
        best = max(self.factions.factions, key=lambda c: Levenshtein.ratio(faction, c.name))
        await ctx.send(str(best))


    @commands.command()
    async def finish(self, ctx: commands.Context, game_id: Optional[int] = None, *, points: Optional[str] = "") -> None:
        is_admin = ctx.author.guild_permissions.administrator
        await ctx.send(self.logic.finish(is_admin , game_id, points))

    @commands.command()
    async def ban(self, ctx: commands.Context, game_id: Optional[int] = None, *, faction: Optional[str] = None) -> None:
        """Ban a faction."""
        await ctx.send(await self.logic.ban(ctx.author.id, game_id, faction))

    @commands.command()
    async def draft(self, ctx: commands.Context, game_id: Optional[int] = None, *, faction: Optional[str] = None) -> None:
        """Draft your faction."""
        await ctx.send(await self.logic.draft(ctx, ctx.author.id, game_id, faction))

    @commands.command()
    async def start(self, ctx: commands.Context, game_id: Optional[int] = None) -> None:
        """Start the lobby."""
        await ctx.send(self.logic.start(self.factions, game_id))

    @commands.command()
    async def cancel(self, ctx: commands.Context, game_id: int) -> None:
        """Admin command to cancel the game or lobby."""
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("Only admins can cancel games")
            return 
        await ctx.send(self.logic.cancel(game_id))

    @commands.command()
    async def game(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        """Fetch game info"""
        await ctx.send(self.logic.game(game_id))

    @commands.command()
    async def games(self, ctx: commands.Context) -> None:
        """Fetches 5 latest games."""
        await ctx.send(self.logic.games(5))

    @commands.command()
    async def lobby(self, ctx: commands.Context, *, name: Optional[str]) -> None:
        """Create a lobby."""
        await ctx.send(self.logic.lobby(ctx.author.id, ctx.author.name, name))

    @commands.command()
    async def lobbies(self, ctx: commands.Context) -> None:
        """Show all open lobbies."""
        await ctx.send(self.logic.lobbies())
    

    @commands.command()
    async def leave(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        """Leave a lobby."""
        id = ctx.author.id
        await ctx.send(self.logic.leave(game_id, id))


    @commands.command()
    async def join(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        """Join a lobby."""
        id = ctx.author.id
        name = ctx.author.name
        await ctx.send(self.logic.join(game_id, id, name))

    @commands.command()
    async def config(self, ctx: commands.Context, game_id: Optional[int], property: Optional[str], value: Optional[str]) -> None:
        """Configure a lobby."""
        await ctx.send(self.logic.config(game_id, property, value))