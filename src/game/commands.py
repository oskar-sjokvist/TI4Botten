import discord
import logging

from . import factions
from typing import Optional
from discord.ext import commands

class Game(commands.Cog):
    """Cog containing game related commands."""

    def __init__(self, factions: factions.Factions = factions.read_factions()) -> None:
        """Initialize the Commands cog with factions."""
        self.factions = factions

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Game cog loaded")


    @commands.command()
    async def factions(self, ctx: commands.Context, number: int = 8, *, sources: str = "") -> None:
        """Returns a specified number of random factions."""
        if number <= 0:
            await ctx.send("Please specify a positive number of factions.")
            return

        random_factions = [str(faction) for faction in self.factions.get_random_factions(number, sources)]

        if not random_factions:
            await ctx.send("No factions found matching the criteria.")
            return
        await ctx.send(f"Here are {number} random factions:\n{'\n'.join(random_factions)}")

