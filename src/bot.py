import discord
import asyncio

from .game.commands import Game
from .misc.commands import Misc
from .betting.commands import Betting

from discord.ext import commands
from sqlalchemy import create_engine
from . import models



class Bot(commands.Bot):
    def __init__(self, intents: discord.Intents) -> None:
        engine = create_engine('sqlite:///app.db', echo=True)

        # Instantiate all the tables.
        models.Base.metadata.create_all(engine)

        # Pass engine to cogs that need it.
        self.init_cogs = [Game(engine), Misc(), Betting(engine)]
        
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        await asyncio.gather(*(self.add_cog(cog) for cog in self.init_cogs))
