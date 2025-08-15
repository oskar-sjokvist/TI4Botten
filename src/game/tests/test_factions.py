import pytest
from src.game.factions import Faction, Factions


@pytest.fixture
def sample_factions():
    return Factions(
        [
            Faction("FactionA", "Base", ""),
            Faction("FactionB", "Expansion", ""),
            Faction("FactionC", "Base", ""),
            Faction("FactionD", "Expansion", ""),
        ]
    )


def test_get_random_factions_count(sample_factions):
    result = sample_factions.get_random_factions(2, None)
    assert len(result) == 2
    assert all(isinstance(f, Faction) for f in result)


def test_get_random_factions_sources(sample_factions):
    result = sample_factions.get_random_factions(2, "Base")
    assert all(f.source == "Base" for f in result)
    assert len(result) <= 2


def test_get_random_factions_multiple_sources(sample_factions):
    result = sample_factions.get_random_factions(3, "Base,Expansion")
    assert len(result) == 3
    sources = set(f.source for f in result)
    assert sources.issubset({"Base", "Expansion"})


def test_get_random_factions_zero(sample_factions):
    result = sample_factions.get_random_factions(0, None)
    assert result == []


def test_get_random_factions_invalid_source(sample_factions):
    result = sample_factions.get_random_factions(2, "Nonexistent")
    assert result == []
