#!/usr/bin/env python3
"""Generate missing lose_against achievement JSON files.
Usage: python scripts/generate_lose_against.py
"""
import csv
import json
import re
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

# read existing lose_against entries
covered = set()
for p in ach_dir.glob('*.json'):
    try:
        d = json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        continue
    rj = d.get('rule_json') or {}
    if rj.get('type') != 'finish':
        continue
    filt = rj.get('filter') or {}
    name = filt.get('lose_against')
    if name:
        covered.add(name)

# helper slugify
def slugify(s: str) -> str:
    s = s.strip()
    # remove common punctuation but keep unicode letters
    s = s.replace('’', "'")
    s = s.replace('‑', '-')
    s = s.replace('–', '-')
    s = s.replace('’', "'")
    s = s.replace(' ', '_')
    # remove characters that are not alnum or underscore or hyphen or apostrophe
    s = re.sub(r"[^0-9A-Za-z_\-']+", '', s)
    s = s.lower()
    s = re.sub(r"'", '', s)
    s = re.sub(r"-", '_', s)
    s = re.sub(r"__+", '_', s)
    return s

created = []
for f in factions:
    variants = {f}
    if f.startswith('The '):
        variants.add(f[len('The '):])
    if any(v in covered for v in variants):
        continue
    # create file
    slug = slugify(f)
    filename = f'lose_against_{slug}.json'
    path = ach_dir / filename
    data = {
        'achievement_id': f'lose_against_{slug}',
        'key': f'lose_against_{slug}',
        'version': 1,
        'name': f'Lose against {f}',
        'description': f'Lose a game against {f}.',
        'rule_json': {
            'type': 'finish',
            'filter': {'lose_against': f},
            'target': 1,
        },
        'points': 50,
        'is_active': True,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    created.append(str(path.name))

print(f'Created {len(created)} achievement files')
for c in created:
    print(c)
