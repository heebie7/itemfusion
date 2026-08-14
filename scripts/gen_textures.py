"""Generate itemfusion textures (stdlib only, no PIL).

Run from repo root: python3 scripts/gen_textures.py
Regenerates block/item textures and the GUI background deterministically.
"""
import struct, zlib, os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
TEX = os.path.join(ROOT, 'src/main/resources/assets/itemfusion/textures')


def write_png(path, pixels):
    w, h = len(pixels[0]), len(pixels)
    raw = b''.join(b'\x00' + b''.join(struct.pack('4B', *px) for px in row) for row in pixels)
    def chunk(typ, data):
        return struct.pack('>I', len(data)) + typ + data + struct.pack('>I', zlib.crc32(typ + data) & 0xffffffff)
    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))


def block_texture():
    """DISABLED 2026-08-12: the block texture is T's own artwork
    (assets/itemfusion/textures/block/fusion_table.png). Do NOT regenerate —
    running this would overwrite it. Kept for reference only."""
    raise SystemExit('block_texture() disabled: block texture is T-authored, do not overwrite')


def _block_texture_old():
    base   = (123, 79, 168, 255)
    border = (86, 50, 122, 255)
    light  = (168, 120, 214, 255)
    px = [[base for _ in range(16)] for _ in range(16)]
    for i in range(16):
        px[0][i] = px[15][i] = px[i][0] = px[i][15] = border
    for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1), (-1, 0), (0, -1), (-1, 1), (1, -1), (-1, -1)]:
        px[7 + dy][7 + dx] = light
    px[6][7] = px[9][7] = px[7][5] = px[7][10] = light
    os.makedirs(f'{TEX}/block', exist_ok=True)
    write_png(f'{TEX}/block/fusion_table.png', px)


def core_texture():
    core = (64, 200, 190, 255)
    rim  = (30, 130, 125, 255)
    glow = (150, 240, 232, 255)
    px = [[(0, 0, 0, 0) for _ in range(16)] for _ in range(16)]
    cx = cy = 7.5
    for y in range(16):
        for x in range(16):
            d2 = (x - cx) ** 2 + (y - cy) ** 2
            if d2 <= 25:
                px[y][x] = core
            elif d2 <= 36:
                px[y][x] = rim
    for y, x in [(5, 5), (5, 6), (6, 5)]:
        px[y][x] = glow
    os.makedirs(f'{TEX}/item', exist_ok=True)
    write_png(f'{TEX}/item/fusion_core.png', px)


