"""Compila los diagramas TikZ (ER de la base transaccional y almacén) y los exporta.

    python defensa/diagramas/exportar.py

Salidas: defensa/fig/<nombre>.pdf (presentación) y docs/img/<nombre>.png (cuaderno y README).
Requiere XeLaTeX (MiKTeX, TeX Live o Overleaf) y PyMuPDF.
"""
import shutil
import subprocess
from pathlib import Path

import pymupdf

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
FIG, IMG = AQUI.parent / "fig", RAIZ / "docs" / "img"
IMG.mkdir(parents=True, exist_ok=True)

for nombre in ("er_oltp", "dw"):
    subprocess.run(["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"{nombre}.tex"], cwd=AQUI, check=True,
                   stdout=subprocess.DEVNULL)
    shutil.copy(AQUI / f"{nombre}.pdf", FIG / f"{nombre}.pdf")
    pymupdf.open(AQUI / f"{nombre}.pdf")[0].get_pixmap(dpi=170).save(IMG / f"{nombre}.png")
    for ext in (".aux", ".log", ".pdf"):
        (AQUI / f"{nombre}{ext}").unlink(missing_ok=True)
    print("  ", nombre)
