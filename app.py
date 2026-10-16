import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB = Path(__file__).with_name("spine_dw.db")
ORDEN = ["L1", "L2", "L3", "L4", "L5"]
FUENTE = {"lumbar-spine-vpxwf": "Lumbar Spine (polígonos)", "nhanes-l1-l5": "NHANES (cajas)"}

st.set_page_config(page_title="Vértebras lumbares — aptitud de los datos", layout="wide")
AZUL, AZUL_CLARO, GRIS, ROJO = "#02568A", "#7FA9C8", "#C9CED6", "#C0392B"      # paleta institucional ITBA
px.defaults.color_discrete_sequence = [AZUL, AZUL_CLARO, ROJO, GRIS, "#3E7CB1", "#9BB7D4"]


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
c1.metric("Imágenes", f"{len(img):,}")
c2.metric("Anotadas", f"{int(img['anotada'].sum()):,}", f"{100 * img['anotada'].mean():.0f} %" if len(img) else None)
c3.metric("Completas L1–L5", f"{completas:,}")
c4.metric("Anotaciones atípicas", f"{100 * h['es_atipico'].mean():.1f} %" if len(h) else "—")
c5.metric("Giradas o invertidas", f"{int(img['orientacion'].isin(['girada 90°', 'invertida']).sum()):,}")

if completas >= minimo:
    st.success(f"**Apto para entrenar:** {completas:,} imágenes completas superan el mínimo supuesto de {minimo:,}.")
elif completas >= minimo / 4:
    st.warning(f"**Insuficiente para entrenar desde cero; útil como ajuste fino o validación:** "
               f"{completas:,} imágenes completas frente a {minimo:,} necesarias.")
else:
    st.error(f"**No alcanza para entrenar el detector.** Con {completas:,} imágenes completas "
             f"({100 * completas / minimo:.0f} % del mínimo supuesto de {minimo:,}) sirve como **conjunto piloto o de validación**; "
             f"hay que sumar datos.")
por_fuente = (img.groupby("fuente").agg(imagenes=("archivo", "size"), anotadas=("anotada", "sum"),
                                         completas=("completa", "sum")).reset_index())
st.dataframe(por_fuente, width="stretch", hide_index=True)

st.divider()

# ------------------------------------------------------------------ P1 cobertura y balance
st.subheader("P1 · Cobertura y balance")
col_a, col_b = st.columns(2)
with col_a:
    est = img.assign(estado=img["anotada"].map({0: "sin anotar"}).fillna(img["completa"].map({1: "completa L1–L5", 0: "incompleta"})))
    rep = est.groupby(["fuente", "estado"]).size().reset_index(name="imagenes")
    fig = px.bar(rep, y="fuente", x="imagenes", color="estado", orientation="h", log_x=True,
                 category_orders={"estado": ["completa L1–L5", "incompleta", "sin anotar"]},
                 color_discrete_map={"completa L1–L5": AZUL, "incompleta": AZUL_CLARO, "sin anotar": GRIS},
                 title="Imágenes por fuente y estado (escala log)", labels={"fuente": "", "estado": ""})
    st.plotly_chart(fig, width="stretch")
with col_b:
    balance = h.groupby(["fuente", "vertebra"]).size().rename("anotaciones").reset_index()
    fig = px.bar(balance, x="vertebra", y="anotaciones", color="fuente", barmode="group", log_y=True,
                 category_orders={"vertebra": ORDEN}, title="Anotaciones por vértebra (escala log)",
                 color_discrete_sequence=[AZUL, AZUL_CLARO], labels={"fuente": ""})
    st.plotly_chart(fig, width="stretch")

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
    fig = px.bar(ori, x="orientacion", y="imagenes", color="fuente", barmode="group", text="imagenes",
                 category_orders={"orientacion": ["vertical", "girada 90°", "invertida"]},
                 color_discrete_sequence=[AZUL, AZUL_CLARO],
                 title="Orientación de las radiografías", labels={"orientacion": "", "fuente": ""})
    st.plotly_chart(fig, width="stretch")
