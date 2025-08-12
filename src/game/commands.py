import logging

from . import gamelogic
from . import factions
from . import model

from sqlalchemy.orm import Session
from typing import Optional
from discord.ext import commands
from sqlalchemy import Engine

class Game(commands.Cog):
    """Cog containing game related commands."""

    def __init__(self,  engine: Engine) -> None:
        """Initialize the Commands cog with factions."""
        self.factions = factions.read_factions()
        self.engine = engine

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
        with Session(self.engine) as session:
            await ctx.send(gamelogic.finish(session, is_admin , game_id, rankings))

    @commands.command()
    async def draft(self, ctx: commands.Context, game_id: Optional[int] = None, *, faction: Optional[str] = None) -> None:
        """Draft your faction."""
        with Session(self.engine) as session:
            await ctx.send(await gamelogic.draft(ctx, session, ctx.author.id, game_id, faction))

    @commands.command()
    async def start(self, ctx: commands.Context, game_id: Optional[int] = None) -> None:
        """Start the lobby."""
        with Session(self.engine) as session:
            await ctx.send(gamelogic.start(session, self.factions, game_id))

    @commands.command()
    async def games(self, ctx: commands.Context) -> None:
        """Fetches 5 latest games."""
        with Session(self.engine) as session:
            await ctx.send(gamelogic.games(session))

    @commands.command()
    async def game(self, ctx: commands.Context, game_id: Optional[int] = None) -> None:
        """Fetches a game and all players in the game."""
        session = Session(self.engine)
        try:
            if game_id is None:
                game = session.query(model.Game).order_by(model.Game.game_id.desc()).first()
            else:
                game = session.query(model.Game).filter_by(game_id=game_id).first()
            if not game:
                await ctx.send(f"No game found.")
                return

            players = game.game_players
            player_info = "\n".join([f"Player {gp.player.name if gp.player.name else "Unknown"}: {gp.faction} - Points: {gp.points}, Rank: {gp.rank}" for gp in players])

            await ctx.send(f"Game ID: {game.game_id}\nState: {game.game_state.value}\nPlayers:\n{player_info}")
        except Exception as e:
            logging.error(f"Error fetching game data: {e}")
            await ctx.send("An error occurred while fetching the game data.")

    @commands.command()
    async def lobby(self, ctx: commands.Context, *, name: Optional[str]) -> None:
        """Create a lobby."""
        with Session(self.engine) as session:
            await ctx.send(gamelogic.lobby(session, name))

    @commands.command()
    async def leave(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        """Leave a lobby."""
        id = ctx.author.id
        with Session(self.engine) as session:
            await ctx.send(gamelogic.leave(session, id, game_id))


    @commands.command()
    async def join(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        """Join a lobby."""
        id = ctx.author.id
        name = ctx.author.name
        with Session(self.engine) as session:
            await ctx.send(gamelogic.join(session, id, name, game_id))

    @commands.command()
    async def config(self, ctx: commands.Context, game_id: Optional[int], property: Optional[str], value: Optional[str]) -> None:
        """Configure a lobby."""
        with Session(self.engine) as session:
            await ctx.send(gamelogic.config(session, game_id, property, value))