import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.game import gamelogic, model
from src.models import Base

@pytest.fixture(scope="function")
def session():
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_parse_ints():
    assert gamelogic._parse_ints("1 2 3") == [1, 2, 3]
    assert gamelogic._parse_ints("-1, 0, 42") == [-1, 0, 42]
    assert gamelogic._parse_ints("") == []


def test_finish_no_game_id(session):
    result = gamelogic.finish(session, True, None, None)
    assert "Please specify a game id." in result


def test_lobby_no_name(session):
    result = gamelogic.lobby(session, 1, "player_name", None)
    assert "Please specify a name for the lobby" in result


def test_leave_not_in_lobby(session, monkeypatch):
    # Patch _find_lobby to return a real Game instance
    game = model.Game(game_id=1, game_state="LOBBY", name="TestLobby")
    session.add(game)
    session.commit()
    monkeypatch.setattr(gamelogic, "_find_lobby", lambda s, gid: game)
    result = gamelogic.leave(session, 1, 1)
    assert "You are not in this game!" in result


def test_join_already_in_lobby(session, monkeypatch):
    # Patch _find_lobby to return a real Game instance
    game = model.Game(game_id=1, game_state="LOBBY", name="TestLobby")
    session.add(game)
    session.commit()
    monkeypatch.setattr(gamelogic, "_find_lobby", lambda s, gid: game)
    player = model.Player(player_id=1, name="Alice")
    session.add(player)
    # Insert a dummy GamePlayer to simulate already in lobby
    gp = model.GamePlayer(game_id=1, player_id=1)
    session.add(gp)
    session.commit()
    result = gamelogic.join(session, 1, "Alice", 1)
    assert "You are already in this lobby!" in result


def test_games_no_games(session):
    result = gamelogic.games(session)
    assert "No games found." in result


def test_lobby_and_join_leave(session):
    # Create lobby
    lobby_name = "TestLobby"
    result = gamelogic.lobby(session, 1, "Alice", lobby_name)
    assert f"Game lobby '{lobby_name}' created" in result
    game = session.query(model.Game).filter_by(name=lobby_name).first()
    assert game is not None

    # Leave lobby
    leave_result = gamelogic.leave(session, 1, game.game_id)
    assert "Removing lobby" in leave_result

    game = session.query(model.Game).filter_by(name=lobby_name).first()
    assert game is None


def test_join_limit(session):
    lobby_name = "FullLobby"
    gamelogic.lobby(session, 0, "Alice", lobby_name)
    game = session.query(model.Game).filter_by(name=lobby_name).first()
    # Add 7 players
    for i in range(1, 8):
        gamelogic.join(session, i, f"Player{i}", game.game_id)
    # Try to add 9th
    result = gamelogic.join(session, 9, "Player9", game.game_id)

    assert "Player limit reached" in result


def test_finish_game_flow(session):
    # Setup game and players
    game = model.Game(game_state="STARTED", name="FinishTest")
    session.add(game)
    session.commit()
    # Add players
    for i in range(1, 4):
        player = model.Player(player_id=i, name=f"P{i}")
        session.add(player)
        gp = model.GamePlayer(game_id=game.game_id, player_id=i, points=0, rank=i)
        session.add(gp)
    session.commit()
    # Patch controller.players_ordered_by_turn
    import src.game.controller as controller
    def ordered_by_turn(session, game):
        return session.query(model.GamePlayer).with_parent(game).all()
    controller.players_ordered_by_turn = ordered_by_turn
    # Finish game
    result = gamelogic.finish(session, False, game.game_id, "10 5 7")
    assert "has finished" in result
    assert "10 point(s)" in result
    assert "5 point(s)" in result
    assert "7 point(s)" in result


def test_games_summary(session):
    # Create finished games
    for i in range(1, 4):
        game = model.Game(game_state="FINISHED", name=f"G{i}")
        session.add(game)
        session.flush()  # Flush to get game_id
        player = model.Player(player_id=i, name=f"Winner{i}")
        session.add(player)
        gp = model.GamePlayer(game_id=game.game_id, player_id=i, faction="FactionA", points=10)
        session.add(gp)
        session.commit()

    result = gamelogic.games(session)
    assert "Winner" in result
    assert "FactionA" in result
    assert "G1" in result
    assert "G2" in result
    assert "G3" in result
