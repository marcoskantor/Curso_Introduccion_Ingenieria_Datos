"""Descriptores de forma con momentos de imagen (OpenCV), intensidad dentro del contorno y segmentos (P5).

Referencia: tutorial de momentos de OpenCV, https://docs.opencv.org/4.13.0/d0/d49/tutorial_moments.html
"""
from pathlib import Path

import cv2
import numpy as np
import pandas as pd


def descriptores(x, y) -> dict:
    """Descriptores de UNA vértebra a partir de los vértices (px) de su contorno.

    m00 = área por momentos (se valida contra la fórmula de Gauss); cx_m, cy_m = centroide (m10/m00, m01/m00).
    mu20, mu02, mu11 = momentos centrales de 2.º orden divididos por m00 (varianza en x, en y y covarianza):
      inclinacion   = 1/2 * atan2(2*mu11, mu20 - mu02), ángulo del eje principal en grados (base del Cobb);
      excentricidad = sqrt(1 - l2/l1) con l1 >= l2 autovalores de esa matriz (0 = círculo);
    circularidad = 4*pi*A/P², solidez = A / área del casco convexo, hu1 y hu2 = momentos de Hu en escala log.
    """
    cnt = np.column_stack([x, y]).astype(np.float32).reshape(-1, 1, 2)
    m = cv2.moments(cnt)
    mu20, mu02, mu11 = m["mu20"] / m["m00"], m["mu02"] / m["m00"], m["mu11"] / m["m00"]
    raiz = np.sqrt(4 * mu11**2 + (mu20 - mu02)**2)
    l1, l2 = (mu20 + mu02 + raiz) / 2, (mu20 + mu02 - raiz) / 2
    hu = cv2.HuMoments(m).ravel()
    area, per = cv2.contourArea(cnt), cv2.arcLength(cnt, True)
    with np.errstate(divide="ignore", invalid="ignore"):   # en cajas Hu2 = 0: log indefinido (no se usa)
        hu1, hu2 = -np.sign(hu[0]) * np.log10(abs(hu[0])), -np.sign(hu[1]) * np.log10(abs(hu[1]))
    return {"m00": abs(m["m00"]), "cx_m": m["m10"] / m["m00"], "cy_m": m["m01"] / m["m00"],
            "inclinacion": 0.5 * np.degrees(np.arctan2(2 * mu11, mu20 - mu02)),
            "excentricidad": np.sqrt(max(0.0, 1 - l2 / l1)), "circularidad": 4 * np.pi * area / per**2,
            "solidez": area / cv2.contourArea(cv2.convexHull(cnt)), "hu1": hu1, "hu2": hu2}


class Intensidad:
    """Intensidad media y contraste (desvío) de los píxeles DENTRO del polígono, en [0, 1].

    Usa una máscara cv2.fillPoly; guarda cada radiografía en memoria para no releerla una vez por vértebra.
    """
    def __init__(self, raw: Path):
        self.raw, self._cache = raw, {}

    def __call__(self, archivo, x, y) -> dict:
        if archivo not in self._cache:
            self._cache[archivo] = cv2.imread(str(next(self.raw.rglob(archivo))), cv2.IMREAD_GRAYSCALE)
        gris = self._cache[archivo]
        mascara = np.zeros(gris.shape, np.uint8)
        cv2.fillPoly(mascara, [np.round(np.column_stack([x, y])).astype(np.int32)], 1)
        vals = gris[mascara == 1].astype(float) / 255
        return {"intensidad_media": vals.mean(), "contraste": vals.std()}


def agregar_descriptores(anotaciones: pd.DataFrame, vertices: pd.DataFrame, intensidad: Intensidad) -> pd.DataFrame:
    """Agrega a cada anotación sus descriptores de forma y de píxel (una fila por vértebra en una imagen)."""
    vert_por_anot = {k: g.sort_values("orden") for k, g in vertices.astype({"archivo": str}).groupby(["archivo", "linea"])}
    filas = []
    for a in anotaciones.itertuples():
        g = vert_por_anot[(str(a.archivo), a.linea)]
        filas.append({**descriptores(g.x_px.to_numpy(), g.y_px.to_numpy()),
                      **intensidad(str(a.archivo), g.x_px.to_numpy(), g.y_px.to_numpy())})
    forma = pd.DataFrame(filas, index=anotaciones.index)
    return pd.concat([anotaciones.drop(columns=forma.columns, errors="ignore"), forma], axis=1)


def segmentos(t: pd.DataFrame, clases: list, clave: str = "archivo") -> pd.DataFrame:
    """Filas de fact_segmento: grano = un par de vértebras consecutivas (L1-L2 ... L4-L5) en una imagen.

    delta_inclinacion  = inclinación(inferior) - inclinación(superior)   [ángulo segmentario, °]
    desplazamiento_rel = diferencia horizontal de centroides / ancho medio de las dos vértebras
    separacion_rel     = borde superior de la inferior - borde inferior de la superior / alto medio
    """
    t = t.sort_values([clave, "orden"])
    sup = t.groupby(clave, observed=True).shift(1)
    ok = (t["orden"] - sup["orden"]) == 1
    ancho_medio = ((t["x_max"] - t["x_min"]) + (sup["x_max"] - sup["x_min"])) / 2
    alto_medio = ((t["y_max"] - t["y_min"]) + (sup["y_max"] - sup["y_min"])) / 2
    out = pd.DataFrame({clave: t[clave], "orden_inf": t["orden"].astype(int),
                        "delta_inclinacion": t["inclinacion"] - sup["inclinacion"],
                        "desplazamiento_rel": (t["cx_m"] - sup["cx_m"]) / ancho_medio,
                        "separacion_rel": (t["y_min"] - sup["y_max"]) / alto_medio})[ok]
    out["segmento"] = [f"{clases[o - 1]}-{clases[o]}" for o in out["orden_inf"]]
    return out


def cobb_aproximado(anotaciones: pd.DataFrame, meta: pd.DataFrame) -> pd.DataFrame:
    """Cobb aproximado por imagen: inclinación máxima - mínima entre L1 y L5 (exige >= 4 vértebras)."""
    cobb = (anotaciones.groupby("archivo", observed=True)
            .agg(cobb_aprox=("inclinacion", lambda s: s.max() - s.min()), vertebras=("inclinacion", "size"))
            .query("vertebras >= 4").reset_index())
    return cobb.assign(archivo=cobb["archivo"].astype(str)).merge(meta, on="archivo")
