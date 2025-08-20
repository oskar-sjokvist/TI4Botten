import csv
from pathlib import Path
from typing import List


class StrategyCard:
    def __init__(self, initiative_order: int, name: str, primary: str, secondary: str) -> None:
        self.initiative_order: int = initiative_order
        self.name: str = name
        self.primary: str = primary
        self.secondary: str = secondary

    def __str__(self) -> str:
        return f"{self.initiative_order}. {self.name}"


def read_strategy_cards(file_path: str = "data/ti4_strategy_cards.csv") -> List[StrategyCard]:
    here = Path(__file__).parent

    strategy_cards: List[StrategyCard] = []
    with open(here / file_path, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        next(reader)  # Skip header row
        for row in reader:
            if len(row) >= 3:  # Ensure there are at least two columns
                initiative: int = int(row[0].strip())
                name: str = row[1].strip()
                primary: str = row[2].strip()
                secondary: str = row[3].strip()
                strategy_cards.append(StrategyCard(initiative, name, primary, secondary))
    return strategy_cards
