#!/usr/bin/env python3
"""Check which factions are missing `win_against` achievement JSONs and report on Minerva."""
import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
csv_path = root / 'src' / 'game' / 'data' / 'ti4_factions.csv'
ach_dir = root / 'src' / 'achievements' / 'achievements'

if not csv_path.exists():
    raise SystemExit(f"Faction CSV not found: {csv_path}")
if not ach_dir.exists():
    raise SystemExit(f"Achievements dir not found: {ach_dir}")

# read factions
factions = []
with csv_path.open(newline='', encoding='utf-8') as fh:
    reader = csv.reader(fh)
    try:
        next(reader)
    except StopIteration:
        pass
    for row in reader:
        if not row:
            continue
        name = row[0].strip()
        if name:
            factions.append(name)

# read existing win_against entries
wins = set()
for p in ach_dir.glob('*.json'):
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    rj = d.get('rule_json') or {}
    if rj.get('type') != 'finish':
        continue
    filt = rj.get('filter') or {}
    name = filt.get('win_against')
    if name:
        wins.add(name)

missing = []
for f in factions:
    variants = {f}
    if f.startswith('The '):
        variants.add(f[len('The '):])
    if not any(v in wins for v in variants):
        missing.append(f)

print(f"Factions total: {len(factions)}")
print(f"win_against achievements found: {len(wins)}")
print()
print("Missing win_against achievements:")
for m in missing:
    print('-', m)

print()
print('Minerva present in factions list:', 'Minerva' in factions)
print('Minerva present in win achievements:', 'Minerva' in wins)

# Also print if any win achievement mentions Minerva substring
print('Any win achievement mentioning "Minerva" (substring search):', any('minerva' in w.lower() for w in wins))
