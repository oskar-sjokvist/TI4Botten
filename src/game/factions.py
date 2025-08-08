import random
import csv

from pathlib import Path

from typing import List, Optional

class Faction:
    def __init__(self, name: str, source: str) -> None:
        self.name: str = name
        self.source: str = source

    def __str__(self) -> str:
        return f"{self.name} ({self.source})"


class Factions:
    def __init__(self, factions: List[Faction]) -> None:
        self.factions: List[Faction] = factions

    def get_random_factions(self, number: int, sources: Optional[str]) -> List[Faction]:
        if number <= 0:
            return []
        try:
            if not sources:
                return random.sample(self.factions, number)

            sources = [source.strip() for source in sources.split(',')]
            filtered_factions = [faction for faction in self.factions if faction.source in sources]
            if not filtered_factions:
                return []
            return random.sample(filtered_factions, min(number, len(filtered_factions)))

        except ValueError:
            return []


def read_factions(file_path: str = 'data/TI4_Factions_with_Discordant_Stars.csv') -> Factions:
    here = Path(__file__).parent

    factions: List[Faction] = []
    with open(here / file_path, newline='') as csvfile:
        reader = csv.reader(csvfile, delimiter=',')
        next(reader)  # Skip header row
        for row in reader:
            if len(row) >= 2:  # Ensure there are at least two columns
                name: str = row[0].strip()
                source: str = row[1].strip()
                factions.append(Faction(name, source))
    return Factions(factions)
