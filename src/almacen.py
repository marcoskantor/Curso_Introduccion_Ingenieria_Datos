"""Carga de la base transaccional (spine_oltp.db, 3FN) y del almacén (spine_dw.db).

El DDL está en sql/oltp.sql y sql/dw.sql; la carga del almacén por SQL, en sql/dw_carga.sql. El almacén se carga
SÓLO desde la base transaccional: las dimensiones y fact_imagen por SQL (ATTACH) y los hechos de vértebra y de
segmento recalculando las medidas desde los vértices.
"""
import sqlite3
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd

from extraccion import area_poligono
from forma import descriptores, segmentos

SQL = Path(__file__).resolve().parent.parent / "sql"


def _nulo(v):
    return None if pd.isna(v) else v


def _int(v):
    return None if pd.isna(v) else int(v)


def crear_oltp(db: Path, imagenes, img2, anotaciones, anot2, vertices, vert2, clases, sha_ls, sha_nh):
    """Crea y carga la base transaccional. Devuelve la conexión.

    Grano de `anotacion`: una vértebra anotada en una imagen (PK compuesta imagen_id + vertebra_id).
    Grano de `vertice`: un vértice de ese contorno (PK compuesta imagen_id + vertebra_id + orden).
    No se guardan derivados (caja, área, momentos): se calculan desde `vertice` al cargar el almacén.
    """
    db.unlink(missing_ok=True)
    con = sqlite3.connect(db)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript((SQL / "oltp.sql").read_text(encoding="utf-8"))

    con.execute("INSERT INTO dataset VALUES (1, 'lumbar-spine-vpxwf', 'Roboflow Universe / rp-team', 1, 'CC BY 4.0', ?, "
                "'poligono')", (sha_ls,))
    con.execute("INSERT INTO dataset VALUES (2, 'nhanes-l1-l5', 'Roboflow Universe / main-kybbe (NHANES)', 1, 'CC BY 4.0', ?, "
                "'caja')", (sha_nh,))
    con.execute("INSERT INTO region VALUES (1, 'lumbar')")
    con.executemany("INSERT INTO vertebra VALUES (?, ?, ?, 1)", [(i, c, i + 1) for i, c in enumerate(clases)])

    diagnosticos = sorted(imagenes["diagnostico"].dropna().astype(str).unique())
    id_diag = {d: i + 1 for i, d in enumerate(diagnosticos)}
    con.executemany("INSERT INTO diagnostico VALUES (?, ?)", [(i, d) for d, i in id_diag.items()])

    imagenes = imagenes.reset_index(drop=True)
    imagenes["imagen_id"] = imagenes.index + 1
    imagenes["dataset_id"] = 1
    img2 = img2.reset_index(drop=True)
    img2["imagen_id"] = img2.index + len(imagenes) + 1
    img2["dataset_id"] = 2
    filas_img = [(int(r.imagen_id), int(r.dataset_id), id_diag.get(str(r.diagnostico)) if pd.notna(r.diagnostico) else None,
                  str(r.archivo), str(r.split), int(r.ancho_px), int(r.alto_px), int(r.anotada),
                  _nulo(r.sexo), _int(r.edad), _nulo(r.nivel_listesis),
                  _nulo(r.formato), _int(r.canales), _int(r.profundidad_bits),
                  None if pd.isna(r.tamano_kb) else float(r.tamano_kb), str(r.vista), _nulo(r.orientacion))
                 for t in (imagenes, img2) for r in t.itertuples()]
    con.executemany("INSERT INTO imagen VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", filas_img)

    id_img = dict(zip(imagenes.archivo.astype(str), imagenes.imagen_id))
    id_img.update(dict(zip(img2.archivo.astype(str), img2.imagen_id)))
    # es_atipico: en las cajas de NHANES llega NULL (no se evalúa la forma de una caja): no se convierte en 0
    cols = ["imagen_id", "vertebra_id", "es_atipico", "orden_coherente", "motivo_atipico"]
    for t in (anotaciones, anot2):
        t["imagen_id"] = t.archivo.astype(str).map(id_img)
        t["vertebra_id"] = t.orden.astype(int)
        filas = [tuple(None if pd.isna(v) else (int(v) if isinstance(v, (np.integer, np.floating)) else v) for v in r)
                 for r in t[cols].itertuples(index=False)]
        con.executemany("INSERT INTO anotacion VALUES (?, ?, ?, ?, ?)", filas)

    for verts, t in ((vertices, anotaciones), (vert2, anot2)):
        v = verts.astype({"archivo": str}).merge(
            t[["archivo", "linea", "imagen_id", "vertebra_id"]].astype({"archivo": str}), on=["archivo", "linea"])
        con.executemany("INSERT INTO vertice VALUES (?, ?, ?, ?, ?)",
                        v[["imagen_id", "vertebra_id", "orden", "x_px", "y_px"]].astype(float).astype(object)
                        .itertuples(index=False))
    con.commit()
    return con


