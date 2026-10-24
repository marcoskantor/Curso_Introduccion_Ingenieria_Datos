import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

DB = Path(__file__).with_name("spine_dw.db")
ORDEN = ["L1", "L2", "L3", "L4", "L5"]
FUENTE = {"lumbar-spine-vpxwf": "Lumbar Spine (polígonos)", "nhanes-l1-l5": "NHANES (cajas)"}
CORTO = {"Normal": "Normal", "Código S (no documentado)": "Código «S»",
         "Escoliosis idiopática (AIS)": "Escoliosis", "Espondilolistesis": "Listesis"}

st.set_page_config(page_title="Vértebras lumbares — aptitud de los datos", layout="wide")
AZUL, AZUL_CLARO, GRIS, GRIS_TXT, TINTA, ROJO = "#02568A", "#7FA9C8", "#C9CED6", "#8A949E", "#1F2933", "#C0392B"
px.defaults.color_discrete_sequence = [AZUL, AZUL_CLARO, ROJO, GRIS]


# Diseño (Storytelling with Data): el título es la conclusión, gris para el contexto y un color de acento
# para el mensaje, leyenda horizontal arriba, sin escalas logarítmicas y ejes de conteo con ticks enteros.
def paso(maximo, marcas=5):
    """Paso 'redondo' (1, 2, 5, 10, 20…) para ejes de conteo; nunca menor que 1: no existen 2,5 imágenes."""
    bruto = max(1.0, float(maximo) / marcas)
    base = 10 ** int(np.floor(np.log10(bruto)))
    return next(m * base for m in (1, 2, 5, 10) if m * base >= bruto)


def es(v, dec=0):
    """Número en formato argentino: punto de miles y coma decimal."""
    return f"{v:,.{dec}f}".replace(",", "#").replace(".", ",").replace("#", ".")


def estilo(fig, conteo=None, maximo=None):
    fig.update_layout(template="simple_white", separators=",.", title_x=0, title_font=dict(size=16, color=TINTA),
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, x=0, title_text=""),
                      margin=dict(t=90))
    if conteo:
        ejes = fig.update_xaxes if conteo == "x" else fig.update_yaxes
        ejes(tick0=0, dtick=paso(maximo), tickformat=",d", rangemode="tozero")
    return fig


@st.cache_data
def cargar():
    con = sqlite3.connect(DB)
    hechos = pd.read_sql("""
        SELECT i.archivo, i.split, i.sexo, i.grupo_edad, i.vista, i.orientacion, d.nombre AS diagnostico,
               ds.nombre AS dataset, v.codigo AS vertebra, v.orden_craneocaudal,
               f.area_norm, f.alto_norm, f.aspecto, f.relleno, f.cy_rel, f.inclinacion,
               f.es_atipico, f.orden_coherente, f.motivo_atipico, f.geometria
        FROM fact_vertebra_anotada f
        JOIN dim_vertebra v     USING (vertebra_key)
        JOIN dim_imagen i       USING (imagen_key)
        JOIN dim_dataset ds     ON ds.dataset_key = i.dataset_key
        JOIN dim_diagnostico d  ON d.diagnostico_key = i.diagnostico_key""", con)
    imagenes = pd.read_sql("""
        SELECT i.archivo, i.split, i.sexo, i.grupo_edad, i.vista, i.orientacion, i.anotada, i.vertebras_anotadas,
               i.completa, d.nombre AS diagnostico, ds.nombre AS dataset
        FROM dim_imagen i JOIN dim_diagnostico d ON d.diagnostico_key = i.diagnostico_key
        JOIN dim_dataset ds ON ds.dataset_key = i.dataset_key""", con)
    segmentos = pd.read_sql("""
        SELECT i.archivo, d.nombre AS diagnostico, i.vista, s.nombre AS segmento,
               f.delta_inclinacion, f.desplazamiento_rel, f.separacion_rel
        FROM fact_segmento f
        JOIN dim_segmento s    USING (segmento_key)
        JOIN dim_imagen i      USING (imagen_key)
        JOIN dim_diagnostico d ON d.diagnostico_key = i.diagnostico_key
        WHERE i.dataset_key = 1""", con)
    con.close()
    for t in (hechos, imagenes):
        t["fuente"] = t["dataset"].map(FUENTE)
    return hechos, imagenes, segmentos


