import logging

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from dataclasses import dataclass

from . import model
from ..game import model as game_model
from .checker import AchievementChecker

from typing import Sequence, List

@dataclass
class LockedAchievement:
    name: str
    points: int
    current: int
    target: int


class AchievementsLogic:
    """Simple logic around achievements.

    Currently supports listing achievements for a player and showing progress
    for counter-based achievement rules. The command handlers expect
    a synchronous method that returns a string message.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.checker = AchievementChecker(engine)



    def update_achievements_and_obtain_locked(self, session: Session, all_ach: Sequence[model.Achievement], player_id: int) -> List[LockedAchievement]:
        locked = []
        for ach in all_ach:
            achieved = self.checker.check(ach, player_id)
            # The return type for check should be updated.
            # This is an ad-hoc check for errors.
            if hasattr(achieved, "already_unlocked"):
                logging.error(achieved["message"])
                continue
            if achieved["already_unlocked"]:
                continue
            if achieved['achieved']:
                session.add(model.PlayerAchievement(
                    achievement_id=ach.achievement_id,
                    player_id=player_id,
                    awarded_by="automation"
                ))
            else:
                locked.append(LockedAchievement(
                        name = ach.name,
                        points = ach.points,
                        current = achieved["current"],
                        target = achieved["target"],
                    ))
        session.flush()
        return locked
                


    def achievements(self, player_id: int) -> str:
        """Return a human-readable list of unlocked and locked achievements for player_id."""
        try:
            with Session(self.engine) as session:
                # Load all active achievements
                all_ach = session.scalars(
                    select(model.Achievement).filter_by(is_active=True)
                ).all()

                if not all_ach:
                    return "No achievements defined."
                


                locked = self.update_achievements_and_obtain_locked(session, all_ach, player_id)

                # Load player's unlocked achievements
                unlocked = session.scalars(
                    select(model.PlayerAchievement).filter_by(player_id=player_id)
                ).all()

                # Load player progress counters
                player = session.get(game_model.Player, player_id)
                if not player:
                    player = game_model.Player(player_id=player_id)
                    session.add(player)
                lines = [f"Achievements for player {player.name}:"]
                

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

                # Locked list
                if locked:
                    lines.append(f"\nLocked ({len(locked)}):")
                    for l in locked:
                        lines.append(f"- {l.name} ({l.points} pts) — Progress ({l.current}/{l.target})")
                else:
                    lines.append("\nlocked (0): None")
                return "\n".join(lines)

                
        except Exception as e:
            logging.error(f"achievements: {e}")
            return "Something went wrong."
