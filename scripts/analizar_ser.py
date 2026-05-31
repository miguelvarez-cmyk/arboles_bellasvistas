"""
Diagnóstico de las bandas SER de Bellas Vistas (data/geojson/ser_bellavistas.geojson).
Utilidad de inspección; NO genera ficheros que use el mapa.
"""
import json
from collections import Counter
from pathlib import Path

ROOT    = Path(__file__).parent.parent
GEOJSON = ROOT / 'data' / 'geojson'

with open(GEOJSON / 'ser_bellavistas.geojson', encoding='utf-8') as f:
    g = json.load(f)

feats  = g['features']
plazas = sum(f['properties']['plazas'] for f in feats)
long_m = sum(f['properties'].get('longitud_m', 0) for f in feats)
colores = Counter(f['properties']['color'] for f in feats)
tipos   = Counter(f['properties']['tipo'] for f in feats)

print(f"Bandas Bellas Vistas : {len(feats)}")
print(f"Plazas totales       : {plazas}")
print(f"Media plazas/banda   : {plazas/len(feats):.1f}")
print(f"Longitud total (m)   : {long_m:.0f}")
print(f"Metros por plaza      : {long_m/max(1,plazas):.2f}")
print(f"Colores SER          : {dict(colores)}")
print(f"Tipos (linea/bat)    : {dict(tipos)}")
print()
for f in feats[:5]:
    p = f['properties']
    nverts = len(f['geometry']['coordinates'])
    print(f"  {p['calle']}: {p['plazas']} plazas, {p['color']}, {p['tipo']}, "
          f"{p['longitud_m']}m, {nverts} vertices")

# Estimación de árboles (extremos + 1 interior cada 3 plazas)
TREE_EVERY = 3
def n_arboles(n):
    if n <= 0: return 0
    if n <= 2: return n
    return 2 + (n - 2) // TREE_EVERY
arboles = sum(n_arboles(f['properties']['plazas']) for f in feats)
print(f"\nArboles estimados  : {arboles}")
print(f"Plazas conservadas : {plazas - arboles} ({100*(plazas-arboles)/max(1,plazas):.1f}%)")
