import logging
import random

from . import factions
from . import model

import Levenshtein
from itertools import batched
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
        "Ten great powers. One empty throne. The galaxy awaits its new master — and the game begins.",
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
    async def draft(self, ctx: commands.Context, game_id: Optional[int] = None, *, faction: Optional[str] = None) -> None:
        """Draft your faction."""
        session = Session(bind=self.conn)
        try:
            if game_id is None:
                game = model.Game.latest_draft(session)
            else:
                game = session.query(model.Game).filter_by(game_id=game_id).first()
            if not game:
                await ctx.send("No game found.")
                return
            if game.game_state != model.GameState.DRAFT:
                await ctx.send("Game is not in draft stage")
                return

            player = session.query(model.GamePlayer).with_parent(game).filter_by(player_id=ctx.author.id).first()
            if not player:
                await ctx.send("You are not in this game!")
                return
            if player.faction:
                await ctx.send("You have drafted {player.faction}")
                return

            if not faction:
                await ctx.send(f"Your available factions are:\n{"\n".join(player.factions)}")
                return
            
            current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()
            if not current_drafter:
                raise LookupError

            if game.turn != player.turn_order:
                await ctx.send(f"It is not your turn to draft! It is {current_drafter.player.name}'s turn")
                return
                
            cutoff = 0.1
            factions = player.factions
            best = max(factions, key=lambda c: Levenshtein.ratio(faction, c))
            if Levenshtein.ratio(faction, best) <= cutoff:
                await ctx.send(f"You can't draft faction {faction}. Check your spelling or available factions.")
                return
            
            player.faction = best
            game.turn += 1

            session.merge(game)
            session.merge(player)
            session.commit()
            await ctx.send(f"{player.player.name} has selected {player.faction}.")
            if game.turn == len(game.game_players):
                players_info_lines = []
                for player in game.game_players:
                    players_info_lines.append(f"{player.player.name} playing {player.faction}")
                
                game.game_state = model.GameState.STARTED
                session.merge(game)
                session.commit()
                await ctx.send(f"Game '{game.name}' has started\n\nPlayers:\n{"".join(players_info_lines)}\n\n{random.choice(Game.game_start_quotes)}")
                return

            current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()

            await ctx.send("Next drafter is {current_drafter.player.name}.")

            


        except Exception as e:
            logging.error(f"Error drafting: {e}")
            await ctx.send("Something went wrong")
            

    @commands.command()
    async def start(self, ctx: commands.Context, game_id: Optional[int] = None) -> None:
        """Start the lobby."""
        session = Session(bind=self.conn)
        try:
            if game_id is None:
                game = model.Game.latest_lobby(session)
            else:
                game = session.query(model.Game).filter_by(game_id=game_id).first()
            if not game:
                await ctx.send("No lobby found.")
                return

            if game.game_state != model.GameState.LOBBY:
                await ctx.send("Given game is not a lobby")
                return



            settings = []
            sources = []
            if game.game_settings.prophecy_of_kings:
                settings.append("Prophecy of Kings active")
                sources.append("pok")

            if game.game_settings.discordant_stars:
                settings.append("Discordant Stars active")
                sources.append("ds")

            if game.game_settings.codex:
                settings.append("Codex faction active")
                sources.append("codex")

            if game.game_settings.drafting_mode != model.DraftingMode.EXCLUSIVE_POOL:
                await ctx.send("Only exclusive pool supported at the moment")
                return
            

            factions_per_player = 4
            factions = self.factions.get_random_factions(len(game.game_players)*factions_per_player, ','.join(sources))
            factions = [faction.name for faction in factions]
            

            players = game.game_players
            number_of_players = len(players)
            turn_order = random.sample(range(number_of_players), number_of_players)
            faction_slices = batched(factions, factions_per_player)

            factions_lines = []

            player_from_turn = {}
            for i, (player, factions) in enumerate(zip(game.game_players, faction_slices)):
                player.turn_order = turn_order[i]
                player_from_turn[player.turn_order] = player.player.name
                player.factions = list(factions)
                factions_lines.extend(list(map(lambda x : f"{x} ({player.player.name})", factions)))

            players_info_lines = []
            for i in range(number_of_players):
                name = player_from_turn[i]
                players_info_lines.append(f"{name}\n")

            game.game_state = model.GameState.DRAFT
            session.merge(game)
            session.commit

            await ctx.send(f"Game ID: {game.game_id}\nState: {game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\nSettings:\n{"\n".join(settings)}\n\nFactions:\n{"\n".join(factions_lines)}")

            current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()
            if current_drafter is None:
                raise LookupError

            await ctx.send(f"{current_drafter.player.name} begins drafting")
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

            await ctx.send(f"Game ID: {game.game_id}\nState: {game.game_state.value}\nPlayers:\n{player_info}")
        except Exception as e:
            logging.error(f"Error fetching game data: {e}")
            await ctx.send("An error occurred while fetching the game data."    )

    @commands.command()
    async def lobby(self, ctx: commands.Context, *, name: Optional[str]) -> None:
        """Create a lobby."""
        if not name:
            await ctx.send("Please specify a name for the lobby")
            return
        try:
            session = Session(bind=self.conn)

            game = model.Game(game_state="LOBBY", name=name)
            session.add(game)
            session.commit()
            settings = model.GameSettings(game_id=game.game_id)
            session.add(settings)
            session.commit()

            await ctx.send(f"Game lobby '{game.name}' created with ID {game.game_id}. Type !join {game.game_id} to join the game. And !start {game.game_id} to start the game")
        except Exception as e:
            logging.error(f"Error creating game: {e}")
            await ctx.send("An error occurred while creating the game.")

    @commands.command()
    async def leave(self, ctx: commands.Context, game_id: Optional[int]) -> None:
        """Leave a lobby."""
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
        """Join a lobby."""
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
            await ctx.send(f"{ctx.author} has joined lobby '{game.name}'. Current number of players {number_of_players+1}. Type !leave {game.game_id} to leave the lobby.")
        except Exception as e:
            logging.error(f"Error joining lobby: {e}")
            await ctx.send("An error occurred while joining the lobby.")
