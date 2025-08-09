import discord
import logging

from . import factions
from . import model

from sqlalchemy.orm import Session
from typing import Optional
from discord.ext import commands

class Game(commands.Cog):
    """Cog containing game related commands."""

    def __init__(self, factions: factions.Factions = factions.read_factions()) -> None:
        """Initialize the Commands cog with factions."""
        self.factions = factions
        self.conn = model.get_engine().connect()

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


    # Debugging command. Fetches game and all players in the game
    @commands.command()
    async def game(self, ctx: commands.Context, game_id: Optional[int] = None) -> None:
        """Fetches a game and all players in the game."""
        if game_id is None:
            await ctx.send("Please provide a game ID.")
            return

        try:
            session = Session(bind=self.conn)
            game = session.query(model.Game).filter_by(game_id=game_id).first()
            if not game:
                await ctx.send(f"No game found with ID {game_id}.")
                return

            players = session.query(model.GamePlayer).filter_by(game_id=game_id).all()
            player_info = "\n".join([f"Player {gp.player_id}: {gp.faction} - Points: {gp.points}, Rank: {gp.rank}" for gp in players])

            await ctx.send(f"Game ID: {game.game_id}\nState: {game.game_state}\nPlayers:\n{player_info}")
        except Exception as e:
            logging.error(f"Error fetching game data: {e}")
            await ctx.send("An error occurred while fetching the game data."    )


    # Debugging command to create a dummy game and dummy players
    @commands.command()
    async def create_dummy_game(self, ctx: commands.Context) -> None:
        try:
            session = Session(bind=self.conn)

            # Create a dummy game
            dummy_game = model.Game(game_state='STARTED')
            session.add(dummy_game)
            session.commit()
            game_id = dummy_game.game_id

            # Create dummy players and game_player entries
            factions = self.factions.get_random_factions(4, "") 
            for i in range(4):  # Create 4 dummy players
                player = model.Player(player_id=i)
                session.merge(player)
                game_player = model.GamePlayer(
                    game_id=game_id,
                    player_id=i,
                    faction=str(factions[i]),
                    points=0,
                    rank=i
                )
                session.add(game_player)

            session.commit()
            await ctx.send(f"Dummy game created with ID {game_id} and 4 dummy players.")
        except Exception as e:
            logging.error(f"Error creating dummy game: {e}")
            await ctx.send("An error occurred while creating the dummy game.")