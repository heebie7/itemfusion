"""Generate the mod's fusion recipe JSONs from T's schematic + decisions.json.

Usage: python3 scripts/gen_recipes.py <chest.schem>

Writes src/main/resources/data/itemfusion/recipes/auto/*.json (that folder is
wiped first, so it always mirrors the schematic exactly).

Wildcards become multi-option ingredients. Result NBT is preserved as SNBT —
the TACZ guns are all the same item id and differ only by GunId.
"""
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nbt_schem import load_schematic, chests_with_items, to_snbt
from scan_conflicts import (MENDING_WILDCARDS, WOODS, has_mending, oak_wildcard,
                            load_overrides, apply_overrides)

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT_DIR = os.path.join(ROOT, 'src/main/resources/data/itemfusion/recipes/auto')


def ingredient_json(item):
    """Ingredient as JSON. NBT on ingredients is ignored (T's rule) except the
    Mending marker, which means 'any item of this class'."""
    iid, tag = item['id'], item['tag']
    if tag and has_mending(tag) and iid in MENDING_WILDCARDS:
        _, expansion = MENDING_WILDCARDS[iid]
        return [{'item': i} for i in expansion]
    oak = oak_wildcard(iid)
    if oak:
        return [{'item': i} for i in oak[1]]
    return {'item': iid}


def result_json(item):
    out = {'item': item['id']}
    if item['count'] > 1:
        out['count'] = item['count']
    tag = {k: v for k, v in (item['tag'] or {}).items() if not (k == 'Damage' and v == 0)}
    if tag:
        types = getattr(item['tag'], 'types', {})
        inner = ','.join(f'{k}:{to_snbt(v, types.get(k))}' for k, v in tag.items())
        out['nbt'] = '{' + inner + '}'
    return out


def slug(text, used):
    base = re.sub(r'[^a-z0-9_]+', '_', text.lower()).strip('_')[:48] or 'recipe'
    name, n = base, 2
    while name in used:
        name = f'{base}_{n}'
        n += 1
    used.add(name)
    return name


def main(schem_path):
    schem = load_schematic(schem_path)
    overrides = load_overrides()

    if os.path.isdir(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    os.makedirs(OUT_DIR)

    used, written, skipped = set(), 0, []
    for pos, cid, items in chests_with_items(schem):
        by_slot = {it['slot']: it for it in items}
        for row in range(3):
            b = row * 9
            for side, (s1, s2, sr) in [('L', (b, b + 1, b + 3)), ('R', (b + 5, b + 6, b + 8))]:
                i1, i2, res = by_slot.get(s1), by_slot.get(s2), by_slot.get(sr)
                if not (i1 and i2 and res):
                    if i1 or i2 or res:
                        have = [x['id'] for x in (i1, i2, res) if x]
                        skipped.append(f'сундук{pos} ряд {row + 1} {side}: неполно, лежит {have}')
                    continue
                i1, i2, _note = apply_overrides(i1, i2, res, overrides)
                recipe = {
                    'type': 'itemfusion:fusion',
                    'ingredients': [ingredient_json(i1), ingredient_json(i2)],
                    'result': result_json(res),
                }
                gun = (res['tag'] or {}).get('GunId')
                label = f"{res['id'].split(':')[-1]}_{str(gun).split(':')[-1]}" if gun \
                    else res['id'].split(':')[-1]
                name = slug(label, used)
                with open(os.path.join(OUT_DIR, f'{name}.json'), 'w', encoding='utf-8') as f:
                    json.dump(recipe, f, ensure_ascii=False, indent=1)
                written += 1

    print(f'написано рецептов: {written}')
    for s in skipped:
        print('  ПРОПУЩЕНО:', s)


if __name__ == '__main__':
    main(sys.argv[1])
