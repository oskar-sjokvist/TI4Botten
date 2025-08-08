import discord
import logging

from discord.ext import commands

class Misc(commands.Cog):
    """Cog containing misc related commands."""

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Misc cog loaded")

    @commands.command()
    async def hello(self, ctx: commands.Context) -> None:
        await ctx.send("Hello!")

