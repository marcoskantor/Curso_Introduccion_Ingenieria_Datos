"""Control de calidad del Proyecto Final: duplicados, inválidos geométricos, atípicos y coherencia anatómica.

Las decisiones (qué se descarta, qué se marca) están justificadas en las celdas Markdown del cuaderno.
"""
import numpy as np
import pandas as pd
from scipy import stats

VARS = ["area_norm", "aspecto", "relleno"]      # variables sin escala sobre las que se buscan atípicos


def deduplicar(t: pd.DataFrame, orden_final: list):
    """Grano esperado: una anotación por (imagen, vértebra). Si una vértebra aparece dos veces en una imagen,
    se conserva la de posición vertical relativa (cy_rel) más cercana a la mediana de esa vértebra.

    Devuelve (anotaciones sin duplicados, filas involucradas en duplicados, cantidad descartada).
    """
    mediana_cy = t.groupby("vertebra", observed=True)["cy_rel"].median()
    t = t.assign(dist_mediana=(t["cy_rel"] - t["vertebra"].map(mediana_cy).astype(float)).abs())
    dup = t.duplicated(["archivo", "vertebra"], keep=False)
    involucradas = t.loc[dup]
    antes = len(t)
    t = (t.sort_values("dist_mediana").drop_duplicates(["archivo", "vertebra"], keep="first")
         .sort_values(orden_final).reset_index(drop=True))
    return t, involucradas, antes - len(t)


def invalidos_geometricos(t: pd.DataFrame, tol: float = 0.02):
    """Polígonos que salen de la imagen más que `tol` de su tamaño o con área < 1 px²: se descartan.
    Los desbordes menores son redondeo del anotador y se recortan al borde."""
    tol_x, tol_y = tol * t["ancho_px"], tol * t["alto_px"]
    fuera = ((t.x_min < -tol_x) | (t.y_min < -tol_y) |
             (t.x_max > t.ancho_px + tol_x) | (t.y_max > t.alto_px + tol_y))
    degenerado = t["area_px"] < 1.0
    t = t[~(fuera | degenerado)].copy()
    t["x_min"] = t["x_min"].clip(lower=0); t["y_min"] = t["y_min"].clip(lower=0)
    t["x_max"] = np.minimum(t["x_max"], t["ancho_px"])
    t["y_max"] = np.minimum(t["y_max"], t["alto_px"])
    return t, int(fuera.sum()), int(degenerado.sum())


def variables_relativas(t: pd.DataFrame) -> pd.DataFrame:
    """Variables sin escala. area_rel depende del encuadre (sólo se usa para mostrar el problema);
    area_norm y alto_norm comparan cada vértebra con la mediana de SUS vecinas en la misma imagen."""
    caja_w = t.x_max - t.x_min
    caja_h = t.y_max - t.y_min
    # float antes de multiplicar: ancho*alto en int16 se desborda en las radiografías grandes
    t["area_rel"] = t.area_px / (t.ancho_px.astype(float) * t.alto_px.astype(float))
    t["area_norm"] = t.area_px / t.groupby("archivo", observed=True)["area_px"].transform("median")
    t["alto_norm"] = caja_h / caja_h.groupby(t["archivo"]).transform("median")
    t["aspecto"] = caja_w / caja_h
    t["relleno"] = t.area_px / (caja_w * caja_h)
    return t


def normalidad(t: pd.DataFrame, variables=VARS) -> pd.DataFrame:
    """p-valor de Shapiro-Wilk por vértebra y variable (n chico por grupo)."""
    filas = [(v, var, len(g), stats.shapiro(g[var]).pvalue)
             for v, g in t.groupby("vertebra", observed=True) for var in variables if len(g) >= 3]
    return pd.DataFrame(filas, columns=["vertebra", "variable", "n", "p_shapiro"])


