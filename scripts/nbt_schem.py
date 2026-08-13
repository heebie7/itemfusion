"""Minimal NBT parser + Sponge .schem chest extractor (stdlib only).

Used by scan_conflicts.py / recipe generator. Big-endian NBT per spec.
"""
import gzip
import struct


class TypedDict(dict):
    """Compound tag that remembers each key's NBT tag id (needed to write SNBT)."""
    __slots__ = ('types',)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.types = {}


class TypedList(list):
    """List tag that remembers its element tag id."""
    __slots__ = ('item_type',)

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.item_type = 0


def _read_string(buf, pos):
    (n,) = struct.unpack_from('>H', buf, pos)
    pos += 2
    return buf[pos:pos + n].decode('utf-8', 'replace'), pos + n


def _read_payload(buf, pos, tag):
    if tag == 1:
        return buf[pos], pos + 1
    if tag == 2:
        return struct.unpack_from('>h', buf, pos)[0], pos + 2
    if tag == 3:
        return struct.unpack_from('>i', buf, pos)[0], pos + 4
    if tag == 4:
        return struct.unpack_from('>q', buf, pos)[0], pos + 8
    if tag == 5:
        return struct.unpack_from('>f', buf, pos)[0], pos + 4
    if tag == 6:
        return struct.unpack_from('>d', buf, pos)[0], pos + 8
    if tag == 7:
        (n,) = struct.unpack_from('>i', buf, pos)
        pos += 4
        return bytes(buf[pos:pos + n]), pos + n
    if tag == 8:
        return _read_string(buf, pos)
    if tag == 9:
        item_tag = buf[pos]
        (n,) = struct.unpack_from('>i', buf, pos + 1)
        pos += 5
        out = TypedList()
        out.item_type = item_tag
        for _ in range(n):
            val, pos = _read_payload(buf, pos, item_tag)
            out.append(val)
        return out, pos
    if tag == 10:
        out = TypedDict()
        while True:
            t = buf[pos]
            pos += 1
            if t == 0:
                return out, pos
            name, pos = _read_string(buf, pos)
            val, pos = _read_payload(buf, pos, t)
            out[name] = val
            out.types[name] = t
    if tag == 11:
        (n,) = struct.unpack_from('>i', buf, pos)
        pos += 4
        vals = list(struct.unpack_from(f'>{n}i', buf, pos))
        return vals, pos + 4 * n
    if tag == 12:
        (n,) = struct.unpack_from('>i', buf, pos)
        pos += 4
        vals = list(struct.unpack_from(f'>{n}q', buf, pos))
        return vals, pos + 8 * n
    raise ValueError(f'unknown tag {tag} at {pos}')


_SNBT_SUFFIX = {1: 'b', 2: 's', 3: '', 4: 'L', 5: 'f', 6: 'd'}


def _snbt_string(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def to_snbt(value, tag_type=None):
    """Serialize a parsed NBT value back to SNBT (the string form Minecraft reads).

    tag_type comes from TypedDict.types / TypedList.item_type — without it,
    numbers lose their byte/short/long/float distinction and the game rejects
    or misreads the tag.
    """
    if isinstance(value, TypedDict) or isinstance(value, dict):
        types = getattr(value, 'types', {})
        inner = ','.join(f'{k}:{to_snbt(v, types.get(k))}' for k, v in value.items())
        return '{' + inner + '}'
    if isinstance(value, TypedList) or isinstance(value, list):
        item_type = getattr(value, 'item_type', None)
        return '[' + ','.join(to_snbt(v, item_type) for v in value) + ']'
    if isinstance(value, bytes):
        return '[B;' + ','.join(f'{b}b' for b in value) + ']'
    if isinstance(value, str):
        return _snbt_string(value)
    if isinstance(value, float):
        return f'{value}{_SNBT_SUFFIX.get(tag_type, "d")}'
    if isinstance(value, int):
        return f'{value}{_SNBT_SUFFIX.get(tag_type, "")}'
    return _snbt_string(value)


def load_nbt(path):
    data = open(path, 'rb').read()
    if data[:2] == b'\x1f\x8b':
        data = gzip.decompress(data)
    tag = data[0]
    name, pos = _read_string(data, 1)
    payload, _ = _read_payload(data, pos, tag)
    return name, payload


def load_schematic(path):
    """Returns the Schematic compound (handles sponge v2 root and v3 nesting)."""
    name, root = load_nbt(path)
    if name == 'Schematic' or 'BlockEntities' in root or 'Palette' in root:
        return root
    if 'Schematic' in root:
        return root['Schematic']
    return root


def chests_with_items(schem):
    """Yield (pos_tuple, id, items) for container block entities that have items.

    Items normalized to list of dicts: {slot, id, count, tag}.
    Handles sponge v2 (flat keys, lowercase 'id' inside Items) formats.
    """
    for be in schem.get('BlockEntities', []):
        be_id = be.get('Id') or be.get('id') or ''
        items_raw = be.get('Items')
        if items_raw is None and 'Data' in be and isinstance(be['Data'], dict):
            items_raw = be['Data'].get('Items')  # sponge v3
        if not items_raw:
            continue
        pos = tuple(be.get('Pos', (0, 0, 0)))
        items = []
        for it in items_raw:
            items.append({
                'slot': it.get('Slot', 0),
                'id': it.get('id') or it.get('Id') or '?',
                'count': it.get('Count', 1),
                'tag': it.get('tag') or {},
            })
        yield pos, be_id, items
