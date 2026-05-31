"""
Calles de CONTORNO del barrio (avenidas y glorieta que forman su límite).

Los árboles —existentes y propuestos— a menos de BUFFER_M del eje de estas vías
se excluyen de la visualización: pertenecen a la avenida perimetral, no al
interior del barrio. Lo usan procesar_arbolado_existentes.py y
generar_arboles_propuestos.py.

El polígono se construye buffeando las geometrías de OSM (osm_streets.json) cuyo
`name` casa con alguna de las calles de contorno.
"""

import json
import unicodedata
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString

CRS_M    = 'EPSG:25830'
BUFFER_M = 15.0          # distancia desde el eje de la vía (m)

# Subcadenas (sin acentos, minúsculas) que identifican las vías de contorno.
CALLES_CONTORNO = [
    'francos rodriguez',
    'bravo murillo',
    'cuatro caminos',     # Glorieta de Cuatro Caminos (y túnel homónimo)
    'reina victoria',
    'pablo iglesias',
]


def _norm(s):
    s = unicodedata.normalize('NFKD', str(s))
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def poligono_contorno(osm_streets_path):
    """Devuelve el polígono (EPSG:25830) de exclusión, o None si no hay vías."""
    osm = json.load(open(Path(osm_streets_path), encoding='utf-8'))
    nodes = {e['id']: (e['lon'], e['lat'])
             for e in osm['elements'] if e['type'] == 'node'}
    geoms = []
    for e in osm['elements']:
        if e['type'] != 'way':
            continue
        name = e.get('tags', {}).get('name')
        if name and any(t in _norm(name) for t in CALLES_CONTORNO):
            pts = [nodes[i] for i in e['nodes'] if i in nodes]
            if len(pts) >= 2:
                geoms.append(LineString(pts))
    if not geoms:
        return None
    return gpd.GeoSeries(geoms, crs='EPSG:4326').to_crs(CRS_M).buffer(BUFFER_M).union_all()
