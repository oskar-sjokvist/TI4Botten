from typing import Any, Dict
from sqlalchemy.orm import Session
from ..achievementtype import *
from ...game import model as game_model
from sqlalchemy import select
from ...rating import model as rating_model

def head_to_head(session: Session, rule: Dict[str, Any], player_id: int) -> AchievementType:
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
