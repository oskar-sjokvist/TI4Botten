from __future__ import annotations

# TODO: Clean up code here, make it more DRY

import random

from . import model, controller
from . import gamelogic
from . import factions as fs
from ..typing import *

from itertools import batched
from sqlalchemy.orm import Session, attributes
from typing import Optional, List, Tuple


class GameMode:
    def __init__(self, game):
        self.game = game
        self.controller = controller.GameController()

    def _get_start_settings(self) -> Tuple[List[str], List[str]]:
        game = self.game
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

    @classmethod
    def create(cls, game: model.Game) -> GameMode:
        match game.game_settings.drafting_mode:
            case model.DraftingMode.EXCLUSIVE_POOL:
                return ExclusivePool(game)
            case model.DraftingMode.PICKS_ONLY:
                return PicksOnly(game)
            case model.DraftingMode.PICKS_AND_BANS:
                return PicksAndBans(game)
        return GameMode(game)

    def draft(
        self, session: Session, player: model.GamePlayer, faction: Optional[str]
    ) -> Optional[str]:
        return f"Mode {self.game.game_settings.drafting_mode} not implemented yet."

    def start(self, session: Session, factions: fs.Factions) -> Result[str]:
        return Err(
            f"Drafting mode {self.game.game_settings.drafting_mode} not supported at the moment"
        )

    def ban(
        self, session: Session, player: model.GamePlayer, faction: Optional[str]
    ) -> Optional[str]:
        return f"Drafting mode {self.game.game_settings.drafting_mode} does not support bans"


class ExclusivePool(GameMode):
    def draft(
        self, session: Session, player: model.GamePlayer, faction: Optional[str]
    ) -> Optional[str]:
        if player.faction:
            return f"You have drafted {player.faction}"

        if not faction:
            return f"Your available factions are:\n{"\n".join(player.factions)}"

        current_drafter = self.controller.current_drafter(session, self.game)

        if self.game.turn != player.turn_order:
            return f"It is not your turn to draft! It is {current_drafter.player.name}'s turn"

        # Extract this out to shared utils.
        best = gamelogic.GameLogic._closest_match(faction, player.factions)
        if not best:
            return f"You can't draft faction {faction}. Check your spelling or available factions."

        player.faction = best
        self.game.turn += 1

        session.merge(self.game)
        session.merge(player)
        lines = [f"{player.player.name} has selected {player.faction}."]
        if self.game.turn == len(self.game.game_players):
            return None
        session.commit()
        current_drafter = self.controller.current_drafter(session, self.game)
        lines.append(f"Next drafter is <@{current_drafter.player_id}>. Use !draft.")

        return "\n".join(lines)

    def start(self, session: Session, factions: fs.Factions) -> Result[str]:

        settings, sources = self._get_start_settings()
        players = self.game.game_players
        number_of_players = len(players)

        factions_per_player = self.game.game_settings.factions_per_player
        fs = factions.get_random_factions(
            number_of_players * factions_per_player, ",".join(sources)
        )
        if len(fs) < number_of_players * factions_per_player:
            return Err(
                f"There are too many factions selected per player. Max allowed for a {number_of_players} player game is {len(fs)//number_of_players}."
            )
        fs = [faction.name for faction in fs]

        turn_order = random.sample(range(number_of_players), number_of_players)
        faction_slices = batched(fs, factions_per_player)

        factions_lines = []

        player_from_turn = {}
        for i, (player, player_factions) in enumerate(
            zip(self.game.game_players, faction_slices)
        ):
            player.turn_order = turn_order[i]
            player_from_turn[player.turn_order] = player.player.name
            player.factions = list(player_factions)
            factions_lines.extend(
                list(map(lambda x: f"{x} ({player.player.name})", player_factions))
            )
            session.merge(player)

        players_info_lines = []
        for i in range(number_of_players):
            name = player_from_turn[i]
            players_info_lines.append(f"{name}")

        self.game.game_state = model.GameState.DRAFT
        session.merge(self.game)
        session.commit()

        lines = [
            f"State: {self.game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\nSettings:\n{"\n".join(settings)}\n\nFactions:\n{"\n".join(factions_lines)}"
        ]

        current_drafter = self.controller.current_drafter(session, self.game)

        lines.append(f"<@{current_drafter.player_id}> begins drafting. Use !draft.")
        return Ok("\n".join(lines))


