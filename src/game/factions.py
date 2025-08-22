import random
import csv
from pathlib import Path
from typing import List, Optional, Dict
from . import utility

class Faction:
    def __init__(self, name: str, source: str, short_lore) -> None:
        self.name: str = name
        self.source: str = source
        self.short_lore: str = short_lore

    def __str__(self) -> str:
        return f"{self.name} ({self.source}) {self.short_lore}"


class Factions:
    def __init__(self, factions: List[Faction]) -> None:
        self.factions: List[Faction] = factions
        sources = {faction.source for faction in self.factions}

        self.__valid_sources: Dict[str, str] = utility.generate_valid_source_references(sources)

    def get_random_factions(self, number: int, sources: Optional[str]) -> List[Faction]:
        if number <= 0:
            return []
        try:
            if not sources:
                return random.sample(self.factions, number)

            raw_sources = (s.strip() for s in sources.split(","))
            filtered_sources = (s for s in raw_sources if s in self.__valid_sources)
            mapped_sources = {self.__valid_sources[s] for s in filtered_sources}
            filtered_factions = [
                faction for faction in self.factions if faction.source in mapped_sources
            ]
            if not filtered_factions:
                return []
            return random.sample(filtered_factions, min(number, len(filtered_factions)))

        except ValueError:
            return []

    def get_factions(self, sources: Optional[str]) -> List[Faction]:
        if not sources:
            return self.factions

        raw_sources = (s.strip() for s in sources.split(","))
        filtered_sources = (s for s in raw_sources if s in self.__valid_sources)
        mapped_sources = {self.__valid_sources[s] for s in filtered_sources}
        filtered_factions = [
            faction for faction in self.factions if faction.source in mapped_sources
        ]
        return filtered_factions


def read_factions(file_path: str = "data/ti4_factions.csv") -> Factions:
    here = Path(__file__).parent

    factions: List[Faction] = []
    with open(here / file_path, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        next(reader)  # Skip header row
        for row in reader:
            if len(row) >= 3:  # Ensure there are at least two columns
                name: str = row[0].strip()
                source: str = row[1].strip()
                short_lore: str = row[2].strip()
                factions.append(Faction(name, source, short_lore))
    return Factions(factions)
