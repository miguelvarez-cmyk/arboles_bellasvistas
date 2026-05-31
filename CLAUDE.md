# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Sitio web del movimiento vecinal **"1000 Árboles para Bellas Vistas"** (Tetuán, Madrid). Tres páginas HTML autocontenidas + datos GeoJSON generados por scripts Python. Sin framework, sin bundler, sin dependencias instalables.

## Arrancar en local

```bash
# Desde d:\Vibecoding\1000_arboles\
python -m http.server 8080
# → http://localhost:8080
```

Los datos OSM y SER están embebidos como variables JS globales (`window.OSM_STREETS`, etc.) cargadas con `<script src>`. El mapa funciona tanto desde `http://localhost` como abriendo directamente el fichero `mapa.html` sin servidor.

## Regenerar datos (orden obligatorio)

```bash
# 1. Descargar viario + árboles existentes + contorno de OSM
python scripts/descargar_osm.py
# Genera: data/geojson/osm_boundary.json, osm_streets.json, osm_trees.json

# 2. Procesar bandas SER desde el shapefile OFICIAL local (data/raw/)
python scripts/procesar_ser.py
# Genera: data/geojson/ser_bellavistas.geojson  (613 bandas LineString, Bellas Vistas)

# 3. Intercalar alcorques en las bandas SER (línea cada ~2-3 plazas + batería ≤7%)
python scripts/generar_arboles_propuestos.py
# Genera: data/geojson/arboles_propuestos.geojson  (534 árboles: 507 línea + 27 batería)

# 4. Procesar contorno de aceras desde la cartografía municipal (data/raw/)
python scripts/procesar_aceras.py
# Genera: data/geojson/aceras.geojson  (616 polígonos de acera con ancho medio)

# 5. Árboles existentes = INVENTARIO OFICIAL del Ayuntamiento (dataset 300761)
python scripts/descargar_arbolado_madrid.py   # baja ZIP ~660 MB + diccionario especies a data/raw/
python scripts/procesar_arbolado_existentes.py # recorta a Bellas Vistas y traduce el código de especie
# Genera: data/geojson/arboles_existentes.geojson  (686 árboles municipales, todos con especie)
```

`scripts/procesar_ser.py` y `scripts/generar_arboles_ser.py` requieren **geopandas/shapely** (sólo en el pipeline offline; el mapa en el navegador no usa dependencias).
`scripts/analizar_ser.py` es una utilidad de diagnóstico; no genera ficheros que use el mapa.

**Diámetro de copa**: `scripts/_copa.py` (módulo compartido) estima el diámetro de copa (m) de cada árbol. Existentes: alometría `copa = clamp(SLOPE·DBH, CROWN_MIN, copa_madura(especie))` con `DBH = PERIMETRO/π` (perímetro de tronco del inventario, cm; `SLOPE=0.27` calibrado para Bellas Vistas), capada por la copa madura típica de la especie (tabla `COPA_ESP`); sin perímetro usa la altura como desarrollo. Propuestos: a cada uno se le asigna una **especie** según la anchura de su calle (proxy = 2·dist al eje, umbral `ANCHURA_ANCHA=9 m`; calle ancha → Olmo de Siberia/Plátano, estrecha → Aligustre del Japón/Peral/Rosa de Siria, elección determinista ponderada por la frecuencia real en el barrio) y su copa = copa madura de esa especie. A todos (existentes y propuestos) se les aplica `jitter()` ±10 % (determinista por coordenadas) para una apariencia natural. El campo resultante es `props.copa`, que el mapa usa como diámetro de la copa dibujada.

**Calles de contorno**: `scripts/_contorno.py` (módulo compartido) construye un polígono buffeando (±`BUFFER_M`=15 m) las avenidas/glorieta límite del barrio (Francos Rodríguez, Bravo Murillo, Glorieta de Cuatro Caminos, Reina Victoria, Pablo Iglesias) a partir de `osm_streets.json`. Tanto `procesar_arbolado_existentes.py` como `generar_arboles_propuestos.py` **excluyen** los árboles dentro de ese polígono (son de la avenida perimetral, no del interior). Para retocar qué calles o el ancho, editar `CALLES_CONTORNO`/`BUFFER_M` ahí.

### Datos georreferenciados oficiales (`data/raw/`)

