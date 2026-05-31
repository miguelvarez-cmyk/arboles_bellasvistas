"""
Estimación del DIÁMETRO DE COPA (m) de cada árbol a partir de su especie y su
grado de desarrollo, para dibujar copas a escala en el mapa.

Modelo (módulo compartido por procesar_arbolado_existentes.py y
generar_arboles_propuestos.py):

  · Cada especie tiene una copa madura típica `crown_mature` y una altura madura
    `h_mature` (tabla COPA_ESP; respeta el hábito: columnar, umbeliforme, arbusto…).
  · Con perímetro de tronco (predictor alométrico): DBH = perímetro/π y
        copa = clamp(SLOPE · DBH, CROWN_MIN, crown_mature)
    de modo que el tronco grueso ⇒ copa cercana a la madura, capada por especie.
  · Sin perímetro: se usa la altura como grado de desarrollo
        copa = crown_mature · clamp(0,3 + 0,7 · altura/h_mature, 0,3, 1)
  · `jitter()` añade ±10 % determinista (según las coordenadas) para que el mapa
    se vea natural sin perder reproducibilidad.
"""

import hashlib
import math
import re

# Calibración del término alométrico (m de copa por cm de DBH). Calibrado con la
# distribución real de PERIMETRO en Bellas Vistas (cm; DBH mediana ~11 cm, p95 ~40 cm):
# 0,27 da copa mediana ~3 m y madura ~11-12 m para los plátanos grandes (capada por especie).
SLOPE     = 0.27
CROWN_MIN = 1.5    # m — copa mínima para un pie joven
JITTER    = 0.10   # ±10 %

# Copa madura (m) y altura madura (m) por especie. Valores horticulturales
# orientativos para arbolado urbano de Madrid.
COPA_ESP = {
    'ligustrum japonicum':        (4.0, 6),
    'platanus x hispanica':       (12.0, 22),
    'acer negundo':               (8.0, 12),
    'hibiscus syriacus':          (2.5, 3),
    'acer platanoides':           (10.0, 18),
    'prunus cerasifera':          (5.0, 6),
    'acer pseudoplatanus':        (11.0, 20),
    'pinus pinea':                (11.0, 18),
    'pyrus calleryana':           (4.5, 9),
    'ulmus pumila':               (12.0, 18),
    'celtis australis':           (10.0, 18),
    'morus alba':                 (9.0, 12),
    'carpinus betulus':           (8.0, 16),
    'malus floribunda':           (5.0, 6),
    'melia azedarach':            (8.0, 9),
    'acer campestre':             (7.0, 12),
    'populus alba':               (12.0, 22),
    'aesculus hippocastanum':     (12.0, 20),
    'lagerstroemia indica':       (4.0, 5),
    'fraxinus excelsior':         (12.0, 22),
    'ailanthus altissima':        (10.0, 18),
    'acer x freemanii':           (9.0, 15),
    'platycladus orientalis':     (3.0, 8),
    'cupressus sempervirens':     (2.0, 18),
    'liquidambar styraciflua':    (8.0, 18),
    'cedrus deodara':             (10.0, 25),
    'styphnolobium japonicum':    (12.0, 18),
    'magnolia grandiflora':       (8.0, 16),
    'fraxinus angustifolia':      (11.0, 18),
    'photinia x fraseri':         (3.0, 4),
    'cercis siliquastrum':        (6.0, 7),
    'robinia pseudoacacia':       (9.0, 18),
    # Recomendadas para los propuestos (además de Celtis y Cercis, ya arriba):
    'fraxinus ornus':             (6.0, 8),
    'koelreuteria paniculata':    (7.0, 9),
}
DEFAULT = (6.0, 10)

# Especies recomendadas para los árboles propuestos (= popup del mapa).
RECOMENDADAS = ['celtis australis', 'cercis siliquastrum',
                'fraxinus ornus', 'koelreuteria paniculata']
COPA_PROPUESTO = sum(COPA_ESP[s][0] for s in RECOMENDADAS) / len(RECOMENDADAS)


def _norm(species):
    s = (species or '').lower()
    s = re.sub(r"'[^']*'", ' ', s)        # quitar cultivar entre comillas
    s = re.sub(r'\bsubsp\.?\b.*', ' ', s) # quitar subespecie y lo que sigue
    return ' '.join(s.split())


def _lookup(species):
    s = _norm(species)
    if s in COPA_ESP:
        return COPA_ESP[s]
    toks = s.split()
    if len(toks) >= 2:                    # género + epíteto (sin cultivar)
        key = ' '.join(toks[:2])
        if key in COPA_ESP:
            return COPA_ESP[key]
    return DEFAULT


def _to_float(v):
    try:
        f = float(v)
        return f if f > 0 else None
    except (TypeError, ValueError):
        return None


def copa_madura(species):
    """Copa madura típica (m) de la especie (para árboles propuestos)."""
    return _lookup(species)[0]


def diametro_copa(species, perimetro_cm=None, altura_m=None):
    crown_mature, h_mature = _lookup(species)
    peri = _to_float(perimetro_cm)
    if peri is not None:
        dbh = peri / math.pi
        copa = max(CROWN_MIN, min(SLOPE * dbh, crown_mature))
    else:
        alt = _to_float(altura_m)
        dev = 0.6 if alt is None else max(0.3, min(0.3 + 0.7 * alt / h_mature, 1.0))
        copa = crown_mature * dev
    return copa


def jitter(value, seed_key, pct=JITTER):
    """Variación determinista ±pct según seed_key (p. ej. 'x,y')."""
    h = hashlib.md5(str(seed_key).encode()).digest()
    u = (h[0] | (h[1] << 8)) / 65535.0      # 0..1
    return value * (1 + pct * (2 * u - 1))


def copa_redondeada(species, perimetro_cm, altura_m, x, y):
    """Diámetro de copa final (m, 1 decimal) con jitter por coordenadas."""
    base = diametro_copa(species, perimetro_cm, altura_m)
    return round(jitter(base, f'{x},{y}'), 1)
