"""Figuras de la defensa, generadas desde el almacén (spine_dw.db) y la base transaccional (spine_oltp.db).

Uso:  python defensa/figuras.py [carpeta_de_trabajo]
      (por defecto ./proyecto_final, la carpeta que crea Proyecto_final.ipynb fuera de Colab)

Criterios de diseño (Knaflic, *Storytelling with Data*, y fundamentos de la Unidad 5):
* el título de cada gráfico es la conclusión, no la descripción de los ejes;
* gris para el contexto y un solo color de acento para lo que hay que mirar (atributo preatentivo);
* etiquetas directas junto a las series en lugar de leyendas lejanas (proximidad);
* sin bordes superiores ni derechos, sin grillas, sin escalas logarítmicas;
* los conteos llevan ticks enteros y separador de miles con punto; los decimales, coma.
"""
import sqlite3
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, MaxNLocator, ScalarFormatter

WORK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("proyecto_final")
OUT = Path(__file__).with_name("fig")
ORDEN = ["L1", "L2", "L3", "L4", "L5"]

AZUL, CLARO, FONDO, GRIS, GRIS_TXT, TINTA, ROJO = ("#02568A", "#7FA9C8", "#EAF1F7", "#C9CED6",
                                                    "#8A949E", "#1F2933", "#C0392B")
CORTO = {"Normal": "Normal", "Código S (no documentado)": "Código «S»",
         "Escoliosis idiopática (AIS)": "Escoliosis", "Espondilolistesis": "Listesis"}

plt.rcParams.update({
    "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "axes.titlecolor": TINTA, "axes.labelcolor": GRIS_TXT, "axes.edgecolor": GRIS,
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
    "xtick.color": GRIS_TXT, "ytick.color": GRIS_TXT, "xtick.labelcolor": TINTA, "ytick.labelcolor": TINTA,
    "legend.frameon": False, "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})


# ---------------------------------------------------------------- formato de números
def miles(v, _=None):
    return f"{v:,.0f}".replace(",", ".")


class _Coma(ScalarFormatter):
    """Los decimales los decide matplotlib según el paso entre ticks (nunca redondea 1,25 a «1,2»); sólo cambia la coma."""
    def __call__(self, x, pos=None):
        return super().__call__(x, pos).replace(".", ",")


def coma(dec=None):
    return _Coma()


def entero(ax, eje="y"):
    """Conteos: sólo ticks enteros, con separador de miles."""
    a = ax.yaxis if eje == "y" else ax.xaxis
    a.set_major_locator(MaxNLocator(integer=True, nbins=5))
    a.set_major_formatter(FuncFormatter(miles))


def sin_eje(ax, eje="y"):
    """Cuando las barras llevan su valor escrito, el eje es redundante (proporción tinta-dato)."""
    if eje == "y":
        ax.spines["left"].set_visible(False); ax.set_yticks([])
    else:
        ax.spines["bottom"].set_visible(False); ax.set_xticks([])


def guardar(fig, nombre):
    fig.savefig(OUT / f"{nombre}.pdf")
    plt.close(fig)
    print("  ", nombre)


# ---------------------------------------------------------------- datos (sólo del almacén y de la OLTP)
dw = sqlite3.connect(WORK / "spine_dw.db")
H = pd.read_sql("""
    SELECT f.*, v.codigo AS vertebra, v.orden_craneocaudal AS orden, i.archivo, i.vista, i.orientacion,
           i.alto_px, d.nombre AS diagnostico, ds.nombre AS dataset
    FROM fact_vertebra_anotada f
    JOIN dim_vertebra v USING (vertebra_key) JOIN dim_imagen i USING (imagen_key)
    JOIN dim_diagnostico d ON d.diagnostico_key = i.diagnostico_key
    JOIN dim_dataset ds ON ds.dataset_key = i.dataset_key""", dw)
I = pd.read_sql("""
    SELECT i.*, d.nombre AS diagnostico, ds.nombre AS dataset
    FROM dim_imagen i JOIN dim_diagnostico d USING (diagnostico_key) JOIN dim_dataset ds USING (dataset_key)""", dw)
S = pd.read_sql("""
    SELECT f.*, s.nombre AS segmento, d.nombre AS diagnostico, i.vista
    FROM fact_segmento f JOIN dim_segmento s USING (segmento_key) JOIN dim_imagen i USING (imagen_key)
    JOIN dim_diagnostico d ON d.diagnostico_key = i.diagnostico_key WHERE i.dataset_key = 1""", dw)
dw.close()

P = H[H.geometria == "poligono"].copy()            # Lumbar Spine: polígonos
LS = I[I.dataset_key == 1].copy()
COBB = (P.groupby(["imagen_key", "diagnostico", "vista"]).inclinacion
        .agg(cobb=lambda s: s.max() - s.min(), n="size").query("n >= 4").reset_index())

# área relativa a la imagen: se recalcula desde los vértices de la OLTP (no es una métrica del almacén)
oltp = sqlite3.connect(WORK / "spine_oltp.db")
V = pd.read_sql("""SELECT v.imagen_id, v.vertebra_id, v.x_px, v.y_px, i.ancho_px, i.alto_px
                   FROM vertice v JOIN imagen i USING (imagen_id) WHERE i.dataset_id = 1
                   ORDER BY v.imagen_id, v.vertebra_id, v.orden""", oltp)
oltp.close()


def area_rel(g):
    x, y = g.x_px.to_numpy(), g.y_px.to_numpy()
    return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))) / (g.ancho_px.iat[0] * g.alto_px.iat[0])


