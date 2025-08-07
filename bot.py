import discord
import logging

from discord.ext import commands


class Commands(commands.Cog):
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Event handler for when the bot is ready."""
        logging.info(f"Logged in")
        print(f"Logged in")

    @commands.command()
    async def hello(self, ctx) -> None:
        """Responds with a greeting message."""
        await ctx.send("Hello! I'm TI4 Bot. How can I assist you today?")



class Bot(commands.Bot):
    def __init__(self, intents: discord.Intents) -> None:
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        await self.add_cog(Commands())