hechos, imagenes, segmentos = cargar()

# ------------------------------------------------------------------ barra lateral
st.sidebar.header("Filtros")
fuentes = list(FUENTE.values())
fuente_sel = st.sidebar.multiselect("Fuente de datos", fuentes, default=fuentes) or fuentes
diags = sorted(imagenes["diagnostico"].unique())
diag_sel = st.sidebar.multiselect("Diagnóstico (Lumbar Spine; NHANES = «sin dato»)", diags, default=diags) or diags
sexo_sel = st.sidebar.multiselect("Sexo", sorted(imagenes["sexo"].unique()), default=sorted(imagenes["sexo"].unique()))
incluir_atipicos = st.sidebar.toggle("Incluir anotaciones atípicas", value=True)
st.sidebar.divider()
st.sidebar.header("Supuesto del veredicto")
minimo = st.sidebar.slider("Imágenes completas (L1–L5) necesarias para entrenar", 50, 5000, 200, step=50,
                           help="Orden de magnitud habitual para entrenar un detector de 5 clases desde un modelo preentrenado.")

img = imagenes[imagenes["fuente"].isin(fuente_sel) & imagenes["diagnostico"].isin(diag_sel)
               & imagenes["sexo"].isin(sexo_sel or imagenes["sexo"].unique())]
h = hechos[hechos["archivo"].isin(img["archivo"])]
if not incluir_atipicos:
    h = h[h["es_atipico"] == 0]
poly = h[h["geometria"] == "poligono"]

# ------------------------------------------------------------------ encabezado y veredicto
st.title("¿Alcanzan los datos públicos para entrenar el detector de vértebras de un CDSS de inestabilidad espinal?")
st.caption("Proyecto Final — Introducción a la Ingeniería de Datos · Marcos Kantor · "
           "Datos: Lumbar Spine (rp-team) y NHANES L1–L5 (main-kybbe), Roboflow Universe, CC BY 4.0 · "
           "Fuente del tablero: almacén `spine_dw.db`")

completas = int(img["completa"].sum())
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Imágenes", f"{es(len(img))}")
c2.metric("Anotadas", f"{es(int(img['anotada'].sum()))}", f"{es(100 * img['anotada'].mean())} %" if len(img) else None)
c3.metric("Completas L1–L5", f"{es(completas)}")
c4.metric("Anotaciones atípicas", f"{es(100 * h['es_atipico'].mean(), 1)} %" if len(h) else "—")
c5.metric("Giradas o invertidas", f"{es(int(img['orientacion'].isin(['girada 90°', 'invertida']).sum()))}")

if completas >= minimo:
    st.success(f"**Apto para entrenar:** {es(completas)} imágenes completas superan el mínimo supuesto de {es(minimo)}.")
elif completas >= minimo / 4:
    st.warning(f"**Insuficiente para entrenar desde cero; útil como ajuste fino o validación:** "
               f"{es(completas)} imágenes completas frente a {es(minimo)} necesarias.")
else:
    st.error(f"**No alcanza para entrenar el detector.** Con {es(completas)} imágenes completas "
             f"({100 * completas / minimo:.0f} % del mínimo supuesto de {es(minimo)}) sirve como **conjunto piloto o de validación**; "
             f"hay que sumar datos.")
por_fuente = (img.groupby("fuente").agg(imagenes=("archivo", "size"), anotadas=("anotada", "sum"),
                                         completas=("completa", "sum")).reset_index())
st.dataframe(por_fuente, width="stretch", hide_index=True)

st.divider()

# ------------------------------------------------------------------ P1 cobertura y balance
st.subheader("P1 · Cobertura y balance")
col_a, col_b = st.columns(2)
with col_a:
    por_f = img.groupby("fuente", as_index=False)["completa"].sum()
    por_f["alcanza"] = np.where(por_f["completa"] >= minimo, "supera el mínimo", "no alcanza el mínimo")
    fig = px.bar(por_f, y="fuente", x="completa", orientation="h", color="alcanza", text="completa",
                 color_discrete_map={"supera el mínimo": AZUL, "no alcanza el mínimo": ROJO},
                 title=f"Imágenes completas por fuente frente al mínimo de {es(minimo)}",
                 labels={"fuente": "", "completa": "imágenes con L1–L5 completas"})
    fig.add_vline(x=minimo, line_dash="dash", line_color=TINTA, annotation_text=f"mínimo: {es(minimo)}")
    fig.update_traces(texttemplate="%{x:,d}", textposition="outside", cliponaxis=False)
    st.plotly_chart(estilo(fig, "x", max(por_f["completa"].max(), minimo)), width="stretch")
