import csv
from pathlib import Path
from typing import List, Optional, Dict
from enum import Enum
import ast
import logging
from . import utility
import random

class TechSpeciality(Enum):
    GREEN = "GREEN"
    RED = "RED"
    BLUE = "BLUE"
    YELLOW = "YELLOW"


class Trait(Enum):
    CULTURAL = "CULTURAL"
    HAZARDOUS = "HAZARDOUS"
    INDUSTRIAL = "INDUSTRIAL"


class Wormhole(Enum):
    ALPHA = "ALPHA"
    BETA = "BETA"
    GAMMA = "GAMMA"
    DELTA = "DELTA"


class Anomaly(Enum):
    ASTEROID_FIELD = "ASTEROID_FIELD"
    GRAVITY_RIFT = "GRAVITY_RIFT"
    NEBULA = "NEBULA"
    SUPERNOVA = "SUPERNOVA"


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

    @staticmethod
    def get_random_planets(planets: List, number: int = 5, source_str: Optional[str] = None):
        final_source_list = set()
        if source_str:
            source_list = source_str.split(",")
            sources = {planet.source for planet in planets}
            valid_sources: Dict[str, str] = utility.generate_valid_source_references(sources)
            for source in source_list:
                if source in valid_sources:
                    final_source_list.add(valid_sources[source])
                else:
                    return f"Couldn't parse {source}"
        else:
            final_source_list = {planet.source for planet in planets}

        valid_planets = [planet for planet in planets if planet.source in final_source_list]
        return random.sample(valid_planets, min(number, len(valid_planets)))


class System:
    def __init__(self, source: str, id: str, planets: List[Planet], system_type: str, wormholes: List[Wormhole], anomalies: List[Anomaly], faction: Optional[str], hyperlanes: Optional[List[List[int]]]) -> None:
        self.source: str = source
        self.id: str = id
        self.planets: List[Planet] = planets
        self.type: str = system_type
        self.wormholes: List[Wormhole] = wormholes
        self.anomalies: List[Anomaly] = anomalies
        self.faction: Optional[str] = faction
        self.hyperlanes: Optional[List[List[int]]] = hyperlanes
        # Source;Id;Type;Planets;Wormholes;Anomalies;Faction;Hyperlanes


    def __str__(self) -> str:
        return f"{self.id}: ({', '.join(map(str,self.planets))})"


    @staticmethod
    def get_random_systems(systems: List, number: int = 5, source_str: Optional[str] = None):
        final_source_list = set()
        if source_str:
            source_list = source_str.split(",")
            sources = {system.source for system in systems}
            valid_sources: Dict[str, str] = utility.generate_valid_source_references(sources)
            for source in source_list:
                if source in valid_sources:
                    final_source_list.add(valid_sources[source])
                else:
                    return f"Couldn't parse {source}"
        else:
            final_source_list = {system.source for system in systems}

        valid_systems = [system for system in systems if system.source in final_source_list]
        return random.sample(valid_systems, min(number, len(valid_systems)))


def parse_list_of_lists(s: str) -> List[List[int]]:
    """
    Parse a string containing a list of list of integers into a Python object.


    Example:
    "[[1, 2, 3], [4, 5], [6]]" -> [[1, 2, 3], [4, 5], [6]]
    """
    try:
        obj = ast.literal_eval(s)
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"Invalid input string: {e}")
    if not (isinstance(obj, list) and all(isinstance(sub, list) for sub in obj)):
        raise ValueError("Input must be a list of lists")
    for sub in obj:
        if not all(isinstance(x, int) for x in sub):
            raise ValueError("All elements must be integers")
    return obj


def read_systems(planet_list: List[Planet], file_path: str = "data/ti4_systems.csv") -> List[System]:
    here = Path(__file__).parent
    planet_map: Dict[str, Planet] = {planet.name.lower(): planet for planet in planet_list}
    systems: List[System] = []
    with open(here / file_path, newline="") as csvfile:
        reader = csv.reader(csvfile, delimiter=";")
        next(reader)  # Skip header row
        for row in reader:
            try:
                source: str = row[0].strip()
                id: str = row[1].strip()
                system_type: str = row[2].strip()
                planet_names: List[str] = row[3].strip().split(",")
                planets: List[Planet] = []
                for planet_name in planet_names:
                    if not planet_name:
                        continue
                    elif planet_name.lower() in planet_map:
                        planets.append(planet_map[planet_name.lower()])
                    else:
                        logging.info(f"Couldn't parse planet name {planet_name}")

                wormhole_str: str = row[4].strip()
                wormholes: List[Wormhole] = []
                if (str(Wormhole.ALPHA.value).lower() in wormhole_str):
                    wormholes.append(Wormhole.ALPHA)
                if (str(Wormhole.BETA.value).lower() in wormhole_str):
                    wormholes.append(Wormhole.BETA)
                if (str(Wormhole.GAMMA.value).lower() in wormhole_str):
                    wormholes.append(Wormhole.GAMMA)
                if (str(Wormhole.DELTA.value).lower() in wormhole_str):
                    wormholes.append(Wormhole.DELTA)

                anomaly_str: str = row[5].strip()
                anomalies: List[Anomaly] = []
                if (str(Anomaly.ASTEROID_FIELD.value).lower() in anomaly_str):
                    anomalies.append(Anomaly.ASTEROID_FIELD)
                if (str(Anomaly.GRAVITY_RIFT.value).lower() in anomaly_str):
                    anomalies.append(Anomaly.GRAVITY_RIFT)
                if (str(Anomaly.NEBULA.value).lower() in anomaly_str):
                    anomalies.append(Anomaly.NEBULA)
                if (str(Anomaly.SUPERNOVA.value).lower() in anomaly_str):
                    anomalies.append(Anomaly.SUPERNOVA)

                faction_str = row[6].strip()
                if faction_str:
                    faction = faction_str
                else:
                    faction = None
                
                hyperlanes_str = row[7].strip()
                if hyperlanes_str:
                    hyperlanes = parse_list_of_lists(hyperlanes_str)
                else:
                    hyperlanes = None
                
                systems.append(System(source, id, planets, system_type, wormholes, anomalies, faction, hyperlanes))
            except Exception as e:
                logging.exception(f"Failed to parse systems list: {e}") 

    return systems


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
