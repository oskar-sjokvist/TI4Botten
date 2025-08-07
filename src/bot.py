import discord
import logging
import src.factions as factions

from typing import Optional
from discord.ext import commands

class Commands(commands.Cog):
    """Cog containing bot commands and event listeners."""


    def __init__(self, factions: factions.Factions) -> None:
        """Initialize the Commands cog with factions."""
        self.factions = factions

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Event handler for when the bot is ready."""
        logging.info("Logged in")

    @commands.command()
    async def hello(self, ctx: commands.Context) -> None:
        """Responds with a greeting message."""
        await ctx.send("Hello! I'm TI4 Bot. How can I assist you today?")

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

class Bot(commands.Bot):
    """Custom Bot class for TI4 Botten."""

    def __init__(self, intents: discord.Intents) -> None:
        self.factions = factions.read_factions()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        await self.add_cog(Commands(self.factions))