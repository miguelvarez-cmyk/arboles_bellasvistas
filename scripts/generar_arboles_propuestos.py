"""
Genera árboles nuevos en Bellas Vistas sobre las bandas de aparcamiento SER,
con un modelo geométrico realista distinto para cada tipo de banda:

LÍNEA (cordón):
  - Una plaza mide ~5 m, pero un alcorque solo necesita ~1,5 m. Intercalar
    alcorques a lo largo de una banda cuesta mucho menos de una plaza por árbol
    (≈0,3 plazas/árbol); por el redondeo, las bandas cortas pierden ~1 plaza.
  - Esquema "como la tabla": árbol en ambos extremos + interiores cada ~2-3
    plazas:  T = 0 si N < MIN_PLAZAS;  si no  T = 2 + (N-2)//GROUP
    (reproduce N=4->2, 5,6,7->3, 8->4, ...). Sin tope global.

BATERÍA (perpendicular):
  - La plaza ocupa solo ~2,5 m de frente de bordillo, así que un alcorque de
    1,5 m se come casi toda la plaza ⇒ **1 árbol = 1 plaza perdida**. Por eso
    el presupuesto es pequeño (tope MAX_BAT_LOSS ≈ 7%).
  - Solo bandas con N >= MIN_BAT plazas; 1 árbol cada ~GROUP_BAT plazas:
    T = max(1, round(N/GROUP_BAT)) (las bandas largas ≥15 plazas reciben 2).

No se plantan árboles en acera. La pérdida de plazas se reporta por tipo.

Genera: data/geojson/arboles_propuestos.geojson  (Point; prop. `ubicacion`)

Requiere geopandas/shapely (pipeline offline; el mapa no usa dependencias).
"""

import json
import math
from pathlib import Path

import geopandas as gpd
from shapely.geometry import shape, Point, LineString

import hashlib

from _contorno import poligono_contorno
from _copa import copa_madura, jitter

# ─── Especie de cada propuesto según la anchura de la calle ──────────────────
# Patrón de los árboles actuales (proxy anchura = 2·dist al eje de calle):
# calles anchas → Olmo de Siberia / Plátano; estrechas → Aligustre / Peral /
# Rosa de Siria. La elección dentro de cada grupo es determinista (hash de las
# coordenadas) y ponderada por la frecuencia real de cada especie en el barrio.
ANCHURA_ANCHA = 9.0   # m (proxy): umbral entre calle estrecha y ancha
PALETA_ANCHA = [
    ('Ulmus pumila',          'Olmo de Siberia',     25),
    ('Platanus x hispanica',  'Plátano de sombra',   91),
]
PALETA_ESTRECHA = [
    ('Ligustrum japonicum',   'Aligustre del Japón', 171),
    ('Pyrus calleryana',      'Peral de flor',        49),
    ('Hibiscus syriacus',     'Rosa de Siria',        45),
]


def elegir_especie(paleta, key):
    """Elección determinista ponderada por frecuencia (sci, comun)."""
    total = sum(w for *_, w in paleta)
    h = hashlib.md5(key.encode()).digest()
    u = ((h[2] << 8 | h[3]) / 65535.0) * total
    acc = 0.0
    for sci, com, w in paleta:
        acc += w
        if u <= acc:
            return sci, com
    return paleta[-1][0], paleta[-1][1]

ROOT    = Path(__file__).parent.parent
GEOJSON = ROOT / 'data' / 'geojson'
CRS_M   = 'EPSG:25830'

# ─── Parámetros comunes ──────────────────────────────────────────────────────
ALCORQUE   = 1.5    # m — lado/diámetro del alcorque
END_INSET  = 0.75   # m — centro del alcorque de los extremos, desde el fin de banda
MIN_DIST   = 4.0    # m — distancia mínima a árbol existente o nuevo ya colocado

# ─── Parámetros LÍNEA ────────────────────────────────────────────────────────
PLAZA_LEN  = 5.0    # m — longitud de una plaza en línea (dato real: ~4,99 m/plaza)
MIN_PLAZAS = 4      # bandas con < 4 plazas se dejan intactas (0 árboles)
GROUP      = 3      # plazas máx. por grupo entre árboles (define la densidad)

# ─── Parámetros BATERÍA ──────────────────────────────────────────────────────
MIN_BAT      = 8      # plazas mínimas para que una banda en batería sea candidata
GROUP_BAT    = 10     # plazas por árbol en batería (1 cada ~10; ≥15 plazas -> 2)
MAX_BAT_LOSS = 0.07   # tope de seguridad: fracción máx. de plazas en batería perdidas


def n_arboles(N):
    """Línea: árbol en ambos extremos + interiores cada ~2-3 plazas.
    Reproduce la tabla: N<4->0; 4->2; 5,6,7->3; 8->4; ..."""
    return 0 if N < MIN_PLAZAS else 2 + (N - 2) // GROUP