AR = (V.groupby(["imagen_id", "vertebra_id"]).apply(area_rel, include_groups=False).rename("area_rel").reset_index()
      .rename(columns={"imagen_id": "imagen_key", "vertebra_id": "vertebra_key"}))
P = P.merge(AR, on=["imagen_key", "vertebra_key"], how="left")
OUT.mkdir(exist_ok=True)
print("Figuras en", OUT)


def tukey_fuera(g, var, k=2.0):
    q1, q3 = g[var].quantile([0.25, 0.75])
    return (g[var] < q1 - k * (q3 - q1)) | (g[var] > q3 + k * (q3 - q1))


def jitter(n, ancho=0.14, semilla=0):
    return np.random.default_rng(semilla).uniform(-ancho, ancho, n)


def strip(ax, var, resaltar, etiqueta_resaltar):
    """Puntos por vértebra: contexto en azul claro, lo que importa en rojo."""
    for k, v in enumerate(ORDEN):
        g = P[P.vertebra == v]
        x = k + jitter(len(g), semilla=k)
        m = resaltar.loc[g.index].to_numpy()
        ax.scatter(x[~m], g[var][~m], s=11, color=CLARO, lw=0)
        ax.scatter(x[m], g[var][m], s=26, color=ROJO, lw=0, zorder=3)
    ax.set_xticks(range(5), ORDEN)
    ax.yaxis.set_major_formatter(coma(1))
    if etiqueta_resaltar:
        ax.text(0.99, 0.98, etiqueta_resaltar, transform=ax.transAxes, ha="right", va="top", color=ROJO, fontsize=8)


def barra_estado(ax, tabla, etiquetas):
    """Imágenes por categoría apiladas en completa / incompleta / sin anotar, con los valores escritos."""
    colores = {"completa": AZUL, "incompleta": CLARO, "sin anotar": ROJO}
    izq = np.zeros(len(tabla))
    for estado, c in colores.items():
        vals = tabla[estado].to_numpy()
        ax.barh(range(len(tabla)), vals, left=izq, color=c, height=0.62)
        for i, (l, v) in enumerate(zip(izq, vals)):
            if v >= 2:
                ax.text(l + v / 2, i, str(int(v)), ha="center", va="center", color="white", fontsize=8, fontweight="bold")
        izq += vals
    ax.set_yticks(range(len(tabla)), etiquetas)
    ax.invert_yaxis()
    sin_eje(ax, "x")
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    # leyenda directa sobre la primera barra
    x = 0
    for estado, c in colores.items():
        ax.text(x, -0.62, estado, color=c, fontsize=8, fontweight="bold", va="bottom")
        x += {"completa": 4.2, "incompleta": 5.2, "sin anotar": 0}[estado]


