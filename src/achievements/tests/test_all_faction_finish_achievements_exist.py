import csv
import json
from pathlib import Path


def test_all_factions_have_finish_achievement():
    root = Path(__file__).resolve().parents[3]
    csv_path = root / "src" / "game" / "data" / "ti4_factions.csv"
    assert csv_path.exists(), f"Faction CSV not found at {csv_path}"

    factions = []
    with csv_path.open(newline='', encoding='utf-8') as fh:
        reader = csv.reader(fh)
        # skip header
        try:
            header = next(reader)
        except StopIteration:
            header = None
        for row in reader:
            if not row:
                continue
            name = row[0].strip()
            if name:
                factions.append(name)

    assert factions, "No factions parsed from CSV"

    achievements_dir = root / "src" / "achievements" / "achievements"
    assert achievements_dir.exists(), f"Achievements dir not found at {achievements_dir}"

    covered = set()
    for p in achievements_dir.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            continue
        rule = data.get("rule_json") or {}
        if rule.get("type") != "finish":
            continue
        filt = rule.get("filter") or {}
        faction_name = filt.get("play_as_faction")
        if faction_name:
            covered.add(faction_name)

    # Accept achievements that list the faction either exactly as in CSV or without a leading 'The '
    def variants(name):
        yield name
        if name.startswith("The "):
            yield name[len("The "):]

    uncovered = []
    for f in factions:
        if any(v in covered for v in variants(f)):
            continue
        uncovered.append(f)

    assert not uncovered, f"Missing finish achievements for factions: {sorted(uncovered)}"