Shapefiles del Ayuntamiento de Madrid (EPSG:25830, ETRS89 UTM 30N). Los clave:
- **`Bandas de Aparcamiento.shp`** (947 bandas en toda la zona SER) con geometría LineString real y atributos `Color`, `Bateria_Li`, `Res_NumPla`. No trae nombre de calle: se recupera por proximidad (`sjoin_nearest` ≤30 m) contra las vías OSM con `name`.
- **`Aceras - Anchos medios (metros).shp`** (1.086 polígonos) con `ANCHO_MEDI` (ancho medio en metros).
- **`arbolado_madrid/ARBOLADO_MADRID.shp`** + **`arbolado_especies.xlsx`** — inventario oficial de arbolado (dataset [300761](https://datos.madrid.es/dataset/300761-0-arbolado-especies), CC BY 4.0, semestral). 793.047 pies en todo Madrid con campos `NBRE_BARRI`/`NBRE_DTO` (filtro directo por barrio, sin sjoin), `CODIGO_ESP` (código de especie → nombre con el XLSX), `ALTURA_TOT`, `PERIMETRO`. Los bajan `descargar_arbolado_madrid.py`; no se versionan (≈660 MB).

Las bandas/aceras se filtran a Bellas Vistas con `Límite de Barrios de la Zona S_E_R_.shp` (`NOMBAR='Bellas Vistas'`); el inventario por su propio `NBRE_BARRI='BELLAS VISTAS'`. Otros shapefiles (`Carriles…` —solo `.dbf`, sin geometría—, `Parquímetros`, `Límite Zona S_E_R_`) no se usan aún.

## Arquitectura

### Páginas

| Fichero | Función |
|---|---|
| `index.html` | Landing page del movimiento con **scrollytelling cinematográfico** en el hero: imagen fija detrás de textos que entran/salen secuenciadamente (0-75% scroll), culminando en cambio de imagen (sin árboles → con árboles) mientras el usuario lee "Ayúdanos a hacerlo realidad". Después: estadísticas, canales de petición, formulario de firmas. Vanilla JS sin deps, optimizado para móvil. |
| `mapa.html` | Mapa Leaflet **minimalista** — dos capas base intercambiables (Carto Voyager con nombres de calle, por defecto / foto satélite Esri World Imagery) vía `L.control.layers` arriba a la derecha + 3 capas de datos fijas: aceras, árboles existentes y árboles propuestos (sólo sobre plazas SER). Sin toggles para las capas de datos, sin paneles; leyenda con conteos dinámicos y **un popup por árbol con la especie** (existentes: nombre común + científico del inventario municipal oficial, `comun`/`species`; propuestos: especie asignada según la anchura de la calle, `comun`/`species`, y copa). Tipografías de marca (Playfair/Nunito) y `tolerance:8` en el canvas para el toque en Chrome/Android |
| `visualizacion.html` | Comparador antes/después mediante slider SVG arrastrable; 5 calles × 3 estaciones generadas dinámicamente en JS |

### Ficheros de datos

| Fichero | Origen | Uso |
|---|---|---|
| `data/geojson/osm_boundary.json` | OSM REST API (tiles 4×4) | Contorno oficial del barrio (relation/10668283) |
| `data/geojson/osm_streets.json` | OSM REST API | 1.175 vías reales con tipos `highway=*` |
| `data/geojson/osm_trees.json` | OSM REST API | 4.817 árboles en el bbox (`natural=tree`); usado por `generar_arboles_propuestos.py` para el filtro de proximidad (`MIN_DIST`) |
| `data/geojson/arboles_existentes.geojson` | `scripts/procesar_arbolado_existentes.py` (inventario oficial 300761) | 686 árboles municipales **dentro de Bellas Vistas** y fuera de las avenidas de contorno, con especie (`comun`/`species`), `altura` y `copa` (diámetro de copa, m); lo que muestra el mapa (var `OSM_TREES`) |
| `data/geojson/ser_bellavistas.geojson` | Shapefile oficial `data/raw/Bandas de Aparcamiento.shp` | 613 bandas SER como **LineString real** (longitud y orientación exactas) |
| `data/geojson/arboles_propuestos.geojson` | Generado por `scripts/generar_arboles_propuestos.py` | 534 árboles propuestos sobre **bandas SER** (507 línea + 27 batería), excluido el contorno; props `ubicacion`, `species`/`comun` (especie asignada por anchura de calle: 93 Olmo/Plátano en anchas, 441 Aligustre/Peral/Rosa de Siria en estrechas) y `copa` (m, madura de la especie). La copa se desplaza ≤1,5 m hacia el eje de la calle (más cuanto mayor) para no invadir fachadas |
| `data/geojson/aceras.geojson` | Shapefile oficial `data/raw/Aceras - Anchos medios (metros).shp` | 616 polígonos de acera (Bellas Vistas) con `ancho_m`, simplificados 0,5 m |
| `data/js/*.js` | Generado por `scripts/json_to_js.py` | Bundles JS con variables globales para `mapa.html` |

### Flujo de carga en `mapa.html`

```
<script> síncrono: los datos ya están en window.* (cargados por <script src>)
 ├─ renderAceras()    → window.ACERAS     (polígonos, pane acerasPane, interactive:false)
 ├─ renderExisting()  → window.OSM_TREES   (circleMarker verde + popup de especie; FeatureCollection recortada al barrio)
 └─ renderProposed()  → window.PROPUESTOS  (circleMarker naranja + popup de especies recomendadas: alcorques en bandas SER)
```

Sólo carga 3 ficheros JS (`arboles_existentes.js`, `aceras.js`, `arboles_propuestos.js`). Los árboles existentes provienen del **inventario municipal oficial filtrado a Bellas Vistas** (`arboles_existentes.geojson`), con especie real. No usa `osm_streets`/`osm_boundary`/`ser_bellavistas` (los nombres de calle los aporta la base Carto). No hay `fetch()`, controles de capas, ni fallback.

### Regenerar los `.js` tras actualizar datos

```bash
# Después de correr los scripts de datos:
python scripts/json_to_js.py
```

### Capas del mapa (`mapa.html`)

| Variable JS | Contenido |
|---|---|
| `gA` | Aceras (polígonos `L.geoJSON`, pane `acerasPane`) |
| `gE` | Árboles existentes (inventario): `L.circle` verde apagado `#7FA07C` |
| `gP` | Árboles propuestos (alcorques en bandas SER): `L.circle` verde vivo `#2ECF4B` |

Capas fijas, sin toggles. Los árboles son `circleMarker` (canvas, renderer `cvs`, `tolerance:8` para el toque) cuyo radio simula la **copa real de cada árbol**: cada feature trae su diámetro de copa en `props.copa` (m) y `copaPx(diam)` lo convierte a píxeles según zoom/latitud, con un mínimo `FLOOR_PX = 3.5` px para que se vean en la vista general y crezcan hasta su tamaño real al acercar; el diámetro se guarda en la capa (`m._copaM`) y se reescala por árbol en `map.on('zoomend', ...)`. Las aceras usan su propio pane `acerasPane` (zIndex 350) con renderer `cvsA`, quedando **por debajo** de los árboles.

## Parámetros clave

**`scripts/generar_arboles_propuestos.py`** — intercala alcorques en bandas SER (línea y batería). **No** planta en acera. La función `colocar(line, T)` reparte T árboles a lo largo de una banda (extremos hacia el borde con `END_INSET`, resto uniforme con `line.interpolate`) y la comparten ambos tipos.

*LÍNEA* (modelo: plaza ≈ 5 m, alcorque ≈ 1,5 m ⇒ cada árbol cuesta ≈0,3 plazas; por el redondeo las bandas cortas pierden ~1 plaza; **sin tope global**):
- `n_arboles(N) = 0 si N < MIN_PLAZAS; si no 2 + (N-2)//GROUP` — árbol en ambos extremos + interiores cada ~2-3 plazas. Reproduce la tabla: N=4→2, 5/6/7→3, 8→4…
- `MIN_PLAZAS = 4`; `GROUP = 3` (**principal regulador de la densidad**: subirlo ⇒ menos árboles)
- `PLAZA_LEN = 5.0` — solo para estimar las plazas perdidas que se reportan

*BATERÍA* (la plaza ocupa solo ~2,5 m de bordillo ⇒ **1 árbol = 1 plaza perdida**; presupuesto pequeño):
- `n_arboles_bat(N) = 0 si N < MIN_BAT; si no max(1, round(N/GROUP_BAT))` — N<8→0; 8..14→1; ≥15→2
- `MIN_BAT = 8`; `GROUP_BAT = 10`; `MAX_BAT_LOSS = 0.07` — tope de seguridad (se recorren las bandas de mayor a menor y se para al alcanzarlo)

*Comunes*: `ALCORQUE = 1.5`; `END_INSET = 0.75`; `MIN_DIST = 4.0` (distancia mínima a árbol existente o a otro nuevo; descarta candidatos, por eso el total real < estimado puro de la fórmula). Los bloqueadores de distancia son la **unión** del inventario oficial (`arboles_existentes.geojson`, lo que se ve en el mapa) **y** los árboles OSM (`osm_trees.json`). Además se descartan los candidatos dentro del contorno (`scripts/_contorno.py`).
- Lee bandas (`ser_bellavistas.geojson`), inventario (`arboles_existentes.geojson`), OSM (`osm_trees.json`) y ejes de calle (`osm_streets.json`, para el desplazamiento de copa hacia la calzada)
- Resultado actual: **534 árboles** = 507 línea (282 plazas, 14,1% de 1.993) + 27 batería (27 plazas, 5,5% de 490)

## Coordenadas

Los shapefiles oficiales y los datos SER usan **UTM ETRS89 Zona 30N (EPSG:25830)**; los scripts del pipeline calculan distancias/áreas en EPSG:25830 y reproyectan a WGS84 con geopandas (`to_crs('EPSG:4326')`). Los datos OSM ya vienen en WGS84 (lat/lon). El bbox de descarga es `[40.4370, -3.7160, 40.4590, -3.6915]` (sur, oeste, norte, este); el norte se amplió a 40.4590 para cubrir todo el polígono del barrio (borde norte en 40.4576), de modo que ningún árbol de dentro del barrio quede sin descargar.

## Descarga OSM: por qué tiles

La API REST de OSM tiene un límite de 50.000 nodos por petición. El bbox completo del barrio excede ese límite, por eso `descargar_osm.py` divide en **16 tiles de 4×4** y fusiona deduplicando por ID de elemento. La API Overpass (`overpass-api.de`) devuelve HTTP 406 desde esta red; no usar.

## Scrollytelling en `index.html`

La landing page implementa una secuencia cinematográfica de scroll (scrollytelling) que guía emocionalmente al usuario desde el problema hasta la solución.

### Arquitectura

**HTML**: El hero se compone de un contenedor alto (`#story`, 500vh) con un stage sticky (`#story-stage`, 100vh) que permanece pinned mientras el usuario scrollea. Dentro del stage:
- Dos capas de imagen (`#bg-before` y `#bg-after`) con crossfade via opacity
- Overlay oscuro con gradiente (para contraste del texto sobre cualquier imagen)
- Tres paneles de texto (`panel-1`, `panel-2`, `panel-3`) centrados y animados

Después del story, una sección puente (`s-bridge`) reintroduce el título "1.000 árboles para nuestro barrio" y las estadísticas principales.

### Flujo visual

| Scroll | Evento | Visual |
|---|---|---|
| 0-10% | Intro (sin paneles activos) | Imagen "antes sin árboles" fija, header invisible, **flecha ↓ amarilla visible**, sin texto |
| 10-40% | Panel 1 entra/sale | "Bellavistas es uno de los barrios con menos arbolado de Madrid." (aparición gradual, desaparición lenta) |
| 35-65% | Panel 2 entra/sale | "Necesitamos que el Ayuntamiento plante nuevos árboles en nuestras calles." (superposición con panel 1 al inicio, texto más conciso) |
| 60-90% | Panel 3 entra/sale (sin cambio de imagen) | "Ayúdanos a hacerlo realidad." — imagen aún es "antes sin árboles" |
| 75%+ | Image swap ocurre aquí | Imagen cambia a "después con árboles" (crossfade 0.8s) mientras panel 3 aún está visible |
| 90%+ | Salida de paneles, header reaparece | Imagen fija con árboles, hay más scroll antes del bridge. Título y estadísticas aparecen, header vuelve visible |

**Nota:** Los beats se solapan ligeramente para un efecto cinematográfico más fluido. El header permanece invisible durante toda la secuencia (0-95%). La flecha desaparece al detectar scroll (p > 0.02).

### Detalles de implementación

**CSS**: Uso de `position: sticky` en `#story-stage` para fijar el canvas. `clamp()` en tipografía para escalar responsivamente. Gradiente de overlay con `rgba()` para adaptarse a cualquier imagen de fondo.

**Indicador de scroll**:
- `.scroll-indicator` aparece en la esquina inferior del stage (posición absoluta, bottom: 60px)
- `.scroll-arrow` contiene el símbolo Unicode `↓` (flecha amarilla #FFE066)
- Tamaño 28px, visible solo entre 0-10% del scroll (antes de que aparezcan los textos)
- Se desvanece suavemente (transition: 0.3s) cuando comienza el primer panel
- Color amarillo dorado para coincidir con los textos

**Colores de textos**:
- Panel 1: `#FFE066` (amarillo dorado) — problema/denuncia
- Panel 2: `#A8E6CF` (verde menta) — esperanza/solución
- Panel 3: `#FF8B94` (rosa salmón) — urgencia/acción
- Font-weight: 900 (ultra-bold) para máxima legibilidad

**JavaScript**: IIFE sin dependencias que:
1. Calcula progreso del scroll como fracción (0-1) comparando posición de `#story` contra viewport
2. Detecta qué beat (fase) está activo según 3 rangos: [0.15, 0.35], [0.35, 0.55], [0.55, 0.75]
3. Aplica/remueve clases `.active` y `.exited` a los paneles (transiciones CSS)
4. Controla `opacity` de `#bg-after` para el cambio de imagen (100% opaco desde beat 2)
5. Listener passive para performance en Chrome Android

**Preload**: Las dos imágenes se precargan vía `<link rel="preload" as="image">` en el `<head>` para evitar flash de contenido.

### Imágenes utilizadas

- `data/images/antes-sin-arboles.png` — Foto de calle real de Bellavistas sin árboles (problema)
- `data/images/despues-con-arboles.png` — Foto de la misma calle con árboles plantados (solución)

Los nombres se han simplificado (sin acentos ni espacios) para máxima compatibilidad con navegadores y servidores web.

### Editables

**Ritmo de paneles y timing de imagen** — modificar en `index.html`:
```js
const BEATS = [
  { from: 0.10, to: 0.40, idx: 0 },  // Panel 1
  { from: 0.35, to: 0.65, idx: 1 },  // Panel 2
  { from: 0.60, to: 0.90, idx: 2 },  // Panel 3 (sin image swap, solo texto)
];

bgAfter.style.opacity = p >= 0.75 ? '1' : '0';  // Imagen con árboles aparece al 75%
```
Los valores representan fracción del scroll dentro de `#story` (0.0 = inicio, 1.0 = fin de 600vh). La imagen ahora aparece DESPUÉS de que el usuario vea el panel 3. Para alargar la secuencia, cambiar `height: 600vh` a mayor.

**Opacidad del overlay** — reducir/aumentar oscuridad en `.story-overlay`:
```css
background: linear-gradient(to bottom,
  rgba(10,20,12,0.15) 0%,    /* arriba más claro */
  rgba(10,20,12,0.25) 50%,
  rgba(10,20,12,0.30) 100%);  /* abajo más oscuro */
```
Valores más altos (0.35–0.65 era el original) oscurecen más la imagen. Más bajos la dejan más visible.

**Visibilidad del header** — modificar el rango en el script:
```js
const inStoryRange = p >= 0 && p <= 0.95;  // 0-95% del scroll
header.classList.toggle('hidden-during-story', inStoryRange);
```
Cambiar `0.95` para que reaparezca antes/después.

**Indicador de scroll** — ajustar timing de visibilidad:
```js
scrollIndicator.classList.toggle('visible', p >= 0 && p <= 0.10);  // Visible solo 0-10%
```
Cambiar el rango `0` y `0.10` para mostrar/ocultar en diferentes momentos. Color amarillo (#FFE066) y símbolo Unicode `↓` en el HTML: `<div class="scroll-arrow">↓</div>`

**Tamaño de textos** — modificar en `.story-panel p`:
```css
font-size: clamp(2.8rem, 11vw, 4rem);  /* min 2.8rem, escalable 11vw, max 4rem */
```
Aumentar los números para textos más grandes, disminuir para más pequeños.

**Color de textos** — todos los paneles usan amarillo dorado:
```css
.story-panel p { color: #FFE066; }  /* amarillo dorado uniforme */
```

**Duración de transiciones** — en `.story-panel` (textos), `#bg-after` (imagen) e indicador:
```css
.story-panel { transition: opacity 0.5s ease, transform 0.5s ease; }
#bg-after { transition: opacity 0.8s ease; }
.scroll-indicator { transition: opacity 0.3s ease; }  /* flecha */
```

### Compatibilidad

- ✅ Chrome/Edge (Windows, Android)
- ✅ Firefox
- ✅ Safari (iOS 15+, posición sticky funciona)
- ✅ Móvil: viewports desde 320px (clamp fonts, layout adapta)
- ✅ Scroll suave `html { scroll-behavior: smooth }` no interfiere con el handler

### Performance

- Vanilla JS: sin bundle, sin build step
- Listener `passive: true`: no bloquea scroll
- Condición `Math.abs(p - lastP) < 0.001` evita actualizaciones micromovimientos innecesarias
- `background-size: cover` y `background-position: center` optimizan carga de imagen
