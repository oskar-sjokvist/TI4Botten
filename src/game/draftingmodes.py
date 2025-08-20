from __future__ import annotations

# TODO: Clean up code here, make it more DRY

import random
import discord

from . import model, controller
from . import gamelogic
from . import factions as fs
from . import strategy_cards
from ..typing import *

from itertools import batched
from sqlalchemy.orm import Session, attributes
from typing import Optional, List, Dict


class GameMode:
    def __init__(self, game):
        self.game = game
        self.controller = controller.GameController()

    def _get_faction_sources(self) ->  str:
        game = self.game
        sources = []
        if game.game_settings.base_game_factions:
            sources.append("base")
        if game.game_settings.prophecy_of_kings_factions:
            sources.append("pok")

        if game.game_settings.discordant_stars_factions:
            sources.append("ds")

        if game.game_settings.codex_factions:
            sources.append("codex")
        return ",".join(sources)

    @classmethod
    def create(cls, game: model.Game) -> GameMode:
        match game.game_settings.drafting_mode:
            case model.DraftingMode.EXCLUSIVE_POOL:
                return ExclusivePool(game)
            case model.DraftingMode.PICKS_ONLY:
                return PicksOnly(game)
            case model.DraftingMode.PICKS_AND_BANS:
                return PicksAndBans(game)
            case model.DraftingMode.HOMEBREW_DRAFT:
                return HomeBrewDraft(game)
        return GameMode(game)

    def draft(
        self, session: Session, player: model.GamePlayer, faction: Optional[str]
    ) -> Optional[str]:
        return f"Mode {self.game.game_settings.drafting_mode} not implemented yet."

    def start(self, session: Session, factions: fs.Factions) -> Result[discord.Embed]:
        return Err(
            f"Drafting mode {self.game.game_settings.drafting_mode} not supported at the moment"
        )

    def ban(
        self, session: Session, player: model.GamePlayer, faction: Optional[str]
    ) -> Optional[str]:
        return f"Drafting mode {self.game.game_settings.drafting_mode} does not support bans"

class GameStarted:
    pass

class ExclusivePool(GameMode):
    def draft(
        self, session: Session, player: model.GamePlayer, faction: Optional[str]
    ) -> Result[discord.Embed|GameStarted]:
        if player.faction:
            return Ok(discord.Embed(
                title="Faction Drafted",
                description=f"You have drafted {player.faction}",
                color=discord.Color.green()
            ))

        if not faction:
            return Ok(discord.Embed(
                title="Available Factions",
                description=f"Your available factions are:\n{"\n".join(player.factions)}".replace('"\\n"', "'\\n'"),
                color=discord.Color.blue()
            ))

        current_drafter = self.controller.current_drafter(session, self.game)

        if self.game.turn != player.turn_order:
            return Err(f"It is not your turn to draft! It is {current_drafter.player.name}'s turn")

        # Extract this out to shared utils.
        best = gamelogic.GameLogic._closest_match(faction, player.factions)
        if not best:
            return Err(f"You can't draft faction {faction}. Check your spelling or available factions.")

        player.faction = best
        self.game.turn += 1

        session.merge(self.game)
        session.merge(player)
        lines = [f"{player.player.name} has selected {player.faction}."]
        if self.game.turn == len(self.game.game_players):
            return Ok(GameStarted())
        session.commit()
        current_drafter = self.controller.current_drafter(session, self.game)
        lines.append(f"Next drafter is <@{current_drafter.player_id}>. Use !draft.")

        return Ok(discord.Embed(
            title="Next Drafter",
            description=f"Next drafter is <@{current_drafter.player_id}>. Use !draft.",
            color=discord.Color.blue()
        ))

    def start(self, session: Session, factions: fs.Factions) -> Result[discord.Embed]:

        players = self.game.game_players
        number_of_players = len(players)

        factions_per_player = self.game.game_settings.factions_per_player
        fs = factions.get_random_factions(
            number_of_players * factions_per_player, self._get_faction_sources()
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
            f"State: {self.game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\nFactions:\n{"\n".join(factions_lines)}"
        ]

        current_drafter = self.controller.current_drafter(session, self.game)

        lines.append(f"<@{current_drafter.player_id}> begins drafting. Use !draft.")
        return Ok(discord.Embed(
            title="🎲 Drafting Phase",
            description="\n".join(lines),
            color=discord.Color.blue()
        ))

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

    def start(self, session: Session, factions: fs.Factions) -> Result[discord.Embed]:
        players = self.game.game_players
        number_of_players = len(players)

        turn_order = random.sample(range(number_of_players), number_of_players)

        total_factions = self.game.game_settings.factions_per_player*number_of_players
        fs = [faction.name for faction in factions.get_random_factions(total_factions, self._get_faction_sources())]

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
            f"State: {self.game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\n"
        ]

        lines.append("Available factions are:")
        lines.extend(fs)
        current_drafter = self.controller.current_drafter(session, self.game)
        lines.append(f"<@{current_drafter.player_id}> begins drafting. Use !draft.")
        return Ok(discord.Embed(
            title="🛡️ Drafting Started!",
            description="\n".join(lines),
            color=discord.Color.green()
        ))


