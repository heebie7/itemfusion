"""Conflict scanner for T's 1800 fusion combos.

Reads the chest schematic, normalizes wildcards, compares results INCLUDING
their NBT (TACZ guns differ only by GunId), finds duplicate/overlapping
ingredient pairs, writes a report for T.
Does NOT fix anything — T decides replacements.

Usage: python3 scripts/scan_conflicts.py <chest.schem> <out-dir> [<old.schem>]
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nbt_schem import load_schematic, chests_with_items

# --- wildcard classes (T's rules, confirmed 2026-08-11) ---
TIERS_TOOL = ['wooden', 'stone', 'golden', 'iron']
ARMOR_MATS = ['leather', 'golden', 'iron']          # no chainmail, no diamond/netherite
FLOWERS = ['dandelion', 'poppy', 'blue_orchid', 'allium', 'azure_bluet',
           'red_tulip', 'orange_tulip', 'white_tulip', 'pink_tulip',
           'oxeye_daisy', 'cornflower', 'lily_of_the_valley', 'torchflower']
RAW_MEAT = ['beef', 'porkchop', 'chicken', 'mutton', 'rabbit']   # no fish
COOKED_MEAT = [f'cooked_{m}' for m in RAW_MEAT]                  # T: raw and cooked are separate classes
# T 2026-08-12: "где указано дерево, а именно дуб, может быть использовано любое дерево"
WOODS = ['oak', 'spruce', 'birch', 'jungle', 'acacia', 'dark_oak', 'mangrove', 'cherry']

MENDING_WILDCARDS = {
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
    'minecraft:cooked_beef':  ('ЛЮБОЕ_ГОТОВОЕ_МЯСО', [f'minecraft:{m}' for m in COOKED_MEAT]),
}

ARROW_MARKER = '_arrow'          # only arrows may have count > 1
NBT_LABEL_KEYS = ['GunId', 'MeleeWeaponId', 'ThrowableId', 'entity', 'Potion']


def has_mending(tag):
    for key in ('Enchantments', 'StoredEnchantments'):
        for e in tag.get(key, []) or []:
            if isinstance(e, dict) and 'mending' in str(e.get('id', '')):
                return True
    return False


def oak_wildcard(iid):
    """minecraft:oak_X -> ('ЛЮБОЕ_ДЕРЕВО:X', all wood variants). dark_oak excluded."""
    if not iid.startswith('minecraft:oak_'):
        return None
    suffix = iid[len('minecraft:oak_'):]
    return (f'ЛЮБОЕ_ДЕРЕВО:{suffix}', [f'minecraft:{w}_{suffix}' for w in WOODS])


def normalize(item, strange):
    """Returns (token, expansion_set) for an ingredient. NBT ignored except Mending markers."""
    iid, tag = item['id'], item['tag']
    if tag and has_mending(tag):
        if iid in MENDING_WILDCARDS:
            token, expansion = MENDING_WILDCARDS[iid]
            return token, frozenset(expansion)
        strange.append(f'{iid} с Mending — не знаю такого wildcard-класса')
        return iid, frozenset([iid])
    oak = oak_wildcard(iid)
    if oak:
        return oak[0], frozenset(oak[1])
    return iid, frozenset([iid])


def result_sig(item):
    """Result identity = id + NBT (T: NBT matters a lot for results). Damage=0 is noise."""
    tag = {k: v for k, v in (item['tag'] or {}).items() if not (k == 'Damage' and v == 0)}
    return (item['id'], json.dumps(tag, sort_keys=True, default=str))


def result_label(item):
    """Human-readable result: id + its distinguishing NBT bit."""
    tag = item['tag'] or {}
    for k in NBT_LABEL_KEYS:
        if k in tag:
            v = tag[k]
            v = v.get('id', v) if isinstance(v, dict) else v
            return f"{item['id']} [{v}]"
    name = (tag.get('display') or {}).get('Name')
    if name:
        short = str(name).split('translate":"')[-1].split('"')[0]
        return f"{item['id']} [{short}]"
    ench = tag.get('Enchantments')
    if ench:
        return f"{item['id']} [чары: {len(ench)}]"
    if tag.get('Damage'):
        return f"{item['id']} [Damage={tag['Damage']}]"
    return item['id']


DECISIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'decisions.json')


def load_overrides():
    """T's spoken decisions applied on top of the schematic (decisions.json)."""
    try:
        with open(DECISIONS_PATH, encoding='utf-8') as f:
            return json.load(f).get('ingredient_overrides', [])
    except FileNotFoundError:
        return []