def orientacion_y_orden(t: pd.DataFrame):
    """Orientación de cada imagen y orden de L1…L5 a lo largo del eje de la columna.

    rx, ry : cuánto se extienden los centroides en horizontal y en vertical; si ry >= rx el eje es vertical
             (imagen derecha o invertida), si no, la imagen está girada 90°.
    roto   : la vértebra que rompe la monotonía de L1->L5 a lo largo del eje (en cualquier sentido) y su vecina.
    """
    t = t.sort_values(["archivo", "orden"])
    rango = t.groupby("archivo").agg(rx=("cx", lambda v: v.max() - v.min()), ry=("cy", lambda v: v.max() - v.min()))
    eje = pd.Series(np.where(rango["ry"] >= rango["rx"], "cy", "cx"), index=rango.index)
    pos = np.where(t["archivo"].map(eje) == "cy", t["cy"], t["cx"])
    t = t.assign(_pos=pos)
    d = t.groupby("archivo")["_pos"].diff()
    sube = t.groupby("archivo")["_pos"].transform(lambda v: v.iloc[-1] >= v.iloc[0])
    roto = d.notna() & np.where(sube, d <= 0, d >= 0)
    roto = roto | roto.groupby(t["archivo"]).shift(-1, fill_value=False)
    primera_y = t.groupby("archivo")["cy"].first(); ultima_y = t.groupby("archivo")["cy"].last()
    orient = pd.Series(np.where(eje == "cx", "girada 90°", np.where(ultima_y >= primera_y, "vertical", "invertida")),
                       index=rango.index)
    return orient, roto.reindex(t.index).sort_index()


def procesar_nhanes(img2: pd.DataFrame, anot2: pd.DataFrame, clases: list):
    """Mismo control de dominio que Lumbar Spine, adaptado a cajas: clases inválidas, geometría inválida,
    duplicados, orientación de la radiografía y orden L1->L5 a lo largo de la columna."""
    bit2 = [("Cajas leídas", len(anot2))]
    antes = len(anot2)
    anot2 = anot2[anot2["clase"].isin(clases)].copy()
    bit2.append(("Descartadas por clase fuera de L1–L5", antes - len(anot2)))
    anot2 = anot2.merge(img2[["archivo", "ancho_px", "alto_px"]], on="archivo")
    fuera2 = ((anot2.x_min < -0.02 * anot2.ancho_px) | (anot2.y_min < -0.02 * anot2.alto_px) |
              (anot2.x_max > 1.02 * anot2.ancho_px) | (anot2.y_max > 1.02 * anot2.alto_px) |
              ((anot2.x_max - anot2.x_min) * (anot2.y_max - anot2.y_min) < 1))
    antes = len(anot2); anot2 = anot2[~fuera2].copy()
    bit2.append(("Descartadas por geometría inválida", antes - len(anot2)))

    anot2["vertebra"] = pd.Categorical(anot2["clase"], categories=clases)
    anot2["orden"] = anot2["vertebra"].cat.codes
    anot2["cx"] = (anot2.x_min + anot2.x_max) / 2
    anot2["cy"] = (anot2.y_min + anot2.y_max) / 2
    anot2["cy_rel"] = anot2["cy"] / anot2["alto_px"]
    anot2, _, n_dup = deduplicar(anot2, ["archivo", "orden"])
    bit2.append(("Descartadas por duplicado (imagen, vértebra)", n_dup))

    orient2, roto2 = orientacion_y_orden(anot2)
    anot2 = anot2.sort_index()
    inc2 = roto2.reindex(anot2.index).fillna(False).astype(bool)
    anot2["orden_coherente"] = (~inc2).astype("int8")
    anot2["es_atipico"] = inc2.astype("int8")
    anot2["motivo_atipico"] = np.where(inc2, "rompe el orden L1→L5 a lo largo de la columna", None)
    img2["orientacion"] = img2["archivo"].map(orient2)
    img2["anotada"] = img2["archivo"].isin(anot2["archivo"]).astype("int8")
    for c in ["diagnostico", "sexo", "edad", "nivel_listesis", "formato", "canales", "profundidad_bits", "tamano_kb"]:
        img2[c] = np.nan
    img2["vista"] = "perfil"
    # cada caja se guarda como un polígono de 4 vértices: entra en el mismo modelo transaccional
    vert2 = pd.concat([pd.DataFrame({"archivo": anot2.archivo, "linea": anot2.linea, "orden": k,
                                     "x_px": anot2[xc], "y_px": anot2[yc]})
                       for k, (xc, yc) in enumerate([("x_min", "y_min"), ("x_max", "y_min"),
                                                     ("x_max", "y_max"), ("x_min", "y_max")])],
                      ignore_index=True)
    return img2, anot2, vert2, pd.DataFrame(bit2, columns=["paso", "cajas"])