def crear_dw(dw_db: Path, oltp_db: Path, clases: list, intensidad):
    """Crea y carga el almacén. Devuelve la conexión.

    fact_imagen:           grano = una radiografía, PK imagen_key (se carga por SQL en sql/dw_carga.sql).
    fact_vertebra_anotada: grano = una vértebra anotada en una imagen, PK (imagen_key, vertebra_key).
    fact_segmento:         grano = un segmento intervertebral en una imagen, PK (imagen_key, segmento_key).
    Las tres comparten dimensiones (dataset, diagnóstico, vista, …). Las medidas aditivas son conteos y marcas 0/1;
    los descriptores se guardan atómicos (sin promedios): SUM, COUNT y AVG se calculan al consultar.
    """
    dw_db.unlink(missing_ok=True)
    dw = sqlite3.connect(dw_db)
    dw.execute("PRAGMA foreign_keys = ON")
    dw.executescript((SQL / "dw.sql").read_text(encoding="utf-8"))
    dw.execute("ATTACH DATABASE ? AS oltp", (str(oltp_db),))
    dw.executescript((SQL / "dw_carga.sql").read_text(encoding="utf-8").replace("{n_clases}", str(len(clases))))

    geo = pd.read_sql("""
    SELECT v.imagen_id, v.vertebra_id, v.orden, v.x_px, v.y_px, i.ancho_px, i.alto_px, i.archivo,
           a.es_atipico, a.orden_coherente, a.motivo_atipico, d.geometria
    FROM oltp.vertice v
    JOIN oltp.anotacion a USING (imagen_id, vertebra_id)
    JOIN oltp.imagen i    USING (imagen_id)
    JOIN oltp.dataset d   USING (dataset_id)
    ORDER BY v.imagen_id, v.vertebra_id, v.orden
    """, dw)
    # dimensiones compartidas de cada imagen (ya cargadas en fact_imagen): se repiten en los otros dos hechos
    dims = pd.read_sql("SELECT imagen_key, dataset_key, diagnostico_key, vista_key, orientacion_key FROM fact_imagen", dw)

    forma_cols = ["inclinacion", "excentricidad", "circularidad", "solidez", "hu1", "hu2"]

    def metricas(g):
        """Medidas de UNA fila de fact_vertebra_anotada a partir de los vértices de la anotación.
        En las cajas de NHANES la forma, la inclinación y la intensidad no miden la vértebra: quedan NULL."""
        x, y = g.x_px.to_numpy(), g.y_px.to_numpy()
        H = g.alto_px.iat[0]
        w, h = x.max() - x.min(), y.max() - y.min()
        area = area_poligono(x, y)
        d = descriptores(x, y)
        poligono = g.geometria.iat[0] == "poligono"
        return pd.Series({"area": area, "alto": h, "aspecto": w / h, "relleno": area / (w * h) if poligono else np.nan,
                          "cy_rel": y.mean() / H,
                          **{k: (d[k] if poligono else np.nan) for k in forma_cols},
                          **(intensidad(g.archivo.iat[0], x, y) if poligono else {"intensidad_media": np.nan, "contraste": np.nan}),
                          "geometria": g.geometria.iat[0],
                          "es_atipico": g.es_atipico.iat[0], "orden_coherente": g.orden_coherente.iat[0],
                          "motivo_atipico": g.motivo_atipico.iat[0],
                          # auxiliares para el grano "segmento" (no se guardan en este hecho)
                          "orden": g.name[1], "cx_m": d["cx_m"], "x_min": x.min(), "x_max": x.max(),
                          "y_min": y.min(), "y_max": y.max()})

    hechos = geo.groupby(["imagen_id", "vertebra_id"]).apply(metricas, include_groups=False).reset_index()
    hechos["area_norm"] = hechos["area"] / hechos.groupby("imagen_id")["area"].transform("median")
    hechos["alto_norm"] = hechos["alto"] / hechos.groupby("imagen_id")["alto"].transform("median")

    seg = segmentos(hechos, clases, clave="imagen_id")
    seg = (seg.rename(columns={"imagen_id": "imagen_key"}).assign(segmento_key=lambda d: d["orden_inf"], segmentos=1)
           .merge(dims.drop(columns="orientacion_key"), on="imagen_key"))
    columnas_seg = [c[1] for c in dw.execute("PRAGMA table_info(fact_segmento)")]
    seg[columnas_seg].to_sql("fact_segmento", dw, if_exists="append", index=False)

    hechos = (hechos.rename(columns={"imagen_id": "imagen_key", "vertebra_id": "vertebra_key"})
              .assign(anotaciones=1).merge(dims, on="imagen_key"))
    hechos["es_atipico"] = hechos["es_atipico"].astype("Int8")           # 0/1 y NULL (no evaluado), nunca 0 por defecto
    columnas = [c[1] for c in dw.execute("PRAGMA table_info(fact_vertebra_anotada)")]
    hechos[columnas].to_sql("fact_vertebra_anotada", dw, if_exists="append", index=False)
    dw.commit()
    dw.execute("DETACH DATABASE oltp")
    return dw


