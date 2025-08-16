import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.betting import bettinglogic, model as betting_model
from src.game import model as game_model
from src.models import Base


@pytest.fixture(scope="function")
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    logic = bettinglogic.BettingLogic(engine)
    yield session, logic
    session.close()


def test_balance_new_bettor(db):
    _, logic = db
    result = logic.balance(1, "Alice")
    assert "Alice has 1000 Jake coins." in result


def test_balance_existing_bettor(db):
    _, logic = db
    result = logic.balance(2, "Bob")
    assert "Bob has 1000 Jake coins." in result


def test_bet_game_not_found(db):
    session, logic = db
    result = logic.bet(1, 10, "Alice", 1, "Alice")
    assert "Game not found." in result


def test_bet_no_amount(db):
    session, logic = db
    # Setup game in DRAFT state
    game = game_model.Game(
        game_id=1, name="TestGame", game_state=game_model.GameState.DRAFT
    )
    session.add(game)
    session.commit()
    result = logic.bet(1, None, "Alice", 1, "Alice")
    assert "Place a bet amount." in result


def test_bet_no_winner(db):
    session, logic = db
    game = game_model.Game(
        game_id=1, name="TestGame", game_state=game_model.GameState.DRAFT
    )
    session.add(game)
    session.commit()
    result = logic.bet(1, 10, None, 1, "Alice")
    assert "Choose a winner." in result


def test_bet_too_much(db):
    session, logic = db
    game = game_model.Game(
        game_id=1, name="TestGame", game_state=game_model.GameState.DRAFT
    )
    session.add(game)
    session.commit()
    player = game_model.Player(player_id=1, name="Alice")
    bettor = betting_model.Bettor(player_id=1, balance=5)
    session.add_all([player,bettor])
    session.commit()
    result = logic.bet(1, 10, "Alice", 1, "Alice")
    assert "You are trying to bet more than you have." in result


def test_bet_negative(db):
    session, logic = db
    game = game_model.Game(
        game_id=1, name="TestGame", game_state=game_model.GameState.DRAFT
    )
    session.add(game)
    session.commit()
    player = game_model.Player(player_id=1, name="Alice")
    bettor = betting_model.Bettor(player_id=1, balance=100)
    session.add_all([player,bettor])
    session.commit()
    result = logic.bet(1, -5, "Alice", 1, "Alice")
    assert "Nice try" in result


def test_bet_success(db):
    session, logic = db
    # Setup game and player
    game = game_model.Game(
        game_id=1, name="TestGame", game_state=game_model.GameState.DRAFT
    )
    player1 = game_model.Player(player_id=1, name="Alice")
    player2 = game_model.Player(player_id=2, name="Bob")
    session.add(game)
    session.add_all([player1, player2])
    session.commit()
    gp = game_model.GamePlayer(game_id=1, player_id=1)
    session.add(gp)
    session.commit()
    bettor = betting_model.Bettor(player_id=2, balance=100)
    session.add(bettor)
    session.commit()
    result = logic.bet(1, 10, "Alice", 2, "Bob")
    assert "You placed a bet on Alice for 10 Jake coins" in result


def test_payout_game_not_found(db):
    _, logic = db
    result = logic.payout(1)
    assert "Game not found." in result


def test_payout_game_not_finished(db):
    session, logic = db
    game = game_model.Game(
        game_id=1, name="TestGame", game_state=game_model.GameState.DRAFT
    )
    session.add(game)
    session.commit()
    result = logic.payout(1)
    assert "Game is not yet finished" in result


def test_payout_success(db):
    session, logic = db
    # Setup finished game, player, bettor, and bet
    game = game_model.Game(
        game_id=1, name="TestGame", game_state=game_model.GameState.FINISHED
    )
    player1 = game_model.Player(player_id=1, name="Alice")
    player2 = game_model.Player(player_id=2, name="Bob")
    gp = game_model.GamePlayer(game_id=1, player_id=1, points=10)
    bettor = betting_model.Bettor(player_id=2, balance=100)
    bet = betting_model.GameBet(game_id=1, player_id=2, winner=1, bet=10)
    session.add_all([game, player1, player2, gp, bettor, bet])
    session.commit()
    result = logic.payout(1)
    assert "Bob won 10 Jake coins!" in result