def estado_por_diag(img):
    img = img.assign(estado=np.where(img.anotada == 0, "sin anotar", np.where(img.completa == 1, "completa", "incompleta")))
    t = img.groupby(["diagnostico", "estado"]).size().unstack(fill_value=0).reindex(columns=["completa", "incompleta", "sin anotar"], fill_value=0)
    return t.reindex(list(CORTO))


# ================================================================ 1. faltantes: cobertura
fig, axes = plt.subplots(1, 2, figsize=(8.9, 3.1), gridspec_kw={"width_ratios": [1, 1.5]})
ax = axes[0]
cnt = P.groupby("vertebra").size().reindex(ORDEN)
ax.bar(ORDEN, cnt, color=GRIS, width=0.6)
for k, v in enumerate(cnt):
    ax.text(k, v + 0.6, str(v), ha="center", va="bottom", color=TINTA, fontsize=9)
sin_eje(ax); ax.set_ylim(0, cnt.max() * 1.25)
ax.set_title("Clases balanceadas: 33–34 anotaciones\npor vértebra (Lumbar Spine)")
ax = axes[1]
barra_estado(ax, estado_por_diag(LS), [CORTO[d] for d in CORTO])
ax.set_title("Las 16 imágenes sin anotar son todas\nde escoliosis o del código «S»", pad=24)
fig.tight_layout(w_pad=3)
guardar(fig, "cobertura")

# ================================================================ 2. atípicos: elegir la variable
fig, axes = plt.subplots(1, 2, figsize=(8.9, 3.1))
for ax, var, color, titulo, fmt in [
        (axes[0], "area_rel", GRIS_TXT, "Área / área de la imagen: depende del encuadre", FuncFormatter(lambda v, _: f"{100 * v:.0f} %")),
        (axes[1], "area_norm", AZUL, "Área / mediana de sus vecinas: comparable", coma(1))]:
    datos = [P.loc[P.vertebra == v, var] for v in ORDEN]
    bp = ax.boxplot(datos, whis=2.0, widths=0.5, patch_artist=True, showfliers=False,
                    medianprops=dict(color="white", lw=1.6), whiskerprops=dict(color=color), capprops=dict(color=color))
    for b in bp["boxes"]:
        b.set(facecolor=color, edgecolor=color)
    for k, v in enumerate(ORDEN):
        g = P[P.vertebra == v]
        m = tukey_fuera(g, var).to_numpy()
        ax.scatter(np.full(m.sum(), k + 1), g[var][m], s=18, color=ROJO, zorder=3, lw=0)
    ax.set_xticks(range(1, 6), ORDEN); ax.yaxis.set_major_formatter(fmt)
    ax.set_title(titulo, color=TINTA)
axes[0].set_ylabel("% del área de la imagen"); axes[1].set_ylabel("1 = tamaño de sus vecinas")
axes[1].axhline(1, color=GRIS, lw=0.8, ls="--", zorder=0)
axes[1].text(5.45, 1, "vecinas", color=GRIS_TXT, fontsize=7, va="center")
fig.text(0.99, 0.0, "En rojo: fuera de las vallas de Tukey (2·RIC)", ha="right", color=ROJO, fontsize=7.5)
fig.tight_layout(w_pad=3)
guardar(fig, "encuadre")

