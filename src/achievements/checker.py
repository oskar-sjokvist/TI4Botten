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
from .achievementtype import *
from .rules import head_to_head, finish, player as player_rule


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
                    return head_to_head(session, rule, player_id)
                if rtype == "finish":
                    return finish(session, rule, player_id)
                if rtype == "player":
                    return player_rule(session, rule, player_id)

                # Unknown or unsupported rule types
                return f"Unsupported rule type: {rtype}"
        except Exception as e:  # pragma: no cover - surface DB/runtime errors
            logging.exception("Error while checking achievement rule")
            return "Error while evaluating rule"
