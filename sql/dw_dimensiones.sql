-- Proyecto Final: carga de las dimensiones del almacén desde la base transaccional (ATTACH oltp)
-- Generado a partir del cuaderno; lo ejecuta src/almacen.py.

INSERT INTO dim_dataset  SELECT dataset_id, nombre, fuente, version, licencia FROM oltp.dataset;
INSERT INTO dim_region   SELECT region_id, nombre FROM oltp.region;
INSERT INTO dim_vertebra SELECT vertebra_id, codigo, orden_craneocaudal, region_id FROM oltp.vertebra;
INSERT INTO dim_diagnostico SELECT diagnostico_id, nombre FROM oltp.diagnostico;
INSERT INTO dim_diagnostico VALUES (0, 'sin dato');      -- miembro "desconocido": evita claves nulas en la dimensión
INSERT INTO dim_segmento SELECT s.vertebra_id + 1, s.codigo || '-' || i.codigo, s.vertebra_id, i.vertebra_id
FROM oltp.vertebra s JOIN oltp.vertebra i ON i.vertebra_id = s.vertebra_id + 1;
INSERT INTO dim_imagen
SELECT i.imagen_id, i.archivo, i.split, i.ancho_px, i.alto_px,
       i.ancho_px || 'x' || i.alto_px,
       COALESCE(i.sexo, 'sin dato'),
       i.edad,
       CASE WHEN i.edad IS NULL THEN 'sin dato' WHEN i.edad < 18 THEN '<18' WHEN i.edad < 40 THEN '18-39'
            WHEN i.edad < 65 THEN '40-64' ELSE '65+' END,
       i.nivel_listesis,
       i.formato, i.canales, i.profundidad_bits, i.tamano_kb, i.vista, COALESCE(i.orientacion, 'sin dato'),
       i.anotada,
       COUNT(a.vertebra_id),
       CASE WHEN COUNT(a.vertebra_id) = {n_clases} THEN 1 ELSE 0 END,
       i.dataset_id,
       COALESCE(i.diagnostico_id, 0)
FROM oltp.imagen i LEFT JOIN oltp.anotacion a ON a.imagen_id = i.imagen_id
GROUP BY i.imagen_id;
