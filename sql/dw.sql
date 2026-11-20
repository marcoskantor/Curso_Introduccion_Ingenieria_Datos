-- Proyecto Final: almacén spine_dw.db (copo de nieve, constelación de dos hechos)
-- Generado a partir del cuaderno; lo ejecuta src/almacen.py.

-- DIMENSIONES. dim_dataset: de qué fuente viene la imagen.
CREATE TABLE dim_dataset (
  dataset_key INTEGER PRIMARY KEY,
  nombre      TEXT, fuente TEXT, version INTEGER, licencia TEXT
);
-- dim_region: nivel superior de la jerarquía anatómica (copo de nieve).
CREATE TABLE dim_region (
  region_key INTEGER PRIMARY KEY,
  nombre     TEXT
);
-- dim_vertebra: L1..L5, con su orden craneocaudal y su región.
CREATE TABLE dim_vertebra (
  vertebra_key       INTEGER PRIMARY KEY,
  codigo             TEXT,
  orden_craneocaudal INTEGER,
  region_key         INTEGER REFERENCES dim_region(region_key)
);
-- dim_diagnostico: incluye el miembro 'sin dato' (clave 0) para NHANES.
CREATE TABLE dim_diagnostico (
  diagnostico_key INTEGER PRIMARY KEY,
  nombre          TEXT
);
-- dim_imagen: una radiografía con sus atributos descriptivos (vista, sexo, grupo de edad) y su
-- completitud: vertebras_anotadas y completa (1 si tiene las 5 vértebras) responden P1.
CREATE TABLE dim_imagen (
  imagen_key          INTEGER PRIMARY KEY,
  archivo             TEXT,
  split               TEXT,
  ancho_px            INTEGER,
  alto_px             INTEGER,
  resolucion          TEXT,
  sexo                TEXT,
  edad                INTEGER,
  grupo_edad          TEXT,
  nivel_listesis      TEXT,
  formato             TEXT,
  canales             INTEGER,
  profundidad_bits    INTEGER,
  tamano_kb           REAL,
  vista               TEXT,
  orientacion         TEXT,
  anotada             INTEGER,
  vertebras_anotadas  INTEGER,
  completa            INTEGER,
  dataset_key         INTEGER REFERENCES dim_dataset(dataset_key),
  diagnostico_key     INTEGER REFERENCES dim_diagnostico(diagnostico_key)
);
-- HECHO 1. Una fila = una vértebra anotada en una imagen. Medidas atómicas de forma, tamaño relativo,
-- posición y calidad; en cajas de NHANES las métricas de forma quedan NULL.
CREATE TABLE fact_vertebra_anotada (
  imagen_key      INTEGER REFERENCES dim_imagen(imagen_key),
  vertebra_key    INTEGER REFERENCES dim_vertebra(vertebra_key),
  area_norm       REAL,
  alto_norm       REAL,
  aspecto         REAL,
  relleno         REAL,
  cy_rel          REAL,
  inclinacion     REAL,
  excentricidad   REAL,
  circularidad    REAL,
  solidez         REAL,
  hu1             REAL,
  hu2             REAL,
  intensidad_media REAL,
  contraste       REAL,
  es_atipico      INTEGER,
  orden_coherente INTEGER,
  motivo_atipico  TEXT,
  geometria       TEXT,
  PRIMARY KEY (imagen_key, vertebra_key)
);
-- dim_segmento: par de vértebras consecutivas (L1-L2 ... L4-L5), normalizado hacia dim_vertebra.
CREATE TABLE dim_segmento (
  segmento_key     INTEGER PRIMARY KEY,
  nombre           TEXT,
  vertebra_sup_key INTEGER REFERENCES dim_vertebra(vertebra_key),
  vertebra_inf_key INTEGER REFERENCES dim_vertebra(vertebra_key)
);
-- HECHO 2. Una fila = un segmento intervertebral en una imagen (medidas que pertenecen al PAR, no a una vértebra).
CREATE TABLE fact_segmento (
  imagen_key         INTEGER REFERENCES dim_imagen(imagen_key),
  segmento_key       INTEGER REFERENCES dim_segmento(segmento_key),
  delta_inclinacion  REAL,
  desplazamiento_rel REAL,
  separacion_rel     REAL,
  PRIMARY KEY (imagen_key, segmento_key)
);
