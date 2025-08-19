import logging
import asyncio

from . import achievementslogic
from . import listener as achievements_listener

from discord.ext import commands
from sqlalchemy import Engine

from typing import Optional
from ..typing import *


class Achievements(commands.Cog):
    """Cog containing achievement related commands."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.logic = achievementslogic.AchievementsLogic(engine)
        try:
            achievements_listener.register(engine)
        except Exception:
            logging.exception("Failed to register achievements listener")

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        logging.info("Achievements cog loaded")
        # Load achievement definitions from JSON files and then reconcile counters
        try:
            asyncio.create_task(asyncio.to_thread(achievements_listener.load_achievements, self.engine))
            asyncio.create_task(asyncio.to_thread(achievements_listener.reconcile, self.engine))
        except Exception:
            logging.exception("Failed to schedule achievements startup tasks")


    @commands.command()
    async def achievements(self, ctx: commands.Context, *, name_input: Optional[str]) -> None:
            """Type !achievements to view your achievements or !achievements {name} to view someone else's."""
            id, name = ctx.author.id, ctx.author.name
            if name_input:
                id = self.logic.player_id_from_name(name_input)
                if not id:
                    await ctx.send("Could not find that player")
                    return
                
                
            match self.logic.achievements(id, name):
                case Ok(s):
                    await s.view_menu(ctx).start()
                case Err(s):
                    await ctx.send(s)

