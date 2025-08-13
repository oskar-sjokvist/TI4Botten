from . import model as model
from ..game import model as game_model

from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import Engine, select

from typing import Tuple
from itertools import combinations


class RatingLogic:
    """Cog containing rating related commands."""

    @staticmethod
    def _expectations(a, b) -> Tuple[float,float]:
        scale_constant = 400
        e_ab = 1/(1+10**((a-b)/scale_constant))
        return e_ab, 1-e_ab

    def refresh_ratings(self):
        with Session(self.engine) as session:
            stmt = select(game_model.Game).filter_by(game_state=game_model.GameState.FINISHED).order_by(game_model.Game.game_finish_time.asc())
            games = session.execute(stmt).scalars().all()


            for game in games:
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
                    print(e_ab, e_ba)
                    if p1.points < p2.points:
                        deltas[p1.player_id].append(0-e_ab)
                        deltas[p2.player_id].append(1-e_ba)
                    elif p2.points > p1.points:
                        deltas[p1.player_id].append(1-e_ab)
                        deltas[p2.player_id].append(0-e_ba)
                    else:
                        deltas[p1.player_id].append(0.5-e_ab)
                        deltas[p2.player_id].append(0.5-e_ba)

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
                    delta = sum(deltas[p.player_id])/len(deltas) * self.k_game
                    delta = delta if delta else 0
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
                session.commit()


    def __init__(self,  engine: Engine) -> None:
        self.engine = engine
        self.k_game = 80 # Boundedness of updates

        self.refresh_ratings()



    def ratings(self) -> str:
        """Retrieve the ratings for all players"""
        with Session(self.engine) as session:
                    
            # Find all players.
            players = session.execute(
                select(model.MatchPlayer)
            ).scalars().all()
            return "\n".join([f"{player.name}: rating {player.rating:.2f}" for player in players])



