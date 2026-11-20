"""Extracción del Proyecto Final: descarga verificada, inventario de imágenes, metadatos y parsing de anotaciones.

Fuentes (CC BY 4.0, copias sin modificar en data/raw/ del repositorio público):
  - Lumbar Spine (Roboflow, rp-team/lumbar-spine-vpxwf v1): export YOLOv8 de segmentación (polígonos).
  - NHANES L1-L5 (Roboflow, main-kybbe v1): anotaciones COCO (cajas).
"""
import hashlib
import json
import re
import zipfile
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
import requests
import yaml

EXT = {".jpg", ".jpeg", ".png", ".bmp"}


def sha256(path: Path) -> str:
    """Huella SHA-256 del archivo, leída en bloques de 1 MiB."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def descargar(url: str, sha: str, carpeta: Path) -> Path:
    """Descarga idempotente: si el archivo ya está y su hash coincide, no se vuelve a bajar."""
    destino = carpeta / url.rsplit("/", 1)[-1]
    if not (destino.exists() and sha256(destino) == sha):
        r = requests.get(url, timeout=300)
        r.raise_for_status()
        destino.write_bytes(r.content)
    digest = sha256(destino)
    assert digest == sha, f"SHA-256 no coincide: {digest}"
    return destino


def descomprimir(zip_path: Path, destino: Path) -> Path:
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(destino)
    return destino


def clases(raw: Path) -> list:
    """Clases declaradas en data.yaml (L1..L5)."""
    nombres = yaml.safe_load(next(raw.rglob("data.yaml")).read_text())["names"]
    return [nombres[k] for k in sorted(nombres)] if isinstance(nombres, dict) else nombres


def metadatos(archivo: str) -> dict:
    """Diagnóstico, sexo, edad y nivel de listesis codificados en el nombre de archivo.

    Ejemplo: N18-Olisthesis-L4-5-F-56-Yrs_jpg.rf.<hash>.jpg. Lo que no se puede interpretar queda nulo
    (no se inventan pacientes). El nivel L4-5 se quita antes de buscar la edad: ese 5 no es una edad.
    """
    base = re.split(r"_(?:jpe?g|png)\.rf\.", archivo, flags=re.I)[0]
    base = re.sub(r"_\d+_\d+$", "", base)                        # sufijos de serie (_1002_1)
    nivel = re.search(r"L\d-(?:\d|S1)", base)                     # nivel de la listesis (L4-5, L5-S1)
    tokens = re.sub(r"L\d-(?:\d|S1)", "", base).split("-")
    if "AIS" in base:
        diag = "Escoliosis idiopática (AIS)"
    elif "Olisthesis" in base:
        diag = "Espondilolistesis"
    elif len(tokens) > 1 and tokens[1] == "N":
        diag = "Normal"
    elif len(tokens) > 1 and tokens[1] == "S":
        diag = "Código S (no documentado)"
    else:
        diag = None
    edades = [int(t) for t in tokens[1:] if t.isdigit() and 0 < int(t) < 100]
    sexos = [t for t in tokens if t in ("M", "F")]
    return {"diagnostico": diag, "sexo": sexos[0] if sexos else None, "edad": edades[0] if edades else None,
            "nivel_listesis": nivel.group(0) if nivel else None}


def inventariar(raw: Path) -> pd.DataFrame:
    """Una fila por imagen: partición, resolución, formato de píxel, si tiene etiquetas y metadatos clínicos."""
    filas = []
    for img_dir in sorted(raw.rglob("images")):
        split = img_dir.parent.name
        for img in sorted(p for p in img_dir.iterdir() if p.suffix.lower() in EXT):
            pix = cv2.imread(str(img), cv2.IMREAD_UNCHANGED)          # formato de píxel tal cual está guardado
            alto, ancho = pix.shape[:2]
            canales = 1 if pix.ndim == 2 else pix.shape[2]
            gris = canales == 1 or bool(np.array_equal(pix[..., 0], pix[..., 1]) and np.array_equal(pix[..., 1], pix[..., 2]))
            lbl = img_dir.parent / "labels" / (img.stem + ".txt")
            lineas = [l for l in lbl.read_text().splitlines() if l.strip()] if lbl.exists() else []
            filas.append({"archivo": img.name, "split": split, "ancho_px": ancho, "alto_px": alto,
                          "formato": img.suffix.lower().lstrip("."), "canales": canales,
                          "profundidad_bits": pix.dtype.itemsize * 8, "gris_en_rgb": gris and canales == 3,
                          "tamano_kb": img.stat().st_size / 1024,
                          "tiene_etiquetas": lbl.exists(), "n_lineas": len(lineas)})
    inv = pd.DataFrame(filas)
    return pd.concat([inv, inv["archivo"].map(metadatos).apply(pd.Series)], axis=1)


def area_poligono(x, y):
    """Área de un polígono por la fórmula de Gauss (shoelace): 1/2 * |sum(x_i*y_(i+1) - y_i*x_(i+1))|.

    np.roll(y, -1) empareja el vértice i con el i+1 y el último con el primero (el contorno se cierra solo).
    """
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))


def parsear_yolo(inventario: pd.DataFrame, raw: Path, stg: Path):
    """Parsea las etiquetas YOLOv8 (`clase x1 y1 ... xn yn`, normalizadas) y escribe el staging.

    Una línea con 4 valores es una caja `xc yc w h` y se convierte a sus 4 esquinas; con < 3 vértices o un
    número impar de coordenadas se rechaza con su motivo. Las coordenadas se desnormalizan a píxeles.
    Escribe staging/imagenes.csv, anotaciones.csv (grano: vértebra en una imagen) y vertices.csv (1FN).
    """
    anot, vert, rechazos = [], [], []
    for fila in inventario[inventario.n_lineas > 0].itertuples():
        lbl = next(raw.rglob(f"{fila.split}/labels/{Path(fila.archivo).stem}.txt"))
        for n_linea, linea in enumerate(l for l in lbl.read_text().splitlines() if l.strip()):
            partes = linea.split()
            try:
                clase, vals = int(float(partes[0])), np.array(partes[1:], dtype=float)
            except ValueError:
                rechazos.append((fila.archivo, n_linea, "valor no numérico")); continue
            if len(vals) == 4:
                xc, yc, w, h = vals
                vals = np.array([xc - w/2, yc - h/2, xc + w/2, yc - h/2, xc + w/2, yc + h/2, xc - w/2, yc + h/2])
            if len(vals) < 6 or len(vals) % 2:
                rechazos.append((fila.archivo, n_linea, "polígono con < 3 vértices o coordenadas impares")); continue
            x, y = vals[0::2] * fila.ancho_px, vals[1::2] * fila.alto_px
            anot.append({"archivo": fila.archivo, "linea": n_linea, "clase_id": clase, "n_vertices": len(x),
                         "x_min": x.min(), "y_min": y.min(), "x_max": x.max(), "y_max": y.max(),
                         "area_px": area_poligono(x, y), "cx": x.mean(), "cy": y.mean()})
            vert += [{"archivo": fila.archivo, "linea": n_linea, "orden": i, "x_px": xi, "y_px": yi}
                     for i, (xi, yi) in enumerate(zip(x, y))]
    inventario.to_csv(stg / "imagenes.csv", index=False)
    pd.DataFrame(anot).to_csv(stg / "anotaciones.csv", index=False)
    pd.DataFrame(vert).to_csv(stg / "vertices.csv", index=False)
    return pd.DataFrame(rechazos, columns=["archivo", "linea", "motivo"])


def leer_nhanes(raw2: Path):
    """Lee las anotaciones COCO de NHANES (train/valid/test): una fila por imagen y una por caja."""
    img2, anot2 = [], []
    for js in sorted(raw2.rglob("*.json")):
        split = js.parent.name
        coco = json.loads(js.read_text(encoding="utf-8"))
        nombre_cat = {c["id"]: c["name"] for c in coco["categories"]}
        for im in coco["images"]:
            img2.append({"archivo": f"nhanes_{split}_{im['id']}", "split": split,
                         "ancho_px": im["width"], "alto_px": im["height"], "_id": (split, im["id"])})
        for n, a in enumerate(coco["annotations"]):
            x, y, w, h = a["bbox"]
            anot2.append({"archivo": f"nhanes_{split}_{a['image_id']}", "linea": n,
                          "clase": nombre_cat.get(a["category_id"]),
                          "x_min": x, "y_min": y, "x_max": x + w, "y_max": y + h})
    return pd.DataFrame(img2).drop(columns="_id"), pd.DataFrame(anot2)
