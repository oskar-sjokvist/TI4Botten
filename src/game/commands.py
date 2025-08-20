import logging
from unittest import case
import Levenshtein
import discord

from . import gamelogic
from . import factions
from . import strategy_cards
from . import board
from ..typing import *

from discord.ext import commands
from typing import Optional
from discord.ext import commands
from sqlalchemy import Engine

class Game(commands.Cog):
    """Cog containing game related commands."""

    def __init__(
        self,
        bot: commands.Bot,
        engine: Engine,
    ) -> None:
        """Initialize the Commands cog with factions."""
        self.factions = factions.read_factions()
        self.strategy_cards = strategy_cards.read_strategy_cards()
        self.logic = gamelogic.GameLogic(bot, engine)
        self.planets = board.read_planets()


    async def __send_embed_or_pretty_err(self, ctx: commands.Context, result: Result[discord.Embed]) -> None:
        match result:
            case Ok(embed):
                await ctx.send(embed=embed) 
            case Err(s):
                embed = discord.Embed(
                    title="❌ Error",
                    description=s,
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Game cog loaded")

    def __game_id(self, ctx: commands.Context):
        # Let's use the channel ID for the game ID.
        return ctx.channel.id

    @commands.command(name="strategy-cards")
    async def strat_cards(
        self, ctx: commands.Context) -> None:
        """Returns the list of strategy cards in the game."""

        await ctx.send(
            f"{'\n'.join([str(sc) for sc in self.strategy_cards])}"
        )

    @commands.command(name="planets")
    async def list_planets(
        self, ctx: commands.Context) -> None:
        """Returns the list of planets in the game."""

        await ctx.send(
            f"{'\n'.join([f"{planet.source}: {str(planet)}" for planet in self.planets])}"
        )
    @commands.command(name="factions")
    async def random_factions(
        self, ctx: commands.Context, number: int = 8, *, sources: str = ""
    ) -> None:
        """Returns a specified number of random factions."""
        if number <= 0:
            await ctx.send("Please specify a positive number of factions.")
            return

        random_factions = [
            str(faction)
            for faction in self.factions.get_random_factions(number, sources)
        ]

        if not random_factions:
            await ctx.send("No factions found matching the criteria.")
            return
        await ctx.send(
            f"Here are {number} random factions:\n{'\n'.join(random_factions)}"
        )

    @commands.command()
    async def faction(self, ctx: commands.Context, faction: str) -> None:
        """Returns info about the given faction."""
        best = max(
            self.factions.factions, key=lambda c: Levenshtein.ratio(faction, c.name)
        )
        await ctx.send(str(best))

    def __string_from_string_result(self, s: Result[str]) -> str:
        match s:
            case Ok(a):
                return a
            case Err(b):
                return b

    @commands.command()
    async def finish(
        self, ctx: commands.Context, *, points: Optional[str] = ""
    ) -> None:
        """Finish the game. Usage !finish {list_of_points} where the order is the turn order of the players."""
        is_admin = ctx.author.guild_permissions.administrator
        await self.__send_embed_or_pretty_err(ctx, self.logic.finish(is_admin, self.__game_id(ctx), points))

    @commands.command()
    async def ban(
        self, ctx: commands.Context, *, faction: Optional[str] = None
    ) -> None:
        """Ban a faction."""
        await ctx.send(
            await self.logic.ban(ctx.author.id, self.__game_id(ctx), faction)
        )

    @commands.command()
    async def draft(
        self, ctx: commands.Context, *, faction: Optional[str] = None
    ) -> None:
        """Draft your faction."""
        await self.__send_embed_or_pretty_err(ctx, await self.logic.draft(ctx.author.id, self.__game_id(ctx), faction))

    @commands.command()
    async def start(self, ctx: commands.Context) -> None:
        """Start the lobby."""
        await self.__send_embed_or_pretty_err(ctx, self.logic.start(self.factions, self.__game_id(ctx)))

    @commands.command()
    async def cancel(self, ctx: commands.Context) -> None:
        """Admin command to cancel the game or lobby."""
        match ctx.author:
            case discord.Member():
                if not ctx.author.guild_permissions.administrator:
                    await ctx.send("Only admins can cancel games")
            case _:
                return

        match self.logic.cancel(self.__game_id(ctx)):
            case Ok(s):
                match ctx.channel:
                    case discord.TextChannel():
                        await ctx.channel.delete()
            case Err(s):
                await ctx.send(s)

    @commands.command()
    async def info(self, ctx: commands.Context, *, game_name: Optional[str]) -> None:
        """Fetch game info"""
        if not game_name:
            game_id = self.__game_id(ctx)
            await self.__send_embed_or_pretty_err(ctx, self.logic.game(game_id))
            return
        await self.__send_embed_or_pretty_err(ctx, self.logic.game_from_name(game_name))
        
        

    @commands.command()
    async def games(self, ctx: commands.Context) -> None:
        """Fetches latest games."""
        match self.logic.games():
            case Ok(paginated):
                await paginated.view_menu(ctx).start()
            case Err(s):
                await ctx.send(s)

    @commands.command()
    async def lobby(self, ctx: commands.Context, *, name: Optional[str]) -> None:
        """Create a lobby."""
        if not ctx.guild:
            embed = discord.Embed(
                title="❌ Error",
                description="This is a server command",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        if not name:
            embed = discord.Embed(
                title="❌ Error",
                description="Specify a lobby name",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        channel = await ctx.guild.create_text_channel(name)
        match await self.logic.lobby(channel, channel.id, ctx.author.id, ctx.author.name, name):
            case Ok(s):
                await channel.send(embed=s)
                await ctx.send(f"Created {channel.mention} for TI4 Lobby")
            case Err(s):
                await ctx.send(s)

    @commands.command()
    async def lobbies(self, ctx: commands.Context) -> None:
        """Show all open lobbies."""
        await ctx.send(self.__string_from_string_result(self.logic.lobbies()))

    @commands.command()
    async def leave(self, ctx: commands.Context) -> None:
        """Leave a lobby."""
        id = ctx.author.id
        await ctx.send(
            self.__string_from_string_result(self.logic.leave(self.__game_id(ctx), id))
        )

    @commands.command()
    async def join(self, ctx: commands.Context) -> None:
        """Join a lobby."""
        id = ctx.author.id
        name = ctx.author.name
        await ctx.send(
            self.__string_from_string_result(
                self.logic.join(self.__game_id(ctx), id, name)
            )
        )

    @commands.command()
    async def polls(self, ctx: commands.Context) -> None:
        """Apply the results of the polls to the game."""
        await ctx.send("Reading polls...")
        await ctx.send(
            self.__string_from_string_result(
                await self.logic.apply_poll_results(self.__game_id(ctx))
            )
        )

    @commands.command()
    async def config(
        self, ctx: commands.Context, property: Optional[str], value: Optional[str]
    ) -> None:
        """Configure a lobby."""
        await self.__send_embed_or_pretty_err(ctx, self.logic.config(self.__game_id(ctx), property, value))
