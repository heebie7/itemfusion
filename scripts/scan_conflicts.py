"""Conflict scanner for T's 1800 fusion combos.

Reads the chest schematic, normalizes wildcards (Mending-enchanted marker
items), finds duplicate/overlapping ingredient pairs, writes a report for T.
Does NOT fix anything — T decides replacements.

Usage: python3 scripts/scan_conflicts.py <chest.schem> <out-dir>
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nbt_schem import load_schematic, chests_with_items

# --- wildcard classes (T's rules: diamond/netherite excluded, "only below") ---
TIERS_TOOL = ['wooden', 'stone', 'golden', 'iron']
ARMOR_MATS = ['leather', 'golden', 'iron']          # T: кожа/железо/золото (chainmail НЕ включён — допущение)
FLOWERS = ['dandelion', 'poppy', 'blue_orchid', 'allium', 'azure_bluet',
           'red_tulip', 'orange_tulip', 'white_tulip', 'pink_tulip',
           'oxeye_daisy', 'cornflower', 'lily_of_the_valley',
           'torchflower']                            # подтверждено Т 08-11: БЕЗ визер-розы и двухблочных
RAW_MEAT = ['beef', 'porkchop', 'chicken', 'mutton', 'rabbit']  # подтверждено Т 08-11: рыба НЕ входит

WILDCARDS = {
    'lbu2:sword_frame':      ('ЛЮБОЙ_МЕЧ',        [f'minecraft:{t}_sword' for t in TIERS_TOOL]),
    'lbu2:helmet_frame':     ('ЛЮБОЙ_ШЛЕМ',       [f'minecraft:{m}_helmet' for m in ARMOR_MATS]),
    'lbu2:chestplate_frame': ('ЛЮБОЙ_НАГРУДНИК',  [f'minecraft:{m}_chestplate' for m in ARMOR_MATS]),
    'lbu2:leggings_frame':   ('ЛЮБЫЕ_ПОНОЖИ',     [f'minecraft:{m}_leggings' for m in ARMOR_MATS]),
    'lbu2:boots_frame':      ('ЛЮБЫЕ_БОТИНКИ',    [f'minecraft:{m}_boots' for m in ARMOR_MATS]),
    'minecraft:iron_pickaxe': ('ЛЮБАЯ_КИРКА',     [f'minecraft:{t}_pickaxe' for t in TIERS_TOOL]),
    'minecraft:iron_axe':     ('ЛЮБОЙ_ТОПОР',     [f'minecraft:{t}_axe' for t in TIERS_TOOL]),
    'minecraft:iron_shovel':  ('ЛЮБАЯ_ЛОПАТА',    [f'minecraft:{t}_shovel' for t in TIERS_TOOL]),
    'minecraft:iron_hoe':     ('ЛЮБАЯ_МОТЫГА',    [f'minecraft:{t}_hoe' for t in TIERS_TOOL]),
    'minecraft:dandelion':    ('ЛЮБОЙ_ЦВЕТОК',    [f'minecraft:{f}' for f in FLOWERS]),
    'minecraft:beef':         ('ЛЮБОЕ_СЫРОЕ_МЯСО', [f'minecraft:{m}' for m in RAW_MEAT]),
}


def has_mending(tag):
    for key in ('Enchantments', 'StoredEnchantments'):
        for e in tag.get(key, []) or []:
            if isinstance(e, dict) and 'mending' in str(e.get('id', '')):
                return True
    return False


def normalize(item, strange):
    """Returns (token, expansion_set). Wildcard if Mending-marked, else concrete id."""
    iid, tag = item['id'], item['tag']
    if tag and has_mending(tag):
        if iid in WILDCARDS:
            token, expansion = WILDCARDS[iid]
            return token, frozenset(expansion)
        strange.append(f"{iid} с Mending — не знаю такого wildcard-класса")
        return iid, frozenset([iid])
    return iid, frozenset([iid])


def extract_combos(schem):
    combos, strange = [], []
    n_chest = 0
    for pos, cid, items in chests_with_items(schem):
        n_chest += 1
        by_slot = {it['slot']: it for it in items}
        for row in range(3):
            b = row * 9
            for side, (s1, s2, sr) in [('лево', (b, b + 1, b + 3)),
                                       ('право', (b + 5, b + 6, b + 8))]:
                i1, i2, res = by_slot.get(s1), by_slot.get(s2), by_slot.get(sr)
                if not (i1 and i2 and res):
                    continue
                t1, e1 = normalize(i1, strange)
                t2, e2 = normalize(i2, strange)
                combos.append({
                    'chest': pos, 'row': row, 'side': side,
                    'in1': t1, 'in2': t2, 'exp1': e1, 'exp2': e2,
                    'result': res['id'],
                    'result_count': res['count'],
                })
    return combos, strange, n_chest


def pair_key(c):
    return tuple(sorted((c['in1'], c['in2'])))


def concrete_pairs(c):
    return {frozenset((a, b)) if a != b else frozenset((a,)) for a in c['exp1'] for b in c['exp2']}


def where(c):
    x, y, z = c['chest']
    return f"сундук(x={x},y={y},z={z}) ряд {c['row'] + 1} {c['side']}"


def fmt(c):
    return f"{c['in1']} + {c['in2']} → {c['result']}  [{where(c)}]"


def main(schem_path, out_dir):
    schem = load_schematic(schem_path)
    combos, strange, n_chest = extract_combos(schem)

    # 1) exact duplicate pairs (same normalized tokens)
    by_pair = defaultdict(list)
    for c in combos:
        by_pair[pair_key(c)].append(c)
    exact_dupes = {k: v for k, v in by_pair.items() if len(v) > 1}

    # 2) wildcard overlaps: different normalized pairs sharing a concrete pair
    pair_reps = list(by_pair.items())
    overlaps = []
    conc = [(k, set().union(*[concrete_pairs(c) for c in v])) for k, v in pair_reps]
    for i in range(len(conc)):
        for j in range(i + 1, len(conc)):
            shared = conc[i][1] & conc[j][1]
            if shared:
                overlaps.append((pair_reps[i][1][0], pair_reps[j][1][0], shared))

    # 3) same-pair-same-result pure duplicates vs different-result conflicts
    hard, soft = [], []
    for k, v in exact_dupes.items():
        results = {c['result'] for c in v}
        (hard if len(results) > 1 else soft).append(v)

    os.makedirs(out_dir, exist_ok=True)

    # machine-readable dump for the future recipe generator
    with open(os.path.join(out_dir, 'combos.json'), 'w', encoding='utf-8') as f:
        json.dump([{k: (list(v) if isinstance(v, frozenset) else v) for k, v in c.items()}
                   for c in combos], f, ensure_ascii=False, indent=1)

    rep = []
    rep.append('# Отчёт сканера конфликтов — 1800 объединений')
    rep.append('')
    rep.append(f'Прочитано: {n_chest} половинок сундуков, **{len(combos)} комбинаций**, '
               f'{len(by_pair)} уникальных пар.')
    rep.append('Ничего не исправлял — только отчёт, решения за Т.')
    rep.append('')
    rep.append(f'## 1. Конфликты: одна пара → РАЗНЫЕ результаты ({len(hard)} шт)')
    rep.append('')
    rep.append('Самое важное: в игре сработает только один рецепт из группы, остальные недостижимы.')
    rep.append('')
    for group in sorted(hard, key=lambda g: -len(g)):
        rep.append(f"### {group[0]['in1']} + {group[0]['in2']}")
        for c in group:
            rep.append(f"- → **{c['result']}**  [{where(c)}]")
        rep.append('')
    rep.append(f'## 2. Дубли: одна пара → ОДИН И ТОТ ЖЕ результат ({len(soft)} шт)')
    rep.append('')
    rep.append('Не ломают игру (рецепт один и тот же), но место в сундуках занято дважды.')
    rep.append('')
    for group in sorted(soft, key=lambda g: -len(g)):
        c0 = group[0]
        places = '; '.join(where(c) for c in group)
        rep.append(f"- {c0['in1']} + {c0['in2']} → {c0['result']}  ×{len(group)}  [{places}]")
    rep.append('')
    rep.append(f'## 3. Пересечения wildcard-пар с другими парами ({len(overlaps)} шт)')
    rep.append('')
    rep.append('Пара с «любой X» покрывает конкретную пару из другого объединения — '
               'при крафте конкретными предметами столкнутся два рецепта.')
    rep.append('')
    for a, b, shared in overlaps:
        ex = ' | '.join(' + '.join(sorted(s)) for s in list(shared)[:3])
        rep.append(f"- {fmt(a)}")
        rep.append(f"  пересекается с: {fmt(b)}")
        rep.append(f"  общие варианты ({len(shared)}): {ex}")
        rep.append('')
    rep.append(f'## 4. Странные предметы ({len(set(strange))} шт)')
    rep.append('')
    for s in sorted(set(strange)):
        rep.append(f'- {s}')
    rep.append('')
    rep.append('## Допущения сканера (Т, проверь)')
    rep.append('')
    rep.append('- «Любая броня» = кожа/золото/железо. **Кольчуга НЕ включена** — включить?')
    rep.append('- «Любой меч/инструмент» = дерево/камень/золото/железо (алмаз и незерит исключены, как ты сказал)')
    rep.append('- «Любой цветок» = все ванильные, включая визер-розу и двухблочные (подсолнух и т.п.) — так?')
    rep.append('- «Любое сырое мясо» = говядина/свинина/курица/баранина/кролик. **Рыба НЕ включена** — включить?')
    rep.append('- Пара считается БЕЗ порядка: A+B и B+A — одно и то же (в столе слоты равноправны)')

    report_path = os.path.join(out_dir, 'conflict-report.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(rep))

    print(f'combos={len(combos)} pairs={len(by_pair)} hard={len(hard)} soft={len(soft)} '
          f'overlaps={len(overlaps)} strange={len(set(strange))}')
    print('report:', report_path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
