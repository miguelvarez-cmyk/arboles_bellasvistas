"""
Procesa las bandas de aparcamiento SER desde el shapefile OFICIAL del
Ayuntamiento de Madrid (data/raw/Bandas de Aparcamiento.shp).

- Filtra a Bellas Vistas con el polígono oficial de barrios.
- Recupera el nombre de calle por proximidad a las vías OSM con nombre.
- Reproyecta EPSG:25830 → WGS84 y exporta LineStrings reales.

Genera: data/geojson/ser_bellavistas.geojson  (geometría LineString real)

Requiere geopandas (sólo en este pipeline offline; el mapa no usa dependencias).
"""

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString

ROOT    = Path(__file__).parent.parent
RAW     = ROOT / 'data' / 'raw'
GEOJSON = ROOT / 'data' / 'geojson'

SHP_BANDAS  = RAW / 'Bandas de Aparcamiento.shp'
SHP_BARRIOS = RAW / 'Límite de Barrios de la Zona S_E_R_.shp'
BARRIO      = 'Bellas Vistas'
MAX_CALLE_M = 30          # radio máximo para asignar nombre de calle OSM

COLORS = {'verde': '#27AE60', 'azul': '#2980B9',
          'amarillo': '#F39C12', 'rojo': '#E74C3C'}


def norm_color(c):
    c = (c or '').strip().lower()
    if 'verde' in c:    return 'verde'
    if 'azul' in c:     return 'azul'
    if 'amarill' in c:  return 'amarillo'
    if 'rojo' in c:     return 'rojo'
    return 'azul'


def norm_tipo(t):
    return 'Batería' if 'bat' in (t or '').lower() else 'Línea'


# ─── 1. Cargar bandas oficiales y filtrar a Bellas Vistas ────────────────────
bandas = gpd.read_file(SHP_BANDAS, encoding='utf-8')
print(f"Bandas SER totales (Madrid): {len(bandas)}")

barrios = gpd.read_file(SHP_BARRIOS, encoding='utf-8')
bv = barrios[barrios['NOMBAR'] == BARRIO]
if bv.empty:
    raise SystemExit(f"No se encontró el barrio {BARRIO!r} en {SHP_BARRIOS.name}")

bandas = bandas.to_crs(bv.crs)
bandas_bv = gpd.sjoin(bandas, bv[['geometry']], predicate='intersects',
                      how='inner').drop(columns='index_right')
print(f"Bandas en {BARRIO}: {len(bandas_bv)}")

# ─── 2. Recuperar nombre de calle desde vías OSM con nombre ──────────────────
with open(GEOJSON / 'osm_streets.json', encoding='utf-8') as f:
    osm = json.load(f)
nodes = {e['id']: (e['lon'], e['lat'])
         for e in osm['elements'] if e['type'] == 'node'}
recs = []
for e in osm['elements']:
    if e['type'] == 'way' and e.get('tags', {}).get('name'):
        pts = [nodes[n] for n in e['nodes'] if n in nodes]
        if len(pts) >= 2:
            recs.append({'calle': e['tags']['name'], 'geometry': LineString(pts)})
streets = gpd.GeoDataFrame(recs, crs='EPSG:4326').to_crs(bandas_bv.crs)

bandas_bv = gpd.sjoin_nearest(bandas_bv, streets[['calle', 'geometry']],
                              max_distance=MAX_CALLE_M, how='left')
# sjoin_nearest puede duplicar si hay empates: quedarse con la primera por banda
bandas_bv = bandas_bv[~bandas_bv.index.duplicated(keep='first')]
sin_calle = int(bandas_bv['calle'].isna().sum())
print(f"Bandas con nombre de calle: {len(bandas_bv) - sin_calle}/{len(bandas_bv)}")

# ─── 3. Construir GeoJSON LineString en WGS84 ────────────────────────────────
bandas_wgs = bandas_bv.to_crs('EPSG:4326')

features = []
plazas_tot = 0
for (_, row), (_, row_m) in zip(bandas_wgs.iterrows(), bandas_bv.iterrows()):
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue
    plazas = int(row['Res_NumPla'] or 0)
    color  = norm_color(row['Color'])
    tipo   = norm_tipo(row['Bateria_Li'])
    calle  = row['calle'] if isinstance(row['calle'], str) else 'Calle SER'
    long_m = round(row_m.geometry.length, 1)  # longitud real en metros (EPSG:25830)
    plazas_tot += plazas

    coords = [[round(x, 7), round(y, 7)] for x, y in geom.coords]
    features.append({
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {
            "plazas": plazas,
            "tipo": tipo,
            "color": color,
            "longitud_m": long_m,
            "calle": calle,
            "fill": COLORS.get(color, '#95A5A6'),
        }
    })

out = {"type": "FeatureCollection", "features": features}
GEOJSON.mkdir(parents=True, exist_ok=True)
with open(GEOJSON / 'ser_bellavistas.geojson', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)

print()
print("=" * 52)
print("BANDAS SER OFICIALES — BELLAS VISTAS")
print("=" * 52)
print(f"Bandas escritas   : {len(features)}")
print(f"Plazas totales    : {plazas_tot}")
print(f"Longitud total (m): {round(sum(f['properties']['longitud_m'] for f in features), 1)}")
print(f"Fichero           : data/geojson/ser_bellavistas.geojson")
print("=" * 52)
