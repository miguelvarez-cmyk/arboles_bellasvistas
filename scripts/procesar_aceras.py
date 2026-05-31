"""
Procesa el contorno de las aceras desde la cartografía OFICIAL del Ayuntamiento
de Madrid (data/raw/Aceras - Anchos medios (metros).shp).

- Filtra a Bellas Vistas con el polígono oficial de barrios.
- Simplifica ligeramente (tolerancia en metros) para aligerar el render.
- Reproyecta EPSG:25830 → WGS84 y exporta los polígonos de acera.

Genera: data/geojson/aceras.geojson  (Polygon, con ancho medio en metros)

Requiere geopandas (pipeline offline; el mapa no usa dependencias).
"""

import json
from pathlib import Path

import geopandas as gpd
from shapely.geometry import mapping


def round_geom(geom):
    """mapping(geom) con coordenadas redondeadas a 7 decimales."""
    def rnd(c):
        if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
            return [round(c[0], 7), round(c[1], 7)]
        return [rnd(x) for x in c]
    m = mapping(geom)
    return {"type": m["type"], "coordinates": rnd(m["coordinates"])}

ROOT    = Path(__file__).parent.parent
RAW     = ROOT / 'data' / 'raw'
GEOJSON = ROOT / 'data' / 'geojson'

SHP_ACERAS  = RAW / 'Aceras - Anchos medios (metros).shp'
SHP_BARRIOS = RAW / 'Límite de Barrios de la Zona S_E_R_.shp'
BARRIO      = 'Bellas Vistas'
SIMPLIFY_M  = 0.5        # tolerancia de simplificación (metros)

# ─── Cargar aceras y filtrar a Bellas Vistas ─────────────────────────────────
aceras = gpd.read_file(SHP_ACERAS, encoding='utf-8')
print(f"Aceras totales (zona SER): {len(aceras)}")

barrios = gpd.read_file(SHP_BARRIOS, encoding='utf-8')
bv = barrios[barrios['NOMBAR'] == BARRIO].to_crs(aceras.crs)
if bv.empty:
    raise SystemExit(f"No se encontró el barrio {BARRIO!r} en {SHP_BARRIOS.name}")

aceras_bv = gpd.sjoin(aceras, bv[['geometry']], predicate='intersects',
                      how='inner').drop(columns='index_right')
print(f"Aceras en {BARRIO}: {len(aceras_bv)}")

# ─── Simplificar (en metros) y reproyectar a WGS84 ───────────────────────────
aceras_bv['geometry'] = aceras_bv.geometry.simplify(SIMPLIFY_M, preserve_topology=True)
aceras_wgs = aceras_bv.to_crs('EPSG:4326')

# ─── Construir GeoJSON ───────────────────────────────────────────────────────
features = []
for _, row in aceras_wgs.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue
    ancho = round(float(row['ANCHO_MEDI'] or 0), 1)
    features.append({
        "type": "Feature",
        "geometry": round_geom(geom),
        "properties": {"ancho_m": ancho}
    })

out = {"type": "FeatureCollection", "features": features}
GEOJSON.mkdir(parents=True, exist_ok=True)
with open(GEOJSON / 'aceras.geojson', 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False)

anchos = [f['properties']['ancho_m'] for f in features]
print()
print("=" * 52)
print("ACERAS OFICIALES — BELLAS VISTAS")
print("=" * 52)
print(f"Polígonos escritos : {len(features)}")
if anchos:
    print(f"Ancho medio (m)    : min {min(anchos):.1f} / med {sorted(anchos)[len(anchos)//2]:.1f} / max {max(anchos):.1f}")
print(f"Fichero            : data/geojson/aceras.geojson")
print("=" * 52)