def n_arboles_bat(N):
    """Batería: 1 árbol cada ~GROUP_BAT plazas, solo bandas con N>=MIN_BAT.
    N<8->0; 8..14->1; >=15->2."""
    return 0 if N < MIN_BAT else max(1, round(N / GROUP_BAT))


# ─── Rejilla espacial para la distancia mínima ───────────────────────────────
class Grid:
    """Hash espacial con celdas de lado = MIN_DIST."""
    def __init__(self, cell):
        self.cell = cell
        self.d = {}

    def _key(self, x, y):
        return (int(x // self.cell), int(y // self.cell))

    def add(self, x, y):
        self.d.setdefault(self._key(x, y), []).append((x, y))

    def has_within(self, x, y, r):
        kx, ky = self._key(x, y)
        r2 = r * r
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for px, py in self.d.get((kx + dx, ky + dy), ()):
                    if (px - x) ** 2 + (py - y) ** 2 < r2:
                        return True
        return False


# ─── Cargar datos ────────────────────────────────────────────────────────────
bands = json.load(open(GEOJSON / 'ser_bellavistas.geojson', encoding='utf-8'))['features']


def reproyectar(feats):
    """LineStrings de las bandas reproyectadas a EPSG:25830 (lista alineada)."""
    return list(gpd.GeoSeries([shape(b['geometry']) for b in feats],
                              crs='EPSG:4326').to_crs(CRS_M))


linea = [b for b in bands if b['properties'].get('tipo') == 'Línea']
bat   = [b for b in bands if b['properties'].get('tipo') == 'Batería']
linea_lines = reproyectar(linea)
bat_lines   = reproyectar(bat)
plazas_linea = sum(int(b['properties'].get('plazas', 0)) for b in linea)
plazas_bat   = sum(int(b['properties'].get('plazas', 0)) for b in bat)

# Bloqueadores de distancia = TODO árbol existente real, para no proponer
# alcorques pegados a uno. Se unen dos fuentes:
#  · inventario oficial (arboles_existentes.geojson) = lo que muestra el mapa,
#  · árboles OSM del bbox (osm_trees.json) = cobertura extra (jardines privados…).
osm = json.load(open(GEOJSON / 'osm_trees.json', encoding='utf-8'))
osm_pts = [Point(e['lon'], e['lat']) for e in osm['elements']
           if e['type'] == 'node' and e.get('lat') is not None]

inv = json.load(open(GEOJSON / 'arboles_existentes.geojson', encoding='utf-8'))
inv_pts = [Point(*f['geometry']['coordinates']) for f in inv['features']
           if f.get('geometry')]

exist_pts = gpd.GeoSeries(inv_pts + osm_pts, crs='EPSG:4326').to_crs(CRS_M)

print(f"Bandas línea  : {len(linea):3d} | plazas: {plazas_linea}")
print(f"Bandas batería: {len(bat):3d} | plazas: {plazas_bat}")
print(f"Árboles existentes (referencia distancia): {len(exist_pts)} "
      f"(inventario {len(inv_pts)} + OSM {len(osm_pts)})")

# ─── Rejilla con los árboles existentes como bloqueadores ────────────────────
grid = Grid(MIN_DIST)
for p in exist_pts:
    grid.add(p.x, p.y)

# Polígono de exclusión: avenidas/glorieta de contorno del barrio.
contorno = poligono_contorno(GEOJSON / 'osm_streets.json')

accepted = []   # (x, y, ubicacion)


def colocar(line, T):
    """Coloca hasta T árboles repartidos a lo largo de `line` (EPSG:25830),
    con los extremos hacia el borde, respetando MIN_DIST contra la rejilla
    global. Devuelve el nº realmente colocado."""
    L = line.length
    if T <= 1:
        ds = [L / 2]
    else:
        span = max(0.0, L - 2 * END_INSET)
        ds = [END_INSET + span * i / (T - 1) for i in range(T)]
    n = 0
    for d in ds:
        pt = line.interpolate(d)
        if grid.has_within(pt.x, pt.y, MIN_DIST):
            continue
        if contorno is not None and contorno.covers(pt):
            continue
        grid.add(pt.x, pt.y)
        accepted.append((pt.x, pt.y, 'aparcamiento'))
        n += 1
    return n


# ─── 1) LÍNEA: alcorques intercalados (sin tope) ─────────────────────────────
n_linea = 0
perdidas_linea = 0
for band, line in zip(linea, linea_lines):
    N = int(band['properties'].get('plazas', 0))
    T = n_arboles(N)
    if T == 0:
        continue
    colocados = colocar(line, T)
    n_linea += colocados
    M = int((line.length - ALCORQUE * colocados) // PLAZA_LEN)  # plazas que quedan
    perdidas_linea += max(0, N - M)

# ─── 2) BATERÍA: 1 árbol = 1 plaza, hasta el tope de seguridad ───────────────
n_bat = 0
perdidas_bat = 0
budget_bat = int(plazas_bat * MAX_BAT_LOSS)
# Bandas de mayor a menor nº de plazas (mejor reparto si se topara el presupuesto).
orden = sorted(range(len(bat)),
               key=lambda i: int(bat[i]['properties'].get('plazas', 0)),
               reverse=True)
for i in orden:
    if perdidas_bat >= budget_bat:
        break
    N = int(bat[i]['properties'].get('plazas', 0))
    T = n_arboles_bat(N)
    if T == 0:
        continue
    T = min(T, budget_bat - perdidas_bat)   # no rebasar el tope
    colocados = colocar(bat_lines[i], T)
    n_bat += colocados
    perdidas_bat += colocados               # en batería 1 árbol = 1 plaza

# ─── Ejes de calle (para alejar las copas de fachada hacia la calzada) ───────
osm_st = json.load(open(GEOJSON / 'osm_streets.json', encoding='utf-8'))
st_nodes = {e['id']: (e['lon'], e['lat'])
            for e in osm_st['elements'] if e['type'] == 'node'}
st_lines = []
for e in osm_st['elements']:
    if e['type'] == 'way' and e.get('tags', {}).get('highway'):
        pts = [st_nodes[n] for n in e['nodes'] if n in st_nodes]
        if len(pts) >= 2:
            st_lines.append(LineString(pts))
streets_m = gpd.GeoSeries(st_lines, crs='EPSG:4326').to_crs(CRS_M).union_all()

# ─── Especie + copa + desplazamiento hacia el centro de la calzada ───────────
# A cada propuesto se le asigna una especie según la anchura de su calle (proxy =
# 2·dist al eje, medido en la banda antes de desplazar) y su copa madura típica
# (±10 % de variación natural). La copa se desplaza hacia el eje de la calle
# (alejándose de fachada) un poco más cuanto mayor es —simula que el tronco busca
# el centro de la calzada al crecer—, con tope de 1,5 m.
shifted = []   # (x, y, ubicacion, copa, species, comun)
n_ancha = 0
for x, y, ubic in accepted:
    p = Point(x, y)
    near = streets_m.interpolate(streets_m.project(p))
    anchura = 2 * p.distance(near)
    paleta = PALETA_ANCHA if anchura >= ANCHURA_ANCHA else PALETA_ESTRECHA
    if paleta is PALETA_ANCHA:
        n_ancha += 1
    sci, com = elegir_especie(paleta, f'{x},{y}')
    copa = round(jitter(copa_madura(sci), f'{x},{y}'), 1)
    vx, vy = near.x - x, near.y - y
    nrm = math.hypot(vx, vy)
    if nrm > 1e-6:
        s = min(1.5, 0.15 * copa)
        x, y = x + vx / nrm * s, y + vy / nrm * s
    shifted.append((x, y, ubic, copa, sci, com))

# ─── Salida GeoJSON (reproyectar a WGS84) ────────────────────────────────────
pts_wgs = gpd.GeoSeries([Point(x, y) for x, y, *_ in shifted],
                        crs=CRS_M).to_crs('EPSG:4326')
features = []
for (x, y, ubic, copa, sci, com), pw in zip(shifted, pts_wgs):
    features.append({
        "type": "Feature",
        "geometry": {"type": "Point",
                     "coordinates": [round(pw.x, 7), round(pw.y, 7)]},
        "properties": {"ubicacion": ubic, "copa": copa,
                       "species": sci, "comun": com}
    })
with open(GEOJSON / 'arboles_propuestos.geojson', 'w', encoding='utf-8') as f:
    json.dump({"type": "FeatureCollection", "features": features}, f, ensure_ascii=False)

pct_l = 100 * perdidas_linea / max(1, plazas_linea)
pct_b = 100 * perdidas_bat / max(1, plazas_bat)
print()
print("=" * 60)
print("ÁRBOLES PROPUESTOS SOBRE APARCAMIENTO SER")
print("=" * 60)
print(f"LÍNEA   : {n_linea:4d} árboles | plazas perdidas {perdidas_linea}/{plazas_linea} ({pct_l:.1f}%)")
print(f"BATERÍA : {n_bat:4d} árboles | plazas perdidas {perdidas_bat}/{plazas_bat} ({pct_b:.1f}%)")
print(f"TOTAL   : {len(features):4d} árboles propuestos")
print(f"Especie : {n_ancha} en calle ancha (Olmo/Plátano) | "
      f"{len(features) - n_ancha} en calle estrecha (Aligustre/Peral/Rosa de Siria)")
import collections as _c
_cnt = _c.Counter(f['properties']['comun'] for f in features)
print("          " + " · ".join(f"{c} {n}" for c, n in _cnt.most_common()))
print(f"Distancia mínima: {MIN_DIST} m | Alcorque: {ALCORQUE} m")
print("=" * 60)
