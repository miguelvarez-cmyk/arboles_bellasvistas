"""
Descarga el INVENTARIO OFICIAL de arbolado del Ayuntamiento de Madrid
(dataset 300761 «Arbolado en parques y zonas verdes de Madrid — detalle»,
CC BY 4.0, actualización semestral) y lo extrae en data/raw/.

El ZIP cubre TODO Madrid (~660 MB, arbolado viario + zonas verdes, cada pie
inventariado individualmente con especie). El recorte a Bellas Vistas lo hace
después scripts/procesar_arbolado_existentes.py.

Fuente: https://datos.madrid.es/dataset/300761-0-arbolado-especies
"""

import sys, time, zipfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.parent
RAW  = ROOT / 'data' / 'raw'
DEST_DIR = RAW / 'arbolado_madrid'          # carpeta donde se extrae el shapefile
ZIP_PATH = RAW / 'arbolado_madrid.zip'
XLSX_PATH = RAW / 'arbolado_especies.xlsx'  # diccionario CODIGO_ESP -> especie

URL = ("https://datos.madrid.es/dataset/300761-0-arbolado-especies/"
       "resource/300761-1-arbolado-especies-zip/download/"
       "300761-1-arbolado-especies-zip.zip")
# Diccionario de especies (código -> nombre común y científico); ~200 KB
URL_ESPECIES = ("https://datos.madrid.es/dataset/300761-0-arbolado-especies/"
                "resource/300761-2-arbolado-especies-xlsx/download/"
                "300761-2-arbolado-especies-xlsx.xlsx")

HEADERS = {'User-Agent': 'Mozilla/5.0 (compatible; 1000arboles-bellavistas research)'}


def descargar(url, dest):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp:
        total = int(resp.headers.get('Content-Length', 0))
        done = 0
        chunk = 1 << 20  # 1 MB
        t0 = time.time()
        with open(dest, 'wb') as f:
            while True:
                buf = resp.read(chunk)
                if not buf:
                    break
                f.write(buf)
                done += len(buf)
                if total:
                    pct = done * 100 // total
                    mb = done / (1 << 20)
                    speed = mb / max(time.time() - t0, 0.1)
                    print(f"\r  {pct:3d}%  {mb:7.1f} MB / {total/(1<<20):.0f} MB"
                          f"  ({speed:.1f} MB/s)", end='', flush=True)
        print()
    return dest


def main():
    RAW.mkdir(parents=True, exist_ok=True)

    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 600 * (1 << 20):
        print(f"ZIP ya presente ({ZIP_PATH.stat().st_size/(1<<20):.0f} MB): {ZIP_PATH}")
    else:
        print(f"Descargando inventario oficial (~660 MB) ...\n  {URL}")
        descargar(URL, ZIP_PATH)
        print(f"Descargado: {ZIP_PATH} ({ZIP_PATH.stat().st_size/(1<<20):.0f} MB)")

    print("Descargando diccionario de especies ...")
    descargar(URL_ESPECIES, XLSX_PATH)
    print(f"Descargado: {XLSX_PATH} ({XLSX_PATH.stat().st_size/1024:.0f} KB)")

    print("Extrayendo ...")
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP_PATH) as z:
        z.extractall(DEST_DIR)

    shps = sorted(DEST_DIR.rglob('*.shp'))
    print(f"Extraído en {DEST_DIR}")
    print(f"Shapefiles encontrados ({len(shps)}):")
    for s in shps:
        print(f"  · {s.relative_to(RAW)}  ({s.stat().st_size/(1<<20):.1f} MB)")
    if not shps:
        print("AVISO: no se encontró ningún .shp dentro del ZIP", file=sys.stderr)


if __name__ == '__main__':
    main()
