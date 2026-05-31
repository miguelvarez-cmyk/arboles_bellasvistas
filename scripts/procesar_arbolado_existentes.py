"""
Recorta el INVENTARIO OFICIAL de arbolado de Madrid (dataset 300761, extraído
por scripts/descargar_arbolado_madrid.py) al barrio de Bellas Vistas y traduce
el código de especie (CODIGO_ESP) a nombre común y científico con el diccionario
oficial de especies (data/raw/arbolado_especies.xlsx).

Sustituye a la fuente OSM para los «árboles existentes» del mapa: ahora muestra
los árboles municipales reales con su especie (popup).

El shapefile (ETRS89 UTM 30N, EPSG:25830) trae el barrio en el campo NBRE_BARRI,
así que el recorte es un filtro por nombre (no hace falta join espacial).

Genera: data/geojson/arboles_existentes.geojson  (Point, sólo Bellas Vistas)
  · props.species : nombre científico (lo que el popup muestra en cursiva)
  · props.comun   : nombre común
  · props.altura  : altura total (m), si el inventario la trae

Requiere geopandas + openpyxl (pipeline offline; el mapa no usa dependencias).
"""

import json
import unicodedata
from pathlib import Path

import geopandas as gpd
import pandas as pd

from _contorno import poligono_contorno
from _copa import copa_redondeada

ROOT    = Path(__file__).parent.parent
RAW     = ROOT / 'data' / 'raw'
GEOJSON = ROOT / 'data' / 'geojson'

SHP_INV   = RAW / 'arbolado_madrid' / 'ARBOLADO_MADRID.shp'
XLSX_ESP  = RAW / 'arbolado_especies.xlsx'
BARRIO    = 'BELLAS VISTAS'          # valor exacto del campo NBRE_BARRI


def _norm(s):
    """minúsculas sin acentos, para casar nombres de columna del XLSX."""
    s = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in s if not unicodedata.combining(c)).strip().lower()


def cargar_especies():
    """CODIGO_ESP -> (nombre_comun, nombre_cientifico) desde el XLSX oficial."""
    df = pd.read_excel(XLSX_ESP, sheet_name=0)
    cols = {_norm(c): c for c in df.columns}
    c_cod = cols['codigo']
    c_com = cols['nombre comun']
    c_cie = cols['nombre cientifico']
    tabla = {}
    for _, r in df.iterrows():
        cod = str(r[c_cod]).strip()
        if cod and cod.lower() != 'nan':
            tabla[cod] = (str(r[c_com]).strip(), str(r[c_cie]).strip())
    return tabla


def _ws(s):
    """colapsa espacios (incl. espacios duros \\xa0) y recorta."""
    return ' '.join(str(s).replace('\xa0', ' ').split())


def limpio(v):
    if v is None:
        return None
    s = _ws(v)
    return s if s and s.lower() not in ('none', 'nan') else None


def limpia_comun(s):
    """El diccionario a veces guarda 'Nombre común/Sinónimo científico'; nos
    quedamos con el nombre común y normalizamos los espacios."""
    s = _ws(s).split('/')[0].strip()
    return s or None


# ─── 1. Diccionario de especies ──────────────────────────────────────────────
especies = cargar_especies()
print(f"Especies en el diccionario oficial: {len(especies)}")

# ─── 2. Inventario filtrado a Bellas Vistas ──────────────────────────────────
inv = gpd.read_file(SHP_INV, where=f"NBRE_BARRI = '{BARRIO}'")
print(f"Pies en {BARRIO}: {len(inv)}")
if inv.empty:
    raise SystemExit(f"Sin árboles para NBRE_BARRI = {BARRIO!r}. Revisa el shapefile.")

# Excluir los árboles de las avenidas/glorieta de contorno del barrio.
contorno = poligono_contorno(GEOJSON / 'osm_streets.json')
if contorno is not None:
    antes = len(inv)
    inv = inv[~inv.geometry.within(contorno)]
    print(f"Excluidos por calles de contorno: {antes - len(inv)}")

inv = inv.to_crs('EPSG:4326')

# ─── 3. Construir GeoJSON Point en WGS84 ─────────────────────────────────────
features = []
con_especie = 0
sin_codigo = 0
codigos_desconocidos = set()

for _, row in inv.iterrows():
    geom = row.geometry
    if geom is None or geom.is_empty:
        continue
    pt = geom if geom.geom_type == 'Point' else list(geom.geoms)[0]

    props = {}
    cod = limpio(row.get('CODIGO_ESP'))
    if cod:
        par = especies.get(cod)
        if par:
            comun, cientifico = par
            cientifico = limpio(cientifico)
            comun = limpia_comun(comun) if comun else None
            if cientifico:
                props['species'] = cientifico
            if comun:
                props['comun'] = comun
            if props.get('species') or props.get('comun'):
                con_especie += 1
        else:
            codigos_desconocidos.add(cod)
    else:
        sin_codigo += 1

    alt = row.get('ALTURA_TOT')
    if alt is not None and str(alt).strip() not in ('', 'nan', 'None'):
        try:
            a = round(float(alt), 1)
            if a > 0:
                props['altura'] = a
        except (ValueError, TypeError):
            pass

    # Diámetro de copa (m) a partir de especie + perímetro de tronco/altura.
    props['copa'] = copa_redondeada(props.get('species'), row.get('PERIMETRO'),
                                    row.get('ALTURA_TOT'), pt.x, pt.y)

    features.append({
        "type": "Feature",
        "geometry": {"type": "Point",
                     "coordinates": [round(pt.x, 7), round(pt.y, 7)]},
        "properties": props
    })

GEOJSON.mkdir(parents=True, exist_ok=True)
with open(GEOJSON / 'arboles_existentes.geojson', 'w', encoding='utf-8') as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)

print("=" * 56)
print("ÁRBOLES EXISTENTES — INVENTARIO OFICIAL, BELLAS VISTAS")
print("=" * 56)
print(f"Pies escritos              : {len(features)}")
print(f"  · con especie catalogada : {con_especie}")
print(f"  · sin código de especie  : {sin_codigo}")
if codigos_desconocidos:
    print(f"  · códigos no hallados en el diccionario: {sorted(codigos_desconocidos)}")
print(f"Fichero: data/geojson/arboles_existentes.geojson")
print("=" * 56)