with col_b:
    vert = h[h["orientacion"] == "vertical"]
    muestra = vert["archivo"].drop_duplicates().sample(min(200, vert["archivo"].nunique()), random_state=0)
    vs = vert[vert["archivo"].isin(muestra)].sort_values("orden_craneocaudal")
    fig = px.line(vs, x="vertebra", y="cy_rel", line_group="archivo",
                  color=vs["orden_coherente"].map({1: "orden correcto", 0: "rompe el orden"}),
                  color_discrete_map={"orden correcto": AZUL_CLARO, "rompe el orden": ROJO},
                  category_orders={"vertebra": ORDEN}, markers=True,
                  title="Posición vertical por imagen (muestra de 200 verticales)",
                  labels={"cy_rel": "centroide vertical / alto de la imagen", "color": ""})
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch")
st.caption(f"Cajas o polígonos que rompen el orden L1→L5 a lo largo de la columna (errores de etiqueta): "
           f"{int((1 - h['orden_coherente']).sum())} en {h.loc[h['orden_coherente'] == 0, 'archivo'].nunique()} imágenes.")

# ------------------------------------------------------------------ P2 calidad geométrica
st.subheader("P2 · Calidad geométrica de las anotaciones (polígonos de Lumbar Spine)")
if len(poly):
    var = st.radio("Variable", ["area_norm", "aspecto", "relleno"], horizontal=True,
                   format_func={"area_norm": "área relativa a sus vecinas", "aspecto": "relación de aspecto",
                                "relleno": "relleno del polígono"}.get)
    fig = px.strip(poly, x="vertebra", y=var, color=poly["es_atipico"].map({0: "normal", 1: "atípica"}),
                   category_orders={"vertebra": ORDEN}, hover_data=["archivo", "motivo_atipico"],
                   color_discrete_map={"normal": AZUL_CLARO, "atípica": ROJO}, labels={"color": ""})
    st.plotly_chart(fig, width="stretch")
atip = h[h["es_atipico"] == 1][["fuente", "archivo", "vertebra", "motivo_atipico"]]
st.markdown(f"**{len(atip)} anotaciones marcadas para revisión manual**")
st.dataframe(atip, width="stretch", hide_index=True)

# ------------------------------------------------------------------ P4 representatividad
st.subheader("P4 · Representatividad")
col_a, col_b = st.columns(2)
with col_a:
    rep = img.groupby(["diagnostico", "vista"]).size().reset_index(name="imagenes")
    fig = px.bar(rep, y="diagnostico", x="imagenes", color="vista", orientation="h", log_x=True,
                 color_discrete_map={"frente": AZUL, "perfil": AZUL_CLARO},
                 title="Imágenes por diagnóstico y vista (escala log)", labels={"diagnostico": ""})
    st.plotly_chart(fig, width="stretch")
with col_b:
    con_dato = img[img["grupo_edad"] != "sin dato"]
    fig = px.histogram(con_dato, x="grupo_edad", color="sexo", barmode="group",
                       title="Edad y sexo (sólo Lumbar Spine: NHANES no trae metadatos)",
                       category_orders={"grupo_edad": ["<18", "18-39", "40-64", "65+"]})
    st.plotly_chart(fig, width="stretch")

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
        fig = px.box(cobb, x="diagnostico", y="cobb_aprox", color="vista", points="all",
                     color_discrete_map={"frente": AZUL, "perfil": ROJO},
                     title="Cobb aproximado por imagen", labels={"cobb_aprox": "grados", "diagnostico": ""})
        st.plotly_chart(fig, width="stretch")
    with col_b:
        med = seg.groupby(["diagnostico", "segmento"], as_index=False)["desplazamiento"].median()
        fig = px.line(med, x="segmento", y="desplazamiento", color="diagnostico", markers=True,
                      title="Desplazamiento entre vértebras vecinas (mediana)",
                      labels={"desplazamiento": "|desplazamiento| / ancho de la vértebra", "segmento": ""})
        st.plotly_chart(fig, width="stretch")
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
