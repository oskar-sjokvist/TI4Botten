import discord
import logging
import asyncio

from .game.commands import Game
from .misc.commands import Misc
from discord.ext import commands
from typing import Optional

class Bot(commands.Bot):
    def __init__(self, intents: discord.Intents) -> None:
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        cogs = [Game(), Misc()]
        await asyncio.gather(*(self.add_cog(cog) for cog in cogs))
        