fig, axes = plt.subplots(1, 2, figsize=(8.9, 3.1))
at = P.es_atipico == 1
strip(axes[0], "relleno", at & P.motivo_atipico.str.contains("relleno", na=False), "4 L3 con relleno bajo")
axes[0].set_title("Relleno (área del polígono / caja)")
strip(axes[1], "area_norm", at & P.motivo_atipico.str.contains("area_norm", na=False), "")
axes[1].text(0.99, 0.02, "1 L3 con área alta", transform=axes[1].transAxes, ha="right", color=ROJO, fontsize=8)
axes[1].axhline(1, color=GRIS, lw=0.8, ls="--", zorder=0)
axes[1].set_title("Área relativa a sus vecinas")
fig.suptitle("Sólo 5 de 169 contornos son atípicos, todos L3: se marcan para revisión, no se borran",
             x=0.01, ha="left", fontsize=10, fontweight="bold", color=TINTA)
fig.tight_layout(w_pad=3)
guardar(fig, "atipicos")

# ================================================================ 3. coherencia anatómica
fig, axes = plt.subplots(1, 2, figsize=(8.9, 3.1))
ax = axes[0]
for _, g in P.sort_values("orden").groupby("imagen_key"):
    ax.plot(g.orden - 1, g.cy_rel, color=GRIS, lw=0.8)
med = P.groupby("orden").cy_rel.median()
ax.plot(med.index - 1, med, "-o", color=AZUL, lw=2.4, ms=4)
ax.text(4.12, med.iloc[-1], "mediana", color=AZUL, fontsize=8, va="center")
ax.invert_yaxis(); ax.set_xticks(range(5), ORDEN); ax.set_xlim(-0.2, 4.7)
ax.yaxis.set_major_formatter(coma(1)); ax.set_ylabel("altura en la imagen (0 = arriba)")
ax.set_title("Las 34 radiografías bajan de L1 a L5:\n0 errores de orden")
ax = axes[1]
q = P.groupby("orden").alto_norm.quantile([0.25, 0.5, 0.75]).unstack()
ax.fill_between(q.index - 1, q[0.25], q[0.75], color=FONDO, lw=0)
ax.plot(q.index - 1, q[0.5], "-o", color=AZUL, lw=2.4, ms=4)
for k in (0, 4):
    ax.text(k, q[0.5].iloc[k] + 0.012, f"{q[0.5].iloc[k]:.2f}".replace(".", ","), ha="center", va="bottom",
            color=AZUL, fontsize=9, fontweight="bold")
ax.text(4.1, q[0.75].iloc[-1], "RIC", color=CLARO, fontsize=8, va="center")
ax.set_xticks(range(5), ORDEN); ax.set_xlim(-0.2, 4.6); ax.yaxis.set_major_formatter(coma(2))
ax.set_ylabel("alto / alto mediano de su imagen")
ax.set_title("Las vértebras crecen hacia caudal,\ncomo en la anatomía")
fig.tight_layout(w_pad=3)
guardar(fig, "anatomia")

# ================================================================ 4. P5: momentos y patología
DIAGS = list(CORTO)
COL_D = {"Normal": GRIS_TXT, "Código S (no documentado)": GRIS_TXT, "Escoliosis idiopática (AIS)": AZUL,
         "Espondilolistesis": ROJO}
fig, axes = plt.subplots(1, 2, figsize=(8.9, 3.2))
ax = axes[0]
for k, d in enumerate(DIAGS):
    v = COBB.loc[COBB.diagnostico == d, "cobb"]
    c = COL_D[d]
    ax.boxplot([v], positions=[k], widths=0.5, showfliers=False, medianprops=dict(color=c, lw=2),
               boxprops=dict(color=c), whiskerprops=dict(color=c), capprops=dict(color=c))
    ax.scatter(k + jitter(len(v), 0.1, k), v, s=12, color=c, alpha=0.7, lw=0, zorder=3)
    ax.text(k + 0.3, v.median(), f"{v.median():.0f}°", color=c, fontsize=8.5, fontweight="bold", va="center")
