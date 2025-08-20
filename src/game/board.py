import csv
from pathlib import Path
from typing import List, Optional
from enum import Enum


class TechSpeciality(Enum):
    GREEN = "GREEN"
    RED = "RED"
    BLUE = "BLUE"
    YELLOW = "YELLOW"


class Trait(Enum):
    CULTURAL = "CULTURAL"
    HAZARDOUS = "HAZARDOUS"
    INDUSTRIAL = "INDUSTRIAL"


class Planet:
    def __init__(self, source: str, name: str, resources: int, influence: int, tech_specialities: List[TechSpeciality], traits: List[Trait], legendary: bool, legendary_ability: Optional[str], home_system: bool, flavour_text: Optional[str]):
        self.source: str = source
        self.name: str = name
        self.resources: int = resources
        self.influence: int = influence
        self.tech_specialities: List[TechSpeciality] = tech_specialities
        self.traits: List[Trait] = traits
        self.legendary: bool = legendary
        self.legendary_ability: Optional[str] = legendary_ability
        self.home_system: bool = home_system
        self.flavour_text: Optional[str] = flavour_text
    
    def __repr__(self):
        return f"{self.name} ({self.resources}/{self.influence})"
    
    def has_green_tech(self):
        return TechSpeciality.GREEN in self.tech_specialities
    
    def has_red_tech(self):
        return TechSpeciality.RED in self.tech_specialities
    
    def has_blue_tech(self):
        return TechSpeciality.BLUE in self.tech_specialities
    
    def has_yellow_tech(self):
        return TechSpeciality.YELLOW in self.tech_specialities

    def is_cultural(self):
        return Trait.CULTURAL in self.traits
    
    def is_hazardous(self):
        return Trait.HAZARDOUS in self.traits
    
    def is_industrial(self):
        return Trait.INDUSTRIAL in self.traits

    def is_legendary(self):
        return self.legendary

class System:
    def __init__(self, id: int, planets: List[Planet], source: str) -> None:
        self.id: int = id
        self.planets: List[Planet] = planets
        self.source: str = source

    def __str__(self) -> str:
        return f"{self.id}: ({','.join(map(str,self.planets))})"


def read_planets(file_path: str = "data/ti4_planets.csv") -> List[Planet]:
    here = Path(__file__).parent

    planets: List[Planet] = []
    with open(here / file_path, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=";")
        next(reader)  # Skip header row
        for row in reader:
            if len(row) >= 9:
                source: str = row[0].strip()
                name: str = row[1].strip()
                traits_str: List[str] = row[2].strip().split(",")
                traits: List[Trait] = []
                if (str(Trait.CULTURAL.value) in traits_str):
                    traits.append(Trait.CULTURAL)
                if (str(Trait.HAZARDOUS.value) in traits_str):
                    traits.append(Trait.HAZARDOUS)
                if (str(Trait.INDUSTRIAL.value) in traits_str):
                    traits.append(Trait.INDUSTRIAL)
                legendary: bool = bool(row[3].strip())
                resources: int = int(row[4].strip())
                influence: int = int(row[5].strip())
                tech_str: List[str] = row[6].strip().split(",")
                tech: List[TechSpeciality] = []
                if (str(TechSpeciality.BLUE) in tech_str):
                    tech.append(TechSpeciality.BLUE)
                if (str(TechSpeciality.RED) in tech_str):
                    tech.append(TechSpeciality.RED)
                if (str(TechSpeciality.YELLOW) in tech_str):
                    tech.append(TechSpeciality.YELLOW)
                if (str(TechSpeciality.GREEN) in tech_str):
                    tech.append(TechSpeciality.GREEN)
                legendary_ability: str = row[7].strip()
                flavour_text: str = row[8].strip()
                planets.append(Planet(source, name, resources, influence, tech, traits, legendary, legendary_ability, False, flavour_text))
    return planets
