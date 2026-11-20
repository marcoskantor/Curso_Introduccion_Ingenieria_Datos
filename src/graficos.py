"""Estilo y figuras del Proyecto Final (Knaflic, 2015): el título enuncia la conclusión, el contexto va en gris y
lo que hay que mirar en un único color de acento; sin bordes ni grillas innecesarios."""
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import ScalarFormatter

PAL = {"azul": "#02568A", "claro": "#7FA9C8", "gris": "#C9CED6", "gris_txt": "#8A949E", "tinta": "#1F2933",
       "rojo": "#C0392B"}
CORTO = {"Normal": "Normal", "Código S (no documentado)": "Código «S»",
         "Escoliosis idiopática (AIS)": "Escoliosis", "Espondilolistesis": "Listesis"}
COL_D = {"Normal": PAL["gris_txt"], "Código S (no documentado)": PAL["gris_txt"],
         "Escoliosis idiopática (AIS)": PAL["azul"], "Espondilolistesis": PAL["rojo"]}


def estilo():
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "axes.titlelocation": "left",
                         "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlecolor": PAL["tinta"],
                         "axes.edgecolor": PAL["gris"], "axes.labelcolor": PAL["gris_txt"],
                         "xtick.color": PAL["gris_txt"], "ytick.color": PAL["gris_txt"], "legend.frameon": False})


class _Coma(ScalarFormatter):
    """Como el formateador de matplotlib, pero con coma decimal (como el resto del informe)."""
    def __call__(self, x, pos=None):
        return super().__call__(x, pos).replace(".", ",")


def atipicos(anotaciones, clases, variables, k):
    """Cajas por vértebra (bigotes = Tukey k·RIC) en gris y las anotaciones atípicas en rojo."""
    at = anotaciones[anotaciones.es_atipico == 1]
    fig, axes = plt.subplots(1, 3, figsize=(15, 3.6))
    for ax, var in zip(axes, variables):
        bp = ax.boxplot([anotaciones.loc[anotaciones.vertebra == v, var] for v in clases], whis=k,
                        patch_artist=True, showfliers=False, medianprops=dict(color="white", lw=1.5))
        for caja in bp["boxes"]:
            caja.set(facecolor=PAL["gris"], edgecolor=PAL["gris"])
        ax.scatter(at["orden"] + 1, at[var], color=PAL["rojo"], zorder=3, s=30)
        ax.set_xticks(range(1, len(clases) + 1), clases); ax.set_title(var, fontsize=10)
        ax.yaxis.set_major_formatter(_Coma())
    fig.suptitle(f"Sólo {len(at)} de {len(anotaciones)} anotaciones son atípicas, todas "
                 f"{', '.join(sorted(at['vertebra'].astype(str).unique()))}: en rojo, para revisión manual "
                 f"(bigotes = Tukey {k:g}·RIC)".replace(".", ","), x=0.01, ha="left", fontweight="bold")
    plt.tight_layout(rect=(0, 0, 1, 0.92)); plt.show()


def alineacion(cobb, seg_d, p_mw, p_w):
    """P5: Cobb aproximado por diagnóstico (izquierda) y desplazamiento por segmento (derecha)."""
    orden_d = list(CORTO)
    med = cobb.groupby("diagnostico")["cobb_aprox"].median()
    p_txt = "p < 0,001" if p_mw < 0.001 else f"p = {p_mw:.3f}".replace(".", ",")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.0))
    ax = axes[0]
    for k, d in enumerate(orden_d):
        v, c = cobb.loc[cobb.diagnostico == d, "cobb_aprox"], COL_D[d]
        ax.boxplot([v], positions=[k], widths=0.5, showfliers=False, medianprops=dict(color=c, lw=2),
                   boxprops=dict(color=c), whiskerprops=dict(color=c), capprops=dict(color=c))
        ax.scatter(np.full(len(v), k), v, color=c, s=14, alpha=0.7, zorder=3)
        ax.text(k + 0.3, v.median(), f"{v.median():.0f}°", color=c, fontweight="bold", va="center")
    ax.axvline(2.5, color=PAL["gris"], ls=":")
    ax.text(3, ax.get_ylim()[1], "de perfil", ha="center", va="top", color=PAL["gris_txt"])
    ax.set_xticks(range(4), [CORTO[d] for d in orden_d]); ax.set_ylabel("Cobb aproximado (°)")
    ax.set_title(f"La escoliosis tiene {med['Escoliosis idiopática (AIS)']:.0f}° frente a "
                 f"{med['Normal']:.0f}° de las normales ({p_txt})")
    ax = axes[1]
    for d in orden_d:
        t = seg_d[seg_d.diagnostico == d].groupby("segmento")["desplazamiento_abs"].median()
        c, lw = (PAL["rojo"], 2.5) if d == "Espondilolistesis" else (PAL["gris"], 1.3)
        ax.plot(t.index, t.values, "-o", color=c, lw=lw, ms=4)
        ax.text(3.1, t.values[-1], CORTO[d], va="center", color=c if d == "Espondilolistesis" else PAL["gris_txt"])
    ax.set_xlim(-0.2, 3.8); ax.set_ylabel("|desplazamiento| / ancho"); ax.yaxis.set_major_formatter(_Coma())
    ax.set_title(f"En la listesis, L4–L5 es el segmento más desplazado (tendencia, p = {p_w:.2f})".replace("0.", "0,"))
    plt.tight_layout(); plt.show()
