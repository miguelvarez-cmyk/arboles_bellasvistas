"""
Descarga datos OSM usando la API REST de OpenStreetMap (no Overpass).
Endpoint: https://api.openstreetmap.org/api/0.6/map?bbox=west,south,east,north
Genera ficheros JSON compatibles con el formato que espera mapa.html.
"""

import urllib.request, urllib.error
import xml.etree.ElementTree as ET
import json, time, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
GEOJSON = ROOT / 'data' / 'geojson'

# Bounding box Bellas Vistas (west, south, east, north)
# El norte llega a 40.4590 para cubrir todo el polígono oficial del barrio
# (su borde norte está en 40.4576); el resto deja margen sur/este.
BBOX_W, BBOX_S, BBOX_E, BBOX_N = -3.7160, 40.4370, -3.6915, 40.4590

HIGHWAY_TYPES = {
    'primary', 'secondary', 'tertiary', 'residential',
    'unclassified', 'living_street', 'pedestrian', 'service'
}

def fetch_tile(w, s, e, n):
    url = f"https://api.openstreetmap.org/api/0.6/map?bbox={w:.6f},{s:.6f},{e:.6f},{n:.6f}"
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (compatible; 1000arboles-bellavistas research)',
        'Accept': 'application/xml, text/xml, */*'
    })
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read()

# ─── Descarga en tiles 4×4 para evitar límite 50K nodos ────
COLS, ROWS = 4, 4
lon_step = (BBOX_E - BBOX_W) / COLS
lat_step = (BBOX_N - BBOX_S) / ROWS

print(f"Descargando OSM en {COLS}x{ROWS}={COLS*ROWS} tiles ...")

all_xml_bytes = []
tile = 0
for row in range(ROWS):
    for col in range(COLS):
        tile += 1
        w = BBOX_W + col * lon_step
        e = w + lon_step
        s = BBOX_S + row * lat_step
        n = s + lat_step
        for attempt in range(1, 4):
            try:
                print(f"  Tile {tile}/{COLS*ROWS} ({w:.4f},{s:.4f},{e:.4f},{n:.4f}) ... ", end='', flush=True)
                t0 = time.time()
                data = fetch_tile(w, s, e, n)
                print(f"OK {len(data)//1024}KB en {time.time()-t0:.1f}s")
                all_xml_bytes.append(data)
                break
            except urllib.error.HTTPError as ex:
                print(f"HTTP {ex.code}")
                if attempt < 3:
                    time.sleep(5)
            except Exception as ex:
                print(f"ERR: {ex}")
                if attempt < 3:
                    time.sleep(5)
        else:
            print(f"  FALLO en tile {tile}, continuando...")
        time.sleep(0.5)  # pausa entre tiles

if not all_xml_bytes:
    print("No se descargó ningún tile.")
    sys.exit(1)

# ─── Parsear y fusionar todos los tiles ──────────────────────
print(f"\nFusionando {len(all_xml_bytes)} tiles ...")

nodes = {}
ways_raw = {}
rels_dict = {}

for xml_bytes in all_xml_bytes:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        continue
    for n in root.findall('node'):
        nid = int(n.get('id'))
        if nid not in nodes:
            tags = {t.get('k'): t.get('v') for t in n.findall('tag')}
            nodes[nid] = {'id': nid, 'lat': float(n.get('lat')),
                          'lon': float(n.get('lon')), 'tags': tags}
    for w in root.findall('way'):
        wid = int(w.get('id'))
        if wid not in ways_raw:
            nd   = [int(r.get('ref')) for r in w.findall('nd')]
            tags = {t.get('k'): t.get('v') for t in w.findall('tag')}
            ways_raw[wid] = {'id': wid, 'nodes': nd, 'tags': tags}
    for r in root.findall('relation'):
        rid = int(r.get('id'))
        if rid not in rels_dict:
            tags    = {t.get('k'): t.get('v') for t in r.findall('tag')}
            members = [{'type': m.get('type'), 'ref': int(m.get('ref')),
                        'role': m.get('role','')} for m in r.findall('member')]
            rels_dict[rid] = {'id': rid, 'tags': tags, 'members': members}