class PicksOnly(GameMode):
    def draft(
        self, session: Session, player: model.GamePlayer, faction: Optional[str]
    ) -> Optional[str]:

        if player.faction:
            return f"You have drafted {player.faction}"

        if not faction:
            return f"Your available factions are:\n{"\n".join(player.factions)}"

        current_drafter = self.controller.current_drafter(session, self.game)

        if self.game.turn != player.turn_order:
            return f"It is not your turn to draft! It is {current_drafter.player.name}'s turn"

        best = gamelogic.GameLogic._closest_match(faction, player.factions)
        if not best:
            return f"You can't draft faction {faction}. Check your spelling or available factions."

        player.faction = best
        self.game.turn += 1

        other_players = [
            other
            for other in self.game.game_players
            if other.player_id != player.player_id
        ]
        for other_player in other_players:
            other_player.factions.remove(player.faction)
            session.merge(other_player)

        session.merge(self.game)
        session.merge(player)
        lines = [f"{player.player.name} has selected {player.faction}."]
        if self.game.turn == len(self.game.game_players):
            return None
        session.commit()

        current_drafter = self.controller.current_drafter(session, self.game)

        lines.append(f"Next drafter is <@{current_drafter.player_id}>. Use !draft.")
        return "\n".join(lines)

    def start(self, session: Session, factions: fs.Factions) -> Result[str]:

        settings, sources = self._get_start_settings()
        players = self.game.game_players
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

        self.game.game_state = model.GameState.DRAFT
        session.merge(self.game)
        session.commit()

        lines = [
            f"State: {self.game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\nSettings:\n{"\n".join(settings)}"
        ]

        current_drafter = self.controller.current_drafter(session, self.game)
        lines.append(f"<@{current_drafter.player_id}> begins drafting. Use !draft.")
        return Ok("\n".join(lines))


class PicksAndBans(GameMode):
    def draft(
        self,
        session: Session,
        game: model.Game,
        player: model.GamePlayer,
        faction: Optional[str],
    ) -> Optional[str]:

        if player.faction:
            return f"You have drafted {player.faction}"

        if not faction:
            return f"Your available factions are:\n{"\n".join(player.factions)}"

        current_drafter = self.controller.current_drafter(session, game)

        if game.turn != player.turn_order:
            return f"It is not your turn to draft! It is {current_drafter.player.name}'s turn"

        all_bans = []
        for game_player in game.game_players:
            if game_player.bans:
                all_bans.extend(game_player.bans)

        all_factions_available = player.factions.copy()
        all_factions_available.extend(all_bans)

        best = gamelogic.GameLogic._closest_match(faction, all_factions_available)
        if not best:
            return f"You can't draft faction {faction}. Check your spelling or available factions."

        # Check if this faction is already banned by anyone

        if best in all_bans:
            return f"Faction {best} has already been banned."

        player.faction = best
        game.turn += 1

        other_players = [
            other for other in game.game_players if other.player_id != player.player_id
        ]
        for other_player in other_players:
            # Somehow the typing doesn't work without the if-statement
            # Look into it later.
            if player.faction:
                other_player.factions.remove(player.faction)
                session.merge(other_player)

        session.merge(game)
        session.merge(player)
        lines = [f"{player.player.name} has selected {player.faction}."]
        if game.turn == len(game.game_players):
            return None
        session.commit()

        current_drafter = self.controller.current_drafter(session, game)

        lines.append(f"Next drafter is <@{current_drafter.player_id}>. Use !draft.")
        return "\n".join(lines)

    def start(self, session: Session, factions: fs.Factions) -> Result[str]:
        settings, sources = self._get_start_settings()
        players = self.game.game_players
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

        self.game.game_state = model.GameState.BAN
        session.merge(self.game)
        session.commit()

        lines = [
            f"State: {self.game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\nSettings:\n{"\n".join(settings)}"
        ]

        current_drafter = self.controller.current_drafter(session, self.game)
        lines.append(f"<@{current_drafter.player_id}> begins banning. Use !ban.")
        return Ok("\n".join(lines))

    def ban(
        self, session: Session, player: model.GamePlayer, faction: Optional[str]
    ) -> Optional[str]:
        current_drafter = self.controller.current_drafter(session, self.game)
        all_bans = [
            banned
            for gameplayer in self.game.game_players
            for banned in gameplayer.bans
            if gameplayer.bans
        ]
        if not faction:
            lines = list()
            if self.game.game_state == model.GameState.BAN:
                lines.append(f"It is {current_drafter.player.name}'s turn to ban.")
            if all_bans:
                lines.append("These factions are banned:")
                lines.extend([f"* {f}" for f in all_bans])
            return "\n".join(lines)

        if current_drafter.player.player_id != player.player_id:
            return f"It is not your turn to ban! It is {current_drafter.player.name}'s turn"

        # Process the ban
        best = gamelogic.GameLogic._closest_match(faction, player.factions)
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
        for any_player in self.game.game_players:
            if best in any_player.factions:
                any_player.factions.remove(best)
                attributes.flag_modified(any_player, "factions")

        lines = [f"{player.player.name} has banned {best}."]

        number_of_players = len(self.game.game_players)

        total_bans_needed = number_of_players * self.game.game_settings.bans_per_player

        self.game.turn = (self.game.turn + 1) % number_of_players
        current_drafter = self.controller.current_drafter(session, self.game)

        if total_bans_needed == len(all_bans) + 1:
            self.game.game_state = model.GameState.DRAFT
            lines.append("Banning is now complete!")
            lines.append(
                f"Next one to draft is <@{current_drafter.player_id}>. Use !draft."
            )
        else:
            lines.append(
                f"Next one to ban is <@{current_drafter.player_id}>. Use !ban."
            )

        session.merge(player)
        session.merge(self.game)
        session.commit()

        return "\n".join(lines)
