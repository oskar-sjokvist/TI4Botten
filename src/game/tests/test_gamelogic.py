import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.game import gamelogic, model
from src.models import Base
from src.typing import *


@pytest.fixture(scope="function")
def db():
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    # GameLogic expects a bot and engine, but tests only use engine
    logic = gamelogic.GameLogic(bot=None, engine=engine)
    yield session, logic
    session.close()


def test_join_new_player(db):
    session, logic = db
    game = model.Game(game_id=2, game_state="LOBBY", name="JoinLobby")
    session.add(game)
    session.commit()
    result = logic.join(game.game_id, 42, "Bob")
    assert "has joined lobby" in result.value
    assert "Current number of players 1" in result.value


def test_leave_after_join(db):
    session, logic = db
    game = model.Game(game_id=3, game_state="LOBBY", name="LeaveLobby")
    session.add(game)
    player = model.Player(player_id=5, name="Eve")
    session.add(player)
    gp = model.GamePlayer(game_id=3, player_id=5)
    session.add(gp)
    session.commit()
    result = logic.leave(game.game_id, 5)
    assert "All players have left" in result.value


def test_join_and_leave_multiple(db):
    session, logic = db
    game = model.Game(game_id=4, game_state="LOBBY", name="MultiLobby")
    session.add(game)
    session.commit()
    # Join 2 players
    logic.join(game.game_id, 10, "A")
    logic.join(game.game_id, 11, "B")
    # Leave one
    result = logic.leave(game.game_id, 10)
    assert "has left lobby" in result.value
    # Leave last
    result2 = logic.leave(game.game_id, 11)
    assert "All players have left" in result2.value


def test_join_invalid_game(db):
    _, logic = db
    result = logic.join(999, 1, "Ghost")
    assert "No lobby found" in result.msg or "not a lobby" in result.msg


def test_leave_invalid_game(db):
    _, logic = db
    result = logic.leave(999, 1)
    assert "No lobby found" in result.msg or "not a lobby" in result.msg


def test_config_no_lobby(db):
    _, logic = db
    result = logic.config(999, None, None)
    assert "No lobby found" in result.msg

def test_parse_ints():
    assert gamelogic.GameLogic._parse_ints("1 2 3") == [1, 2, 3]
    assert gamelogic.GameLogic._parse_ints("-1, 0, 42") == [-1, 0, 42]
    assert gamelogic.GameLogic._parse_ints("") == []


def test_leave_not_in_lobby(db):
    session, logic = db
    game = model.Game(game_id=1, game_state="LOBBY", name="TestLobby")
    session.add(game)
    session.commit()
    result = logic.leave(1, 1)
    assert "You are not in this game!" in result.msg


def test_join_already_in_lobby(db):
    session, logic = db
    game = model.Game(game_id=1, game_state="LOBBY", name="TestLobby")
    session.add(game)
    session.commit()
    player = model.Player(player_id=1, name="Alice")
    session.add(player)
    gp = model.GamePlayer(game_id=1, player_id=1)
    session.add(gp)
    session.commit()
    result = logic.join(1, 1, "Alice")
    assert "You are already in this lobby!" in result.msg


def test_games_no_games(db):
    _, logic = db
    result = logic.games()
    assert "No games found." in result.msg


def test_lobby_and_join_leave(db):
    session, logic = db
    lobby_name = "TestLobby"
    # Simulate lobby creation by directly adding to DB, since logic.lobby is async and expects Discord context
    game = model.Game(game_id=100, game_state="LOBBY", name=lobby_name)
    session.add(game)
    player = model.Player(player_id=1, name="Alice")
    session.add(player)
    gp = model.GamePlayer(game_id=100, player_id=1)
    session.add(gp)
    session.commit()
    game = session.query(model.Game).filter_by(name=lobby_name).first()
    assert game is not None

    leave_result = logic.leave(game.game_id, 1)
    assert "All players have left" in leave_result.value


