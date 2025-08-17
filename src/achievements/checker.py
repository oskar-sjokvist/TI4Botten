import logging
from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from . import model as achievements_model
from ..rating import model as rating_model
from ..game import model as game_model


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

    def check(self, achievement: achievements_model.Achievement, player_id: int) -> Dict[str, Any]:
        """Evaluate whether `player_id` satisfies `achievement`'s rule_json.

        Currently supports rule_json of type "counter" with keys:
          - counter_key: str
          - target: int

        Returns a result dict, e.g.
          {"achieved": True, "already_unlocked": False, "counter_key": "games_won", "current": 12, "target": 10}
        """
        try:
            with Session(self.engine) as session:
                # If already unlocked, report as achieved
                if self._is_unlocked(session, achievement.achievement_id, player_id):
                    return {
                        "achieved": True,
                        "already_unlocked": True,
                        "message": "Already unlocked",
                    }

                rule = (achievement.rule_json or {}) if getattr(achievement, "rule_json", None) is not None else {}
                rtype = rule.get("type")

                if rtype == "counter":
                    counter_key = rule.get("counter_key")
                    target = rule.get("target")
                    if not counter_key or target is None:
                        return {"achieved": False, "message": "Invalid counter rule (missing counter_key or target)"}

                    current = self._get_counter(session, counter_key, player_id)
                    achieved = int(current) >= int(target)
                    return {
                        "achieved": achieved,
                        "already_unlocked": False,
                        "counter_key": counter_key,
                        "current": current,
                        "target": int(target),
                    }

                if rtype == "head_to_head":
                    # rule expects: opponent_name (str) and target (int)
                    opponent_name = rule.get("opponent_name")
                    target = rule.get("target")
                    if not opponent_name or target is None:
                        return {"achieved": False, "message": "Invalid head_to_head rule (missing opponent_name or target)"}

                    # Resolve opponent player_id via game Player table
                    opponent_player = session.scalar(
                        select(game_model.Player).filter_by(name=opponent_name)
                    )
                    if not opponent_player:
                        return {"achieved": False, "message": f"Opponent not found: {opponent_name}"}

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

                    print(">>>>>>>> JAKE", current, target)
                    achieved = int(current) >= int(target)
                    return {
                        "achieved": achieved,
                        "already_unlocked": False,
                        "opponent": opponent_name,
                        "current": current,
                        "target": int(target),
                    }

                # Unknown or unsupported rule types
                return {"achieved": False, "message": f"Unsupported rule type: {rtype}"}
        except Exception as e:  # pragma: no cover - surface DB/runtime errors
            logging.exception("Error while checking achievement rule")
            return {"achieved": False, "message": "error while evaluating rule"}