ax.axvline(2.5, color=GRIS, lw=0.8, ls=":")
ax.text(1, ax.get_ylim()[1], "de frente", ha="center", va="top", color=GRIS_TXT, fontsize=7.5)
ax.text(3, ax.get_ylim()[1], "de perfil", ha="center", va="top", color=GRIS_TXT, fontsize=7.5)
ax.set_xticks(range(4), [CORTO[d] for d in DIAGS]); ax.set_ylabel("Cobb aproximado (°)")
ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
ax.set_title("La escoliosis tiene 36° frente a 7° de las normales\n(Mann-Whitney, p < 0,001)")
ax = axes[1]
SEGS = ["L1-L2", "L2-L3", "L3-L4", "L4-L5"]
md = S.assign(d=S.desplazamiento_rel.abs()).pivot_table(index="diagnostico", columns="segmento", values="d", aggfunc="median")[SEGS]
for d in DIAGS:
    destacado = d == "Espondilolistesis"
    c, lw = (ROJO, 2.4) if destacado else (GRIS, 1.3)
    ax.plot(range(4), md.loc[d], "-o", color=c, lw=lw, ms=3.5, zorder=3 if destacado else 2)
    ax.text(3.12, md.loc[d].iloc[-1], CORTO[d], color=ROJO if destacado else GRIS_TXT, fontsize=8, va="center")
ax.set_xticks(range(4), [s.replace("-", "–") for s in SEGS]); ax.set_xlim(-0.2, 3.9)
ax.yaxis.set_major_formatter(coma(2)); ax.set_ylabel("|desplazamiento| / ancho")
ax.set_title("En la listesis L4–L5 es el segmento más desplazado\n(tendencia: Wilcoxon, n = 8, p = 0,15)")
fig.tight_layout(w_pad=3)
guardar(fig, "p5")

# ================================================================ 5. análisis exploratorio: ACP
DESC = ["area_norm", "alto_norm", "aspecto", "relleno", "incl_abs", "excentricidad", "circularidad", "solidez",
        "hu1", "hu2", "intensidad_media", "contraste"]
D = P.assign(incl_abs=P.inclinacion.abs()).dropna(subset=DESC)
Z = D[DESC].to_numpy(float); Z = (Z - Z.mean(0)) / Z.std(0)
U, Sv, Vt = np.linalg.svd(Z, full_matrices=False)
ve = Sv**2 / np.sum(Sv**2); sc = U * Sv
k80 = int(np.searchsorted(np.cumsum(ve), 0.80) + 1)

fig, axes = plt.subplots(1, 3, figsize=(11, 3.3))
ax = axes[0]
n = np.arange(1, len(ve) + 1)
ax.bar(n, 100 * ve, color=[AZUL if i <= k80 else GRIS for i in n], width=0.7)
ax.plot(n, 100 * np.cumsum(ve), "-o", color=TINTA, ms=3, lw=1.2)
ax.axhline(80, color=GRIS_TXT, lw=0.8, ls="--")
ax.text(12.5, 76, "80 %", color=GRIS_TXT, fontsize=8, va="top", ha="right")
ax.set_xticks(n); ax.set_xlabel("componente principal"); ax.set_ylabel("% de varianza")
ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
ax.set_title(f"{k80} componentes explican el 80 %")
ax = axes[1]
azules = dict(zip(ORDEN, plt.cm.Blues(np.linspace(0.35, 0.95, 5))))
for v in ORDEN:
    m = (D.vertebra == v).to_numpy()
    ax.scatter(sc[m, 0], sc[m, 1], s=12, color=azules[v], lw=0)
    ax.text(0.02 + 0.09 * ORDEN.index(v), 0.02, v, transform=ax.transAxes, color=azules[v], fontsize=8, fontweight="bold")