def test_join_limit(db):
    session, logic = db
    lobby_name = "FullLobby"
    # Simulate lobby creation
    game = model.Game(game_id=200, game_state="LOBBY", name=lobby_name)
    session.add(game)
    session.commit()
    for i in range(1, 9):
        logic.join(game.game_id, i, f"Player{i}")
    result = logic.join(game.game_id, 9, "Player9")
    assert "Player limit reached" in result.msg

def test_join_after_leave(db):
    session, logic = db
    game = model.Game(game_id=300, game_state="LOBBY", name="RejoinLobby")
    session.add(game)
    session.commit()
    logic.join(game.game_id, 1, "Alice")
    logic.leave(game.game_id, 1)
    result = logic.join(game.game_id, 1, "Alice")
    assert "has joined lobby" in result.value

def test_join_with_duplicate_name(db):
    session, logic = db
    game = model.Game(game_id=400, game_state="LOBBY", name="DupNameLobby")
    session.add(game)
    session.commit()
    logic.join(game.game_id, 1, "Alice")
    result = logic.join(game.game_id, 2, "Alice")
    assert "has joined lobby" in result.value

def test_leave_twice(db):
    session, logic = db
    game = model.Game(game_id=500, game_state="LOBBY", name="LeaveTwiceLobby")
    session.add(game)
    session.commit()
    logic.join(game.game_id, 1, "Alice")
    logic.leave(game.game_id, 1)
    result = logic.leave(game.game_id, 1)
    assert "You are not in this game!" in result.msg

def test_config_wrong_type(db):
    session, logic = db
    game = model.Game(game_id=700, game_state="LOBBY", name="ConfigTypeLobby")
    session.add(game)
    session.commit()
    # Assume there is a property 'factions_per_player' which is Integer
    result = logic.config(game.game_id, "factions_per_player", "notanumber")
    assert "Supply a valid integer value" in result.msg or "Invalid datatype" in result.msg

def test_config_not_lobby(db):
    session, logic = db
    game = model.Game(game_id=800, game_state="STARTED", name="ConfigNotLobby")
    session.add(game)
    session.commit()
    result = logic.config(game.game_id, "factions_per_player", "5")
    assert "Game is not in lobby" in result.msg

def test_join_when_not_lobby(db):
    session, logic = db
    game = model.Game(game_id=900, game_state="STARTED", name="NotLobby")
    session.add(game)
    session.commit()
    result = logic.join(game.game_id, 1, "Alice")
    assert "not a lobby" in result.msg

def test_leave_when_not_lobby(db):
    session, logic = db
    game = model.Game(game_id=901, game_state="STARTED", name="NotLobby2")
    session.add(game)
    session.commit()
    result = logic.leave(game.game_id, 1)
    assert "not a lobby" in result.msg


def test_finish_game_flow(db):
    session, logic = db
    game = model.Game(game_state="STARTED", name="FinishTest")
    session.add(game)
    session.commit()
    for i in range(1, 4):
        player = model.Player(player_id=i, name=f"P{i}")
        session.add(player)
        gp = model.GamePlayer(game_id=game.game_id, player_id=i, points=0)
        session.add(gp)
    session.commit()
    result = logic.finish(False, game.game_id, "10 5 7").value
    # finish returns an Embed
    embed = result
    # message begins with a players summary
    assert "Players:" in embed.description
    assert "10 point(s)" in embed.description
    assert "5 point(s)" in embed.description
    assert "7 point(s)" in embed.description


def test_games_summary(db):
    session, logic = db
    for i in range(1, 4):
        game = model.Game(game_state="FINISHED", name=f"G{i}")
        session.add(game)
        session.flush()
        player = model.Player(player_id=i, name=f"Winner{i}")
        session.add(player)
        gp = model.GamePlayer(
            game_id=game.game_id, player_id=i, faction="FactionA", points=10
        )
        session.add(gp)
        session.commit()

    result = logic.games().value
    # games returns an Embed
    embed = result
    assert "Winner" in embed.description
    assert "FactionA" in embed.description
    assert "G1" in embed.description
    assert "G2" in embed.description
    assert "G3" in embed.description
