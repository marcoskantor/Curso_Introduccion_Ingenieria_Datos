-- Proyecto Final: base transaccional spine_oltp.db (3FN)
-- Generado a partir del cuaderno; lo ejecuta src/almacen.py.

-- Fuente del dato (2 filas): nombre, licencia y SHA-256 del zip crudo que se descargó.
CREATE TABLE dataset (
  dataset_id INTEGER PRIMARY KEY,
  nombre     TEXT NOT NULL,
  fuente     TEXT NOT NULL,
  version    INTEGER NOT NULL,
  licencia   TEXT NOT NULL,
  sha256     TEXT NOT NULL
);
-- Región anatómica (hoy sólo 'lumbar'); extender a cervical/torácica es agregar filas.
CREATE TABLE region (
  region_id INTEGER PRIMARY KEY,
  nombre    TEXT NOT NULL
);
-- Catálogo de vértebras L1..L5 con su orden craneocaudal (1 = más craneal).
CREATE TABLE vertebra (
  vertebra_id        INTEGER PRIMARY KEY,
  codigo             TEXT NOT NULL,
  orden_craneocaudal INTEGER NOT NULL,
  region_id          INTEGER NOT NULL REFERENCES region(region_id)
);
-- Diagnóstico clínico extraído del nombre de archivo (sólo Lumbar Spine).
CREATE TABLE diagnostico (
  diagnostico_id INTEGER PRIMARY KEY,
  nombre         TEXT NOT NULL
);
-- Una radiografía. Atributos que dependen sólo de la imagen: resolución, sexo, edad, vista, formato de píxel.
-- sexo, edad y diagnóstico_id pueden ser NULL (NHANES no trae metadatos clínicos).
CREATE TABLE imagen (
  imagen_id      INTEGER PRIMARY KEY,
  dataset_id     INTEGER NOT NULL REFERENCES dataset(dataset_id),
  diagnostico_id INTEGER REFERENCES diagnostico(diagnostico_id),
  archivo        TEXT NOT NULL,
  split          TEXT NOT NULL CHECK (split IN ('train', 'valid', 'test')),
  ancho_px       INTEGER NOT NULL,
  alto_px        INTEGER NOT NULL,
  anotada        INTEGER NOT NULL CHECK (anotada IN (0, 1)),
  sexo           TEXT CHECK (sexo IN ('M', 'F')),
  edad           INTEGER CHECK (edad BETWEEN 0 AND 120),
  nivel_listesis TEXT,
  formato        TEXT,
  canales        INTEGER,
  profundidad_bits INTEGER,
  tamano_kb      REAL,
  vista          TEXT NOT NULL CHECK (vista IN ('frente', 'perfil')),
  orientacion    TEXT CHECK (orientacion IN ('vertical', 'invertida', 'girada 90°'))
);
-- Una vértebra anotada en una imagen (grano). Guarda sólo lo que depende del par (imagen, vértebra):
-- marcas de calidad y el tipo de geometría ('poligono' en Lumbar Spine, 'caja' en NHANES).
CREATE TABLE anotacion (
  imagen_id       INTEGER NOT NULL REFERENCES imagen(imagen_id),
  vertebra_id     INTEGER NOT NULL REFERENCES vertebra(vertebra_id),
  es_atipico      INTEGER NOT NULL CHECK (es_atipico IN (0, 1)),
  orden_coherente INTEGER NOT NULL CHECK (orden_coherente IN (0, 1)),
  motivo_atipico  TEXT,
  geometria       TEXT NOT NULL CHECK (geometria IN ('poligono', 'caja')),
  PRIMARY KEY (imagen_id, vertebra_id)
);
-- Un vértice del contorno de una anotación (1FN: el polígono es un grupo repetitivo, una fila por vértice).
CREATE TABLE vertice (
  imagen_id   INTEGER NOT NULL,
  vertebra_id INTEGER NOT NULL,
  orden       INTEGER NOT NULL,
  x_px        REAL NOT NULL,
  y_px        REAL NOT NULL,
  PRIMARY KEY (imagen_id, vertebra_id, orden),
  FOREIGN KEY (imagen_id, vertebra_id) REFERENCES anotacion(imagen_id, vertebra_id)
);
