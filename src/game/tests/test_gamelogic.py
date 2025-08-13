import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.game import gamelogic, model
from src.models import Base

@pytest.fixture(scope="function")
def db():
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    logic = gamelogic.GameLogic(engine)
    yield session, logic
    session.close()

def test_parse_ints():
    assert gamelogic.GameLogic._parse_ints("1 2 3") == [1, 2, 3]
    assert gamelogic.GameLogic._parse_ints("-1, 0, 42") == [-1, 0, 42]
    assert gamelogic.GameLogic._parse_ints("") == []

def test_finish_no_game_id(db):
    _, logic = db
    result = logic.finish(True, None, None)
    assert "Please specify a game id." in result

def test_lobby_no_name(db):
    _, logic = db
    result = logic.lobby(1, "player_name", None)
    assert "Please specify a name for the lobby" in result

def test_leave_not_in_lobby(db):
    session, logic = db
    game = model.Game(game_id=1, game_state="LOBBY", name="TestLobby")
    session.add(game)
    session.commit()
    result = logic.leave(1, 1)
    assert "You are not in this game!" in result

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
    assert "You are already in this lobby!" in result

def test_games_no_games(db):
    _, logic = db
    result = logic.games()
    assert "No games found." in result

def test_lobby_and_join_leave(db):
    session, logic = db
    lobby_name = "TestLobby"
    result = logic.lobby(1, "Alice", lobby_name)
    assert f"Game lobby '{lobby_name}' created" in result
    game = session.query(model.Game).filter_by(name=lobby_name).first()
    assert game is not None

    leave_result = logic.leave(1, game.game_id)
    assert "Removing lobby" in leave_result

    game = session.query(model.Game).filter_by(name=lobby_name).first()
    assert game is None

def test_join_limit(db):
    session, logic = db
    lobby_name = "FullLobby"
    logic.lobby(0, "Alice", lobby_name)
    game = session.query(model.Game).filter_by(name=lobby_name).first()
    for i in range(1, 8):
        logic.join(game.game_id, i, f"Player{i}")
    result = logic.join(game.game_id, 9, "Player9")
    assert "Player limit reached" in result

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
    result = logic.finish(False, game.game_id, "10 5 7")
    assert "has finished" in result
    assert "10 point(s)" in result
    assert "5 point(s)" in result
    assert "7 point(s)" in result

def test_games_summary(db):
    session, logic = db
    for i in range(1, 4):
        game = model.Game(game_state="FINISHED", name=f"G{i}")
        session.add(game)
        session.flush()
        player = model.Player(player_id=i, name=f"Winner{i}")
        session.add(player)
        gp = model.GamePlayer(game_id=game.game_id, player_id=i, faction="FactionA", points=10)
        session.add(gp)
        session.commit()

    result = logic.games()
    assert "Winner" in result
    assert "FactionA" in result
    assert "G1" in result
    assert "G2" in result
    assert "G3" in result