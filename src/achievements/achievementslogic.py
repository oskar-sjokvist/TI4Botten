import logging

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from . import model as achievements_model


class AchievementsLogic:
    """Simple logic around achievements.

    Currently supports listing achievements for a player and showing progress
    for counter-based achievement rules. The command handlers expect
    a synchronous method that returns a string message.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine

    def achievements(self, player_id: int) -> str:
        """Return a human-readable list of unlocked and locked achievements for player_id."""
        try:
            with Session(self.engine) as session:
                # Load all active achievements
                all_ach = session.scalars(
                    select(achievements_model.Achievement).filter_by(is_active=True)
                ).all()

                if not all_ach:
                    return "No achievements defined."

                # Load player's unlocked achievements
                unlocked = session.scalars(
                    select(achievements_model.PlayerAchievement).filter_by(player_id=player_id)
                ).all()

                unlocked_ids = {u.achievement_id for u in unlocked}

                # Load player progress counters
                progress_rows = session.scalars(
                    select(achievements_model.PlayerProgress).filter_by(player_id=player_id)
                ).all()
                progress_map = {p.counter_key: p.value for p in progress_rows}

                lines = [f"Achievements for player {player_id}:"]

                # Unlocked list
                if unlocked:
                    lines.append(f"\nUnlocked ({len(unlocked)}):")
                    for u in unlocked:
                        a = u.achievement
                        unlocked_at = (
                            u.unlocked_at.strftime("%Y-%m-%d %H:%M:%S")
                            if getattr(u, "unlocked_at", None)
                            else "unknown"
                        )
                        lines.append(f"- {a.name} ({a.points} pts) — unlocked {unlocked_at}")
                else:
                    lines.append("\nUnlocked (0): None")

                # Locked achievements and progress
                locked = [a for a in all_ach if a.achievement_id not in unlocked_ids]
                if locked:
                    lines.append(f"\nLocked ({len(locked)}):")
                    for a in locked:
                        # Try to extract simple counter progress from rule_json
                        progress_text = "Locked"
                        try:
                            rule = a.rule_json or {}
                            counter_key = rule.get("counter_key")
                            target = rule.get("target")
                            if counter_key and target is not None:
                                curr = progress_map.get(counter_key, 0)
                                progress_text = f"Progress: {curr}/{int(target)}"
                        except Exception:
                            progress_text = "Locked"

                        lines.append(f"- {a.name} ({a.points} pts) — {progress_text}")
                else:
                    lines.append("\nLocked (0): None")

                return "\n".join(lines)
        except Exception as e:
            logging.error(f"achievements: {e}")
            return "Something went wrong."
