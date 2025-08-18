import logging
from typing import Any, Dict, Union, Optional
from dataclasses import dataclass

from sqlalchemy import select, func
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from . import model as achievements_model
from ..rating import model as rating_model
from ..game import model as game_model
from ..typing import *

@dataclass
class Achieved:
    """Marker for an achieved achievement."""


@dataclass
class Unlocked:
    """Marker for an already unlocked achievement."""

@dataclass
class Locked:
    current: Optional[int]
    target: Optional[int]


AchievementType = Achieved|Unlocked|Locked|str



class AchievementChecker:
    """Check achievement rules against DB rows for a given player.

    Usage:
      checker = AchievementChecker(engine)
      result = checker.check(achievement_row, player_id)

    Returns a dict with at least the key 'achieved' (bool) and other details.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def _is_unlocked(self, session: Session, achievement_id: str, player_id: int) -> bool:
        return session.get(achievements_model.PlayerAchievement, (player_id, achievement_id)) is not None

    def _get_counter(self, session: Session, counter_key: str, player_id: int) -> int:
        row = session.get(achievements_model.PlayerProgress, (player_id, counter_key))
        return int(row.value) if row is not None and getattr(row, "value", None) is not None else 0

    def _rule_head_to_head(self, session: Session, rule: Dict[str, Any], player_id: int) -> AchievementType:
        # rule expects: opponent_name (str) and target (int)
        opponent_name = rule.get("opponent_name")
        target = rule.get("target")
        if not opponent_name or target is None:
            return "Invalid head_to_head rule (missing opponent_name or target)"

        # Resolve opponent player_id via game Player table
        opponent_player = session.scalar(
            select(game_model.Player).filter_by(name=opponent_name)
        )
        if not opponent_player:
            return f"Opponent not found: {opponent_name}"

        # Map to MatchPlayer id (MatchPlayer.player_id references player.player_id)
        opponent_mp = session.scalar(
            select(rating_model.MatchPlayer).filter_by(player_id=opponent_player.player_id)
        )
        if not opponent_mp:
            # No match_player entry -> zero wins against them
            current = 0
        else:
            # Count WinnerHeadToHead rows where winner_id == player_id and loser_id == opponent_mp.player_id
            cnt = session.execute(
                select(rating_model.WinnerHeadToHead).filter_by(winner_id=player_id, loser_id=opponent_mp.player_id)
            ).all()
            current = len(cnt)

        if int(current) >= int(target):
            return Achieved()
        return Locked(
            current=current,
            target=target,
        )

    # Not fully implemented
    def _rule_finish(self, session: Session, rule: Dict[str, Any], player_id: int) -> AchievementType:
        target = rule.get("target")
        if target is None:
            return "Invalid finish rule (missing target)"

        stmt = (
            select(
                game_model.GamePlayer,
                func.count("*").label("played"),
            )
            .group_by(game_model.GamePlayer.player_id)
            .where(
                game_model.GamePlayer.player_id == player_id,
                game_model.GamePlayer.game.has(
                    game_state=game_model.GameState.FINISHED
                )
            )
        )

        filter_ = rule.get("filter")
        if isinstance(filter_, dict) and "points" in filter_:
            f = filter_["points"]
            match f["op"]:
                case "lte":
                    stmt = stmt.where(game_model.GamePlayer.points <= f.get("target"))
                case _:
                    return "Unsupported operation"
        if isinstance(filter_, dict) and "play_as_faction" in filter_:
            f = filter_["play_as_faction"]
            stmt = stmt.where(game_model.GamePlayer.faction == f)

        c = session.execute(stmt).one_or_none()
        if not c:
            return Locked(
                current=0,
                target=int(target),
            )
            
        current = c.played
        target = rule.get("target")
        if current >= target:
            return Achieved()
    
        return Locked(
            current=current,
            target=target,
        )

    def _rule_player(self, session: Session, rule: Dict[str, Any], player_id: int) -> AchievementType:
        target = rule.get("target")
        if target is None:
            return "Invalid player rule (missing target)"

        player = session.get(game_model.Player, player_id)
        if not player:
            return "Player not found"

        if player.name == target:
            return Achieved()
        return Locked(current=None, target=None)


    def check(self, achievement: achievements_model.Achievement, player_id: int) -> AchievementType:
        """Evaluate whether `player_id` satisfies `achievement`'s rule_json.
        """
        try:
            with Session(self.engine) as session:
                if self._is_unlocked(session, achievement.achievement_id, player_id):
                    return Unlocked()

                rule: Dict[str, Any] = (achievement.rule_json or {}) if getattr(achievement, "rule_json", None) is not None else {}
                rtype = rule.get("type")

                # Refactor this like we do for drafting modes.
                if rtype == "counter":
                    counter_key = rule.get("counter_key")
                    target = rule.get("target")
                    if not counter_key or target is None:
                        return "Invalid counter rule (missing counter_key or target)"

                    current = self._get_counter(session, counter_key, player_id)
                    achieved = int(current) >= int(target)
                    if achieved:
                        return Achieved()
                    return Locked(
                        current=current,
                        target=int(target),
                    )
                if rtype == "head_to_head":
                    return self._rule_head_to_head(session, rule, player_id)
                if rtype == "finish":
                    return self._rule_finish(session, rule, player_id)
                if rtype == "player":
                    return self._rule_player(session, rule, player_id)

                # Unknown or unsupported rule types
                return f"Unsupported rule type: {rtype}"
        except Exception as e:  # pragma: no cover - surface DB/runtime errors
            logging.exception("Error while checking achievement rule}")
            return "Error while evaluating rule"
