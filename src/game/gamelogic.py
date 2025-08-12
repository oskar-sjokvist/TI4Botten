import logging
import re
import random
import Levenshtein

from . import factions as fs
from . import controller
from . import model

from itertools import batched
from sqlalchemy.orm import Session
from typing import Optional

_game_start_quotes = [
    "In the ashes of Mecatol Rex, the galaxy trembles. Ancient rivalries stir, alliances are whispered in shadow, and war fleets awaken from slumber. The throne is empty… but not for long.",
    "The age of peace is over. Steel will be our currency, blood our tribute. Let the weak hide behind treaties — we will claim the stars themselves.",
    "Our fleets are in position. Every planet is a resource, every neighbour a pawn. The throne will be ours… through persuasion or annihilation.",
    "Attention, denizens of the galaxy: the Lazax are no more. The throne stands vacant. May the worthy rise… and the unworthy perish.",
]

_game_end_quotes = [
    "The galaxy falls silent. The throne is claimed, and a new era begins.",
    "From the ruins of war, a ruler emerges. Their will shall shape the stars.",
    "The council is dissolved. All voices bow to one — the new master of Mecatol Rex.",
    "War fleets drift like shadows, but the victor’s banner flies above them all.",
    "The game is over. The galaxy belongs to those bold enough to take it.",
    "Power is not given; it is seized. Today, history remembers the conqueror.",
    "In the wake of conquest, the galaxy is remade in the victor’s image.",
    "The war for Mecatol Rex has ended — but the scars will never fade."
]


def _parse_int_pairs(s):
    nums = list(map(int, re.findall(r"-?\d+", s)))
    if len(nums) % 2 != 0:
        raise ValueError(f"Odd number of integers found in '{s}'")
    return [(nums[i], nums[i+1]) for i in range(0, len(nums), 2)]

def finish(session : Session, is_admin : bool, game_id: Optional[int], rankings: Optional[str]) -> str:
    if not game_id:
        return "Please specify a game id."
    try:
        game = session.query(model.Game).filter_by(game_id=game_id).first()
        if not game:
            return "Game not found."
        if is_admin and game.game_state == model.GameState.FINISHED:
            # Admins can update finished games.
            pass
        elif game.game_state != model.GameState.STARTED:
            return f"Can't finish game. Game is in {game.game_state.value} state."

        players = controller.players_ordered_by_turn(session, game)
        lines = [p.player.name for p in players]

        if not rankings:
            return f"Players\n{"\n".join(lines)}\n\nSpecify the ranking and points based on the player order. E.g. !finish game_id 1 3, 2 5"

        try:
            for player, (rank, points) in zip(players, _parse_int_pairs(rankings)):
                player.rank = rank
                player.points = points
        except: 
            return f"Players\n{"\n".join(lines)}\n\nSpecify the ranking and points based on the player order. E.g. !finish game_id 1 3, 2 5"

        session.add_all(players)
        game.game_state = model.GameState.FINISHED
        session.merge(game)
        session.commit()

        players = session.query(model.GamePlayer).with_parent(game).order_by(model.GamePlayer.rank.asc()).all()
        lines = [f"{p.rank}. {p.player.name} played {p.faction} and finished with {p.points} point(s)" for p in players]
        return f"Game '{game.name}' #{game.game_id} has finished\n\nPlayers:\n{"".join(lines)}\n\n{random.choice(_game_end_quotes)}\n\nWrong result? Rerun the !finish command."
    except Exception as e:
        logging.error(f"Can't finish game: {e}")
        return "Can't finish game. Something went wrong."


def draft(session: Session, player_id: int,  game_id: Optional[int] = None, faction: Optional[str] = None) -> str:
    try:
        if game_id is None:
            game = model.Game.latest_draft(session)
        else:
            game = session.query(model.Game).filter_by(game_id=game_id).first()
        if not game:
            return "No game found."
        if game.game_state != model.GameState.DRAFT:
            return "Game is not in draft stage"

        player = session.query(model.GamePlayer).with_parent(game).filter_by(player_id=player_id).first()
        if not player:
            return "You are not in this game!"
        if player.faction:
            return "You have drafted {player.faction}"

        if not faction:
           return f"Your available factions are:\n{"\n".join(player.factions)}"
        
        current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()
        if not current_drafter:
            raise LookupError

        if game.turn != player.turn_order:
            return f"It is not your turn to draft! It is {current_drafter.player.name}'s turn"
            
        cutoff = 0.1
        factions = player.factions
        best = max(factions, key=lambda c: Levenshtein.ratio(faction, c))
        if Levenshtein.ratio(faction, best) <= cutoff:
           return f"You can't draft faction {faction}. Check your spelling or available factions."
        
        player.faction = best
        game.turn += 1

        session.merge(game)
        session.merge(player)
        session.commit()
        lines = [f"{player.player.name} has selected {player.faction}."]
        if game.turn == len(game.game_players):
            players_info_lines = []
            for player in game.game_players:
                players_info_lines.append(f"{player.player.name} playing {player.faction}")
            
            game.game_state = model.GameState.STARTED
            session.merge(game)
            session.commit()
            return f"Game '{game.name}' #{game.game_id} has started\n\nPlayers:\n{"".join(players_info_lines)}\n\n{random.choice(_game_start_quotes)}"

        current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()

        lines.append("Next drafter is <@{current_drafter.player_id}>. Use !draft.")
        return "\n".join(lines)

    except Exception as e:
        logging.error(f"Error drafting: {e}")
        return "Something went wrong"

