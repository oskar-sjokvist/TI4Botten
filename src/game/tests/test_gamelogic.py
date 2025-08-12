import pytest
from unittest.mock import MagicMock
from sqlalchemy.orm import Session
from src.game import gamelogic

@pytest.fixture
def mock_session():
    # Use MagicMock for session. Consider using a hermetic db with fake data.
    return MagicMock(spec=Session)


def test_parse_ints():
    assert gamelogic._parse_ints("1 2 3") == [1, 2, 3]
    assert gamelogic._parse_ints("-1, 0, 42") == [-1, 0, 42]
    assert gamelogic._parse_ints("") == []


def test_finish_no_game_id(mock_session):
    result = gamelogic.finish(mock_session, True, None, None)
    assert "Please specify a game id." in result


def test_lobby_no_name(mock_session):
    result = gamelogic.lobby(mock_session, None)
    assert "Please specify a name for the lobby" in result


def test_leave_not_in_lobby(mock_session):
    # _find_lobby returns a mock game
    mock_session.query.return_value.with_parent.return_value.filter.return_value.first.return_value = None
    gamelogic._find_lobby = MagicMock(return_value=MagicMock())
    result = gamelogic.leave(mock_session, 1, 1)
    assert "You are not in this game!" in result


def test_join_already_in_lobby(mock_session):
    mock_game = MagicMock()
    gamelogic._find_lobby = MagicMock(return_value=mock_game)
    mock_session.query.return_value.with_parent.return_value.filter.return_value.first.return_value = True
    result = gamelogic.join(mock_session, 1, "Player", 1)
    assert "You are already in this lobby!" in result


def test_games_no_games(mock_session):
    mock_session.query.return_value.order_by.return_value.filter_by.return_value.limit.return_value.all.return_value = []
    result = gamelogic.games(mock_session)
    assert "No games found." in result
