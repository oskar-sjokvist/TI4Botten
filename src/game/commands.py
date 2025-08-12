import logging

from . import gamelogic
from . import factions
from . import model

from sqlalchemy.orm import Session
from typing import Optional, Tuple, List
from discord.ext import commands

class Game(commands.Cog):
    """Cog containing game related commands."""

    game_start_quotes = [
        "In the ashes of Mecatol Rex, the galaxy trembles. Ancient rivalries stir, alliances are whispered in shadow, and war fleets awaken from slumber. The throne is empty… but not for long.",
        "The age of peace is over. Steel will be our currency, blood our tribute. Let the weak hide behind treaties — we will claim the stars themselves.",
        "Our fleets are in position. Every planet is a resource, every neighbour a pawn. The throne will be ours… through persuasion or annihilation.",
        "Attention, denizens of the galaxy: the Lazax are no more. The throne stands vacant. May the worthy rise… and the unworthy perish.",
    ]

    game_end_quotes = [
        "The galaxy falls silent. The throne is claimed, and a new era begins.",
        "From the ruins of war, a ruler emerges. Their will shall shape the stars.",
        "The council is dissolved. All voices bow to one — the new master of Mecatol Rex.",
        "War fleets drift like shadows, but the victor’s banner flies above them all.",
        "The game is over. The galaxy belongs to those bold enough to take it.",
        "Power is not given; it is seized. Today, history remembers the conqueror.",
        "In the wake of conquest, the galaxy is remade in the victor’s image.",
        "The war for Mecatol Rex has ended — but the scars will never fade."
    ]

    def __init__(self, factions: factions.Factions = factions.read_factions()) -> None:
        """Initialize the Commands cog with factions."""
        self.factions = factions
        self.conn = model.get_engine().connect()

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
    async def finish(self, ctx: commands.Context, game_id: Optional[int] = None, *, rankings: Optional[str] = "") -> None:
        is_admin = ctx.author.guild_permissions.administrator
        with Session(bind=self.conn) as session:
            await ctx.send(gamelogic.finish(session, is_admin , game_id, rankings))

    @commands.command()
    async def draft(self, ctx: commands.Context, game_id: Optional[int] = None, *, faction: Optional[str] = None) -> None:
        """Draft your faction."""
        with Session(bind=self.conn) as session:
            await ctx.send(gamelogic.draft(session, ctx.author.id, game_id, faction))

    @commands.command()
    async def start(self, ctx: commands.Context, factions : factions.Factions, game_id: Optional[int] = None) -> None:
        """Start the lobby."""
        with Session(bind=self.conn) as session:
            await ctx.send(gamelogic.start(session, factions, game_id))

    @commands.command()
    async def games(self, ctx: commands.Context) -> None:
        """Fetches 5 latest games."""
        with Session(bind=self.conn) as session:
            await ctx.send(gamelogic.games(session))

    @commands.command()
    async def lobby(self, ctx: commands.Context, *, name: Optional[str]) -> None:
        """Create a lobby."""
        with Session(bind=self.conn) as session:
            await ctx.send(gamelogic.lobby(session, name))

    @commands.command()
    async def leave(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        """Leave a lobby."""
        id = ctx.author.id
        with Session(bind=self.conn) as session:
            await ctx.send(gamelogic.leave(session, id, game_id))


    @commands.command()
    async def join(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        """Join a lobby."""
        id = ctx.author.id
        name = ctx.author.name
        with Session(bind=self.conn) as session:
            await ctx.send(gamelogic.join(session, id, name, game_id))