class PicksAndBans(GameMode):
    def draft(
        self,
        session: Session,
        player: model.GamePlayer,
        faction: Optional[str],
    ) -> Optional[str]:

        if player.faction:
            return f"You have drafted {player.faction}"

        if not faction:
            return f"Your available factions are:\n{"\n".join(player.factions)}"

        current_drafter = self.controller.current_drafter(session, self.game)

        if self.game.turn != player.turn_order:
            return f"It is not your turn to draft! It is {current_drafter.player.name}'s turn"

        all_bans = []
        for game_player in self.game.game_players:
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
        self.game.turn += 1

        other_players = [
            other for other in self.game.game_players if other.player_id != player.player_id
        ]
        for other_player in other_players:
            # Somehow the typing doesn't work without the if-statement
            # Look into it later.
            if player.faction:
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

    def start(self, session: Session, factions: fs.Factions) -> Result[discord.Embed]:
        players = self.game.game_players
        number_of_players = len(players)

        turn_order = random.sample(range(number_of_players), number_of_players)

        total_factions = self.game.game_settings.factions_per_player*number_of_players
        fs = [faction.name for faction in factions.get_random_factions(total_factions, self._get_faction_sources())]

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
            f"State: {self.game.game_state.value}\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\n"
        ]
        lines.append("Available factions are:")
        lines.extend(fs)

        current_drafter = self.controller.current_drafter(session, self.game)
        lines.append(f"<@{current_drafter.player_id}> begins banning. Use !ban.")
        return Ok(discord.Embed(
            title="🛡️ Banning Started!",
            description="\n".join(lines),
            color=discord.Color.green()
        ))


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



