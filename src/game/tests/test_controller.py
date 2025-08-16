import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.game.controller import GameController
from src.game import model
from src.models import Base


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


def test_players_ordered_by_turn_and_current_drafter(db):
    session = db
    game = model.Game(game_id=1,game_state=model.GameState.LOBBY, name="Ctest")
    session.add(game)
    # create three players and gameplayers with turn orders 2,0,1
    for i, turn in enumerate([2, 0, 1], start=1):
        p = model.Player(player_id=i, name=f"P{i}")
        session.add(p)
        gp = model.GamePlayer(game_id=game.game_id, player_id=p.player_id, turn_order=turn)
        session.add(gp)
    session.commit()

    ctrl = GameController()
    ordered = ctrl.players_ordered_by_turn(session, game)
    assert [g.player.name for g in ordered] == ["P2", "P3", "P1"]

    # set turn to 1 -> current drafter should be player with turn_order == 1
    game.turn = 1
    session.merge(game)
    session.commit()
    current = ctrl.current_drafter(session, game)
    assert current.turn_order == 1


def test_winner_and_errors(db):
    session = db
    game = model.Game(game_state=model.GameState.STARTED, name="WinnerTest")
    session.add(game)
    # no players yet -> winner should raise
    session.commit()
    ctrl = GameController()
    with pytest.raises(LookupError):
        ctrl.winner(session, game)

    # add players with points
    p1 = model.Player(player_id=10, name="A")
    p2 = model.Player(player_id=11, name="B")
    session.add_all([p1, p2])
    gp1 = model.GamePlayer(game_id=game.game_id, player_id=10, points=5)
    gp2 = model.GamePlayer(game_id=game.game_id, player_id=11, points=12)
    session.add_all([gp1, gp2])
    session.commit()

    winner = ctrl.winner(session, game)
    assert winner.player.name == "B"
