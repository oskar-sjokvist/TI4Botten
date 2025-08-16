import Levenshtein
import logging
import asyncio
import random
import re
import discord
import enum

from . import factions as fs
from . import model
from . import draftingmodes
from . import controller

from ..typing import *

from discord.ext import commands
from datetime import datetime, timedelta
from sqlalchemy import inspect, Enum, Boolean, String, Integer, select
from sqlalchemy.orm import Session
from string import Template
from typing import Optional, Dict, Any, Iterable, Sequence

from blinker import signal


class GameLogic:

    def __init__(self, bot: commands.Bot, engine):
        self.bot = bot
        self.engine = engine
        self.signal = signal("finish")
        self.controller = controller.GameController()

    __game_start_quotes = [
        "In the ashes of Mecatol Rex, the galaxy trembles. Ancient rivalries stir, alliances are whispered in shadow, and war fleets awaken from slumber. The throne is empty… but not for long.\n-$player",
        "The age of peace is over. Steel will be our currency, blood our tribute. Let the weak hide behind treaties — we will claim the stars themselves.\n-$player",
        "Our fleets are in position. Every planet is a resource, every neighbour a pawn. The throne will be ours… through persuasion or annihilation.\n-$player",
        "Attention, denizens of the galaxy: the Lazax are no more. The throne stands vacant. May the worthy rise… and the unworthy perish.\n-$player",
    ]

    __game_end_quotes = [
        "The galaxy falls silent. The throne is claimed by $winner, and a new era begins.",
        "From the ruins of war, a ruler emerges. $winner's will shall shape the stars.",
        "The council is dissolved. All voices bow to $winner — the new master of Mecatol Rex.",
        "War fleets drift like shadows, but $winner's banner flies above them all.",
        "The game is over. The galaxy belongs to $winner, bold enough to take it.",
        "Power is not given; it is seized. Today, history remembers $winner.",
        "In the wake of conquest, the galaxy is remade in $winner's image.",
        "The war for Mecatol Rex has ended — but the scars of $loser will never fade.",
    ]

    @staticmethod
    def __game_start_quote(player_name: str) -> str:
        return Template(random.choice(GameLogic.__game_start_quotes)).safe_substitute(
            player=player_name
        )

    @staticmethod
    def __game_end_quote(winner: str, loser: str) -> str:
        return Template(random.choice(GameLogic.__game_end_quotes)).safe_substitute(
            winner=winner, loser=loser
        )

    _introduction = """These are some resources that can be useful for your game
- https://www.youtube.com/watch?v=_u2xEap5hBM (Twilight Imperium 4th edition in 32 minutes)
- https://www.youtube.com/watch?v=gdpW4FBCUuo (Common Twilight Imperium Rules Mistakes 1)
- https://www.youtube.com/watch?v=Jk5PA4EUGJw (Common Twilight Imperium Rules Mistakes 2)

Learn to play compressed
- https://images-cdn.fantasyflightgames.com/filer_public/f3/c6/f3c66512-8e19-4f30-a0d4-d7d75701fd37/ti-k0289_learn_to_playcompressed.pdf

Living rules reference (Prophecy of Kings)
- https://images-cdn.fantasyflightgames.com/filer_public/51/55/51552c7f-c05c-445b-84bf-4b073456d008/ti10_pok_living_rules_reference_20_web.pdf"""

    @staticmethod
    def _parse_ints(s):
        return list(map(int, re.findall(r"-?\d+", s)))

    # Extract this to a utility module. It's being used everywhere and is generic enough.
    # Could even be made more generic by extracting a custom key extractor.
    # E.g. comparing some internal field of the object.
    @staticmethod
    def _closest_match(s: str, ss: Iterable[str], cutoff=0.1) -> str | None:
        best = max(ss, key=lambda c: Levenshtein.ratio(s, c))
        if Levenshtein.ratio(s, best) <= cutoff:
            return None
        return best

    def __finish_game(self, session: Session, game: model.Game) -> None:
        game.game_state = model.GameState.FINISHED
        game.game_finish_time = datetime.now()
        session.merge(game)

    def __end_game_message(
        self, game: model.Game, players: Sequence[model.GamePlayer]
    ) -> str:
        lines = [
            f"{i+1}. {p.player.name} played {p.faction} and finished with {p.points} point(s)"
            for i, p in enumerate(players)
        ]
        msg = (
            f"Game '{game.name}' has finished\n\n"
            f"Players:\n{"\n".join(lines)}\n\n"
            f"> {self.__game_end_quote(players[0].player.name, players[-1].player.name)}\n\n"
            "Wrong result? Rerun the !finish command."
        )
        return "\n".join(lines) + msg

    def finish(
        self, is_admin: bool, game_id: int, all_points: Optional[str]
    ) -> Result[str]:
        with Session(self.engine) as session:
            try:
                game = session.get(model.Game, game_id)
                if not game:
                    return Err("Game not found.")
                if is_admin and game.game_state == model.GameState.FINISHED:
                    # Admins can update finished games.
                    pass
                elif game.game_state != model.GameState.STARTED:
                    return Err(
                        f"Can't finish game. Game is in {game.game_state.value} state."
                    )

                players = self.controller.players_ordered_by_turn(session, game)
                lines = [p.player.name for p in players]

                if not all_points:
                    return Err(
                        f"Players\n{"\n".join(lines)}\n\n"
                        "Specify the points based on the player order. "
                        "E.g. !finish 2 10 to give player A 2 points and player B 10 points"
                    )

                for player, points in zip(players, self._parse_ints(all_points)):
                    player.points = points
                session.add_all(players)

                self.__finish_game(session, game)
                players = self.controller.players_ordered_by_points(session, game)
                msg = self.__end_game_message(game, players)
                session.commit()

                self.signal.send(None, game_id=game.game_id)
                return Ok(msg)
            except Exception as e:
                logging.error(f"Can't finish game: {e}")
                return Err("Can't finish game. Something went wrong.")

    async def ban(
        self, player_id: int, game_id: int, faction: Optional[str] = None
    ) -> Optional[str]:
        try:
            with Session(self.engine) as session:
                game = session.get(model.Game, game_id)
                if not game:
                    return "No game found."

                if game.game_state != model.GameState.BAN:
                    return "Game is not in ban stage."

                player = self.controller.player_from_game(session, game, player_id)
                if not player:
                    return "You are not in this game!"

                return draftingmodes.GameMode.create(game).ban(session, player, faction)

        except Exception as e:
            logging.error(f"Error drafting: {e}")
            return "Something went wrong"

    async def draft(
        self, player_id: int, game_id: int, faction: Optional[str] = None
    ) -> str:
        try:
            with Session(self.engine) as session:
                game = session.get(model.Game, game_id)
                if not game:
                    return "No game found."
                if game.game_state != model.GameState.DRAFT:
                    return "Game is not in draft stage"

                player = self.controller.player_from_game(session, game, player_id)

                if not player:
                    return "You are not in this game!"

                draft_mode = draftingmodes.GameMode.create(game)

                error_message = draft_mode.draft(session, player, faction)

                if error_message:
                    return error_message

                return self._start_game(session, game, player.player.name)

        except Exception as e:
            logging.error(f"Error drafting: {e}")
            return "Something went wrong"

    def cancel(self, game_id: int) -> Result[str]:
        with Session(self.engine) as session:
            game = session.get(model.Game, game_id)
            if not game:
                return Err(f"No such game found")

            if game.game_state == model.GameState.FINISHED:
                return Err(f"Game has already finished.")

            session.delete(game)
            session.commit()
            return Ok(f"Successfully deleted {game.name}")

    def _start_game(self, session: Session, game: model.Game, name: str) -> str:
        players_info_lines = []
        for player in game.game_players:
            players_info_lines.append(f"{player.player.name} playing {player.faction}")

        game.game_state = model.GameState.STARTED
        session.merge(game)
        session.commit()
        return (
            f"# Game '{game.name}' has started\n"
            f"\nPlayers:\n{"\n".join(players_info_lines)}\n\n"
            ""
            f"> {GameLogic.__game_start_quote(name)}\n\n{self._introduction}"
        )

    def start(self, factions: fs.Factions, game_id: int) -> Result[str]:
        try:
            with Session(self.engine) as session:
                res = self._find_lobby(session, game_id)
                if isinstance(res, Err):
                    return res
                game = res.value
                return draftingmodes.GameMode.create(game).start(session, factions)

        except Exception as e:
            logging.error(f"Error fetching game data: {e}")
            return Err("An error occurred while fetching the game data.")

    def game(self, game_id) -> Result[str]:
        with Session(self.engine) as session:
            try:
                game = session.get(model.Game, game_id)
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

                match self.config(game.game_id, "get", None):
                    case Ok(s):
                        lines.append(s)
                return Ok("\n".join(lines))
            except Exception as e:
                logging.error(f"!game error: {e}")
                return Err("An error occurred while fetching the game data.")

    def lobbies(self) -> Result[str]:
        with Session(self.engine) as session:
            try:
                games = session.scalars(
                    select(model.Game)
                    .order_by(model.Game.lobby_create_time.desc())
                    .filter_by(game_state=model.GameState.LOBBY)
                ).all()
                if not games:
                    return Err("No games found.")
                lines = ["Open lobbies:"]
                for game in games:
                    lines.append(
                        f"- <#{game.game_id}> {game.name}. {len(game.game_players)} player(s)."
                    )
                return Ok("\n".join(lines))
            except Exception as e:
                logging.error(f"Error fetching game data: {e}")
                return Err("An error occurred while fetching the game data.")

    def _get_valid_values(self, dtype):
        if isinstance(dtype, Enum):
            return dtype.enums
        elif isinstance(dtype, Boolean):
            return [True, False]
        elif isinstance(dtype, Integer):
            return list(range(1,6))
        return []

    async def lobby(
        self, ctx: commands.Context, channel: discord.TextChannel, game_id: int, player_id: int, player_name: str, name: str
    ) -> Result[str]:
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

                lines = [
                    f"# Game lobby '{game.name}' created\n"
                    "Type !join to join the game. And !start to start the game",
                    f"Players: {player_name}.\n"
                    "Feel free to give some context like where and when you want to play.\n",
                    "-# Configure the game by using the !config command. Good luck!",
                ]
                await channel.send("\n".join(lines))
                settings = inspect(model.GameSettings)
                valid_keys: Dict[str, Any] = dict()
                for key, dtype in [(col.key, col.type) for col in settings.columns]:
                    if not ("game" in key and "id" in key):
                        valid_keys[key] = dtype
                thread = await channel.create_thread(name="Configuration", type=discord.ChannelType.public_thread)
                messages = []
                for k,v in valid_keys.items():
                    poll = discord.Poll(question=k, duration=timedelta(hours=24))
                    for opt in self._get_valid_values(v):
                        if isinstance(opt, enum.Enum):
                            opt = opt.name
                        poll.add_answer(text=str(opt))
                    messages.append(thread.send(poll=poll))

                awaited_messages = await asyncio.gather(*messages)
                for message in awaited_messages:
                    settings_poll = model.SettingsPoll(message_id=message.id, game_id=game_id, thread_id=thread.id)
                    session.add(settings_poll)
                await channel.send("Type !polls to apply the results of the polls to the configuration")
                session.commit()
                return Ok("")

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

    def leave(self, game_id: int, player_id: int) -> Result[str]:
        with Session(self.engine) as session:
            try:
                res = self._find_lobby(session, game_id)
                if isinstance(res, Err):
                    return res
                game = res.value

                gp = self.controller.player_from_game(session, game, player_id)

                if gp is None:
                    return Err("You are not in this game!")

                name = gp.player.name
                session.delete(gp)
                session.commit()
                if len(game.game_players) == 0:
                    return Ok(
                        f"All players have left the lobby. Admin can use !cancel to remove the lobby and channel"
                    )
                return Ok(
                    f"{name} has left lobby. Current number of players is {len(game.game_players)}. Type !join to join the lobby again."
                )

            except Exception as e:
                logging.error(f"Error leaving lobby: {e}")
                return Err("An error occurred while leaving the lobby.")

    def join(self, game_id: int, player_id: int, player_name: str) -> Result[str]:
        with Session(self.engine) as session:
            try:
                res = self._find_lobby(session, game_id)
                if isinstance(res, Err):
                    return res
                game = res.value

                gp = self.controller.player_from_game(session, game, player_id)
                if gp is not None:
                    return Err("You are already in this lobby!")

                number_of_players = len(game.game_players) if game.game_players else 0
                if number_of_players >= 8:
                    return Err(
                        f"Player limit reached. {number_of_players} have joined the game"
                    )

                player = model.Player(player_id=player_id, name=player_name)
                session.merge(player)
                game_player = model.GamePlayer(
                    game_id=game.game_id,
                    player_id=player_id,
                )
                session.add(game_player)
                session.commit()
                return Ok(
                    "{player_name} has joined lobby. "
                    f"Current number of players {number_of_players+1}. "
                    "Type !leave to leave the lobby."
                )
            except Exception as e:
                logging.error(f"Error joining lobby: {e}")
                return Err("An error occurred while joining the lobby.")

    def games(self, game_limit: int = 5) -> Result[str]:
        with Session(self.engine) as session:
            try:
                games = session.scalars(
                    select(model.Game)
                    .order_by(model.Game.game_finish_time.desc())
                    .filter_by(game_state=model.GameState.FINISHED)
                    .limit(game_limit)
                ).all()
                if not games:
                    return Err(f"No games found.")
                lines = []
                for game in games:
                    winner = self.controller.winner(session, game)
                    lines.append(
                        f"{game.name}. Winner {f"{winner.player.name} ({winner.faction})" if winner else "Unknown"}"
                    )
                return Ok("\n".join(lines))
            except Exception as e:
                logging.error(f"Error fetching game data: {e}")
                return Err("An error occurred while fetching the game data.")

    def config(
        self, game_id: int, property: Optional[str], value: Optional[str]
    ) -> Result[str]:
        """Configure a game session"""
        with Session(self.engine) as session:
            try:
                game = session.get(model.Game, game_id)
                if not game:
                    return Err("No lobby found.")

                def get_valid_values(dtype):
                    if isinstance(dtype, Enum):
                        return dtype.enums
                    elif isinstance(dtype, Boolean):
                        return [True, False]
                    return None

                settings = inspect(model.GameSettings)
                valid_keys: Dict[str, Any] = dict()
                for key, dtype in [(col.key, col.type) for col in settings.columns]:
                    if not ("game" in key and "id" in key):
                        valid_keys[key] = dtype

                if not property or not value:
                    game_settings = session.get(model.GameSettings, game.game_id)
                    ret = "Configuration:\n"
                    ret += "Use !config factions_per_player 5 to update a setting for example."
                    for key, dtype in valid_keys.items():
                        ret += f"* {key}:\n"
                        set_config = getattr(game_settings, key)

                        if isinstance(set_config, enum.Enum):
                            set_config = set_config.name

                        valid_values = get_valid_values(dtype)
                        if not valid_values:
                            ret += f"  - **{set_config}**\n"
                            continue
                        for data in valid_values:
                            if data == set_config:
                                ret += f"  - **{data}**\n"
                            else:
                                ret += f"  - {data}\n"
                    return Ok(ret)

                if game.game_state != model.GameState.LOBBY:
                    return Err("Game is not in lobby. Can't change config now")

                valid_properties = valid_keys.keys()
                best_prop = GameLogic._closest_match(property, valid_properties)
                if not best_prop:
                    return Err(
                        "Cannot understand which property you mean. Please check your spelling."
                    )
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

                game_settings = session.get(model.GameSettings, game_id)
                setattr(game_settings, property, new_value)
                session.commit()
                return Ok(f"Set property '{property}' to '{new_value}'")

            except Exception as e:
                logging.error(f"Error configuring lobby: {e}")
                return Err("An error occurred while configuring the lobby.")

    async def apply_poll_results(self, game_id: int) -> Result[str]:
        with Session(self.engine) as session:
            try:
                messages = session.scalars(
                    select(model.SettingsPoll)
                    .filter_by(game_id=game_id)
                ).all()
                lines = ["Poll results are:"]
                polls = []

                if not messages:
                    return Err("Polls can not be found")

                thread = self.bot.get_channel(messages[0].thread_id)
                if not isinstance(thread, discord.Thread):
                    return Err("Polls can not be found")
                msgs = await asyncio.gather(*[thread.fetch_message(message.message_id) for message in messages])

                for msg in msgs:
                    if not msg.poll:
                        continue
                    poll = msg.poll
                    answer = max(poll.answers, key=lambda c: c.vote_count)
                    lines.append(f"{poll.question}: {answer.text} with {answer.vote_count}")

                    game_settings = session.get(model.GameSettings, game_id)

                    # Coerce the poll answer into the type we want.
                    t = type(getattr(game_settings, poll.question))
                    setattr(game_settings, poll.question, t(answer.text))

                lines.append("See !config for the updated values.")
                session.commit()
                return Ok("\n".join(lines))
            except Exception as e:
                logging.error(f"Error fetching polls data: {e}")
                return Err("An error occurred while fetching the game data.")
