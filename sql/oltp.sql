-- Proyecto Final: base transaccional spine_oltp.db (3FN)
-- Generado a partir del cuaderno; lo ejecuta src/almacen.py.
--
-- Relaciones (cardinalidad y clave que la implementa):
--   dataset     1 ── N imagen     imagen.dataset_id     → dataset.dataset_id
--   diagnostico 1 ── N imagen     imagen.diagnostico_id → diagnostico.diagnostico_id (NULL si la fuente no trae diagnóstico)
--   region      1 ── N vertebra   vertebra.region_id    → region.region_id
--   imagen      N ── M vertebra   se resuelve con la entidad asociativa anotacion, PK (imagen_id, vertebra_id):
--                                 imagen 1 ── N anotacion   y   vertebra 1 ── N anotacion
--   anotacion   1 ── N vertice    vertice.(imagen_id, vertebra_id) → anotacion.(imagen_id, vertebra_id)
--
-- En cada columna: qué es y de qué variable de la fuente sale.
-- Nulos: «estructural» = el atributo no aplica o la fuente no lo registra; «perdido» = debería existir y falta.

-- Fuente del dato (2 filas).
CREATE TABLE dataset (
  dataset_id INTEGER PRIMARY KEY,            -- clave sustituta (1 = Lumbar Spine, 2 = NHANES)
  nombre     TEXT NOT NULL,                  -- proyecto de Roboflow Universe
  fuente     TEXT NOT NULL,                  -- espacio de trabajo que lo publica
  version    INTEGER NOT NULL,               -- versión del export
  licencia   TEXT NOT NULL,                  -- CC BY 4.0 en las dos
  sha256     TEXT NOT NULL,                  -- huella del zip crudo descargado (verificación de integridad)
  geometria  TEXT NOT NULL CHECK (geometria IN ('poligono', 'caja'))
                                             -- tipo de anotación de la fuente: depende sólo del dataset
);
-- Región anatómica (hoy sólo 'lumbar'); extender a cervical/torácica es agregar filas.
CREATE TABLE region (
  region_id INTEGER PRIMARY KEY,
  nombre    TEXT NOT NULL
);
-- Catálogo de vértebras. Fuente: lista `names` de data.yaml (Lumbar Spine) y `categories` del COCO (NHANES).
CREATE TABLE vertebra (
  vertebra_id        INTEGER PRIMARY KEY,    -- = índice de clase de YOLO (0 = L1 … 4 = L5)
  codigo             TEXT NOT NULL,          -- L1 … L5
  orden_craneocaudal INTEGER NOT NULL,       -- 1 = más craneal; regla de dominio para el control de orden
  region_id          INTEGER NOT NULL REFERENCES region(region_id)
);
-- Diagnóstico clínico. Fuente: código del nombre de archivo de Lumbar Spine (AIS, Olisthesis, N, S).
CREATE TABLE diagnostico (
  diagnostico_id INTEGER PRIMARY KEY,
  nombre         TEXT NOT NULL
);
-- Una radiografía. Atributos que dependen sólo de la imagen.
CREATE TABLE imagen (
  imagen_id      INTEGER PRIMARY KEY,
  dataset_id     INTEGER NOT NULL REFERENCES dataset(dataset_id),
  diagnostico_id INTEGER REFERENCES diagnostico(diagnostico_id),
                                             -- NULL estructural en NHANES (la encuesta no lo publica)
  archivo        TEXT NOT NULL,              -- nombre del archivo de imagen (NHANES: nhanes_<split>_<id COCO>)
  split          TEXT NOT NULL CHECK (split IN ('train', 'valid', 'test')),  -- carpeta del export
  ancho_px       INTEGER NOT NULL,           -- cabecera de la imagen (NHANES: campo width del COCO)
  alto_px        INTEGER NOT NULL,           -- cabecera de la imagen (NHANES: campo height del COCO)
  anotada        INTEGER NOT NULL CHECK (anotada IN (0, 1)),
                                             -- 1 si su archivo de etiquetas tiene al menos una línea válida
  sexo           TEXT CHECK (sexo IN ('M', 'F')),
                                             -- token M/F del nombre de archivo; NULL perdido (1 archivo trae «N»)
                                             -- o estructural (NHANES)
  edad           INTEGER CHECK (edad BETWEEN 0 AND 120),
                                             -- token numérico del nombre de archivo (años); NULL estructural en NHANES
  nivel_listesis TEXT,                       -- token L4-5 / L5-S1 del nombre; NULL estructural si no hay listesis
  formato        TEXT,                       -- extensión del archivo; NULL estructural en NHANES (sin píxeles)
  canales        INTEGER,                    -- canales del arreglo leído con OpenCV; NULL estructural en NHANES
  profundidad_bits INTEGER,                  -- bits por canal; NULL estructural en NHANES
  tamano_kb      REAL,                       -- tamaño del archivo; NULL estructural en NHANES
  vista          TEXT NOT NULL CHECK (vista IN ('frente', 'perfil')),
                                             -- inferida: perfil en espondilolistesis y en NHANES, frente en el resto
  orientacion    TEXT CHECK (orientacion IN ('vertical', 'invertida', 'girada 90°'))
                                             -- derivada de los centroides; NULL si la imagen no tiene anotaciones
);
-- Entidad asociativa: resuelve la relación N:M imagen–vértebra. Una fila = una vértebra anotada en una imagen.
-- Fuente: una línea del .txt YOLOv8 (`clase x1 y1 … xn yn`) o una anotación COCO (`category_id`, `bbox`).
-- Sólo guarda lo que depende del PAR (imagen, vértebra): las marcas de calidad.
CREATE TABLE anotacion (
  imagen_id       INTEGER NOT NULL REFERENCES imagen(imagen_id),
  vertebra_id     INTEGER NOT NULL REFERENCES vertebra(vertebra_id),
  es_atipico      INTEGER CHECK (es_atipico IN (0, 1)),
                                             -- forma o tamaño atípico (Tukey / Mahalanobis); NULL estructural en
                                             -- las cajas de NHANES: una caja no tiene forma (no evaluado ≠ 0)
  orden_coherente INTEGER NOT NULL CHECK (orden_coherente IN (0, 1)),
                                             -- 1 si respeta el orden L1→L5 a lo largo de la columna
  motivo_atipico  TEXT,                      -- regla que la marcó; NULL si no es atípica
  PRIMARY KEY (imagen_id, vertebra_id)
);
-- Un vértice del contorno (1FN: el polígono es un grupo repetitivo de largo variable, una fila por vértice).
-- Fuente: pares (x, y) normalizados de la línea YOLOv8, desnormalizados a píxeles; las cajas de NHANES
-- se guardan como 4 vértices (esquinas del bbox).
CREATE TABLE vertice (
  imagen_id   INTEGER NOT NULL,
  vertebra_id INTEGER NOT NULL,
  orden       INTEGER NOT NULL,              -- posición del vértice en el contorno (0, 1, 2, …)
  x_px        REAL NOT NULL,                 -- columna en píxeles (0 = borde izquierdo)
  y_px        REAL NOT NULL,                 -- fila en píxeles (0 = borde superior)
  PRIMARY KEY (imagen_id, vertebra_id, orden),
  FOREIGN KEY (imagen_id, vertebra_id) REFERENCES anotacion(imagen_id, vertebra_id)
);
