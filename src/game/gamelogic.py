import Levenshtein
import logging
import random
import re

from . import factions as fs
from . import model
from ..typing import *

from discord.ext import commands
from datetime import datetime
from itertools import batched
from sqlalchemy import inspect, Enum, Boolean, String, Integer
from sqlalchemy.orm import Session, attributes
from string import Template
from typing import Optional, Dict, Any, Iterable, List, Tuple

from blinker import signal


class GameLogic:

    def __init__(self, engine):
        self.engine = engine
        self.signal = signal("finish")

    _game_start_quotes = [
        "'In the ashes of Mecatol Rex, the galaxy trembles. Ancient rivalries stir, alliances are whispered in shadow, and war fleets awaken from slumber. The throne is empty… but not for long.'\n-$player",
        "'The age of peace is over. Steel will be our currency, blood our tribute. Let the weak hide behind treaties — we will claim the stars themselves.'\n-$player",
        "'Our fleets are in position. Every planet is a resource, every neighbour a pawn. The throne will be ours… through persuasion or annihilation.'\n-$player",
        "'Attention, denizens of the galaxy: the Lazax are no more. The throne stands vacant. May the worthy rise… and the unworthy perish.'\n-$player",
    ]

    _game_end_quotes = [
        "The galaxy falls silent. The throne is claimed by $winner, and a new era begins.",
        "From the ruins of war, a ruler emerges. $winner's will shall shape the stars.",
        "The council is dissolved. All voices bow to $winner — the new master of Mecatol Rex.",
        "War fleets drift like shadows, but $winner's banner flies above them all.",
        "The game is over. The galaxy belongs to $winner, bold enough to take it.",
        "Power is not given; it is seized. Today, history remembers $winner.",
        "In the wake of conquest, the galaxy is remade in $winner's image.",
        "The war for Mecatol Rex has ended — but the scars of $loser will never fade."
    ]

    _introduction = '''These are some resources that can be useful for your game
- https://www.youtube.com/watch?v=_u2xEap5hBM (Twilight Imperium 4th edition in 32 minutes)
- https://www.youtube.com/watch?v=gdpW4FBCUuo (Common Twilight Imperium Rules Mistakes 1)
- https://www.youtube.com/watch?v=Jk5PA4EUGJw (Common Twilight Imperium Rules Mistakes 2)

Learn to play compressed
- https://images-cdn.fantasyflightgames.com/filer_public/f3/c6/f3c66512-8e19-4f30-a0d4-d7d75701fd37/ti-k0289_learn_to_playcompressed.pdf

Living rules reference (Prophecy of Kings)
- https://images-cdn.fantasyflightgames.com/filer_public/51/55/51552c7f-c05c-445b-84bf-4b073456d008/ti10_pok_living_rules_reference_20_web.pdf'''


    def _players_ordered_by_turn(self, session : Session, game : model.Game) -> List[model.GamePlayer]:
        return session.query(model.GamePlayer).with_parent(game).order_by(model.GamePlayer.turn_order.asc()).all()

    def _players_ordered_by_points(self, session : Session, game : model.Game) -> List[model.GamePlayer]:
        return session.query(model.GamePlayer).with_parent(game).order_by(model.GamePlayer.points.desc()).all()

    def _winner(self, session : Session, game : model.Game) -> model.GamePlayer:
        winner = session.query(model.GamePlayer).with_parent(game).order_by(model.GamePlayer.points.desc()).first()
        if winner is None:
            raise LookupError("Winner not found for this game!")
        return winner

    def _current_drafter(self, session : Session, game : model.Game) -> model.GamePlayer:
        current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()
        if current_drafter is None:
            raise LookupError("Current drafter not found for this game!")
        return current_drafter


    @staticmethod
    def _parse_ints(s):
        return list(map(int, re.findall(r"-?\d+", s)))

    @staticmethod
    def _closest_match(s : str, ss : Iterable[str], cutoff=0.1) -> str|None :
        best = max(ss, key=lambda c: Levenshtein.ratio(s, c))
        if Levenshtein.ratio(s, best) <= cutoff:
            return None
        return best

    def finish(self, is_admin : bool, game_id: int, all_points: Optional[str]) -> Result[str]:
        with Session(self.engine) as session:
            try:
                game = session.query(model.Game).filter_by(game_id=game_id).first()
                if not game:
                    return Err("Game not found.")
                # if is_admin and game.game_state == model.GameState.FINISHED:
                    # Admins can update finished games.
                    pass
                elif game.game_state != model.GameState.STARTED:
                    return Err(f"Can't finish game. Game is in {game.game_state.value} state.")

                players = self._players_ordered_by_turn(session, game)
                lines = [p.player.name for p in players]

                if not all_points:
                    return Err(f"Players\n{"\n".join(lines)}\n\nSpecify the points based on the player order. E.g. !finish game_id 2 10")
                for player, points in zip(players, self._parse_ints(all_points)):
                    player.points = points

                session.add_all(players)
                game.game_state = model.GameState.FINISHED
                game.game_finish_time = datetime.now()
                session.merge(game)
                session.commit()

                players = self._players_ordered_by_points(session, game)
                lines = [f"{i+1}. {p.player.name} played {p.faction} and finished with {p.points} point(s)" for i, p in enumerate(players)]
                
                self.signal.send(None, game_id=game.game_id)

                return Ok(f"Game '{game.name}' has finished\n\nPlayers:\n{"\n".join(lines)}\n\n{self._game_end_quote(players[0].player.name, players[-1].player.name)}\n\nWrong result? Rerun the !finish command.")
            except Exception as e:
                logging.error(f"Can't finish game: {e}")
                return Err("Can't finish game. Something went wrong.")


    @staticmethod
    def _game_start_quote(player_name: str) -> str:
        return Template(random.choice(GameLogic._game_start_quotes)).safe_substitute(player=player_name)

    @staticmethod
    def _game_end_quote(winner: str, loser: str) -> str:
        return Template(random.choice(GameLogic._game_end_quotes)).safe_substitute(winner=winner, loser=loser)

    def ban_picks_and_bans(self, session: Session, game: model.Game, player: model.GamePlayer, faction: Optional[str]) -> Optional[str]:

        current_drafter = self._current_drafter(session, game)
        all_bans = [banned for gameplayer in game.game_players for banned in gameplayer.bans if gameplayer.bans]
        if not faction or game.game_state != model.GameState.BAN:
            lines = list()
            if game.game_state == model.GameState.BAN:
                lines.append(f"It is {current_drafter.player.name}'s turn to ban.")
            else:
                lines.append("This game is not in banning phase.")
            if all_bans:
                lines.append("These factions are banned:")
                lines.extend([f"* {f}" for f in all_bans])
            return   "\n".join(lines)

        if current_drafter.player.player_id != player.player_id:
            return f"It is not your turn to ban! It is {current_drafter.player.name}'s turn"

        # Process the ban
        best = GameLogic._closest_match(faction, player.factions)
        if not best:
            return f"You can't ban faction {faction}. Check your spelling or available factions."
        
        # Check if this faction is already banned by anyone
        if best in all_bans:
            return f"Faction {best} has already been banned!"
        
        
        # Initialize bans list if it doesn't exist
        if not player.bans:
            player.bans = []

        player.bans.append(best)
        attributes.flag_modified(player, "bans")

        # Remove banned faction from all players' available factions
        for any_player in game.game_players:
            if best in any_player.factions:
                any_player.factions.remove(best)
                attributes.flag_modified(any_player, "factions")


        lines = [f"{player.player.name} has banned {best}."]

        number_of_players = len(game.game_players)

        total_bans_needed = number_of_players * game.game_settings.bans_per_player

        game.turn = (game.turn + 1) % number_of_players
        current_drafter = self._current_drafter(session, game)

        if total_bans_needed == len(all_bans) + 1:
            game.game_state = model.GameState.DRAFT
            lines.append("Banning is now complete!")
            lines.append(f"Next one to draft is <@{current_drafter.player_id}>. Use !draft.")
        else:
            lines.append(f"Next one to ban is <@{current_drafter.player_id}>. Use !ban.")

        session.merge(player)
        session.merge(game)
        session.commit()

        return "\n".join(lines)


    async def ban(self, player_id: int,  game_id: int, faction: Optional[str] = None) -> Optional[str]:
        try:
            with Session(self.engine) as session:
                game = session.query(model.Game).filter_by(game_id=game_id).first()
                if not game:
                    return "No game found."

                player = session.query(model.GamePlayer).with_parent(game).filter_by(player_id=player_id).first()

                if not player:
                    return "You are not in this game!"

                if game.game_settings.drafting_mode == model.DraftingMode.PICKS_AND_BANS:
                    return self.ban_picks_and_bans(session, game, player, faction)
                else:
                    return "This drafting mode doesn't support banning"

        except Exception as e:
            logging.error(f"Error drafting: {e}")
            return "Something went wrong"


    def draft_exclusive_pool(self, session: Session, game: model.Game, player: model.GamePlayer, faction: Optional[str]) -> Optional[str]:

            if player.faction:
                return f"You have drafted {player.faction}"

            if not faction:
                return f"Your available factions are:\n{"\n".join(player.factions)}"
            
            current_drafter = self._current_drafter(session, game)

            if game.turn != player.turn_order:
                return f"It is not your turn to draft! It is {current_drafter.player.name}'s turn"
                
            best = GameLogic._closest_match(faction, player.factions)
            if not best:
                return f"You can't draft faction {faction}. Check your spelling or available factions."
            
            player.faction = best
            game.turn += 1

            session.merge(game)
            session.merge(player)
            lines = [f"{player.player.name} has selected {player.faction}."]
            if game.turn == len(game.game_players):
                return None
            session.commit()

            current_drafter = self._current_drafter(session, game)

            lines.append(f"Next drafter is <@{current_drafter.player_id}>. Use !draft.")
            return "\n".join(lines)


    def draft_picks_only(self, session: Session, game: model.Game, player: model.GamePlayer, faction: Optional[str]) -> Optional[str]:

            if player.faction:
                return f"You have drafted {player.faction}"

            if not faction:
                return f"Your available factions are:\n{"\n".join(player.factions)}"
            
            current_drafter = self._current_drafter(session, game)

            if game.turn != player.turn_order:
                return f"It is not your turn to draft! It is {current_drafter.player.name}'s turn"

            best = GameLogic._closest_match(faction, player.factions)
            if not best:
                return f"You can't draft faction {faction}. Check your spelling or available factions."
            
            player.faction = best
            game.turn += 1

            other_players = [other for other in game.game_players if other.player_id != player.player_id]
            for other_player in other_players:
                other_player.factions.remove(player.faction)
                session.merge(other_player)

            session.merge(game)
            session.merge(player)
            lines = [f"{player.player.name} has selected {player.faction}."]
            if game.turn == len(game.game_players):
                return None
            session.commit()

            current_drafter = self._current_drafter(session, game)

            lines.append(f"Next drafter is <@{current_drafter.player_id}>. Use !draft.")
            return "\n".join(lines)


    def draft_picks_and_bans(self, session: Session, game: model.Game, player: model.GamePlayer, faction: Optional[str]) -> Optional[str]:

            if player.faction:
                return f"You have drafted {player.faction}"

            if not faction:
                return f"Your available factions are:\n{"\n".join(player.factions)}"
            
            current_drafter = self._current_drafter(session, game)

            if game.turn != player.turn_order:
                return f"It is not your turn to draft! It is {current_drafter.player.name}'s turn"
            
            all_bans = []
            for game_player in game.game_players:
                if game_player.bans:
                    all_bans.extend(game_player.bans)
            
            all_factions_available = player.factions.copy()
            all_factions_available.extend(all_bans)

            best = GameLogic._closest_match(faction, all_factions_available)
            if not best:
                return f"You can't draft faction {faction}. Check your spelling or available factions."
            
            # Check if this faction is already banned by anyone

            if best in all_bans:
                return f"Faction {best} has already been banned."

            player.faction = best
            game.turn += 1

            other_players = [other for other in game.game_players if other.player_id != player.player_id]
            for other_player in other_players:
                other_player.factions.remove(player.faction)
                session.merge(other_player)

            session.merge(game)
            session.merge(player)
            lines = [f"{player.player.name} has selected {player.faction}."]
            if game.turn == len(game.game_players):
                return None
            session.commit()

            current_drafter = self._current_drafter(session, game)

            lines.append(f"Next drafter is <@{current_drafter.player_id}>. Use !draft.")
            return "\n".join(lines)


    async def draft(self, ctx: commands.Context, player_id: int,  game_id: int, faction: Optional[str] = None) -> str:
        try:
            with Session(self.engine) as session:
                game = session.query(model.Game).filter_by(game_id=game_id).first()
                if not game:
                    return "No game found."
                if game.game_state != model.GameState.DRAFT:
                    return "Game is not in draft stage"

                player = session.query(model.GamePlayer).with_parent(game).filter_by(player_id=player_id).first()

                if not player:
                    return "You are not in this game!"

                error_message = None
                if game.game_settings.drafting_mode == model.DraftingMode.EXCLUSIVE_POOL:
                    error_message = self.draft_exclusive_pool(session, game, player, faction)
                elif game.game_settings.drafting_mode == model.DraftingMode.PICKS_ONLY:
                    error_message = self.draft_picks_only(session, game, player, faction)
                elif game.game_settings.drafting_mode == model.DraftingMode.PICKS_AND_BANS:
                    error_message = self.draft_picks_and_bans(session, game, player, faction)
                else:
                    return f"Mode {game.game_settings.drafting_mode} not implemented yet."
                
                if error_message:
                    return error_message
                else:
                    return await self._start_game(ctx, session, game, player.player.name)

        except Exception as e:
            logging.error(f"Error drafting: {e}")
            return "Something went wrong"


    def cancel(self, game_id: int) -> str:
        with Session(self.engine) as session:
            game = session.get(model.Game, game_id)
            if not game:
                return f"No such game found"
            
            if game.game_state == model.GameState.FINISHED:
                return f"Game has already finished."

            session.delete(game)
            session.commit()
            return f"Successfully deleted {game.name}"

    async def _start_game(self, session: Session, game: model.Game, name: str) -> str:
        players_info_lines = []
        for player in game.game_players:
            players_info_lines.append(f"{player.player.name} playing {player.faction}")
        
        game.game_state = model.GameState.STARTED
        session.merge(game)
        session.commit()
        launch = f"Game '{game.name}' has started\n\nPlayers:\n{"\n".join(players_info_lines)}\n\n{GameLogic._game_start_quote(name)}\n{GameLogic._introduction}"
        return launch

    @staticmethod
    def _get_start_settings(game: model.Game) -> Tuple[List[str], List[str]]:
        settings = []
        sources = []
        if game.game_settings.base_game:
            settings.append("Base game active")
            sources.append("base")
        if game.game_settings.prophecy_of_kings:
            settings.append("Prophecy of Kings active")
            sources.append("pok")

        if game.game_settings.discordant_stars:
            settings.append("Discordant Stars active")
            sources.append("ds")

        if game.game_settings.codex:
            settings.append("Codex faction active")
            sources.append("codex")
        return settings, sources



    def start_exclusive_pool(self, session: Session, factions : fs.Factions, game: model.Game) -> Result[str]: 

        settings, sources = GameLogic._get_start_settings(game)
        players = game.game_players
        number_of_players = len(players)

        factions_per_player = game.game_settings.factions_per_player
        fs = factions.get_random_factions(number_of_players * factions_per_player, ','.join(sources))
        if len(fs) < number_of_players * factions_per_player:
            return Err(f"There are too many factions selected per player. Max allowed for a {number_of_players} player game is {len(fs)//number_of_players}.")
        fs = [faction.name for faction in fs]

        turn_order = random.sample(range(number_of_players), number_of_players)
        faction_slices = batched(fs, factions_per_player)

        factions_lines = []

        player_from_turn = {}
        for i, (player, player_factions) in enumerate(zip(game.game_players, faction_slices)):
            player.turn_order = turn_order[i]
            player_from_turn[player.turn_order] = player.player.name
            player.factions = list(player_factions)
            factions_lines.extend(list(map(lambda x : f"{x} ({player.player.name})", player_factions)))
            session.merge(player)

        players_info_lines = []
        for i in range(number_of_players):
            name = player_from_turn[i]
            players_info_lines.append(f"{name}")

        game.game_state = model.GameState.DRAFT
        session.merge(game)
        session.commit()

        lines = [f"State: {game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\nSettings:\n{"\n".join(settings)}\n\nFactions:\n{"\n".join(factions_lines)}"]

        current_drafter = self._current_drafter(session, game)

        lines.append(f"<@{current_drafter.player_id}> begins drafting. Use !draft.")
        return Ok("\n".join(lines))


    def start_picks_only(self, session: Session, factions : fs.Factions, game: model.Game) -> Result[str]:
        
        settings, sources = GameLogic._get_start_settings(game)
        players = game.game_players
        number_of_players = len(players)

        turn_order = random.sample(range(number_of_players), number_of_players)

        fs = [faction.name for faction in factions.get_factions(",".join(sources))]
        
        player_from_turn = {}
        for i, player in enumerate(players):
            player.turn_order = turn_order[i]
            player_from_turn[player.turn_order] = player.player.name
            player.factions = fs
        
        players_info_lines = []
        for i in range(number_of_players):
            name = player_from_turn[i]
            players_info_lines.append(f"{name}")

        game.game_state = model.GameState.DRAFT
        session.merge(game)
        session.commit()

        lines = [f"State: {game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\nSettings:\n{"\n".join(settings)}"]

        current_drafter = self._current_drafter(session, game)
        lines.append(f"<@{current_drafter.player_id}> begins drafting. Use !draft.")
        return Ok("\n".join(lines))


    def start_picks_and_bans(self, session: Session, factions : fs.Factions, game: model.Game) -> Result[str]:

        settings, sources = GameLogic._get_start_settings(game)
        players = game.game_players
        number_of_players = len(players)

        turn_order = random.sample(range(number_of_players), number_of_players)

        fs = [faction.name for faction in factions.get_factions(",".join(sources))]
        
        player_from_turn = {}
        for i, player in enumerate(players):
            player.turn_order = turn_order[i]
            player_from_turn[player.turn_order] = player.player.name
            player.factions = fs
        
        players_info_lines = []
        for i in range(number_of_players):
            name = player_from_turn[i]
            players_info_lines.append(f"{name}")

        game.game_state = model.GameState.BAN
        session.merge(game)
        session.commit()

        lines = [f"State: {game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\nSettings:\n{"\n".join(settings)}"]

        current_drafter = self._current_drafter(session, game)
        lines.append(f"<@{current_drafter.player_id}> begins banning. Use !ban.")
        return Ok("\n".join(lines))


    def start(self, factions : fs.Factions, game_id: int) -> Result[str]:
        try:
            with Session(self.engine) as session:
                game = self._find_lobby(session, game_id)
                if isinstance(game, str):
                    return Err(game)

                if game.game_settings.drafting_mode == model.DraftingMode.EXCLUSIVE_POOL:
                    return self.start_exclusive_pool(session, factions, game)
                elif game.game_settings.drafting_mode == model.DraftingMode.PICKS_ONLY:
                    return self.start_picks_only(session, factions, game)
                elif game.game_settings.drafting_mode == model.DraftingMode.PICKS_AND_BANS:
                    return self.start_picks_and_bans(session, factions, game)
                else:
                    return Err(f"Drafting mode {game.game_settings.drafting_mode} not supported at the moment")
        except Exception as e:
            logging.error(f"Error fetching game data: {e}")
            return Err("An error occurred while fetching the game data.")

    def game(self, game_id: Optional[int]) -> Result[str]:
        with Session(self.engine) as session:
            try:
                if game_id is None:
                    game = session.query(model.Game).order_by(model.Game.game_id.desc()).first()
                else:
                    game = session.query(model.Game).filter_by(game_id=game_id).first()
                if not game:
                    return Err(f"No game found.")

                lines = [
                    f"{game.name}",
                    f"Game state: {game.game_state.value}",
                ]

                players = game.game_players
                if players:
                    lines.append("")
                    lines.append("Players:")
                    for player in players:
                        s = player.player.name if player.player.name else "Unknown"
                        if player.faction:
                            s += f" Faction: {player.faction}"
                        if player.points:
                            s += f" Points: {player.points}"
                    lines.append(s)
                lines.append("")

                lines.append(self.config(game.game_id, "get", None))
                return Ok("\n".join(lines))
            except Exception as e:
                logging.error(f"!game error: {e}")
                return Err("An error occurred while fetching the game data.")


    def lobbies(self) -> Result[str]:
        with Session(self.engine) as session:
            try:
                games = session.query(model.Game).order_by(model.Game.lobby_create_time.desc()).filter_by(game_state=model.GameState.LOBBY).all()
                if not games:
                    return Err("No games found.")
                lines = []
                for game in games:
                    lines.append(f"#{game.game_id}: {game.name}. {len(game.game_players)} player(s).")
                return Ok("\n".join(lines))
            except Exception as e:
                logging.error(f"Error fetching game data: {e}")
                return Err("An error occurred while fetching the game data.")

    def lobby(self, game_id: int, player_id: int, player_name: str, name: str) -> Result[str]:
        with Session(self.engine) as session:
            try:
                game = model.Game(game_id=game_id, game_state="LOBBY", name=name)
                session.add(game)
                session.flush()
                settings = model.GameSettings(game_id=game.game_id)
                session.add(settings)
                player = model.Player(player_id=player_id, name=player_name)
                session.merge(player)
                game_player = model.GamePlayer(
                    game_id=game.game_id,
                    player_id=player_id,
                )
                session.add(game_player)
                session.commit()


                lines = [
                    f"Game lobby '{game.name}' created. Type !join to join the game. And !start to start the game",
                    f"Players: {player_name}."
                ]
                return Ok('\n'.join(lines))

            except Exception as e:
                logging.error(f"Error creating game: {e}")
                return Err("An error occurred while creating the game.")

    def _find_lobby(self, session: Session, game_id: int) -> Result[model.Game]:
        game = session.get(model.Game, game_id)

        if game is None:
            return Err("No lobby found.")

        if game.game_state != model.GameState.LOBBY:
            return Err("Game is not a lobby!")

        return Ok(game)

    def leave(self, game_id: int, player_id : int) -> Result[str]:
        with Session(self.engine) as session:
            try:
                res = self._find_lobby(session, game_id)
                if isinstance(res, Err):
                    return res
                game = res.value

                gp = session.query(model.GamePlayer).with_parent(game).filter(model.GamePlayer.player_id==player_id).first()

                if gp is None:
                    return Err("You are not in this game!")

                name = gp.player.name
                session.delete(gp)
                if len(game.game_players) == 0:
                    return Ok(f"All players have left the lobby. Admin can use !cancel to remove the lobby and channel")
                session.commit()
                return Ok(f"{name} has left lobby. Current number of players {len(game.game_players)}. Type !join to join the lobby again.")

            except Exception as e:
                logging.error(f"Error leaving lobby: {e}")
                return Err("An error occurred while leaving the lobby.")



    def join(self, game_id : int, player_id : int, player_name : str) -> Result[str]:
        with Session(self.engine) as session:
            try:
                res = self._find_lobby(session, game_id)
                if isinstance(res, Err):
                    return res
                game = res.value

                gp = session.query(model.GamePlayer).with_parent(game).filter(model.GamePlayer.player_id==player_id).first()
                if gp is not None:
                    return Err("You are already in this lobby!")

                number_of_players = len(game.game_players) if game.game_players else 0
                if number_of_players >= 8:
                    return Err(f"Player limit reached. {number_of_players} have joined the game")
                
                
                player = model.Player(player_id=player_id, name=player_name)
                session.merge(player)
                game_player = model.GamePlayer(
                    game_id=game.game_id,
                    player_id=player_id,
                )
                session.add(game_player)
                session.commit()
                return Ok(f"{player_name} has joined lobby '{game.name}'. Current number of players {number_of_players+1}. Type !leave to leave the lobby.")
            except Exception as e:
                logging.error(f"Error joining lobby: {e}")
                return Err("An error occurred while joining the lobby.")



    def games(self, game_limit: int = 5) -> Result[str]:
        with Session(self.engine) as session:
            try:
                games = session.query(model.Game).order_by(model.Game.game_id.desc()).filter_by(game_state=model.GameState.FINISHED).limit(game_limit).all()
                if not games:
                    return Err(f"No games found.")
                lines = []
                for game in games:
                    winner = self._winner(session, game)
                    lines.append(f"{game.name}. Winner {f"{winner.player.name} ({winner.faction})" if winner else "Unknown"}")
                return Ok("\n".join(lines))
            except Exception as e:
                logging.error(f"Error fetching game data: {e}")
                return Err("An error occurred while fetching the game data.")


    def config(self, game_id: int, property: Optional[str], value: Optional[str]) -> Result[str]:
        '''Configure a game session'''
        with Session(self.engine) as session:
            try:
                if game_id is None:
                    game = model.Game.latest_lobby(session)
                else:
                    game = session.query(model.Game).filter_by(game_id=game_id).first()
                if not game:
                    return Err("No lobby found.")

                def get_valid_values(dtype):
                    if isinstance(dtype, Enum):
                        return dtype.enums
                    elif isinstance(dtype, Boolean):
                        return [True, False]
                    elif isinstance(dtype, String):
                        return ["String"]
                    elif isinstance(dtype, Integer):
                        return ["Integer"]
                    else:
                        raise TypeError(f"Unsupported column type: {dtype}")

                settings = inspect(model.GameSettings)
                valid_keys : Dict[str, Any] = dict()
                for key, dtype in [(col.key, col.type) for col in settings.columns]:
                    if not ("game" in key and "id" in key):
                        valid_keys[key] = dtype

                if property == "get":
                    game_settings = session.query(model.GameSettings).filter_by(game_id=game.game_id).first()

                    ret = "Settings:\n"
                    for key in valid_keys.keys():
                        ret += f"* {key}: {str(getattr(game_settings, key))}\n"
                    return Ok(ret)
                if not property or not value:
                    ret = "Use 'get' to retrieve current settings.\nValid keys and datatypes:\n"
                    for key, dtype in valid_keys.items():
                        ret += f"* {key}:\n"
                        for data in get_valid_values(dtype):
                            ret += f"\t{data}\n"
                    return Err(ret)

                if game.game_state != model.GameState.LOBBY:
                    return Err("Game is not in lobby.")

                valid_properties = valid_keys.keys()
                best_prop = GameLogic._closest_match(property, valid_properties)
                if not best_prop:
                    return Err("Cannot understand which property you mean. Please check your spelling.")
                property = best_prop

                if property not in valid_keys.keys():
                    return Err("Property not found.")
                
                dtype = valid_keys[property]
                if isinstance(dtype, Enum):
                    enum_list = list(dtype.enums)
                    best_value = GameLogic._closest_match(value, enum_list)
                    if not best_value:
                        return Err(f"Valid values are: {enum_list}")
                    new_value = best_value
                elif isinstance(dtype, Boolean):
                    val = value.lower()
                    if val in ["true", "t", "yes", "y", "1"]:
                        new_value = True
                    elif val in ["false", "f", "no", "n", "0"]:
                        new_value = False
                    else:
                        return Err(f"Supply a boolean value.")
                elif isinstance(dtype, Integer):
                    if value.isdigit():
                        new_value = int(value)
                    else:
                        return Err("Supply a valid integer value")
                elif isinstance(dtype, String):
                    new_value = value
                else:
                    return Err("Invalid datatype")

                game_settings = session.query(model.GameSettings).filter_by(game_id=game.game_id).first()
                setattr(game_settings, property, new_value)
                session.commit()
                return Ok(f"Set property '{property}' to '{new_value}'")

            except Exception as e:
                logging.error(f"Error configuring lobby: {e}")
                return Err("An error occurred while configuring the lobby.")