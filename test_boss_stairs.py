import pytmx
tmx_data = pytmx.TiledMap('assets/maps/map_glace.tmx')
layer = tmx_data.get_layer_by_name('Collisions')
tiles = [(x*32, y*32) for x, y, surf in layer.tiles()]

boss_tiles = [(x, y) for x, y in tiles if 3000 <= x <= 3600 and 2400 <= y <= 2800]

from collections import defaultdict
cols = defaultdict(list)
for x, y in boss_tiles:
    cols[x].append(y)

for x in sorted(cols.keys()):
    ys = sorted(cols[x])
    print(f"X={x}: Ys={ys}")