with col_b:
    # % de las imágenes anotadas de cada fuente que tienen cada vértebra: compara fuentes de tamaño muy distinto
    # en escala lineal (las cantidades absolutas difieren en dos órdenes de magnitud)
    balance = h.groupby(["fuente", "vertebra"])["archivo"].nunique().rename("imagenes").reset_index()
    balance["pct"] = 100 * balance["imagenes"] / balance["fuente"].map(img[img["anotada"] == 1].groupby("fuente").size())
    fig = px.bar(balance, x="vertebra", y="pct", color="fuente", barmode="group",
                 category_orders={"vertebra": ORDEN}, color_discrete_sequence=[AZUL, AZUL_CLARO],
                 title="Las cinco clases están balanceadas en las dos fuentes",
                 labels={"pct": "% de imágenes anotadas que tienen la vértebra", "vertebra": ""},
                 hover_data={"imagenes": ":,d"})
    fig.update_yaxes(range=[0, 105], ticksuffix=" %")
    st.plotly_chart(estilo(fig), width="stretch")

if "Lumbar Spine (polígonos)" in fuente_sel:
    with st.expander("Grilla imagen × vértebra de Lumbar Spine (gris = falta, azul = anotada, rojo = atípica)"):
        ls = img[img["fuente"] == "Lumbar Spine (polígonos)"]
        estado = poly.assign(estado=poly["es_atipico"].map({0: 1, 1: 2}))
        grilla = (ls[["archivo"]].merge(estado[["archivo", "vertebra", "estado"]], how="left")
                  .pivot_table(index="archivo", columns="vertebra", values="estado", aggfunc="first")
                  .reindex(index=ls["archivo"], columns=ORDEN).fillna(0))
        grilla = grilla.loc[(grilla > 0).sum(axis=1).sort_values(ascending=False).index]
        fig = px.imshow(grilla.astype(int), zmin=0, zmax=2, color_continuous_scale=[(0, GRIS), (0.5, AZUL), (1, ROJO)],
                        aspect="auto")
        fig.update_layout(coloraxis_showscale=False, height=480, yaxis=dict(showticklabels=False))
        st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ P3 coherencia anatómica
st.subheader("P3 · Coherencia anatómica y orientación")
col_a, col_b = st.columns(2)
with col_a:
    ori = img[img["anotada"] == 1].groupby(["fuente", "orientacion"]).size().reset_index(name="imagenes")
    ori["pct"] = 100 * ori["imagenes"] / ori.groupby("fuente")["imagenes"].transform("sum")
    malas = int(ori.loc[ori["orientacion"] != "vertical", "imagenes"].sum())
    fig = px.bar(ori, y="orientacion", x="imagenes", facet_col="fuente", orientation="h", text="imagenes",
                 color=np.where(ori["orientacion"] == "vertical", "derecha", "a enderezar"),
                 color_discrete_map={"derecha": GRIS, "a enderezar": ROJO},
                 category_orders={"orientacion": ["vertical", "girada 90°", "invertida"]},
                 title=f"{es(malas)} radiografías ({es(100 * malas / max(1, ori['imagenes'].sum()))} %) llegan giradas o invertidas",
                 labels={"orientacion": "", "imagenes": "radiografías", "color": ""}, custom_data=["pct"])
    fig.update_traces(texttemplate="%{x:,d} (%{customdata[0]:.0f} %)", textposition="outside", cliponaxis=False)
    fig.update_xaxes(matches=None, showticklabels=False)        # cada fuente con su escala; el valor va escrito
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    st.plotly_chart(estilo(fig), width="stretch")
with col_b:
    vert = h[h["orientacion"] == "vertical"]
    muestra = vert["archivo"].drop_duplicates().sample(min(200, vert["archivo"].nunique()), random_state=0)
    vs = vert[vert["archivo"].isin(muestra)].sort_values("orden_craneocaudal")
    fig = px.line(vs, x="vertebra", y="cy_rel", line_group="archivo",
                  color=vs["orden_coherente"].map({1: "orden correcto", 0: "rompe el orden"}),
                  color_discrete_map={"orden correcto": GRIS, "rompe el orden": ROJO},
                  category_orders={"vertebra": ORDEN}, markers=True,
                  title="Las vértebras bajan de L1 a L5 (muestra de 200 radiografías derechas)",
                  labels={"cy_rel": "altura en la imagen (0 = arriba, 1 = abajo)", "color": "", "vertebra": ""})
    fig.update_yaxes(autorange="reversed", tickformat=".1f")
    st.plotly_chart(estilo(fig), width="stretch")