ax.set_title("Por vértebra los puntos se mezclan")
ax = axes[2]
lis = (D.diagnostico == "Espondilolistesis").to_numpy()
ax.scatter(sc[~lis, 0], sc[~lis, 1], s=12, color=GRIS, lw=0)
ax.scatter(sc[lis, 0], sc[lis, 1], s=14, color=ROJO, lw=0)
ax.text(0.98, 0.02, "espondilolistesis\n(vista de perfil)", transform=ax.transAxes, ha="right", va="bottom", color=ROJO, fontsize=8)
ax.text(0.02, 0.97, "resto de los diagnósticos", transform=ax.transAxes, color=GRIS_TXT, fontsize=8, va="top")
ax.set_title("Por diagnóstico, la listesis se separa en la CP1")
for ax in axes[1:]:
    ax.set_xlabel(f"CP1 · alargamiento ({100 * ve[0]:.0f} %)"); ax.set_ylabel(f"CP2 · relleno vs. inclinación ({100 * ve[1]:.0f} %)")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True)); ax.yaxis.set_major_locator(MaxNLocator(integer=True))
fig.tight_layout(w_pad=2.5)
guardar(fig, "eda_acp")

# ================================================================ 6. análisis exploratorio: redundancia y perfiles
corr = D[DESC].corr(method="spearman")
fig, axes = plt.subplots(1, 2, figsize=(9, 4.4), gridspec_kw={"width_ratios": [1.45, 1]})
ax = axes[0]
mask = np.triu(np.ones_like(corr, dtype=bool))
vals = np.where(mask, np.nan, corr.abs().values)
ax.imshow(vals, cmap="Blues", vmin=0, vmax=1)
for i in range(len(DESC)):
    for j in range(i):
        r = corr.iat[i, j]
        if abs(r) >= 0.5:
            ax.text(j, i, f"{r:+.1f}".replace(".", ","), ha="center", va="center", fontsize=6.5,
                    color="white" if abs(r) > 0.75 else TINTA)
ax.set_xticks(range(len(DESC)), DESC, rotation=45, ha="right", fontsize=7)
ax.set_yticks(range(len(DESC)), DESC, fontsize=7)
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(length=0)
ax.set_title("Excentricidad, circularidad, Hu1 y Hu2 miden lo mismo\n(|ρ| = 1): alcanza con una")
ax.text(1.0, 0.98, "|ρ| de Spearman; se escribe\nsólo si |ρ| ≥ 0,5", transform=ax.transAxes, ha="right", va="top",
        fontsize=7, color=GRIS_TXT)
ax = axes[1]
zdf = pd.DataFrame(Z, columns=DESC).assign(diagnostico=D.diagnostico.to_numpy())
medias = zdf.groupby("diagnostico")[DESC].mean()
dist = np.sqrt(((medias - medias.loc["Normal"]) ** 2).sum(axis=1)).drop("Normal").sort_values()
cols = [ROJO if d == "Espondilolistesis" else GRIS for d in dist.index]
ax.barh(range(len(dist)), dist, color=cols, height=0.6)
for i, (d, v) in enumerate(dist.items()):
    ax.text(v + 0.06, i, f"{v:.2f}".replace(".", ","), va="center", fontsize=9,
            color=ROJO if d == "Espondilolistesis" else TINTA, fontweight="bold" if d == "Espondilolistesis" else None)
ax.set_yticks(range(len(dist)), [CORTO[d] for d in dist.index]); ax.tick_params(axis="y", length=0)
sin_eje(ax, "x"); ax.spines["left"].set_visible(False); ax.set_xlim(0, dist.max() * 1.25)
ax.set_title("La listesis es el perfil más lejano\na la columna normal")
ax.text(0, -0.75, "distancia euclídea entre vectores de medias (z)", fontsize=7, color=GRIS_TXT)
fig.tight_layout(w_pad=3)
guardar(fig, "eda_perfiles")

# ================================================================ 7. representatividad
fig, ax = plt.subplots(figsize=(5.4, 2.9))
G = ["<18", "18-39", "40-64", "65+"]
t = LS[LS.sexo.isin(["F", "M"])].groupby(["grupo_edad", "sexo"]).size().unstack(fill_value=0).reindex(G, fill_value=0)
x = np.arange(len(G))
for dx, sexo, c, nombre in [(-0.2, "F", AZUL, "mujeres"), (0.2, "M", CLARO, "varones")]:
    ax.bar(x + dx, t[sexo], width=0.38, color=c)
    for xi, v in zip(x + dx, t[sexo]):
        ax.text(xi, v + 0.3, str(v), ha="center", va="bottom", fontsize=8, color=TINTA)