def esquema(con) -> pd.DataFrame:
    """Resumen del esquema: por tabla, su clave primaria, sus claves foráneas y su cantidad de filas."""
    filas = []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid"):
        info = con.execute(f"PRAGMA table_info({t})").fetchall()
        pk = [c[1] for c in sorted(info, key=lambda c: c[5]) if c[5]]
        fk = sorted({f"{r[3]}→{r[2]}" for r in con.execute(f"PRAGMA foreign_key_list({t})")})
        filas.append({"tabla": t, "PK": ", ".join(pk), "FK": ", ".join(fk) or "—",
                      "filas": con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]})
    return pd.DataFrame(filas).set_index("tabla")


def resumen(con) -> str:
    """Filas por tabla y claves primarias compuestas, en pocos renglones (versión compacta de `esquema`)."""
    filas, compuestas = [], []
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY rowid"):
        pk = [c[1] for c in sorted(con.execute(f"PRAGMA table_info({t})"), key=lambda c: c[5]) if c[5]]
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        filas.append(f"{t} {n:,}".replace(",", "."))
        if len(pk) > 1:
            compuestas.append(f"{t} ({', '.join(pk)})")
    envolver = lambda t: textwrap.fill(t, 90, break_long_words=False, break_on_hyphens=False)
    return envolver("Filas: " + " · ".join(filas)) + "\n" + envolver("PK compuestas: " + " · ".join(compuestas))


def nulos(con) -> pd.DataFrame:
    """Auditoría de nulos de la base transaccional: cuántos NULL tiene cada columna, por fuente.

    Sólo muestra las columnas con algún nulo y agrupa las de una misma tabla con los mismos conteos. El tipo
    (estructural o perdido) y la decisión de cada uno están en la sección 3.1 del cuaderno; esta tabla verifica que
    los nulos estén donde se esperaba y en ningún otro lado.
    """
    filas = []
    for tabla, desde in (("imagen", "imagen t"), ("anotacion", "anotacion t JOIN imagen i USING (imagen_id)")):
        ds = "t.dataset_id" if tabla == "imagen" else "i.dataset_id"
        grupos = {}
        # motivo_atipico no se audita: es texto explicativo, NULL por definición cuando la anotación no es atípica
        for (col,) in [(c[1],) for c in con.execute(f"PRAGMA table_info({tabla})") if c[1] != "motivo_atipico"]:
            n = dict(con.execute(f"SELECT {ds}, SUM(t.{col} IS NULL) FROM {desde} GROUP BY {ds}").fetchall())
            if any(n.values()):
                grupos.setdefault((n.get(1, 0), n.get(2, 0)), []).append(col)
        filas += [{"atributo": f"{tabla}: {', '.join(cols)}", "Lumbar Spine": ls, "NHANES": nh}
                  for (ls, nh), cols in grupos.items()]
    return pd.DataFrame(filas).set_index("atributo")