rels = list(rels_dict.values())
print(f"  Nodos únicos : {len(nodes)}")
print(f"  Ways únicos  : {len(ways_raw)}")
print(f"  Relations    : {len(rels)}")

# ─── 1. Fichero límite (boundary) ───────────────────────────
# Buscar relación Bellas Vistas
bv_rel = None
for r in rels:
    name = r['tags'].get('name', '')
    if 'bellas' in name.lower() or 'bellavistas' in name.lower().replace(' ', ''):
        bv_rel = r
        print(f"  Límite encontrado: relation/{r['id']} — {name}")
        break

if not bv_rel:
    print("  AVISO: No se encontró relación 'Bellas Vistas'. Se usará el polígono de respaldo.")

boundary_data = {
    'version': 0.6,
    'elements': []
}
if bv_rel:
    boundary_data['elements'].append({'type': 'relation', 'id': bv_rel['id'],
                                       'tags': bv_rel['tags'], 'members': bv_rel['members']})
    # Añadir los ways y nodos miembro
    for m in bv_rel['members']:
        if m['type'] == 'way' and m['ref'] in ways_raw:
            w = ways_raw[m['ref']]
            boundary_data['elements'].append({'type': 'way', 'id': w['id'],
                                              'nodes': w['nodes'], 'tags': w['tags']})
            for nid in w['nodes']:
                if nid in nodes:
                    n = nodes[nid]
                    boundary_data['elements'].append({'type': 'node', 'id': n['id'],
                                                      'lat': n['lat'], 'lon': n['lon']})

with open(GEOJSON / 'osm_boundary.json', 'w', encoding='utf-8') as f:
    json.dump(boundary_data, f)
print(f"  osm_boundary.json — {len(boundary_data['elements'])} elementos")

# ─── 2. Fichero calles ───────────────────────────────────────
street_ways = []
street_nodes = set()

for wid, w in ways_raw.items():
    hw = w['tags'].get('highway', '')
    if hw not in HIGHWAY_TYPES:
        continue
    street_ways.append({'type': 'way', 'id': w['id'], 'nodes': w['nodes'], 'tags': w['tags']})
    street_nodes.update(w['nodes'])

street_elements = street_ways[:]
for nid in street_nodes:
    if nid in nodes:
        n = nodes[nid]
        street_elements.append({'type': 'node', 'id': n['id'],
                                 'lat': n['lat'], 'lon': n['lon']})

streets_data = {'version': 0.6, 'elements': street_elements}
with open(GEOJSON / 'osm_streets.json', 'w', encoding='utf-8') as f:
    json.dump(streets_data, f)
print(f"  osm_streets.json — {len(street_ways)} calles, {len(street_nodes)} nodos")

# ─── 3. Fichero arbolado existente ───────────────────────────
tree_elements = []
for nid, n in nodes.items():
    if n['tags'].get('natural') in ('tree', 'tree_row'):
        tree_elements.append({'type': 'node', 'id': n['id'],
                              'lat': n['lat'], 'lon': n['lon'], 'tags': n['tags']})

trees_data = {'version': 0.6, 'elements': tree_elements}
with open(GEOJSON / 'osm_trees.json', 'w', encoding='utf-8') as f:
    json.dump(trees_data, f)
print(f"  osm_trees.json — {len(tree_elements)} árboles")

# ─── Resumen ────────────────────────────────────────────────
print()
print("=" * 48)
print("FICHEROS OSM DESCARGADOS CORRECTAMENTE")
print("=" * 48)
for fn in ('osm_boundary.json', 'osm_streets.json', 'osm_trees.json'):
    path = GEOJSON / fn
    with open(path, encoding='utf-8') as f:
        d = json.load(f)
    kb = path.stat().st_size // 1024
    print(f"  {fn}: {len(d['elements'])} elementos ({kb} KB)")
print()
print("El mapa cargara estos ficheros localmente.")
print("No necesita conexion a Overpass en tiempo de ejecucion.")
