from typing import Any, Dict
from sqlalchemy.orm import Session
from ..achievementtype import *
from ...game import model as game_model


def player(session: Session, rule: Dict[str, Any], player_id: int) -> AchievementType:
    target = rule.get("target")
    if target is None:
        return "Invalid player rule (missing target)"

    player = session.get(game_model.Player, player_id)
    if not player:
        return "Player not found"

    if player.name == target:
        return Achieved()
    return Locked(current=None, target=None)
