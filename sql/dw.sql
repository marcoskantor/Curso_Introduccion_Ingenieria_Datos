-- Proyecto Final: almacén spine_dw.db
-- Constelación de tres tablas de hechos con dimensiones compartidas (conformadas); la jerarquía anatómica
-- región → vértebra → segmento está normalizada (copo de nieve). Generado a partir del cuaderno; lo ejecuta src/almacen.py.
--
-- Diseño a partir de las preguntas: cada pregunta es «¿cuántos … por …?». Lo que va después de «por» es una
-- DIMENSIÓN; lo que se cuenta o se suma es una MEDIDA. Las medidas aditivas (conteos y marcas 0/1) se suman con
-- SUM; los descriptores geométricos no son aditivos: se guardan atómicos y se promedian (AVG = SUM / COUNT) o se
-- comparan al consultar. No se guardan promedios.
--
--   P1 ¿Cuántas imágenes completas L1–L5 hay por fuente? ¿Cuántas anotaciones por vértebra?
--        → fact_imagen.completa, fact_vertebra_anotada.anotaciones   por dim_dataset, dim_vertebra
--   P2 ¿Cuántas anotaciones tienen forma o tamaño atípico, por vértebra?
--        → SUM(es_atipico) (+ area_norm, aspecto, relleno)             por dim_vertebra
--   P3 ¿Cuántas anotaciones rompen el orden L1→L5? ¿Cuántas imágenes hay por orientación?
--        → SUM(1 - orden_coherente), fact_imagen.imagenes              por dim_vertebra, dim_dataset, dim_orientacion
--   P4 ¿Cuántas imágenes (y completas) hay por diagnóstico, sexo y grupo de edad?
--        → fact_imagen.imagenes, completa                              por dim_diagnostico, dim_sexo, dim_grupo_edad
--   P5 ¿La inclinación distingue las patologías?  (Cobb = MAX − MIN de la inclinación por imagen, al consultar)
--        → inclinacion, delta_inclinacion, desplazamiento_rel          por dim_diagnostico, dim_vista, dim_segmento
--
-- Miembro 'sin dato' (clave 0) en las dimensiones cuyo atributo puede faltar: un hecho nunca tiene una clave nula
-- y el faltante queda visible como una categoría más (no se confunde con un cero).

-- ================================================================ DIMENSIONES
-- dim_dataset: de qué fuente viene el dato y qué tipo de anotación trae.
CREATE TABLE dim_dataset (
  dataset_key INTEGER PRIMARY KEY,
  nombre      TEXT, fuente TEXT, version INTEGER, licencia TEXT,
  geometria   TEXT                          -- 'poligono' (Lumbar Spine) o 'caja' (NHANES)
);
-- dim_diagnostico: 0 = 'sin dato' (NHANES).
CREATE TABLE dim_diagnostico (
  diagnostico_key INTEGER PRIMARY KEY,
  nombre          TEXT
);
-- dim_sexo: 0 = 'sin dato'.
CREATE TABLE dim_sexo (
  sexo_key INTEGER PRIMARY KEY,
  sexo     TEXT
);
-- dim_grupo_edad: rangos de edad en años; 0 = 'sin dato'.
CREATE TABLE dim_grupo_edad (
  grupo_edad_key INTEGER PRIMARY KEY,
  grupo          TEXT,
  edad_min       INTEGER,
  edad_max       INTEGER
);
-- dim_vista: frente o perfil (separa P5: la inclinación de frente mide la escoliosis; de perfil, la lordosis).
CREATE TABLE dim_vista (
  vista_key INTEGER PRIMARY KEY,
  vista     TEXT
);
-- dim_orientacion: vertical, girada 90° o invertida; 0 = 'sin dato' (imagen sin anotaciones).
CREATE TABLE dim_orientacion (
  orientacion_key INTEGER PRIMARY KEY,
  orientacion     TEXT
);
-- dim_imagen: atributos descriptivos de la radiografía (para filtrar o bajar al detalle). No guarda medidas.
CREATE TABLE dim_imagen (
  imagen_key       INTEGER PRIMARY KEY,
  archivo          TEXT,
  split            TEXT,
  ancho_px         INTEGER,
  alto_px          INTEGER,
  resolucion       TEXT,
  formato          TEXT,
  canales          INTEGER,
  profundidad_bits INTEGER,
  tamano_kb        REAL,
  nivel_listesis   TEXT
);
-- Jerarquía anatómica normalizada (copo de nieve): región → vértebra → segmento.
CREATE TABLE dim_region (
  region_key INTEGER PRIMARY KEY,
  nombre     TEXT
);
CREATE TABLE dim_vertebra (
  vertebra_key       INTEGER PRIMARY KEY,
  codigo             TEXT,
  orden_craneocaudal INTEGER,
  region_key         INTEGER REFERENCES dim_region(region_key)
);
-- dim_segmento: par de vértebras consecutivas (L1-L2 … L4-L5).
CREATE TABLE dim_segmento (
  segmento_key     INTEGER PRIMARY KEY,
  nombre           TEXT,
  vertebra_sup_key INTEGER REFERENCES dim_vertebra(vertebra_key),
  vertebra_inf_key INTEGER REFERENCES dim_vertebra(vertebra_key)
);

