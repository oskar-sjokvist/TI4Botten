from . import model as model
from ..game import model as game_model

from blinker import signal
from collections import defaultdict
from itertools import combinations
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from typing import Tuple


class RatingLogic:
    """Cog containing rating related commands."""

    def __init__(self,  engine: Engine) -> None:
        self.engine = engine
        self.k_game = 50 # Boundedness of updates
        self._refresh_ratings()
        signal("finish").connect(self.update_rating)

    def update_rating(self, _, game_id: int):
        with Session(self.engine) as session:
            stmt = select(game_model.Game).filter_by(game_id=game_id,game_state=game_model.GameState.FINISHED)
            game = session.execute(stmt).scalar()
            if not game:
                return
            self._update_game_rating(session, game)
            session.commit()
        

    @staticmethod
    def _expectations(a, b) -> Tuple[float,float]:
        scale_constant = 400
        e_ab = 1/(1+10**((a-b)/scale_constant))
        return e_ab, 1-e_ab

    def _update_game_rating(self, session, game):
        deltas = defaultdict(list)
        for p1, p2 in combinations(game.game_players, 2):
            a = session.execute(
                select(model.MatchPlayer).filter_by(player_id=p1.player_id)
            ).scalar()
            if not a:
                a = model.MatchPlayer(player_id=p1.player_id, name=p1.player.name)
                session.add(a)
                session.flush()
            
            b = session.execute(
                select(model.MatchPlayer).filter_by(player_id=p2.player_id)
            ).scalar()
            if not b:
                b = model.MatchPlayer(player_id=p2.player_id, name=p2.player.name)
                session.add(b)
                session.flush()

            e_ab, e_ba = self._expectations(a.rating, b.rating)
            if p1.points < p2.points:
                deltas[p1.player_id].append(0-e_ab)
                deltas[p2.player_id].append(1-e_ba)
            elif p1.points > p2.points:
                deltas[p1.player_id].append(1-e_ab)
                deltas[p2.player_id].append(0-e_ba)
            else:
                deltas[p1.player_id].append(0.5-e_ab)
                deltas[p2.player_id].append(0.5-e_ba)

        if len(deltas) <= 1:
            ## Solo game.
            return

        for player in game.game_players:
            outcome = session.execute(select(model.OutcomeLedger).filter_by(game_id=game.game_id, player_id=player.player_id)).scalar()
            if outcome is not None:
                # Already processed this before
                continue
            p = session.execute(
                select(model.MatchPlayer).filter_by(player_id=player.player_id)
            ).scalar()
            if not p:
                p = model.MatchPlayer(player_id=player.player_id, name=player.player.name)
                session.add(p)
                session.flush()
            delta = sum(deltas[p.player_id])/(len(deltas)-1) * self.k_game
            ol = model.OutcomeLedger(
                game_id = game.game_id,
                player_id = p.player_id,
                rating_before = p.rating,
                rating_delta = delta,
                rating_after = p.rating + delta,
                match_time = game.game_finish_time,
            )
            session.add(ol)

            p.rating += delta

            session.merge(p)


    def _refresh_ratings(self):
        with Session(self.engine) as session:
            stmt = select(game_model.Game).filter_by(game_state=game_model.GameState.FINISHED).order_by(game_model.Game.game_finish_time.asc())
            games = session.execute(stmt).scalars().all()


            for game in games:
                self._update_game_rating(session, game)
                session.commit()



    def ratings(self) -> str:
        """Retrieve the ratings for all players"""
        with Session(self.engine) as session:
            # Find all players.
            players = session.execute(
                select(model.MatchPlayer).order_by(model.MatchPlayer.rating.desc())
            ).scalars().all()
            if not players:
                return "No players found."
            return "\n".join([f"{player.name}: rating {player.rating:.2f}" for player in players])