class HomeBrewDraft(GameMode):
    def draft(
        self,
        session: Session,
        player: model.GamePlayer,
        draft_choice: Optional[str],
    ) -> Result[discord.Embed|GameStarted]:

        if player.faction and player.position and player.strategy_card:
            return Ok(discord.Embed(
                title="Drafting phase",
                description=f"You have drafted {player.faction}, starting with {player.strategy_card} in position {player.position}",
                color=discord.Color.green()
            ))


        strategy_cards_map : Dict[str, strategy_cards.StrategyCard] = {sc.name.lower(): sc for sc in strategy_cards.read_strategy_cards()}
        available_strategy_cards: Dict[str, strategy_cards.StrategyCard] = {sc.name.lower(): sc for sc in strategy_cards_map.values() if sc.name not in [other.strategy_card for other in self.game.game_players if other.strategy_card]}
        available_positions: List[int] = [x for x in range(1, len(self.game.game_players) + 1) if x not in [other.position for other in self.game.game_players if other.position]]

        lines = []
        if not draft_choice:
            if not player.faction:
                lines.append("You may draft **Faction**.")
            if not player.strategy_card:
                lines.append("You may draft **Strategy card**.")
            if not player.position:
                lines.append("You may draft **Starting position**.")
            if not player.faction:
                lines.append(f"\nYour available Factions are:\n* {"\n* ".join(player.factions)}")
            if not player.strategy_card:
                lines.append(f"\nYour available Strategy cards are:\n{"\n".join([str(sc) for sc in sorted(available_strategy_cards.values(), key=lambda x: x.initiative_order)])}")
            if not player.position:
                lines.append(f"\nYour available Starting positions are: {", ".join(map(str,available_positions))}")
            return Ok(discord.Embed(
                title="Draft Options",
                description="\n".join(lines),
                color=discord.Color.blue()
            ))

        current_drafter = self.controller.current_drafter(session, self.game)

        if self.game.turn != player.turn_order:
            return Err(f"It is not your turn to draft! It is {current_drafter.player.name}'s turn")


        def get_direction(game: model.Game) -> int:
            num_drafts = sum([bool(player.faction) + bool(player.strategy_card) + bool(player.position) for player in game.game_players])
            return 1 if ((num_drafts // len(game.game_players)) % 2) == 0 else -1

        # This is used later, but need to be calculated before the drafting
        direction = get_direction(self.game)

        all_bans: List[str] = []
        for game_player in self.game.game_players:
            if game_player.bans:
                all_bans.extend(game_player.bans)

        available_factions = player.factions.copy()
        available_factions.extend(all_bans)

        # Draft position
        if draft_choice.isdigit():
            if not player.position:
                if int(draft_choice) not in available_positions:
                    return Err(f"You can't draft position {draft_choice}.")
                else:
                    player.position = int(draft_choice)
                    lines.append(f"Player <@{current_drafter.player_id}> drafted position {player.position}")
            else:
                return Err("You've already drafted position")
        # Draft strategy card
        elif draft_choice.lower() in strategy_cards_map.keys():
            if not player.strategy_card:
                if draft_choice.lower() not in available_strategy_cards.keys():
                    return Err(f"Strategy card {available_strategy_cards[draft_choice.lower()].name} is already picked.")
                else:
                    player.strategy_card = available_strategy_cards[draft_choice.lower()].name
                    lines.append(f"Player <@{current_drafter.player_id}> drafted Strategy card {player.strategy_card}")
            else:
                return Err("You've already drafted Strategy card")

        # Check what the best match is. If it's a faction, draft faction
        else:
            possible_matches : Dict[str, Union[str, strategy_cards.StrategyCard]] = {x.lower(): x for x in available_factions}
            possible_matches.update({sc.name.lower(): sc for sc in strategy_cards_map.values()})
            
            best = gamelogic.GameLogic._closest_match(draft_choice.lower(), possible_matches.keys())
            if not best:
                return Err(f"Not possible to match {draft_choice} to anything. Check your spelling or available picks")
            if best in strategy_cards_map.keys():
                if not player.strategy_card:
                    return Err(f"Did you mean to draft {strategy_cards_map[best].name}? Strict spelling is enforced for strategy cards.")
                else:
                    return Err(f"Best match was {strategy_cards_map[best].name}, but you've already drafted Strategy card")
            if not player.faction:
                # Check if this faction is already banned by anyone
                value = possible_matches[best]
                if value in all_bans:
                    return Err(f"Faction {value} is banned.")
                if isinstance(value, str):
                    player.faction = value
                    lines = [f"<@{current_drafter.player_id}> has drafted {player.faction}."]
                else:
                    return Err("An error occurred when matching text to strategy card or faction.")
                
                # Update other players available factions
                other_players = [
                    other for other in self.game.game_players if other.player_id != player.player_id
                ]
                for other_player in other_players:
                    if player.faction:
                        other_player.factions.remove(player.faction)
                        session.merge(other_player)
            else:
                return Err("You've already drafted faction.")


        def check_draft_over(game: model.Game) -> bool:
            done = [bool(player.faction) and bool(player.strategy_card) and bool(player.position) for player in game.game_players]
            return all(done)

        self.game.turn += direction
            
        session.merge(player)
        if self.game.turn == -1 or self.game.turn == len(self.game.game_players):
            if check_draft_over(self.game):
                session.merge(self.game)
                session.commit()
                return Ok(GameStarted())
            else:
                # Flip direction and go back.
                self.game.turn -= direction
        session.merge(self.game)
        session.commit()

        current_drafter = self.controller.current_drafter(session, self.game)

        lines.append(f"Next drafter is <@{current_drafter.player_id}>. Use !draft.")
        return Ok(discord.Embed(
            title="Next Drafter",
            description="\n".join(lines),
            color=discord.Color.blue()
        ))

    def start(self, session: Session, factions: fs.Factions) -> Result[discord.Embed]:

        self.direction: int = 1

        players = self.game.game_players
        number_of_players = len(players)

        factions_per_player = self.game.game_settings.factions_per_player
        fs = factions.get_random_factions(
            number_of_players * factions_per_player, self._get_faction_sources()
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
            f"State: {self.game.game_state.value}\n\nSnake drafting enabled\n\nPlayers (in draft order):\n{"\n".join(players_info_lines)}\n\nFactions:\n{"\n".join(factions_lines)}"
        ]

        current_drafter = self.controller.current_drafter(session, self.game)

        lines.append(f"<@{current_drafter.player_id}> begins drafting. Use !draft.")
        return Ok(discord.Embed(
            title="🎲 Drafting Phase",
            description="\n".join(lines),
            color=discord.Color.blue()
        ))