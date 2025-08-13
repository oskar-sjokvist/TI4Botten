import csv
import Levenshtein
import time
from datetime import datetime

from .. import factions
from .. import model
from ... import models
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

file_path = "data.csv"

fs = factions.read_factions()

here = Path(__file__).parent

def _closest_match(s : str, ss, cutoff=0.1) -> str|None:
    best = max(ss, key=lambda c: Levenshtein.ratio(s, c))
    if Levenshtein.ratio(s, best) <= cutoff:
        return None
    return best

def main():
    names = [faction.name for faction in  fs.factions]
    items = []

    with open(here / file_path, mode="r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        unique_players = set()
        ## Using a dict to keep it ordered.
        unique_games = dict()
        for row in reader:
            game_name, player, faction, points = row
            unique_players.add(player)
            unique_games[game_name] = True
            print(f"{game_name},{player},{_closest_match(faction, names)},{points}")
            items.append((game_name,player,_closest_match(faction, names),points))
        print(unique_players)

    name_to_game_id = {game:i+1 for i, game in enumerate(unique_games)}

    # If you can get the player ID, it will be seamless to connect it to an existing discord user.
    name_to_player_id = {player:i for i, player in enumerate(unique_players)}
        

    engine = create_engine('sqlite:///app.db', echo=True)
    # Instantiate all the tables.
    models.Base.metadata.create_all(engine)

    with Session(engine) as session:
        for item in items:
            game_name, player, faction, points = item
            ## Retrive game if it exists, so at least the games are ordered by time ASC
            game = session.get(model.Game, name_to_game_id[game_name])
            if not game:
                game_id = name_to_game_id[game_name]
                # Making sure the finish time is ascending. A bit hacky, but won't be needed if we update the script and dumps to include timestamps 
                game = model.Game(game_id=game_id, name=game_name, game_state=model.GameState.FINISHED, game_finish_time=datetime.fromordinal(len(unique_games)+1-game_id))
                session.add(game)
            player = session.merge(model.Player(player_id=name_to_player_id[player], name=player))
            session.flush()
            session.merge(model.GamePlayer(game_id = game.game_id, player_id=player.player_id,faction=faction,points=points))
            session.commit()

if __name__ == "__main__":
    main()
