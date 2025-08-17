import logging
from blinker import signal
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from pathlib import Path
import json

from . import model as achievements_model
from ..game import controller as game_controller
from ..game import model as game_model


def register(engine) -> None:
    """Connect to the game finish signal and update counters when a game finishes.

    This will increment the 'games_won' counter for the winning player in PlayerProgress.
    """

    def _on_finish(sender, game_id: int):
        try:
            with Session(engine) as session:
                # Load finished game and determine winner
                game = session.get(game_model.Game, game_id)
                if not game:
                    return
                # Use controller to find winner
                ctrl = game_controller.GameController()
                try:
                    winner = ctrl.winner(session, game)
                except LookupError:
                    return

                # Increment or create PlayerProgress counter
                counter_key = "games_won"
                up = session.get(achievements_model.PlayerProgress, (winner.player_id, counter_key))
                if up is None:
                    up = achievements_model.PlayerProgress(player_id=winner.player_id, counter_key=counter_key, value=1)
                    session.add(up)
                else:
                    up.value = (up.value or 0) + 1
                    session.merge(up)

                # Increment or create played counter
                counter_key = "games_played"
                for player in game.game_players:
                    up = session.get(achievements_model.PlayerProgress, (player.player_id, counter_key))
                    if up is None:
                        up = achievements_model.PlayerProgress(player_id=player.player_id, counter_key=counter_key, value=1)
                        session.add(up)
                    else:
                        up.value = (up.value or 0) + 1
                        session.merge(up)

                # Commit the increment
                session.commit()
        except Exception as e:
            logging.exception("Error handling game finish for achievements: %s", e)

    signal("finish").connect(_on_finish)


def reconcile_games(session: Session):
    stmt = (
        select(
            game_model.GamePlayer.player_id,
            func.count("*").label("played"),
        ).group_by(game_model.GamePlayer.player_id)
    )
    rows = session.execute(stmt).all()

    session.execute(delete(achievements_model.PlayerProgress).where(achievements_model.PlayerProgress.counter_key == "games_played"))

    for player_id, played in rows:
        up = achievements_model.PlayerProgress(player_id=player_id, counter_key="games_played", value=int(played))
        session.add(up)


def reconcile_wins(session: Session):
    # Build subquery to find max points per finished game
    sq = (
        select(
            game_model.GamePlayer.game_id,
            func.max(game_model.GamePlayer.points).label("max_points"),
        )
        .group_by(game_model.GamePlayer.game_id)
        .filter(
            game_model.GamePlayer.game.has(
                game_model.Game.game_state == game_model.GameState.FINISHED
            )
        )
        .subquery()
    )

    # Count wins per player by joining with subquery where points == max_points
    stmt = (
        select(game_model.GamePlayer.player_id, func.count("*").label("wins"))
        .select_from(game_model.GamePlayer)
        .join(
            sq,
            (sq.c.game_id == game_model.GamePlayer.game_id)
            & (sq.c.max_points == game_model.GamePlayer.points),
        )
        .group_by(game_model.GamePlayer.player_id)
    )

    rows = session.execute(stmt).all()

    # Remove existing games_won counters
    session.execute(delete(achievements_model.PlayerProgress).where(achievements_model.PlayerProgress.counter_key == "games_won"))

    # Insert new counters
    for player_id, wins in rows:
        up = achievements_model.PlayerProgress(player_id=player_id, counter_key="games_won", value=int(wins))
        session.add(up)



def reconcile(engine) -> None:
    """Recompute the 'games_won' counters from finished games and sync PlayerProgress to that source of truth.

    This will replace any existing PlayerProgress rows for counter_key='games_won'.
    """

    try:
        with Session(engine) as session:
            reconcile_wins(session)
            session.commit()
    except Exception as e:
        logging.exception("Error reconciling achievements counters: %s", e)


def load_achievements(engine, dir_path: str | None = None) -> None:
    """Load achievement JSON files from `dir_path` (defaults to package 'achievements' dir)

    Each JSON file should contain keys matching the Achievement model:
      - achievement_id (optional)
      - key
      - version (optional, default 1)
      - name
      - description
      - rule_json
      - points (optional)
      - is_active (optional)

    Existing achievements with the same achievement_id will be updated. If achievement_id
    is not provided we try to match by (key, version) and otherwise create a new id.
    """
    try:
        base = Path(dir_path) if dir_path else Path(__file__).parent / "achievements"
        if not base.exists():
            logging.info("No achievements dir found at %s", str(base))
            return

        files = list(base.glob("*.json"))
        if not files:
            logging.info("No achievement JSON files found in %s", str(base))
            return

        with Session(engine) as session:
            for fp in files:
                try:
                    data = json.loads(fp.read_text(encoding="utf-8"))
                except Exception as e:
                    logging.exception("Failed to parse achievement file %s: %s", fp, e)
                    continue

                achievement_id = data.get("achievement_id")
                key = data.get("key")
                version = int(data.get("version", 1))
                name = data.get("name")
                description = data.get("description")
                rule_json = data.get("rule_json") or {}
                points = int(data.get("points", 0))
                is_active = bool(data.get("is_active", True))

                if not key or not name or description is None:
                    logging.warning("Skipping invalid achievement file %s: missing key/name/description", fp)
                    continue

                ach = session.get(achievements_model.Achievement, achievement_id)


                if ach is None:
                    ach = achievements_model.Achievement(
                        achievement_id=achievement_id,
                        key=key,
                        version=version,
                        name=name,
                        description=description,
                        rule_json=rule_json,
                        points=points,
                        is_active=is_active,
                    )
                    session.add(ach)
                    continue

                # Update fields
                ach.key = key
                ach.version = version
                ach.name = name
                ach.description = description
                ach.rule_json = rule_json
                ach.points = points
                ach.is_active = is_active
                session.merge(ach)

            session.commit()
    except Exception as e:
        logging.exception("Error loading achievement JSON files: %s", e)
