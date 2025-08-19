#!/usr/bin/env python3
# prints factions missing a lose_against achievement
import csv, json
from pathlib import Path
root = Path(__file__).resolve().parents[1]
csv_path = root / 'src' / 'game' / 'data' / 'ti4_factions.csv'
ach_dir = root / 'src' / 'achievements' / 'achievements'

factions = []
with csv_path.open(encoding='utf-8', newline='') as fh:
    r = csv.reader(fh)
    try:
        next(r)
    except StopIteration:
        pass
    for row in r:
        if row:
            name = row[0].strip()
            if name:
                factions.append(name)

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

missing = []
for f in factions:
    variants = {f}
    if f.startswith('The '):
        variants.add(f[len('The '):])
    if not any(v in covered for v in variants):
        missing.append(f)

print('Missing lose_against achievements count:', len(missing))
if missing:
    print('\n'.join(sorted(missing)))
else:
    print('All factions covered')