def gui_texture():
    """256x256 sheet, panel 176x166 at (0,0). Old-smithing layout:
    two input slots + plus + arrow + result slot. Slot item areas must match
    FusionTableMenu coordinates: (27,47), (76,47), result (134,47),
    player inv (8,84), hotbar (8,142)."""
    W = H = 256
    PW, PH = 176, 166
    bg   = (198, 198, 198, 255)
    hi   = (255, 255, 255, 255)
    lo   = (85, 85, 85, 255)
    blk  = (0, 0, 0, 255)
    slot_dark = (55, 55, 55, 255)
    slot_fill = (139, 139, 139, 255)
    deco = (85, 85, 85, 255)

    px = [[(0, 0, 0, 0) for _ in range(W)] for _ in range(H)]
    for y in range(PH):
        for x in range(PW):
            px[y][x] = bg
    # panel border: black perimeter, white top/left inner, dark bottom/right inner
    for x in range(PW):
        px[0][x] = px[PH - 1][x] = blk
    for y in range(PH):
        px[y][0] = px[y][PW - 1] = blk
    for x in range(1, PW - 1):
        px[1][x] = px[2][x] = hi
        px[PH - 2][x] = px[PH - 3][x] = lo
    for y in range(1, PH - 1):
        px[y][1] = px[y][2] = hi
        px[y][PW - 2] = px[y][PW - 3] = lo
    # fix corner overlap: bottom-left and top-right blend
    px[PH - 2][1] = px[PH - 2][2] = lo
    px[1][PW - 2] = px[2][PW - 2] = hi

    def slot(sx, sy):
        # sx,sy = item area top-left (16x16); frame is 18x18 around it
        for x in range(sx - 1, sx + 17):
            px[sy - 1][x] = slot_dark
            px[sy + 16][x] = hi
        for y in range(sy - 1, sy + 17):
            px[y][sx - 1] = slot_dark
            px[y][sx + 16] = hi
        px[sy + 16][sx - 1] = slot_dark  # bottom-left corner
        px[sy - 1][sx + 16] = hi         # top-right corner
        for y in range(sy, sy + 16):
            for x in range(sx, sx + 16):
                px[y][x] = slot_fill

    # fusion slots
    slot(27, 47)
    slot(76, 47)
    slot(134, 47)
    # player inventory + hotbar
    for row in range(3):
        for col in range(9):
            slot(8 + col * 18, 84 + row * 18)
    for col in range(9):
        slot(8 + col * 18, 142)

    # plus between inputs (centered around x=59, y=55)
    for x in range(54, 65):
        for y in range(54, 57):
            px[y][x] = deco
    for x in range(58, 61):
        for y in range(50, 61):
            px[y][x] = deco

    # arrow from input2 to result (body + head, centered on y=55)
    for x in range(98, 119):
        for y in range(54, 57):
            px[y][x] = deco
    for i in range(6):
        for dy in range(-(5 - i), (5 - i) + 1):
            px[55 + dy][119 + i] = deco

    os.makedirs(f'{TEX}/gui', exist_ok=True)
    write_png(f'{TEX}/gui/fusion_table.png', px)


def recipe_book_texture():
    """256x256 sheet, panel 216x196. 9x6 grid of item cells starting at (18,40),
    step 20; slot frames at cell+2 — must match FusionRecipeBookScreen constants
    (T ruling 08-15: wider panel, items centered, room for search + page label)."""
    W = H = 256
    PW, PH = 216, 196
    bg = (198, 198, 198, 255)
    hi = (255, 255, 255, 255)
    lo = (85, 85, 85, 255)
    blk = (0, 0, 0, 255)
    slot_dark = (55, 55, 55, 255)
    slot_fill = (139, 139, 139, 255)

    px = [[(0, 0, 0, 0) for _ in range(W)] for _ in range(H)]
    for y in range(PH):
        for x in range(PW):
            px[y][x] = bg
    for x in range(PW):
        px[0][x] = px[PH - 1][x] = blk
    for y in range(PH):
        px[y][0] = px[y][PW - 1] = blk
    for x in range(1, PW - 1):
        px[1][x] = px[2][x] = hi
        px[PH - 2][x] = px[PH - 3][x] = lo
    for y in range(1, PH - 1):
        px[y][1] = px[y][2] = hi
        px[y][PW - 2] = px[y][PW - 3] = lo
    px[PH - 2][1] = px[PH - 2][2] = lo
    px[1][PW - 2] = px[2][PW - 2] = hi

    def slot(sx, sy):
        for x in range(sx - 1, sx + 17):
            px[sy - 1][x] = slot_dark
            px[sy + 16][x] = hi
        for y in range(sy - 1, sy + 17):
            px[y][sx - 1] = slot_dark
            px[y][sx + 16] = hi
        px[sy + 16][sx - 1] = slot_dark
        px[sy - 1][sx + 16] = hi
        for y in range(sy, sy + 16):
            for x in range(sx, sx + 16):
                px[y][x] = slot_fill

    for row in range(6):
        for col in range(9):
            slot(18 + col * 20 + 2, 40 + row * 20 + 2)

    os.makedirs(f'{TEX}/gui', exist_ok=True)
    write_png(f'{TEX}/gui/recipe_book.png', px)


if __name__ == '__main__':
    gui_texture()
    recipe_book_texture()
    print('textures regenerated')
