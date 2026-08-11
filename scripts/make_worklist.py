"""Editable per-recipe worklist for T's conflict resolution.

Each conflicting recipe gets its own block with a stable id and an empty
ЗАМЕНА field. T edits the file and sends it back; ids survive editing.

Usage: python3 scripts/make_worklist.py <chest.schem> <out.txt>
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nbt_schem import load_schematic
from scan_conflicts import extract_combos, pair_key, concrete_pairs, where

HEADER = """КОНФЛИКТЫ ОБЪЕДИНЕНИЙ — РАБОЧИЙ ЛИСТ
=====================================

Как редактировать (можно прямо в телефоне):
1. В каждой группе реши, какой рецепт остаётся как есть —
   в его строке ЗАМЕНА напиши:  оставить
2. Остальным впиши новую пару предметов, например:
   ЗАМЕНА: minecraft:stick + minecraft:diamond
   (названия можно и по-русски — «палка + алмаз», я разберу)
3. Если рецепт вообще не нужен:  ЗАМЕНА: удалить
4. Номера [1.2] не трогай — по ним я пойму, о каком рецепте речь.
5. Готовый файл пришли обратно как есть.

ЛЮБОЙ_МЕЧ и прочие ЛЮБОЙ_* — твои wildcard-предметы (фреймы с мендингом).
"""


def main(schem_path, out_path):
    schem = load_schematic(schem_path)
    combos, _, _ = extract_combos(schem)

    by_pair = defaultdict(list)
    for c in combos:
        by_pair[pair_key(c)].append(c)

    hard = [v for v in by_pair.values() if len(v) > 1 and len({c['result'] for c in v}) > 1]
    soft = [v for v in by_pair.values() if len(v) > 1 and len({c['result'] for c in v}) == 1]

    pair_items = list(by_pair.items())
    conc = [(k, set().union(*[concrete_pairs(c) for c in v])) for k, v in pair_items]
    overlaps = []
    for i in range(len(conc)):
        for j in range(i + 1, len(conc)):
            if conc[i][1] & conc[j][1]:
                overlaps.append((pair_items[i][1][0], pair_items[j][1][0]))

    out = [HEADER]
    n = 0

    out.append('')
    out.append(f'ЧАСТЬ 1. ОДНА ПАРА -> РАЗНЫЕ РЕЗУЛЬТАТЫ ({len(hard)} групп)')
    out.append('Работает только один рецепт из группы, остальные мертвы.')
    out.append('=' * 53)
    for group in sorted(hard, key=lambda g: -len(g)):
        n += 1
        out.append('')
        out.append(f'--- группа {n}: {group[0]["in1"]} + {group[0]["in2"]} ---')
        for m, c in enumerate(group, 1):
            out.append(f'[{n}.{m}] {c["in1"]} + {c["in2"]} -> {c["result"]}')
            out.append(f'      где: {where(c)}')
            out.append('      ЗАМЕНА: ')
    out.append('')
    out.append(f'ЧАСТЬ 2. ПОЛНЫЕ ДУБЛИ — пара и результат совпадают ({len(soft)} шт)')
    out.append('Игру не ломают. «оставить» — оставлю один, второй уберу при генерации.')
    out.append('=' * 53)
    for group in soft:
        n += 1
        c = group[0]
        out.append('')
        out.append(f'[{n}.1] {c["in1"]} + {c["in2"]} -> {c["result"]}   (встречается ×{len(group)})')
        for cc in group:
            out.append(f'      где: {where(cc)}')
        out.append('      ЗАМЕНА: ')
    out.append('')
    out.append(f'ЧАСТЬ 3. ПЕРЕСЕЧЕНИЯ «ЛЮБОЙ_X» С КОНКРЕТНЫМИ ({len(overlaps)} пар)')
    out.append('Wildcard-рецепт покрывает и конкретную пару из другого рецепта.')
    out.append('Конкретный рецепт я сделаю ПРИОРИТЕТНЫМ (он победит wildcard) — если')
    out.append('это ок, пиши «оставить» обоим. Иначе — замену тому, что менять.')
    out.append('=' * 53)
    for a, b in overlaps:
        n += 1
        out.append('')
        out.append(f'[{n}.1] {a["in1"]} + {a["in2"]} -> {a["result"]}')
        out.append(f'      где: {where(a)}')
        out.append('      ЗАМЕНА: ')
        out.append(f'[{n}.2] {b["in1"]} + {b["in2"]} -> {b["result"]}')
        out.append(f'      где: {where(b)}')
        out.append('      ЗАМЕНА: ')

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    print(f'groups={n} file={out_path}')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
