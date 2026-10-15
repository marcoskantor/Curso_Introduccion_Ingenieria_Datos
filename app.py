import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

DB = Path(__file__).with_name("spine_dw.db")
ORDEN = ["L1", "L2", "L3", "L4", "L5"]

st.set_page_config(page_title="Vértebras lumbares — aptitud del dataset", layout="wide")


@st.cache_data
def cargar():
    con = sqlite3.connect(DB)
    hechos = pd.read_sql("""
        SELECT i.archivo, i.split, i.resolucion, i.sexo, i.grupo_edad, d.nombre AS diagnostico,
               v.codigo AS vertebra, v.orden_craneocaudal,
               f.area_norm, f.alto_norm, f.aspecto, f.relleno, f.cy_rel,
               f.es_atipico, f.orden_coherente, f.motivo_atipico
        FROM fact_vertebra_anotada f
        JOIN dim_vertebra v     USING (vertebra_key)
        JOIN dim_imagen i       USING (imagen_key)
        JOIN dim_diagnostico d  ON d.diagnostico_key = i.diagnostico_key""", con)
    imagenes = pd.read_sql("""
        SELECT i.archivo, i.split, i.resolucion, i.sexo, i.grupo_edad, i.anotada, i.vertebras_anotadas, i.completa,
               d.nombre AS diagnostico
        FROM dim_imagen i JOIN dim_diagnostico d ON d.diagnostico_key = i.diagnostico_key""", con)
    con.close()
    return hechos, imagenes


hechos, imagenes = cargar()

# ------------------------------------------------------------------ barra lateral
st.sidebar.header("Filtros")
diags = sorted(imagenes["diagnostico"].unique())
diag_sel = st.sidebar.multiselect("Diagnóstico (del nombre de archivo)", diags, default=diags) or diags
sexo_sel = st.sidebar.multiselect("Sexo", sorted(imagenes["sexo"].unique()), default=sorted(imagenes["sexo"].unique()))
incluir_atipicos = st.sidebar.toggle("Incluir anotaciones atípicas", value=True)
st.sidebar.divider()
st.sidebar.header("Supuesto del veredicto")
minimo = st.sidebar.slider("Imágenes completas (L1–L5) necesarias para entrenar", 50, 1000, 200, step=50,
                           help="Orden de magnitud habitual para entrenar un detector de 5 clases desde un modelo preentrenado.")

img = imagenes[imagenes["diagnostico"].isin(diag_sel) & imagenes["sexo"].isin(sexo_sel or imagenes["sexo"].unique())]
h = hechos[hechos["archivo"].isin(img["archivo"])]
if not incluir_atipicos:
    h = h[h["es_atipico"] == 0]

# ------------------------------------------------------------------ encabezado y veredicto
st.title("¿Alcanza este dataset para entrenar el detector de vértebras de un CDSS de inestabilidad espinal?")
st.caption("Proyecto Final — Introducción a la Ingeniería de Datos · Marcos Kantor · "
           "Datos: Lumbar Spine (rp-team, Roboflow Universe, CC BY 4.0) · Fuente del tablero: almacén `spine_dw.db`")

completas = int(img["completa"].sum())
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Imágenes", len(img))
c2.metric("Anotadas", int(img["anotada"].sum()), f"{100 * img['anotada'].mean():.0f} %" if len(img) else None)
c3.metric("Completas L1–L5", completas)
c4.metric("Anotaciones atípicas", f"{100 * h['es_atipico'].mean():.1f} %" if len(h) else "—")
c5.metric("Rompen el orden L1→L5", int((1 - h["orden_coherente"]).sum()) if len(h) else 0)

if completas >= minimo:
    st.success(f"**Apto para entrenar:** {completas} imágenes completas superan el mínimo supuesto de {minimo}.")
elif completas >= minimo / 4:
    st.warning(f"**Insuficiente para entrenar desde cero; útil como ajuste fino o validación:** "
               f"{completas} imágenes completas frente a {minimo} necesarias.")
else:
    st.error(f"**No alcanza para entrenar el detector.** Con {completas} imágenes completas "
             f"({100 * completas / minimo:.0f} % del mínimo supuesto de {minimo}) sirve como **conjunto piloto o de validación** "
             f"y para probar el pipeline, pero hay que sumar datos.")

st.divider()

