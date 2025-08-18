import logging

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from dataclasses import dataclass
from datetime import datetime

from . import model
from ..game import model as game_model
from .checker import AchievementChecker

from typing import Sequence, List, Optional
from ..typing import *

@dataclass
class Achievement:
    name: str
    points: int
    description: str
    unlocked_count: int
    current: Optional[int] = None
    target: Optional[int] = None
    unlocked_time: Optional[datetime] = None

@dataclass
class PlayerAchievements:
    name: str
    locked: List[Achievement]
    unlocked: List[Achievement]

    def string_view(self):
        lines = [f"## Achievements for player {self.name}:"]

        if self.unlocked:
            lines.append(f"### Unlocked ({len(self.unlocked)}):")
            for u in self.unlocked:
                lines.append(f"- {u.name} — unlocked at {u.unlocked_time}")
                lines.append(f"-# ({u.points} pts) {u.description}")
                if u.unlocked_count == 1:
                    lines.append(f"-# Only you have this achievement")
                if u.unlocked_count > 2:
                    lines.append(f"-# unlocked by {u.unlocked_count-1} other players")
        else:
            lines.append("### Unlocked (0): None")
        if self.locked:
            lines.append(f"### Locked ({len(self.locked)}):")
            for l in self.locked:
                progress = f" - Progress ({l.current}/{l.target})" if l.current and l.target else ""
                lines.append(f"- {l.name}{progress}")
                lines.append(f"-# ({l.points} pts) {l.description}")
                if l.unlocked_count > 0:
                    lines.append(f"-# unlocked by {l.unlocked_count} other players")
        else:
            lines.append("### Locked (0): None")
        return "\n".join(lines)


class AchievementsLogic:
    """Simple logic around achievements.

    Currently supports listing achievements for a player and showing progress
    for counter-based achievement rules. The command handlers expect
    a synchronous method that returns a string message.
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.checker = AchievementChecker(engine)
        with Session(engine) as session:
            ps = session.scalars(select(game_model.Player))
            for p in ps:
                self.achievements(p.player_id, p.name)



    def update_achievements_and_obtain_locked(self, session: Session, all_ach: Sequence[model.Achievement], player_id: int) -> List[Achievement]:
        locked = []
        for ach in all_ach:
            achieved = self.checker.check(ach, player_id)
            if "already_unlocked" not in achieved:
                if "message" in achieved:
                    logging.error(achieved["message"])
                continue
            if achieved['achieved']:
                session.add(model.PlayerAchievement(
                    achievement_id=ach.achievement_id,
                    player_id=player_id,
                    awarded_by="automation"
                ))
            else:
                locked.append(Achievement(
                        name = ach.name,
                        points = ach.points,
                        current = achieved.get("current"),
                        target = achieved.get("target"),
                        unlocked_count = len(ach.player_unlocks),
                        description = ach.description,
                    ))
        session.flush()
        return locked
                


    # Remove this stringbuilder pattern. Return an object that creates the "string view".
    def achievements(self, player_id: int, player_name) -> Result[PlayerAchievements]:
        """Return a human-readable list of unlocked and locked achievements for player_id."""
        try:
            with Session(self.engine) as session:
                sq = select(model.PlayerAchievement).filter_by(player_id=player_id)
                subquery = sq.subquery()
                locked_achievements = session.scalars(
                    select(model.Achievement)
                    .outerjoin(subquery, onclause=subquery.c.achievement_id==model.Achievement.achievement_id)
                    .where(
                        model.Achievement.is_active.is_(True),
                        subquery.c.achievement_id.is_(None)
                    )
                    
                ).all()



                locked = self.update_achievements_and_obtain_locked(session, locked_achievements, player_id)
                pa = session.scalars(
                    sq
                ).all()
                unlocked = []
                for p in pa:
                    ach = p.achievement
                    unlocked.append(Achievement(
                        name = ach.name,
                        points = ach.points,
                        description = ach.description,
                        unlocked_time=p.unlocked_at,
                        unlocked_count = len(ach.player_unlocks),
                    ))

                player = session.get(game_model.Player, player_id)
                if not player:
                    player = game_model.Player(player_id=player_id, name=player_name)
                    session.add(player)
                session.commit()
                return Ok(PlayerAchievements(
                    name=player.name,
                    unlocked=unlocked,
                    locked=locked,
                ))
                
        except Exception as e:
            logging.exception("Something went wrong")
            return Err("Something went wrong.")

    def player_id_from_name(self, name: str) -> Optional[int]:
        with Session(self.engine) as session:
            return session.scalar(
                select(game_model.Player.player_id).filter_by(name=name)
            )