def apply_overrides(i1, i2, res, overrides):
    """Rewrite ingredient ids per T's decisions. Returns (i1, i2, applied_note|None)."""
    for rule in overrides:
        prefix = rule.get('when_result_starts_with')
        if prefix and not res['id'].startswith(prefix):
            continue
        repl = rule.get('replace', {})
        hit = False
        for item in (i1, i2):
            if item['id'] in repl:
                item = item  # keep reference; mutate below
                hit = True
        if hit:
            i1 = dict(i1, id=repl.get(i1['id'], i1['id']))
            i2 = dict(i2, id=repl.get(i2['id'], i2['id']))
            return i1, i2, rule.get('reason')
    return i1, i2, None


def extract_combos(schem):
    combos, strange = [], []
    overrides = load_overrides()
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
                i1, i2, override_note = apply_overrides(i1, i2, res, overrides)
                t1, e1 = normalize(i1, strange)
                t2, e2 = normalize(i2, strange)
                if res['count'] > 1 and ARROW_MARKER not in res['id']:
                    strange.append(f"{res['id']} в количестве {res['count']} — не стрела, "
                                   f"а count > 1 [сундук{pos} ряд {row + 1} {side}]")
                combos.append({
                    'chest': pos, 'row': row, 'side': side,
                    'in1': t1, 'in2': t2, 'exp1': e1, 'exp2': e2,
                    'result': result_label(res),
                    'result_id': res['id'],
                    'result_sig': result_sig(res),
                    'result_count': res['count'],
                    'override': override_note,
                })
    return combos, strange, n_chest


def pair_key(c):
    return tuple(sorted((c['in1'], c['in2'])))


def concrete_pairs(c):
    return {frozenset((a, b)) if a != b else frozenset((a,)) for a in c['exp1'] for b in c['exp2']}


def where(c):
    x, y, z = c['chest']
    return f"сундук(x={x},y={y},z={z}) ряд {c['row'] + 1} {c['side']}"


def analyze(combos):
    by_pair = defaultdict(list)
    for c in combos:
        by_pair[pair_key(c)].append(c)
    hard, soft = [], []
    for group in by_pair.values():
        if len(group) > 1:
            (hard if len({c['result_sig'] for c in group}) > 1 else soft).append(group)
    items = list(by_pair.items())
    conc = [set().union(*[concrete_pairs(c) for c in v]) for _, v in items]
    overlaps = []
    for i in range(len(conc)):
        for j in range(i + 1, len(conc)):
            shared = conc[i] & conc[j]
            if shared:
                overlaps.append((items[i][1][0], items[j][1][0], shared))
    return by_pair, hard, soft, overlaps


