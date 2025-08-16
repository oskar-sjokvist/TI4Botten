import logging

from . import model as model
from ..game import model as game_model

from blinker import signal
from collections import defaultdict
from itertools import combinations
from sqlalchemy import Engine, select, func, text
from sqlalchemy.orm import Session
from tabulate import tabulate
from typing import Tuple


class RatingLogic:
    """Cog containing rating related commands."""

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.k_game = 50  # Boundedness of updates
        self._refresh_ratings()

        # Let's not auto update the ratings until we allow rollbacks or implement a proper refresh command
        # I.e. clear the ledger and reset ratings before recalculating the ratings.
        # signal("finish").connect(self.update_rating)

    def update_rating(self, _, game_id: int):
        with Session(self.engine) as session:
            game = session.scalar(
                select(game_model.Game).filter_by(
                    game_id=game_id, game_state=game_model.GameState.FINISHED
                )
            )
            if not game:
                return
            self._update_game_rating(session, game)
            session.commit()

    @staticmethod
    def _expectations(a, b) -> Tuple[float, float]:
        scale_constant = 400
        e_ab = 1 / (1 + 10 ** ((a - b) / scale_constant))
        return e_ab, 1 - e_ab

    def __match_player(
        self, session: Session, game_player: game_model.GamePlayer
    ) -> model.MatchPlayer:
        p = session.get(model.MatchPlayer, game_player.player_id)
        if not p:
            p = model.MatchPlayer(
                player_id=game_player.player_id, name=game_player.player.name
            )
            session.add(p)
            session.flush()
        return p


    def __wins_statement(self):
        sq = (
            select(
                game_model.GamePlayer.game_id,
                func.max(game_model.GamePlayer.points).label("max_points"),
            )
            .group_by(game_model.GamePlayer.game_id)
            .filter(
                game_model.GamePlayer.game.has(
                    game_state=game_model.GameState.FINISHED
                )
            )
            .subquery()
        )
        return (
            select(game_model.Player.player_id, game_model.Player.name, func.count("*").label("wins"))
            .select_from(game_model.GamePlayer)
            .group_by(game_model.Player.player_id)
            .join(
                sq,
                (sq.c.game_id == game_model.GamePlayer.game_id)
                & (sq.c.max_points == game_model.GamePlayer.points),
            )
            .join(
                game_model.Player,
                game_model.Player.player_id == game_model.GamePlayer.player_id,
            )
            .order_by(text("wins desc"))
            )

    def __deltas(self, session: Session, game: game_model.Game):
        deltas = defaultdict(list)
        for p1, p2 in combinations(game.game_players, 2):
            a = self.__match_player(session, p1)
            b = self.__match_player(session, p2)

            e_ab, e_ba = self._expectations(a.rating, b.rating)
            if p1.points < p2.points:
                deltas[p1.player_id].append(0 - e_ab)
                deltas[p2.player_id].append(1 - e_ba)
            elif p1.points > p2.points:
                deltas[p1.player_id].append(1 - e_ab)
                deltas[p2.player_id].append(0 - e_ba)
            else:
                deltas[p1.player_id].append(0.5 - e_ab)
                deltas[p2.player_id].append(0.5 - e_ba)
        return deltas

    def _update_game_rating(self, session, game):
        deltas = self.__deltas(session, game)

        if len(deltas) <= 1:
            ## Solo game.
            return

        for player in game.game_players:
            outcome = session.execute(
                select(model.OutcomeLedger).filter_by(
                    game_id=game.game_id, player_id=player.player_id
                )
            ).scalar()
            if outcome is not None:
                # Already processed this before
                continue
            p = self.__match_player(session, player)
            delta = sum(deltas[p.player_id]) / (len(deltas) - 1) * self.k_game

            ol = model.OutcomeLedger(
                game_id=game.game_id,
                player_id=p.player_id,
                rating_before=p.rating,
                rating_delta=delta,
                rating_after=p.rating + delta,
                match_time=game.game_finish_time,
            )
            session.add(ol)

            p.rating += delta
            session.merge(p)

    def _refresh_ratings(self):
        with Session(self.engine) as session:
            games = session.scalars(
                select(game_model.Game)
                .filter_by(game_state=game_model.GameState.FINISHED)
                .order_by(game_model.Game.game_finish_time.asc())
            )

            for game in games:
                self._update_game_rating(session, game)
                session.commit()

    def stats(self, player_id: int) -> str:
        """Retrieve the ratings for all players"""
        try:
            with Session(self.engine) as session:
                # Find player info
                mp = session.get(model.MatchPlayer, player_id)
                if not mp:
                    mp = session.merge(model.MatchPlayer(player_id=player_id))
                    session.commit()

                pp = session.execute(
                    select(game_model.GamePlayer.faction, func.count("*"))
                    .group_by(game_model.GamePlayer.faction)
                    .filter_by(player_id=player_id)
                    .filter(
                        game_model.GamePlayer.game.has(
                            game_state=game_model.GameState.FINISHED
                        )
                    )
                ).all()

                lines = [
                    f"Your stats are",
                    f"Elo rating {mp.rating:.2f}",
                ]
                games = session.execute(
                    select(func.count("*"))
                    .select_from(game_model.GamePlayer)
                    .filter_by(player_id=player_id)
                    .filter(
                        game_model.GamePlayer.game.has(
                            game_state=game_model.GameState.FINISHED
                        )
                    )
                ).scalar()
                lines.append(f"You have played {games} games")
                sq = (
                    select(
                        game_model.GamePlayer.game_id,
                        func.max(game_model.GamePlayer.points).label("max_points"),
                    )
                    .group_by(game_model.GamePlayer.game_id)
                    .filter(
                        game_model.GamePlayer.game.has(
                            game_state=game_model.GameState.FINISHED
                        )
                    )
                    .subquery()
                )
                stmt = (
                    select(func.count("*"))
                    .select_from(game_model.GamePlayer)
                    .filter_by(player_id=player_id)
                    .join(
                        sq,
                        (sq.c.game_id == game_model.GamePlayer.game_id)
                        & (sq.c.max_points == game_model.GamePlayer.points),
                    )
                )

                wins = session.execute(stmt).scalar()
                lines.append(f"With {wins} wins")
                lines.append(f"Your favorite factions are")
                lines.extend(
                    [f"{p.faction} (played {p.count} time(s))" for p in pp[:3]]
                )
                pp = session.execute(
                    select(func.sum(game_model.GamePlayer.points) / func.count("*"))
                    .filter_by(player_id=player_id)
                    .filter(
                        game_model.GamePlayer.game.has(
                            game_state=game_model.GameState.FINISHED
                        )
                    )
                ).scalar()
                lines.append(f"Average points per game: {pp:.2f}")

                return "\n".join(lines)
        except Exception as e:
            logging.error(f"stats: {e}")
            return "Something went wrong."

    def ratings(self) -> str:
        """Retrieve the ratings for all players in a table format"""
        try:
            with Session(self.engine) as session:
                sq = self.__wins_statement().subquery()
                players = session.execute(
                    select(model.MatchPlayer,sq.c.wins).select_from(model.MatchPlayer).order_by(model.MatchPlayer.rating.desc())
                    .outerjoin(sq, sq.c.player_id == model.MatchPlayer.player_id)
                ).all()

                if not players:
                    return "No players found."

                # Prepare table data
                table_data = []
                for i, row in enumerate(players):
                    player = row[0]
                    wins = row[1] if row[1] else 0
                    table_data.append(
                        [i + 1, player.name, int(player.rating), wins]
                    )

                # Generate table using tabulate
                table = tabulate(
                    table_data, headers=["#", "Player", "Rating", "Wins"], tablefmt="double_outline"
                )

                # Send as Discord code block (triple backticks)
                return f"```\n{table}\n```"

        except Exception as e:
            logging.error(f"ratings: {e}")
            return "Something went wrong."

    def wins(self) -> str:
        try:
            with Session(self.engine) as session:
                players = session.execute(self.__wins_statement()).all()
                # Prepare table data
                table_data = []
                for i, player in enumerate(players):
                    table_data.append(
                        [i + 1, player.name, int(player.wins)]
                    )

                # Generate table using tabulate
                table = tabulate(
                    table_data, headers=["#", "Player", "Wins"], tablefmt="double_outline"
                )

                # Send as Discord code block (triple backticks)
                return f"```\n{table}\n```"
        except Exception as e:
            logging.error(f"wins: {e}")
            return "Something went wrong."