# ------------------------------------------------------------------ P1 cobertura y balance
st.subheader("P1 · Cobertura y balance")
col_a, col_b = st.columns([3, 2])
with col_a:
    estado = h.assign(estado=h["es_atipico"].map({0: "anotada", 1: "anotada (atípica)"}))
    grilla = (img[["archivo"]].merge(estado[["archivo", "vertebra", "estado"]], how="left")
              .pivot_table(index="archivo", columns="vertebra", values="estado", aggfunc="first")
              .reindex(columns=ORDEN).fillna("falta"))
    codigo = grilla.replace({"falta": 0, "anotada": 1, "anotada (atípica)": 2}).astype(int)
    fig = px.imshow(codigo, color_continuous_scale=[(0, "#e5e5e5"), (0.5, "#4f81bd"), (1, "#c0504d")],
                    aspect="auto", labels={"color": "estado"})
    fig.update_layout(coloraxis_showscale=False, height=520, yaxis=dict(showticklabels=False),
                      title="Cobertura imagen × vértebra (gris = falta, azul = anotada, rojo = atípica)")
    st.plotly_chart(fig, width="stretch")
with col_b:
    balance = h.groupby("vertebra").size().reindex(ORDEN, fill_value=0).rename("anotaciones").reset_index()
    fig = px.bar(balance, x="vertebra", y="anotaciones", text="anotaciones", title="Anotaciones por vértebra")
    st.plotly_chart(fig, width="stretch")
    if balance["anotaciones"].min() > 0:
        st.caption(f"Razón máx/mín entre clases: {balance['anotaciones'].max() / balance['anotaciones'].min():.2f} "
                   "(1 = balance perfecto).")

# ------------------------------------------------------------------ P3 coherencia anatómica
st.subheader("P3 · Coherencia anatómica")
col_a, col_b = st.columns(2)
with col_a:
    fig = px.box(h, x="vertebra", y="alto_norm", points="all", color="vertebra",
                 category_orders={"vertebra": ORDEN},
                 title="Alto de cada vértebra relativo a sus vecinas (se espera un aumento hacia L5)",
                 labels={"alto_norm": "alto / mediana del alto en la imagen"})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, width="stretch")
with col_b:
    fig = px.line(h.sort_values("orden_craneocaudal"), x="vertebra", y="cy_rel", line_group="archivo",
                  color=h.sort_values("orden_craneocaudal")["orden_coherente"].map({1: "orden correcto", 0: "rompe el orden"}),
                  category_orders={"vertebra": ORDEN}, markers=True,
                  title="Posición vertical de cada vértebra por imagen (debe crecer de L1 a L5)",
                  labels={"cy_rel": "centroide vertical / alto de la imagen", "color": ""})
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, width="stretch")

# ------------------------------------------------------------------ P2 calidad geométrica
st.subheader("P2 · Calidad geométrica de las anotaciones")
var = st.radio("Variable", ["area_norm", "aspecto", "relleno"], horizontal=True,
               format_func={"area_norm": "área relativa a sus vecinas", "aspecto": "relación de aspecto",
                            "relleno": "relleno del polígono"}.get)
fig = px.strip(h, x="vertebra", y=var, color=h["es_atipico"].map({0: "normal", 1: "atípica"}),
               category_orders={"vertebra": ORDEN}, hover_data=["archivo", "motivo_atipico"],
               color_discrete_map={"normal": "#4f81bd", "atípica": "#c0504d"}, labels={"color": ""})
st.plotly_chart(fig, width="stretch")
atip = h[h["es_atipico"] == 1][["archivo", "vertebra", "diagnostico", "motivo_atipico"]]
st.markdown(f"**{len(atip)} anotaciones marcadas para revisión manual**")
st.dataframe(atip, width="stretch", hide_index=True)

# ------------------------------------------------------------------ P4 representatividad
st.subheader("P4 · Representatividad")
col_a, col_b = st.columns(2)
with col_a:
    rep = img.groupby(["diagnostico", "completa"]).size().reset_index(name="imagenes")
    rep["completa"] = rep["completa"].map({1: "completa L1–L5", 0: "incompleta o sin anotar"})
    fig = px.bar(rep, y="diagnostico", x="imagenes", color="completa", orientation="h",
                 title="Imágenes por diagnóstico", color_discrete_sequence=["#4f81bd", "#bfbfbf"], labels={"completa": ""})
    st.plotly_chart(fig, width="stretch")
with col_b:
    fig = px.histogram(img, x="grupo_edad", color="sexo", barmode="group", title="Edad y sexo (del nombre de archivo)",
                       category_orders={"grupo_edad": ["<18", "18-39", "40-64", "65+", "sin dato"]})
    st.plotly_chart(fig, width="stretch")

st.divider()
st.markdown(
    "**Mensaje.** El dataset tiene clases balanceadas y anotaciones geométricamente consistentes, "
    "pero una parte de las imágenes no está anotada y las completas son pocas: alcanza para validar el pipeline del CDSS "
    "y como conjunto de prueba, no para entrenar el detector. La espondilolistesis incluida es directamente relevante "
    "para el criterio de **alineación** del SINS."
)
