from typing import Any, Dict
from datetime import datetime
from sqlalchemy.orm import Session, aliased
from ..achievementtype import *
from ...game import model as game_model
from sqlalchemy import select, func, and_

def finish(session: Session, rule: Dict[str, Any], player_id: int) -> AchievementType:
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
        op = f.get("op")
        pts = f.get("target")
        if pts is None:
            return "Invalid points filter (missing target)"
        try:
            pts_val = int(pts)
        except Exception:
            return "Invalid points filter (target must be an integer)"

        match op:
            case "lte":
                stmt = stmt.where(game_model.GamePlayer.points <= pts_val)
            case "lt":
                stmt = stmt.where(game_model.GamePlayer.points < pts_val)
            case "gte":
                stmt = stmt.where(game_model.GamePlayer.points >= pts_val)
            case "gt":
                stmt = stmt.where(game_model.GamePlayer.points > pts_val)
            case "eq" | "=":
                stmt = stmt.where(game_model.GamePlayer.points == pts_val)
            case "neq" | "!=":
                stmt = stmt.where(game_model.GamePlayer.points != pts_val)
            case _:
                return "Unsupported operation"

    # Optional finish_date_after to only count games finished on/after a date.
    if isinstance(filter_, dict) and "finish_date_after" in filter_:
        from_date = filter_["finish_date_after"]
        if from_date:
            try:
                dt = datetime.fromisoformat(from_date)
            except Exception:
                return "Invalid from_date format; expected ISO date or datetime"

            # Add an additional correlated filter requiring the game's finish time
            # to be on/after the provided date.
            stmt = stmt.where(
                game_model.GamePlayer.game.has(
                    game_model.Game.game_finish_time >= dt
                )
        )
    if isinstance(filter_, dict) and "play_as_faction" in filter_:
        f = filter_["play_as_faction"]
        stmt = stmt.where(game_model.GamePlayer.faction == f)

    # Support counting finishes where another player in the same game played
    # a specific faction (i.e. finished against that faction).
    if isinstance(filter_, dict) and "against_faction" in filter_:
        f = filter_["against_faction"]
        gp_other = aliased(game_model.GamePlayer)
        # Allow string, list, or dict mapping faction->role expectations for the
        # other player (e.g. {"The Mentak Coalition": "winner"}). If a dict
        # is provided we only require that a player with that faction exists
        # and optionally that the other player's role matches winner/loser.
        if isinstance(f, str):
            stmt = stmt.where(select(gp_other).where(
                gp_other.game_id == game_model.GamePlayer.game_id,
                gp_other.faction == f,
                gp_other.player_id != game_model.GamePlayer.player_id,
            ).exists())
        elif isinstance(f, (list, tuple)):
            stmt = stmt.where(select(gp_other).where(
                gp_other.game_id == game_model.GamePlayer.game_id,
                gp_other.faction.in_(f),
                gp_other.player_id != game_model.GamePlayer.player_id,
            ).exists())
        elif isinstance(f, dict):
            # for each faction -> role mapping, require a matching player row
            # and if role is specified, compare points to assert winner/loser
            role_filters = []
            for faction_name, role in f.items():
                if role not in {"winner", "loser", None}:
                    return "Unsupported role in against_faction filter"

                gp_named = aliased(game_model.GamePlayer)
                gp_cmp = aliased(game_model.GamePlayer)

                if role == "winner":
                    # primary GamePlayer must have fewer or equal points than named? No,
                    # we require that the named player is the winner. So named player's
                    # row has no other player with more points.
                    role_clause = select(gp_named).where(
                        gp_named.game_id == game_model.GamePlayer.game_id,
                        gp_named.faction == faction_name,
                        ~select(gp_cmp).where(
                            gp_cmp.game_id == gp_named.game_id,
                            gp_cmp.points > gp_named.points,
                        ).exists(),
                        gp_named.player_id != game_model.GamePlayer.player_id,
                    ).exists()
                elif role == "loser":
                    role_clause = select(gp_named).where(
                        gp_named.game_id == game_model.GamePlayer.game_id,
                        gp_named.faction == faction_name,
                        ~select(gp_cmp).where(
                            gp_cmp.game_id == gp_named.game_id,
                            gp_cmp.points < gp_named.points,
                        ).exists(),
                        gp_named.player_id != game_model.GamePlayer.player_id,
                    ).exists()
                else:
                    role_clause = select(gp_named).where(
                        gp_named.game_id == game_model.GamePlayer.game_id,
                        gp_named.faction == faction_name,
                        gp_named.player_id != game_model.GamePlayer.player_id,
                    ).exists()

                role_filters.append(role_clause)

            # Require all specified mappings to hold (AND)
            for rf in role_filters:
                stmt = stmt.where(rf)
        else:
            return "Invalid against_faction filter"

    # win_against: the primary GamePlayer must be the winner and some opponent
    # with the specified faction must be present in the game.
    if isinstance(filter_, dict) and "win_against" in filter_:
        f = filter_["win_against"]
        gp_op = aliased(game_model.GamePlayer)
        # primary is winner: no other player in same game has more points
        stmt = stmt.where(~select(gp_op).where(
            gp_op.game_id == game_model.GamePlayer.game_id,
            gp_op.points > game_model.GamePlayer.points,
        ).exists())

        if isinstance(f, str):
            stmt = stmt.where(select(gp_op).where(
                gp_op.game_id == game_model.GamePlayer.game_id,
                gp_op.faction == f,
                gp_op.player_id != game_model.GamePlayer.player_id,
            ).exists())
        elif isinstance(f, (list, tuple)):
            stmt = stmt.where(select(gp_op).where(
                gp_op.game_id == game_model.GamePlayer.game_id,
                gp_op.faction.in_(f),
                gp_op.player_id != game_model.GamePlayer.player_id,
            ).exists())
        else:
            return "Invalid win_against filter"

    # lose_against: the primary GamePlayer must be the loser and some opponent
    # with the specified faction must be present in the game.
    if isinstance(filter_, dict) and "lose_against" in filter_:
        f = filter_["lose_against"]
        gp_op = aliased(game_model.GamePlayer)
        # primary is loser: no other player in same game has fewer points
        stmt = stmt.where(~select(gp_op).where(
            gp_op.game_id == game_model.GamePlayer.game_id,
            gp_op.points < game_model.GamePlayer.points,
        ).exists())

        if isinstance(f, str):
            stmt = stmt.where(select(gp_op).where(
                gp_op.game_id == game_model.GamePlayer.game_id,
                gp_op.faction == f,
                gp_op.player_id != game_model.GamePlayer.player_id,
            ).exists())
        elif isinstance(f, (list, tuple)):
            stmt = stmt.where(select(gp_op).where(
                gp_op.game_id == game_model.GamePlayer.game_id,
                gp_op.faction.in_(f),
                gp_op.player_id != game_model.GamePlayer.player_id,
            ).exists())
        else:
            return "Invalid lose_against filter"

    if isinstance(filter_, dict) and "player" in filter_:
        f = filter_["player"]
        if isinstance(f, str):
            # Check if the player with filter_["player"] name is in the game as well
            other_player = session.scalar(
                select(game_model.Player).filter_by(name=f)
            )
            if not other_player:
                return f"Player not found: {f}"

            gp_named = aliased(game_model.GamePlayer)
            # Require that the named player appears in the same game as the
            # primary GamePlayer row (i.e., they were in the game together).
            stmt = stmt.where(select(gp_named).where(
                gp_named.game_id == game_model.GamePlayer.game_id,
                gp_named.player_id == other_player.player_id,
            ).exists())

        elif isinstance(f, dict):
            for name, role in f.items():
                other_player = session.scalar(
                    select(game_model.Player).filter_by(name=name)
                )
                if not other_player:
                    return f"Player not found: {name}"

                gp_named = aliased(game_model.GamePlayer)
                gp_cmp = aliased(game_model.GamePlayer)

                if role == "winner":
                    # Require that the named player's GamePlayer row in the same
                    # game has no other player with more points (i.e. they finished first)
                    stmt = stmt.where(select(gp_named).where(
                        gp_named.game_id == game_model.GamePlayer.game_id,
                        gp_named.player_id == other_player.player_id,
                        ~select(gp_cmp).where(
                            gp_cmp.game_id == gp_named.game_id,
                            gp_cmp.points > gp_named.points,
                        ).exists(),
                    ).exists())
                elif role == "loser":
                    # Require that the named player's GamePlayer row in the same
                    # game has no other player with fewer points (i.e. they finished last)
                    stmt = stmt.where(select(gp_named).where(
                        gp_named.game_id == game_model.GamePlayer.game_id,
                        gp_named.player_id == other_player.player_id,
                        ~select(gp_cmp).where(
                            gp_cmp.game_id == gp_named.game_id,
                            gp_cmp.points < gp_named.points,
                        ).exists(),
                    ).exists())
                else:
                    return "Unsupported player role"
        else:
            return "Invalid player filter"

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