-- ================================================================ HECHOS
-- HECHO 1. Grano: una radiografía. Responde P1 (cobertura), P3 (orientación) y P4 (representatividad).
-- Todas las medidas son aditivas: SUM(imagenes) = cuántas imágenes, SUM(completa) = cuántas completas.
CREATE TABLE fact_imagen (
  imagen_key         INTEGER PRIMARY KEY REFERENCES dim_imagen(imagen_key),
  dataset_key        INTEGER NOT NULL REFERENCES dim_dataset(dataset_key),
  diagnostico_key    INTEGER NOT NULL REFERENCES dim_diagnostico(diagnostico_key),
  sexo_key           INTEGER NOT NULL REFERENCES dim_sexo(sexo_key),
  grupo_edad_key     INTEGER NOT NULL REFERENCES dim_grupo_edad(grupo_edad_key),
  vista_key          INTEGER NOT NULL REFERENCES dim_vista(vista_key),
  orientacion_key    INTEGER NOT NULL REFERENCES dim_orientacion(orientacion_key),
  imagenes           INTEGER NOT NULL,      -- siempre 1: SUM = cantidad de imágenes
  anotada            INTEGER NOT NULL,      -- 0/1: SUM = imágenes con anotaciones
  vertebras_anotadas INTEGER NOT NULL,      -- 0…5: SUM = cantidad de anotaciones
  completa           INTEGER NOT NULL,      -- 0/1 (las 5 vértebras): SUM = imágenes completas
  edad               INTEGER                -- años; NULL = sin dato. Edad media = SUM(edad) / COUNT(edad)
);
-- HECHO 2. Grano: una vértebra anotada en una imagen. Responde P1 (balance), P2 (calidad) y P3 (orden).
-- Aditivas: anotaciones, es_atipico, orden_coherente. No aditivas (se promedian): descriptores geométricos.
-- En las cajas de NHANES la forma, la inclinación, la intensidad y es_atipico quedan NULL (no aplica).
CREATE TABLE fact_vertebra_anotada (
  imagen_key      INTEGER REFERENCES dim_imagen(imagen_key),
  vertebra_key    INTEGER REFERENCES dim_vertebra(vertebra_key),
  dataset_key     INTEGER NOT NULL REFERENCES dim_dataset(dataset_key),
  diagnostico_key INTEGER NOT NULL REFERENCES dim_diagnostico(diagnostico_key),
  vista_key       INTEGER NOT NULL REFERENCES dim_vista(vista_key),
  orientacion_key INTEGER NOT NULL REFERENCES dim_orientacion(orientacion_key),
  anotaciones     INTEGER NOT NULL,         -- siempre 1: SUM = cantidad de anotaciones
  es_atipico      INTEGER,                  -- 0/1, NULL = no evaluado: SUM = atípicas
  orden_coherente INTEGER NOT NULL,         -- 0/1: SUM(1 - orden_coherente) = rompen el orden
  area_norm       REAL,                     -- área / mediana de las vértebras de la misma imagen
  alto_norm       REAL,                     -- alto / mediana de las vértebras de la misma imagen
  aspecto         REAL,                     -- ancho / alto de la caja envolvente
  relleno         REAL,                     -- área del polígono / área de la caja
  cy_rel          REAL,                     -- centroide vertical / alto de la imagen (0 = arriba)
  inclinacion     REAL,                     -- eje principal por momentos de OpenCV (°)
  excentricidad   REAL,
  circularidad    REAL,
  solidez         REAL,
  hu1             REAL,
  hu2             REAL,
  intensidad_media REAL,                    -- gris medio dentro del polígono
  contraste       REAL,                     -- desvío del gris dentro del polígono
  motivo_atipico  TEXT,                     -- atributo degenerado: regla que marcó la anotación
  PRIMARY KEY (imagen_key, vertebra_key)
);
-- HECHO 3. Grano: un segmento intervertebral (par de vértebras consecutivas) en una imagen. Responde P5.
-- Medidas del PAR, no de una vértebra; no aditivas (se promedian o se comparan).
CREATE TABLE fact_segmento (
  imagen_key         INTEGER REFERENCES dim_imagen(imagen_key),
  segmento_key       INTEGER REFERENCES dim_segmento(segmento_key),
  dataset_key        INTEGER NOT NULL REFERENCES dim_dataset(dataset_key),
  diagnostico_key    INTEGER NOT NULL REFERENCES dim_diagnostico(diagnostico_key),
  vista_key          INTEGER NOT NULL REFERENCES dim_vista(vista_key),
  segmentos          INTEGER NOT NULL,      -- siempre 1: SUM = cantidad de segmentos
  delta_inclinacion  REAL,                  -- inclinación(inferior) − inclinación(superior), °; NULL en cajas
  desplazamiento_rel REAL,                  -- corrimiento horizontal / ancho medio de las dos vértebras
  separacion_rel     REAL,                  -- espacio entre las dos vértebras / alto medio
  PRIMARY KEY (imagen_key, segmento_key)
);
