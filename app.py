
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

st.set_page_config(
    page_title="SINS — Inestabilidad Espinal",
    layout="wide"
)

st.title("🦴 ¿Es este dataset apto para entrenar un CDSS de inestabilidad espinal?")
st.markdown(
    "**Proyecto Final — Entregable Técnico**  \n"
    "*Marcos Kantor — Director: Ramiro Irastorza — Codirector: Marcelo Cappelletti*  \n"
    "**Materia:** DIA.04 — Introducción a la Ingeniería de Datos"
)
st.divider()

# --- Mensaje de investigación ---
st.markdown("""
### Contexto clínico

La **inestabilidad espinal** —a diferencia de la compresión medular— está frecuentemente subdiagnosticada.
El **SINS** (Spinal Instability Neoplastic Score) es la escala clínica validada para evaluarla, pero su uso
está limitado a especialistas. Un CDSS basado en IA requiere un dataset con:

1. **Cobertura anatómica** de las vértebras relevantes (L1–L5 en este caso).
2. **Balance de clases** adecuado para no sesgar el entrenamiento.
3. **Calidad geométrica** de las anotaciones (bounding boxes sin outliers).
""")
st.divider()

conn = sqlite3.connect("spine_dw.db")

# --- Sidebar ---
st.sidebar.header("Filtros")
splits = pd.read_sql("SELECT name FROM dim_split", conn)["name"].tolist()
clases_disponibles = pd.read_sql("SELECT name FROM dim_class", conn)["name"].tolist()
clases_sel = st.sidebar.multiselect("Clases", clases_disponibles, default=clases_disponibles)
if not clases_sel:
    clases_sel = clases_disponibles

ph_cls = ",".join(["?"] * len(clases_sel))
q = f"""
SELECT c.name AS clase, s.name AS split, i.filename AS filename,
       f.bbox_x, f.bbox_y, f.bbox_w, f.bbox_h, f.area, f.area_ratio, f.aspect_ratio,
       f.image_width, f.image_height
FROM fact_annotations f
JOIN dim_class c ON f.class_key = c.class_key
JOIN dim_split s ON f.split_key = s.split_key
JOIN dim_image i ON f.image_key = i.image_key
WHERE c.name IN ({ph_cls})
"""
df = pd.read_sql(q, conn, params=clases_sel)

# --- KPIs clínicos ---
st.subheader("📊 Indicadores de aptitud clínica")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Anotaciones", f"{len(df):,}")
c2.metric("Vértebras cubiertas", f"{df['clase'].nunique()}/5")
c3.metric("Imágenes únicas", f"{df['filename'].nunique():,}")
c4.metric("Área promedio (px²)", f"{df['area'].mean():.1f}")

# --- Balance de clases ---
st.subheader("1️⃣ Balance de clases (aptitud para entrenamiento)")
conteo = df.groupby("clase").size().reset_index(name="total").sort_values("clase")
fig1 = px.bar(conteo, x="clase", y="total", color="clase", text="total",
              color_discrete_sequence=px.colors.qualitative.Set2)
fig1.update_traces(textposition="outside")
st.plotly_chart(fig1, use_container_width=True)

max_c, min_c = conteo["total"].max(), conteo["total"].min()
ratio = max_c / min_c if min_c > 0 else float("inf")
if ratio <= 1.5:
    st.success(f"✅ Clases balanceadas (ratio max/min = {ratio:.2f}). Apto para entrenamiento.")
elif ratio <= 3:
    st.warning(f"⚠️  Desbalance moderado (ratio max/min = {ratio:.2f}). Considerar augmentation.")
else:
    st.error(f"❌ Desbalance severo (ratio max/min = {ratio:.2f}). Requiere re-muestreo.")

# --- Calidad geométrica ---
st.subheader("2️⃣ Calidad geométrica de las anotaciones")
fig2 = px.scatter(df, x="bbox_w", y="bbox_h", color="clase",
                  hover_data=["filename"], opacity=0.6,
                  labels={"bbox_w": "Ancho (px)", "bbox_h": "Alto (px)"})
st.plotly_chart(fig2, use_container_width=True)

# --- Distribución de áreas ---
st.subheader("3️⃣ Distribución de áreas por vértebra")
fig3 = px.box(df, x="clase", y="area", color="clase", log_y=True,
              labels={"area": "Área (px², escala log)"},
              color_discrete_sequence=px.colors.qualitative.Set2)
st.plotly_chart(fig3, use_container_width=True)

st.divider()
st.caption(
    "**Fuente:** Roboflow Universe — rp-team/lumbar-spine-vpxwf (CC BY 4.0)  |  "
    "**Mensaje:** este dashboard evalúa la aptitud del dataset para un CDSS basado en SINS."
)
