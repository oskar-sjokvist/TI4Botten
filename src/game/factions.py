import random
import csv

from collections import defaultdict

from pathlib import Path

from typing import List, Optional, Dict, Set

class Faction:
    def __init__(self, name: str, source: str) -> None:
        self.name: str = name
        self.source: str = source

    def __str__(self) -> str:
        return f"{self.name} ({self.source})"


class Factions:
    def __init__(self, factions: List[Faction]) -> None:
        self.factions: List[Faction] = factions
        self.__valid_sources : Dict[str, str] = self.__generate_valid_source_references()

    def __generate_valid_source_references(self) -> Dict[str, str]:
        sources = {faction.source for faction in self.factions}

        # Build shortforms
        valid_shortforms: Dict[str, Set[str]] = defaultdict(set)
        for source in sources:
            words = source.split()
            if not words:
                continue

            # Initials in mixed, lower, and upper case
            initials = "".join(word[0] for word in words)
            valid_shortforms[source].update({initials, initials.lower(), initials.upper()})

            # First word logic (skip "a" or "the")
            first_word_index = 1 if words[0].lower() in {"a", "the"} and len(words) > 1 else 0
            first_word = words[first_word_index]
            valid_shortforms[source].update({first_word, first_word.lower(), first_word.upper()})

        # Uniqueness check
        shortform_to_sources = defaultdict(list)
        for source, shortforms in valid_shortforms.items():
            for sf in shortforms:
                shortform_to_sources[sf].append(source)

        # Keep only unique mappings
        shortform_mapping = {sf: srcs[0] for sf, srcs in shortform_to_sources.items() if len(srcs) == 1}

        # Always map full sources to themselves
        shortform_mapping.update({src: src for src in sources})

        return shortform_mapping

    def get_random_factions(self, number: int, sources: Optional[str]) -> List[Faction]:
        if number <= 0:
            return []
        try:
            if not sources:
                return random.sample(self.factions, number)

            raw_sources = (s.strip() for s in sources.split(','))
            filtered_sources = (s for s in raw_sources if s in self.__valid_sources)
            mapped_sources = {self.__valid_sources[s] for s in filtered_sources}
            filtered_factions = [faction for faction in self.factions if faction.source in mapped_sources]
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
