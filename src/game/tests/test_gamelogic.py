import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.game import gamelogic, model

@pytest.fixture(scope="function")
def session():
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    model.Base.metadata.create_all(engine)
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
    result = gamelogic.lobby(session, None)
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
    # Insert a dummy GamePlayer to simulate already in lobby
    gp = model.GamePlayer(game_id=1, player_id=1)
    session.add(gp)
    session.commit()
    result = gamelogic.join(session, 1, "Player", 1)
    assert "You are already in this lobby!" in result


def test_games_no_games(session):
    result = gamelogic.games(session)
    assert "No games found." in result
