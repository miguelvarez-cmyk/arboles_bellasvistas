"""
Convierte los ficheros de datos JSON/GeoJSON a variables JS globales.
Así mapa.html funciona tanto desde file:// como desde http://,
sin ninguna llamada fetch() ni dependencia de red.
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
GEOJSON = ROOT / 'data' / 'geojson'
JS = ROOT / 'data' / 'js'
JS.mkdir(parents=True, exist_ok=True)

FILES = [
    ('osm_boundary.json',      'OSM_BOUNDARY'),
    ('osm_streets.json',       'OSM_STREETS'),
    ('arboles_existentes.geojson', 'OSM_TREES'),  # recortados al barrio (para el mapa)
    ('ser_bellavistas.geojson','SER_BANDS'),
    ('arboles_propuestos.geojson', 'PROPUESTOS'),
    ('aceras.geojson',         'ACERAS'),
]

for filename, varname in FILES:
    src = GEOJSON / filename
    if not src.exists():
        print(f"  FALTA: {src}")
        continue
    with open(src, encoding='utf-8') as f:
        data = json.load(f)
    out = JS / (src.stem + '.js')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(f'window.{varname}=')
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        f.write(';')
    kb = out.stat().st_size // 1024
    n  = len(data.get('elements', data.get('features', [])))
    print(f"  {out.name:30s}  window.{varname:20s}  {n:5d} elementos  {kb} KB")

print("\nListo. Incluir en mapa.html con <script src='data/js/xxx.js'>")
