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
    async def start(self, ctx: commands.Context, game_id: Optional[int] = None) -> None:
        session = Session(bind=self.conn)
        try:
            if game_id is None:
                game = model.Game.latest_lobby(session)
            else:
                game = session.query(model.Game).filter_by(game_id=game_id).first()
            if not game:
                await ctx.send(f"No lobby found.")
                return


            players_info = ""
            for player in game.game_players:
                players_info += f"{player.player.name}\n"

            settings = ""
            sources = []
            if game.game_settings.prophecy_of_kings:
                settings += "Prophecy of Kings active\n"
                sources.append("pok")

            if game.game_settings.discordant_stars:
                settings += "Discordant stars active\n"
                sources.append("ds")

            if game.game_settings.codex:
                settings += "Codex active\n"
                sources.append("codex")

            if game.game_settings.drafting_mode != model.DraftingMode.EXCLUSIVE_POOL:
                await ctx.send("Only exclusive pool supported at the moment")
                return
            

            factions = self.factions.get_random_factions(len(game.game_players)*4, ','.join(sources))
            factions_string = '\n'.join([str(faction) for faction in factions])
            

            await ctx.send(f"Game ID: {game.game_id}\nState: {game.game_state}\nPlayers:\n{players_info}\nSettings:\n{settings}\nFactions:\n{factions_string}")
        except Exception as e:
            logging.error(f"Error fetching game data: {e}")
            await ctx.send("An error occurred while fetching the game data."    )




    # Debugging command. Fetches game and all players in the game
    @commands.command()
    async def game(self, ctx: commands.Context, game_id: Optional[int] = None) -> None:
        """Fetches a game and all players in the game."""
        session = Session(bind=self.conn)
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

            await ctx.send(f"Game ID: {game.game_id}\nState: {game.game_state}\nPlayers:\n{player_info}")
        except Exception as e:
            logging.error(f"Error fetching game data: {e}")
            await ctx.send("An error occurred while fetching the game data."    )

    @commands.command()
    async def lobby(self, ctx: commands.Context) -> None:
        try:
            session = Session(bind=self.conn)

            game = model.Game(game_state="LOBBY")
            session.add(game)
            session.commit()
            settings = model.GameSettings(game_id=game.game_id)
            session.add(settings)
            session.commit()

            await ctx.send(f"Game lobby created with ID {game.game_id}. Type !join {game.game_id} to join the game. And !start to start the game")
        except Exception as e:
            logging.error(f"Error creating game: {e}")
            await ctx.send("An error occurred while creating the game.")

    @commands.command()
    async def leave(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        id = ctx.author.id
        try:
            session = Session(bind=self.conn)

            if game_id is None:
                game = model.Game.latest_lobby(session)
            else:
                game: Optional[model.Game] = session.query(model.Game).get(game_id)
            if game is None:
                await ctx.send(f"No lobby with game id {game_id}")
                return

            gp = session.query(model.GamePlayer).with_parent(game).filter(model.GamePlayer.player_id==id).first()

            if gp is None:
                await ctx.send("You are not in this game!")
                return

            session.delete(gp)
            session.commit()

            await ctx.send(f"{ctx.author} has left lobby #{game.game_id}. Current number of players {len(game.game_players)}. Type !join {game.game_id} to join the lobby again.")
        except Exception as e:
            logging.error(f"Error leaving lobby: {e}")
            await ctx.send("An error occurred while leaving the lobby.")



    @commands.command()
    async def join(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        id = ctx.author.id
        try:
            session = Session(bind=self.conn)

            if game_id is None:
                game = model.Game.latest_lobby(session)
            else:
                game = session.query(model.Game).get(game_id)

            if game is None:
                await ctx.send(f"No lobby found.")
                return

            if game.game_state != model.GameState.LOBBY:
                await ctx.send("Game is not a lobby!")
                return

            gp = session.query(model.GamePlayer).with_parent(game).filter(model.GamePlayer.player_id==id).first()
            if gp is not None:
                await ctx.send("You are already in this lobby!")
                return

            number_of_players = len(game.game_players) if game.game_players else 0
            if number_of_players >= 8:
                await ctx.send(f"Player limit reached. {number_of_players} have joined the game")
                return

            
            
            player = model.Player(player_id=id, name=ctx.author.name)
            session.merge(player)
            game_player = model.GamePlayer(
                game_id=game.game_id,
                player_id=id,
            )
            session.add(game_player)
            session.commit()
            await ctx.send(f"{ctx.author} has joined lobby #{game.game_id}. Current number of players {number_of_players+1}. Type !leave {game.game_id} to leave the lobby.")
        except Exception as e:
            logging.error(f"Error joining lobby: {e}")
            await ctx.send("An error occurred while joining the lobby.")


    # Debugging command to create a dummy game and dummy players
    @commands.command()
    async def create_dummy_game(self, ctx: commands.Context) -> None:
        try:
            session = Session(bind=self.conn)

            # Create a dummy game
            dummy_game = model.Game(game_state="STARTED")
            session.add(dummy_game)
            session.commit()
            game_id = dummy_game.game_id

            # Create dummy players and game_player entries
            factions = self.factions.get_random_factions(4, "") 
            for i in range(4):  # Create 4 dummy players
                player = model.Player(player_id=i, player_name=str(i))
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