st.caption(f"Cajas o polígonos que rompen el orden L1→L5 a lo largo de la columna (errores de etiqueta): "
           f"{int((1 - h['orden_coherente']).sum())} en {h.loc[h['orden_coherente'] == 0, 'archivo'].nunique()} imágenes.")

# ------------------------------------------------------------------ P2 calidad geométrica
st.subheader("P2 · Calidad geométrica de las anotaciones (polígonos de Lumbar Spine)")
if len(poly):
    var = st.radio("Variable", ["area_norm", "aspecto", "relleno"], horizontal=True,
                   format_func={"area_norm": "área relativa a sus vecinas", "aspecto": "relación de aspecto",
                                "relleno": "relleno del polígono"}.get)
    n_at = int(poly["es_atipico"].sum())
    fig = px.strip(poly, x="vertebra", y=var, color=poly["es_atipico"].map({0: "normal", 1: "atípica"}),
                   category_orders={"vertebra": ORDEN}, hover_data=["archivo", "motivo_atipico"],
                   color_discrete_map={"normal": AZUL_CLARO, "atípica": ROJO},
                   title=f"Sólo {n_at} de {len(poly)} contornos son atípicos: se revisan a mano, no se borran",
                   labels={"color": "", "vertebra": ""})
    if var == "area_norm":
        fig.add_hline(y=1, line_dash="dot", line_color=GRIS_TXT, annotation_text="mismo tamaño que sus vecinas")
    fig.update_yaxes(tickformat=".1f")
    st.plotly_chart(estilo(fig), width="stretch")
atip = h[h["es_atipico"] == 1][["fuente", "archivo", "vertebra", "motivo_atipico"]]
st.markdown(f"**{len(atip)} anotaciones marcadas para revisión manual**")
st.dataframe(atip, width="stretch", hide_index=True)

# ------------------------------------------------------------------ P4 representatividad
st.subheader("P4 · Representatividad")
col_a, col_b = st.columns(2)
with col_a:
    # sólo imágenes con diagnóstico: NHANES («sin dato», 4.436) aplastaría la escala lineal
    con_diag = img[img["diagnostico"] != "sin dato"]
    est = con_diag.assign(estado=np.where(con_diag["anotada"] == 0, "sin anotar",
                                          np.where(con_diag["completa"] == 1, "completa", "incompleta")),
                          diag=con_diag["diagnostico"].map(CORTO))
    rep = est.groupby(["diag", "estado"]).size().reset_index(name="imagenes")
    fig = px.bar(rep, y="diag", x="imagenes", color="estado", orientation="h", text="imagenes",
                 category_orders={"estado": ["completa", "incompleta", "sin anotar"], "diag": list(CORTO.values())},
                 color_discrete_map={"completa": AZUL, "incompleta": AZUL_CLARO, "sin anotar": ROJO},
                 title="Las imágenes sin anotar son de escoliosis y del código «S»",
                 labels={"diag": "", "imagenes": "imágenes de Lumbar Spine"})
    st.plotly_chart(estilo(fig, "x", est.groupby("diag").size().max() if len(est) else 1), width="stretch")
with col_b:
    con_dato = img[img["grupo_edad"] != "sin dato"]
    edad = con_dato.groupby(["grupo_edad", "sexo"]).size().reset_index(name="imagenes")
    fig = px.bar(edad, x="grupo_edad", y="imagenes", color="sexo", barmode="group", text="imagenes",
                 color_discrete_map={"F": AZUL, "M": AZUL_CLARO, "sin dato": GRIS},
                 title="La mayoría son mujeres menores de 18 años (NHANES no trae edad ni sexo)",
                 category_orders={"grupo_edad": ["<18", "18-39", "40-64", "65+"], "sexo": ["F", "M", "sin dato"]},
                 labels={"grupo_edad": "grupo de edad", "imagenes": "imágenes"})
    st.plotly_chart(estilo(fig, "y", edad["imagenes"].max() if len(edad) else 1), width="stretch")

