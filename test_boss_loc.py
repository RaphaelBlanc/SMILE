import pytmx
tmx_data = pytmx.TiledMap('assets/maps/map_glace.tmx')
for obj in tmx_data.get_layer_by_name('Objets'):
    if hasattr(obj, 'name') and 'Boss' in str(obj.name):
        print(f"Name: {obj.name}, Type: {obj.type}, Pos: {obj.x}, {obj.y}")
    elif hasattr(obj, 'type') and 'Boss' in str(obj.type):
        print(f"Name: {obj.name}, Type: {obj.type}, Pos: {obj.x}, {obj.y}")
