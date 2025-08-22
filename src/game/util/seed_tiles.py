import json
from pathlib import Path
from typing import List, Dict
import argparse

GRAVITY_RIFT = "gravity_rift"
ASTEROID_FIELD = "asteroid_field"
NEBULA = "nebula"
SUPERNOVA = "supernova"

ALPHA = "alpha"
BETA = "beta"
GAMMA = "gamma"
DELTA = "delta"

def get_anomalies(obj_or_planet) -> List[str]:
    anomalies: List[str] = []
    if "anomaly" in obj_or_planet.keys() and obj_or_planet["anomaly"]:
        if "rift" in obj_or_planet["anomaly"] or "gravity" in obj_or_planet["anomaly"]:
            anomalies.append(GRAVITY_RIFT)
        if "asteroid" in obj_or_planet["anomaly"]:
            anomalies.append(ASTEROID_FIELD)
        if "nebula" in obj_or_planet["anomaly"]:
            anomalies.append(NEBULA)
        if "nova" in obj_or_planet["anomaly"]:
            anomalies.append(SUPERNOVA)
    return anomalies

def get_wormholes(obj) -> List[str]:
    wormholes: List[str] = []
    if "wormhole" in obj.keys() and obj["wormhole"]:
        if "alpha" in obj["wormhole"]:
            wormholes.append(ALPHA)
        if "beta" in obj["wormhole"]:
            wormholes.append(BETA)
        if "gamma" in obj["wormhole"]:
            wormholes.append(GAMMA)
        if "delta" in obj["wormhole"]:
            wormholes.append(DELTA)
        if "all" in obj["wormhole"]:
            wormholes.extend([ALPHA, BETA, GAMMA])
    return wormholes


# Define handlers for each type
def handle_green(obj: Dict) -> List[str]:
    # Access type-specific fields, e.g., obj["energy"] or obj["strength"]
    # Planets;Wormholes;Anomalies;Faction;Hyperlanes
    planets: List[str] = []
    anomalies: List[str] = []
    for planet in obj["planets"]:
        planets.append(planet["name"])
        anomalies.extend(get_anomalies(planet))
    anomalies.extend(get_anomalies(obj))
    wormholes = get_wormholes(obj)
    if "faction" in obj.keys():
        faction = obj["faction"]
    else:
        faction = ""

    return [",".join(planets), ",".join(wormholes), ",".join(anomalies), faction, ""]

def handle_blue(obj: Dict) -> List[str]:
    # print(f"Handling BLUE: {obj}")
    # Process blue-specific properties
    
    return handle_green(obj)


def handle_red(obj: Dict) -> List[str]:
    # print(f"Handling RED: {obj}")
    # Process red-specific properties
    return handle_green(obj)


def handle_hyperlane(obj: Dict) -> List[str]:
    # print(f"Handling HYPERLANE: {obj}")
    # Process hyperlane-specific properties

    # Planets;Wormholes;Anomalies;Faction;Hyperlanes
    obj["hyperlanes"]
    return ["", "", "", "", str(obj["hyperlanes"])]


# Dispatch map
type_handlers = {
    "green": handle_green,
    "blue": handle_blue,
    "red": handle_red,
    "hyperlane": handle_hyperlane,
}


def parse_json_file(filepath) -> List[str]:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Top-level JSON structure must be a dictionary.")

    top_row = "Source;Id;Type;Planets;Wormholes;Anomalies;Faction;Hyperlanes"
    all_data: List[str] = [top_row]
    for key, obj in data.items():
        if not isinstance(obj, dict):
            print(f"Skipping {key}: not an object")
            continue
        columns:List[str] = []
        if (str.isdigit(key) and int(key) <= 51):
            columns.append("Base game")
        elif (len(key) <= 3):
            columns.append("Prophecy of Kings")
        else:
            columns.append("Discordant Stars")
        columns.append(key)

        obj_type = obj.get("type")
        if obj_type not in type_handlers:
            print(f"Skipping {key}: unknown type '{obj_type}'")
            continue
        columns.append(obj_type)

        handler = type_handlers[obj_type]
        columns.extend(handler(obj))

        all_data.append(";".join(columns))
    print("\n".join(all_data))
    return all_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", dest="input", type=str, required=True, help="Path to input json file from git@github.com:oskar-sjokvist/miltydraft.git (tiles.json)")
    parser.add_argument("-o", "--output", dest="output", type=str, required=True, help="Path to output csv file, used by this library.")
    args = parser.parse_args()

    data = parse_json_file(args.input)
    with open(args.output, 'w') as output:
        output.write("\n".join(data))

