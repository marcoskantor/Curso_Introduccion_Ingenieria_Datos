-- Proyecto Final: carga del almacén desde la base transaccional (ATTACH oltp).
-- Dimensiones y fact_imagen se cargan por SQL; fact_vertebra_anotada y fact_segmento, en src/almacen.py
-- (sus medidas se recalculan desde los vértices). Generado a partir del cuaderno; lo ejecuta src/almacen.py.

-- Dimensiones con miembro 'sin dato' (clave 0): un faltante es una categoría visible, nunca una clave nula ni un 0.
INSERT INTO dim_dataset     SELECT dataset_id, nombre, fuente, version, licencia, geometria FROM oltp.dataset;
INSERT INTO dim_diagnostico VALUES (0, 'sin dato');
INSERT INTO dim_diagnostico SELECT diagnostico_id, nombre FROM oltp.diagnostico;
INSERT INTO dim_sexo        VALUES (0, 'sin dato'), (1, 'F'), (2, 'M');
INSERT INTO dim_grupo_edad  VALUES (0, 'sin dato', NULL, NULL), (1, '<18', 0, 17), (2, '18-39', 18, 39),
                                   (3, '40-64', 40, 64), (4, '65+', 65, 120);
INSERT INTO dim_vista       VALUES (1, 'frente'), (2, 'perfil');
INSERT INTO dim_orientacion VALUES (0, 'sin dato'), (1, 'vertical'), (2, 'girada 90°'), (3, 'invertida');
INSERT INTO dim_region      SELECT region_id, nombre FROM oltp.region;
INSERT INTO dim_vertebra    SELECT vertebra_id, codigo, orden_craneocaudal, region_id FROM oltp.vertebra;
INSERT INTO dim_segmento    SELECT i.vertebra_id, s.codigo || '-' || i.codigo, s.vertebra_id, i.vertebra_id
                            FROM oltp.vertebra s JOIN oltp.vertebra i ON i.vertebra_id = s.vertebra_id + 1;
INSERT INTO dim_imagen
SELECT imagen_id, archivo, split, ancho_px, alto_px, ancho_px || 'x' || alto_px,
       formato, canales, profundidad_bits, tamano_kb, nivel_listesis
FROM oltp.imagen;

-- fact_imagen: una fila por radiografía; la completitud se cuenta desde las anotaciones de la imagen.
INSERT INTO fact_imagen
SELECT i.imagen_id, i.dataset_id, COALESCE(i.diagnostico_id, 0), sx.sexo_key, ge.grupo_edad_key, vi.vista_key,
       ori.orientacion_key,
       1, i.anotada, COUNT(a.vertebra_id), CASE WHEN COUNT(a.vertebra_id) = {n_clases} THEN 1 ELSE 0 END, i.edad
FROM oltp.imagen i
LEFT JOIN oltp.anotacion a ON a.imagen_id = i.imagen_id
JOIN dim_sexo sx         ON sx.sexo = COALESCE(i.sexo, 'sin dato')
JOIN dim_grupo_edad ge   ON (i.edad IS NULL AND ge.grupo_edad_key = 0) OR i.edad BETWEEN ge.edad_min AND ge.edad_max
JOIN dim_vista vi        ON vi.vista = i.vista
JOIN dim_orientacion ori ON ori.orientacion = COALESCE(i.orientacion, 'sin dato')
GROUP BY i.imagen_id;