ax.text(-0.2, t.loc["<18", "F"] / 2, "mujeres", rotation=90, ha="center", va="center", color="white", fontsize=8, fontweight="bold")
ax.text(0.2, t.loc["<18", "M"] / 2, "varones", rotation=90, ha="center", va="center", color=TINTA, fontsize=8)
ax.set_xticks(x, ["menores de 18", "18–39", "40–64", "65 o más"]); sin_eje(ax)
ax.set_title("La mayoría son mujeres menores de 18 años")
guardar(fig, "representatividad")

# ================================================================ 8. réplicas del tablero (mismo diseño que app.py)
# P1 · grilla imagen × vértebra
estado = P.assign(e=np.where(P.es_atipico == 1, 2, 1)).pivot_table(index="imagen_key", columns="vertebra", values="e", aggfunc="first")
grilla = estado.reindex(index=LS.imagen_key, columns=ORDEN).fillna(0)
grilla = grilla.loc[(grilla > 0).sum(axis=1).sort_values(ascending=False, kind="stable").index]
from matplotlib.colors import ListedColormap
fig, ax = plt.subplots(figsize=(5.4, 5.2))
ax.imshow(grilla.values, cmap=ListedColormap([GRIS, AZUL, ROJO]), vmin=0, vmax=2, aspect="auto", interpolation="nearest")
ax.set_xticks(np.arange(-0.5, 5), minor=True); ax.set_yticks(np.arange(-0.5, len(grilla)), minor=True)
ax.grid(which="minor", color="white", lw=0.6); ax.tick_params(which="minor", length=0)
ax.set_xticks(range(5), ORDEN); ax.set_yticks([]); ax.xaxis.tick_top()
for s in ax.spines.values():
    s.set_visible(False)
ax.tick_params(axis="x", length=0)
n_sin = int((grilla.sum(axis=1) == 0).sum())
ax.text(2, len(grilla) - n_sin / 2 - 0.5, f"{n_sin} radiografías sin anotar", ha="center", va="center", color=TINTA,
        fontsize=10, fontweight="bold")
ax.text(2, 12, "33 completas", ha="center", va="center", color="white", fontsize=10, fontweight="bold")
ax.set_ylabel("cada fila es una radiografía")
guardar(fig, "tab_cobertura")

# P1 · completas por fuente
fig, ax = plt.subplots(figsize=(6.6, 2.6))
comp = I.groupby("dataset").completa.sum().reindex(["lumbar-spine-vpxwf", "nhanes-l1-l5"])
nombres = ["Lumbar Spine", "NHANES"]
ax.barh(nombres, comp, color=[ROJO, AZUL], height=0.55)
for i, v in enumerate(comp):
    ax.text(v + 0.07 * comp.max(), i, f"{miles(v)} completas", va="center", fontsize=9, color=[ROJO, AZUL][i], fontweight="bold")
ax.axvline(200, color=TINTA, lw=1, ls="--")
ax.text(230, 1.42, "mínimo supuesto: 200", fontsize=8, color=TINTA, va="center")
ax.set_xlim(0, comp.max() * 1.3); entero(ax, "x"); ax.tick_params(axis="y", length=0)
ax.spines["left"].set_visible(False); ax.set_xlabel("imágenes con L1–L5 completas")
guardar(fig, "tab_fuentes")

# P3 · orden
fig, ax = plt.subplots(figsize=(5.4, 4.6))
for _, g in P.sort_values("orden").groupby("imagen_key"):
    ax.plot(g.orden - 1, g.cy_rel, "-o", color=CLARO, lw=0.9, ms=2)
