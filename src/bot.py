import discord
import asyncio
import Levenshtein

from .game.commands import Game
from .misc.commands import Misc
from .rating.commands import Rating
from .betting.commands import Betting
from .achievements.commands import Achievements

from discord.ext import commands
from sqlalchemy import create_engine
from . import models

from sqlalchemy.engine import Engine
from sqlalchemy import event


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()


class Bot(commands.Bot):
    def __init__(self, intents: discord.Intents) -> None:
        engine = create_engine("sqlite:///app.db", connect_args={"timeout": 15})

        # Instantiate all the tables.
        models.Base.metadata.create_all(engine)

        # Pass engine to cogs that need it.
        self.init_cogs = [Game(self, engine), Misc(), Betting(engine), Rating(engine), Achievements(engine)]

        super().__init__(command_prefix="!", intents=intents)

    async def on_command_error(self, ctx: commands.Context, error: Exception) -> None:
        similarity = max([(command.name, Levenshtein.ratio(ctx.message.content, command.name)) for command in self.commands], key = lambda x: x[1])[0]

        if isinstance(error, commands.CommandNotFound):
            await ctx.send(embed=discord.Embed(
                title="Command not found",
                description=f"{error}. Did you mean !{similarity}? Type !help for a list of commands",
                color=discord.Color.red()
            ))

    async def setup_hook(self) -> None:
        await asyncio.gather(*(self.add_cog(cog) for cog in self.init_cogs))