# ------------------------------------------------------------------ P5 alineación
st.subheader("P5 · Alineación medida con momentos de imagen (OpenCV, polígonos de Lumbar Spine)")
st.caption("La inclinación de cada vértebra es el ángulo del eje principal de su contorno, "
           "θ = ½·atan2(2μ11, μ20 − μ02). En radiografías de frente el rango L1–L5 aproxima el ángulo de Cobb (escoliosis); "
           "en las de perfil (espondilolistesis) refleja la lordosis. Las cajas de NHANES no tienen inclinación.")
cobb = (poly.dropna(subset=["inclinacion"]).groupby(["archivo", "diagnostico", "vista"])
        .agg(cobb_aprox=("inclinacion", lambda s: s.max() - s.min()), vertebras=("inclinacion", "size"))
        .query("vertebras >= 4").reset_index())
seg = segmentos[segmentos["archivo"].isin(img["archivo"])].assign(desplazamiento=lambda d: d["desplazamiento_rel"].abs())
if len(cobb):
    col_a, col_b = st.columns(2)
    with col_a:
        mediana = cobb.groupby("diagnostico")["cobb_aprox"].median()
        titulo = "Cobb aproximado por radiografía"
        if {"Escoliosis idiopática (AIS)", "Normal"} <= set(mediana.index):
            titulo = (f"La escoliosis tiene {mediana['Escoliosis idiopática (AIS)']:.0f}° de Cobb "
                      f"frente a {mediana['Normal']:.0f}° de las normales")
        cobb["diag"] = cobb["diagnostico"].map(CORTO)
        fig = px.box(cobb, x="diag", y="cobb_aprox", color="diag", points="all",
                     category_orders={"diag": list(CORTO.values())},
                     color_discrete_map={"Normal": GRIS_TXT, "Código «S»": GRIS_TXT, "Escoliosis": AZUL, "Listesis": ROJO},
                     title=titulo, labels={"cobb_aprox": "Cobb aproximado (°)", "diag": ""})
        fig.update_layout(showlegend=False)
        if "Listesis" in set(cobb["diag"]):
            fig.add_annotation(x="Listesis", y=cobb["cobb_aprox"].max(), text="de perfil (lordosis)", showarrow=False,
                               yshift=18, font=dict(color=GRIS_TXT, size=11))
        st.plotly_chart(estilo(fig), width="stretch")
    with col_b:
        med = seg.groupby(["diagnostico", "segmento"], as_index=False)["desplazamiento"].median()
        med["diag"] = med["diagnostico"].map(CORTO)
        fig = px.line(med, x="segmento", y="desplazamiento", color="diag", markers=True,
                      color_discrete_map={"Normal": GRIS, "Código «S»": GRIS, "Escoliosis": GRIS, "Listesis": ROJO},
                      title="En la listesis, L4–L5 es el segmento más desplazado (tendencia, n = 8)",
                      labels={"desplazamiento": "|desplazamiento| / ancho de la vértebra", "segmento": "", "diag": ""})
        fig.update_traces(line_width=2)
        fig.update_traces(selector=dict(name="Listesis"), line_width=4)
        fig.update_yaxes(tickformat=".2f")
        st.plotly_chart(estilo(fig), width="stretch")
    resumen_p5 = cobb.groupby(["vista", "diagnostico"])["cobb_aprox"].median().round(1).rename("Cobb aprox. (mediana, °)")
    st.dataframe(resumen_p5.reset_index(), width="stretch", hide_index=True)
else:
    st.info("Seleccioná la fuente Lumbar Spine para ver P5.")

st.divider()
st.markdown(
    "**Mensaje.** Lumbar Spine sola no alcanza (33 imágenes completas), pero tiene polígonos y metadatos clínicos: "
    "permite medir forma y alineación (Cobb aproximado). Sumando NHANES —4.405 radiografías completas de perfil— "
    "los datos públicos **sí alcanzan para entrenar el detector**, con dos condiciones que el control de calidad dejó a la vista: "
    "**normalizar la orientación** (un 11 % de NHANES está girada o invertida) y **completar vistas de frente**, "
    "que hoy sólo aporta Lumbar Spine."
)