ax.invert_yaxis(); ax.set_xticks(range(5), ORDEN); ax.yaxis.set_major_formatter(coma(1))
ax.set_ylabel("altura en la imagen (0 = arriba, 1 = abajo)")
ax.text(0.98, 0.02, "34 de 34 bajan de L1 a L5", transform=ax.transAxes, ha="right", color=AZUL, fontsize=10, fontweight="bold")
guardar(fig, "tab_orden")

# P3 · orientación (NHANES)
fig, ax = plt.subplots(figsize=(5.8, 3.4))
on = I[(I.dataset_key == 2)].orientacion.value_counts().reindex(["vertical", "girada 90°", "invertida"])
tot = on.sum()
cols = [GRIS, ROJO, ROJO]
ax.barh(range(3), on, color=cols, height=0.6)
for i, v in enumerate(on):
    ax.text(v + 50, i, f"{miles(v)}  ({100 * v / tot:.0f} %)", va="center", fontsize=9,
            color=ROJO if i else TINTA, fontweight="bold" if i else None)
ax.set_yticks(range(3), ["derecha", "girada 90°", "invertida"]); ax.invert_yaxis()
ax.tick_params(axis="y", length=0); ax.spines["left"].set_visible(False)
ax.set_xlim(0, on.max() * 1.35); entero(ax, "x"); ax.set_xlabel("radiografías de NHANES")
ax.text(0.99, 0.5, f"{miles(on.iloc[1:].sum())} ({100 * on.iloc[1:].sum() / tot:.0f} %)\nhay que enderezarlas", transform=ax.transAxes,
        ha="right", va="center", color=ROJO, fontsize=9, fontweight="bold")
guardar(fig, "tab_orientacion")

# P2 · calidad
fig, ax = plt.subplots(figsize=(6.6, 4.6))
strip(ax, "area_norm", P.es_atipico == 1, "")
ax.axhline(1, color=GRIS, lw=0.8, ls="--", zorder=0)
ax.text(4.45, 1, "mismo tamaño\nque sus vecinas", color=GRIS_TXT, fontsize=7.5, va="center")
ax.set_xlim(-0.5, 5.2); ax.set_ylabel("área / mediana del área de su radiografía")
ax.annotate("5 atípicas, todas L3", xy=(2.1, P.loc[P.es_atipico == 1, "area_norm"].max()), xytext=(2.6, 1.6),
            color=ROJO, fontsize=9, fontweight="bold", arrowprops=dict(arrowstyle="-", color=ROJO, lw=0.8))
guardar(fig, "tab_calidad")

# P4 · diagnóstico
fig, ax = plt.subplots(figsize=(5.4, 3.4))
barra_estado(ax, estado_por_diag(LS), [CORTO[d] for d in CORTO])
guardar(fig, "tab_diagnostico")

# P5 · Cobb
fig, ax = plt.subplots(figsize=(5.4, 4.6))
for k, d in enumerate(DIAGS):
    v = COBB.loc[COBB.diagnostico == d, "cobb"]
    c = COL_D[d]
    ax.boxplot([v], positions=[k], widths=0.5, showfliers=False, medianprops=dict(color=c, lw=2),
               boxprops=dict(color=c), whiskerprops=dict(color=c), capprops=dict(color=c))
    ax.scatter(k + jitter(len(v), 0.1, k), v, s=16, color=c, alpha=0.75, lw=0, zorder=3)
    ax.text(k + 0.3, v.median(), f"{v.median():.0f}°", color=c, fontsize=9, fontweight="bold", va="center")
ax.axvline(2.5, color=GRIS, lw=0.8, ls=":")
ax.set_xticks(range(4), [CORTO[d] for d in DIAGS]); ax.set_ylabel("Cobb aproximado (°)")
ax.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
ax.text(1, ax.get_ylim()[1], "de frente", ha="center", va="top", color=GRIS_TXT, fontsize=8)
ax.text(3, ax.get_ylim()[1], "de perfil", ha="center", va="top", color=GRIS_TXT, fontsize=8)
guardar(fig, "tab_cobb")