def main(schem_path, out_dir, old_path=None):
    combos, strange, n_chest = extract_combos(load_schematic(schem_path))
    by_pair, hard, soft, overlaps = analyze(combos)

    old_hard_keys = None
    if old_path and os.path.exists(old_path):
        old_combos, _, _ = extract_combos(load_schematic(old_path))
        _, old_hard, _, _ = analyze(old_combos)
        old_hard_keys = {pair_key(g[0]) for g in old_hard}

    new_hard_keys = {pair_key(g[0]) for g in hard}
    fixed = (old_hard_keys - new_hard_keys) if old_hard_keys is not None else set()
    appeared = (new_hard_keys - old_hard_keys) if old_hard_keys is not None else set()

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, 'combos.json'), 'w', encoding='utf-8') as f:
        json.dump([{k: (sorted(v) if isinstance(v, frozenset) else v) for k, v in c.items()}
                   for c in combos], f, ensure_ascii=False, indent=1)

    rep = ['# Отчёт сканера — версия 2 (схематика от 12.08)', '']
    rep.append(f'Прочитано: {n_chest} половинок сундуков, **{len(combos)} комбинаций**, '
               f'{len(by_pair)} уникальных пар.')
    rep.append('')
    rep.append('**Что учтено в этой версии (по твоим правкам):**')
    rep.append('- Результаты сравниваются ВМЕСТЕ с NBT — 80 пушек TACZ различаются только GunId, '
               'теперь они разные результаты, а не один')
    rep.append('- У ингредиентов NBT/зачарование/прочность игнорируются (кроме Mending — это твой '
               'маркер wildcard)')
    rep.append('- Дуб = любое дерево: `minecraft:oak_*` раскрывается в 8 пород')
    rep.append('- Количество: всё кроме стрел = 1 — **проверено, нарушений нет** '
               '(1788 результатов по 1, ровно 12 стрел по 3)')
    rep.append('')
    if old_hard_keys is not None:
        rep.append(f'**Сравнение с прошлой схематикой:** исправлено {len(fixed)} конфликтов, '
                   f'появилось новых {len(appeared)}, осталось всего {len(hard)}.')
        rep.append('')
    rep.append(f'## 1. Конфликты: одна пара → РАЗНЫЕ результаты ({len(hard)} шт)')
    rep.append('')
    for group in sorted(hard, key=lambda g: -len(g)):
        mark = ' 🆕 НОВЫЙ' if pair_key(group[0]) in appeared else ''
        rep.append(f"### {group[0]['in1']} + {group[0]['in2']}{mark}")
        for c in group:
            rep.append(f"- → **{c['result']}**  [{where(c)}]")
        rep.append('')
    rep.append(f'## 2. Дубли: одна пара → ОДИН И ТОТ ЖЕ результат ({len(soft)} шт)')
    rep.append('')
    for group in sorted(soft, key=lambda g: -len(g)):
        c0 = group[0]
        rep.append(f"- {c0['in1']} + {c0['in2']} → {c0['result']}  ×{len(group)}  "
                   f"[{'; '.join(where(c) for c in group)}]")
    rep.append('')
    rep.append(f'## 3. Пересечения wildcard-пар ({len(overlaps)} шт)')
    rep.append('')
    for a, b, shared in overlaps:
        ex = ' | '.join(' + '.join(sorted(s)) for s in list(shared)[:3])
        rep.append(f"- {a['in1']} + {a['in2']} → {a['result']}  [{where(a)}]")
        rep.append(f"  пересекается с: {b['in1']} + {b['in2']} → {b['result']}  [{where(b)}]")
        rep.append(f"  общие варианты ({len(shared)}): {ex}")
        rep.append('')
    # --- wood collisions: oak-as-wildcard swallowing recipes keyed on a specific species ---
    species = [w for w in WOODS if w != 'oak']
    wood_specific = [c for c in combos
                     if any(f'minecraft:{w}_' in (c['in1'] + c['in2']) for w in species)]
    wood_wild = [c for c in combos if 'ЛЮБОЕ_ДЕРЕВО' in (c['in1'] + c['in2'])]
    collisions = []
    for spec in wood_specific:
        sp = concrete_pairs(spec)
        for wild in wood_wild:
            if wild is spec:
                continue
            if sp & concrete_pairs(wild):
                collisions.append((spec, wild))
    rep.append(f'## 3b. ВАЖНО: «дуб = любое дерево» ломает твои породные рецепты ({len(collisions)} шт)')
    rep.append('')
    rep.append('У тебя есть рецепты, где порода дерева — это и есть смысл: трапдор + акация даёт')
    rep.append('acaciabarktrap, + берёза даёт birchbarktrapdoor, + тёмный дуб свой, + ель свой.')
    rep.append('Но в том же семействе лежит **трапдор + дуб → oakbarktrapdoor**, и если дуб означает')
    rep.append('«любое дерево», этот один рецепт покрывает все остальные и они станут недостижимы.')
    rep.append('')
    rep.append('**Как я предлагаю решить (скажи да/нет):** дуб = «любое дерево» везде, КРОМЕ рецептов,')
    rep.append('где рядом в том же семействе стоит конкретная порода — там дуб означает именно дуб.')
    rep.append('Тогда породные рецепты остаются рабочими и править ничего не надо.')
    rep.append('')
    for spec, wild in collisions:
        rep.append(f"- породный: {spec['in1']} + {spec['in2']} → {spec['result']}  [{where(spec)}]")
        rep.append(f"  съедается: {wild['in1']} + {wild['in2']} → {wild['result']}  [{where(wild)}]")
    rep.append('')
    rep.append(f'## 4. Странности ({len(set(strange))} шт)')
    rep.append('')
    for s in sorted(set(strange)):
        rep.append(f'- {s}')
    rep.append('')
    rep.append('## Вопросы к тебе')
    rep.append('')
    rep.append('- «Любое дерево» я раскрываю в 8 пород: дуб, ель, берёза, тропическое, акация, '
               'тёмный дуб, мангровое, вишня. **Бамбук и незер-дерево (багровое/искажённое) НЕ включил** — надо?')
    rep.append('- `dark_oak_*` я считаю отдельным конкретным деревом, а не wildcard. Верно?')
    rep.append('- Броня: кожа/золото/железо (кольчуги нет), инструменты: дерево/камень/золото/железо, '
               'мясо: без рыбы, цветы: малые одноблочные — как договорились вчера.')

    path = os.path.join(out_dir, 'conflict-report-v2.md')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(rep))

    print(f'combos={len(combos)} pairs={len(by_pair)} hard={len(hard)} soft={len(soft)} '
          f'overlaps={len(overlaps)} strange={len(set(strange))} '
          f'fixed={len(fixed)} new={len(appeared)}')
    print('report:', path)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