def start(session: Session, factions : fs.Factions, game_id: Optional[int] = None) -> str:
    try:
        if game_id is None:
            game = model.Game.latest_lobby(session)
        else:
            game = session.query(model.Game).filter_by(game_id=game_id).first()
        if not game:
           return "No lobby found."

        if game.game_state != model.GameState.LOBBY:
           return "Given game is not a lobby"

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
           return "Only exclusive pool supported at the moment"
        
        players = game.game_players
        number_of_players = len(players)

        factions_per_player = 4
        fs = factions.get_random_factions(number_of_players, ','.join(sources))
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

        players_info_lines = []
        for i in range(number_of_players):
            name = player_from_turn[i]
            players_info_lines.append(f"{name}\n")

        game.game_state = model.GameState.DRAFT
        session.merge(game)
        session.commit()

        lines = [f"Game ID: {game.game_id}\nState: {game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\nSettings:\n{"\n".join(settings)}\n\nFactions:\n{"\n".join(factions_lines)}"]

        current_drafter = session.query(model.GamePlayer).with_parent(game).filter_by(turn_order=game.turn).first()
        if current_drafter is None:
            raise LookupError

        lines.append(f"<@{current_drafter.player_id}> begins drafting. Use !draft.")
        return "\n".join(lines)

    except Exception as e:
        logging.error(f"Error fetching game data: {e}")
        return "An error occurred while fetching the game data."


def lobby(session: Session, name: Optional[str]) -> str:
        if not name:
            return "Please specify a name for the lobby"
        try:
            game = model.Game(game_state="LOBBY", name=name)
            session.add(game)
            session.flush()
            settings = model.GameSettings(game_id=game.game_id)
            session.add(settings)
            session.commit()

            return f"Game lobby '{game.name}' created with ID {game.game_id}. Type !join {game.game_id} to join the game. And !start {game.game_id} to start the game"
        except Exception as e:
            logging.error(f"Error creating game: {e}")
            return "An error occurred while creating the game."


def leave(session: Session, player_id : int, game_id: Optional[int]) -> str:
    try:
        if game_id is None:
            game = model.Game.latest_lobby(session)
        else:
            game: Optional[model.Game] = session.query(model.Game).get(game_id)
        if game is None:
            return f"No lobby with game id {game_id}"

        gp = session.query(model.GamePlayer).with_parent(game).filter(model.GamePlayer.player_id==player_id).first()

        if gp is None:
            return "You are not in this game!"

        name = gp.player.name
        session.delete(gp)
        session.commit()
        return f"{name} has left lobby #{game.game_id}. Current number of players {len(game.game_players)}. Type !join {game.game_id} to join the lobby again."

    except Exception as e:
        logging.error(f"Error leaving lobby: {e}")
        return "An error occurred while leaving the lobby."



def join(session: Session, player_id : int, player_name : str, game_id : Optional[int]) -> str:
        try:
            if game_id is None:
                game = model.Game.latest_lobby(session)
            else:
                game = session.query(model.Game).get(game_id)

            if game is None:
                return f"No lobby found."

            if game.game_state != model.GameState.LOBBY:
                return "Game is not a lobby!"

            gp = session.query(model.GamePlayer).with_parent(game).filter(model.GamePlayer.player_id==player_id).first()
            if gp is not None:
                return "You are already in this lobby!"

            number_of_players = len(game.game_players) if game.game_players else 0
            if number_of_players >= 8:
                return f"Player limit reached. {number_of_players} have joined the game"
            
            
            player = model.Player(player_id=player_id, name=player_name)
            session.merge(player)
            game_player = model.GamePlayer(
                game_id=game.game_id,
                player_id=player_id,
            )
            session.add(game_player)
            session.commit()
            return f"{player_name} has joined lobby '{game.name}'. Current number of players {number_of_players+1}. Type !leave {game.game_id} to leave the lobby."
        except Exception as e:
            logging.error(f"Error joining lobby: {e}")
            return "An error occurred while joining the lobby."



def games(session : Session) -> str:
    try:
        games = session.query(model.Game).order_by(model.Game.game_id.desc()).filter_by(game_state=model.GameState.FINISHED).limit(5).all()
        if not games:
            return f"No games found."
        lines = []
        for game in games:
            winner = session.query(model.GamePlayer).with_parent(game).order_by(model.GamePlayer.rank.asc()).first()
            lines.append(f"#{game.game_id}: {game.name}. Winner {f"{winner.player.name} ({winner.faction})" if winner else "Unknown"}")
        return "\n".join(lines)
    except Exception as e:
        logging.error(f"Error fetching game data: {e}")
        return "An error occurred while fetching the game data."