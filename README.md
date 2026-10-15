# 🦴 Curso Introducción a la Ingeniería de Datos

**Alumno:** Marcos Kantor  
**Materia:** (20262Q) DIA.04 — Introducción a la Ingeniería de Datos — Comisión A  
**Institución:** ITBA — Instituto Tecnológico de Buenos Aires  
**Tema de tesis:** Inteligencia artificial para la evaluación de inestabilidad espinal (**SINS**, *Spinal Instability Neoplastic Score*)  
**Dirección de tesis:** Ramiro M. Irastorza (IFLySiB-CONICET) · Marcelo A. Cappelletti (LEICI-CONICET, UNAJ)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-OLTP%20%2B%20DW-003B57?logo=sqlite&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Tablero-FF4B4B?logo=streamlit&logoColor=white)
![Licencia del dataset](https://img.shields.io/badge/Dataset-CC%20BY%204.0-02568A)

---

## 📖 Índice

| Entrega | Tema | Archivos | Colab |
|---|---|---|---|
| [🎓 Proyecto Final](#-proyecto-final) | Calidad de un dataset de vértebras lumbares para un CDSS de inestabilidad espinal | [`Proyecto_final.ipynb`](./Proyecto_final.ipynb) · [`app.py`](./app.py) · [`Proyecto_final_defensa.pdf`](./Proyecto_final_defensa.pdf) | [Abrir](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb) |
| [📘 TP1](#-tp1--ingesta-y-exploración-de-gdelt-20) | Ingesta y exploración de GDELT 2.0 | [`tp1_ID.ipynb`](./tp1_ID.ipynb) | [Abrir](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/tp1_ID.ipynb) |
| [📊 TP2](#-tp2--modelado-oltp--olap) | Modelado transaccional y dimensional (GDELT / CAMEO) | [`TP2.md`](./TP2.md) · [`TP2.drawio`](./TP2.drawio) | — |
| [📈 TP3](#-tp3--análisis-multivariante) | Análisis multivariante del ecosistema global de noticias | [`TP3.ipynb`](./TP3.ipynb) | [Abrir](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/TP3.ipynb) |
| [🔎 TP4](#-tp4--detección-de-eventos-atípicos) | Detección de eventos atípicos en GDELT 2.0 | [`TP4.ipynb`](./TP4.ipynb) | [Abrir](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/TP4.ipynb) |

Todos los notebooks se ejecutan en Google Colab con *Entorno de ejecución → Ejecutar todo*, **sin credenciales ni archivos subidos a mano**.

---

# 🎓 Proyecto Final

## 🩺 Pregunta de investigación

> **¿El dataset público *Lumbar Spine* (Roboflow Universe) tiene la cobertura, el balance, la calidad geométrica y la coherencia anatómica necesarias para entrenar el detector de vértebras L1–L5 de un sistema de soporte a la decisión clínica (CDSS) orientado al SINS?**

| # | Pregunta de análisis | Responde con |
|---|---|---|
| P1 | ¿Cuántas imágenes tienen L1–L5 completas y qué tan balanceadas están las clases? | imágenes completas, anotaciones por vértebra |
| P2 | ¿Qué anotaciones tienen tamaño o forma atípicos para su vértebra? | área relativa a sus vecinas, aspecto, relleno, marca de atípico |
| P3 | ¿Se respeta el orden L1→L5 y el aumento de tamaño hacia caudal? | posición vertical relativa, alto relativo, orden coherente |
| P4 | ¿Qué diagnósticos, sexos y edades cubre? | imágenes y completas por diagnóstico, sexo y grupo de edad |

## 📦 Entregables

| Componente | Archivo |
|---|---|
| Entregable técnico (Colab reproducible) | [`Proyecto_final.ipynb`](./Proyecto_final.ipynb) |
| Tablero interactivo (Streamlit) | [`app.py`](./app.py) — se muestra al final del notebook vía proxy nativo de Colab |
| Presentación de la defensa (PDF) | [`Proyecto_final_defensa.pdf`](./Proyecto_final_defensa.pdf) — fuente LaTeX en [`defensa/`](./defensa/) (compilar con XeLaTeX) |
| Dato crudo | [`data/raw/lumbar-spine-vpxwf-v1-yolov8.zip`](./data/raw/lumbar-spine-vpxwf-v1-yolov8.zip) |

## 🧬 Dataset

| Campo | Valor |
|---|---|
| Origen | [rp-team/lumbar-spine-vpxwf](https://universe.roboflow.com/rp-team/lumbar-spine-vpxwf), versión 1 |
| Tarea | Segmentación de instancias (polígonos) en radiografías |
| Formato | Export YOLOv8 crudo |
| Clases | L1, L2, L3, L4, L5 |
| Licencia | CC BY 4.0 (permite redistribuir citando la fuente) |
| Contenido | 50 radiografías (34 anotadas), 170 polígonos; diagnóstico, sexo y edad codificados en el nombre de archivo |
| Acceso | Copia sin modificar en este repositorio, descargada por URL pública y verificada por **SHA-256** (Roboflow exige API key) |

## 🛠️ Pipeline

| Etapa | Qué se hace | Artefacto |
|---|---|---|
| Extracción | Descarga por URL pública, verificación SHA-256, idempotente | zip crudo |
| Transformación | Inventario por imagen, metadatos clínicos por expresiones regulares, parsing de polígonos (fórmula de Gauss), carga optimizada (`usecols` + tipado) | staging CSV |
| Calidad | Faltantes en tres niveles, duplicados (imagen, vértebra), inválidos geométricos, atípicos (Shapiro-Wilk → Tukey 2·IQR, Mahalanobis robusta) sobre variables normalizadas por imagen, control del orden craneocaudal L1→L5 | marcas de calidad |
| Carga transaccional | SQLite en 3FN: `dataset`, `diagnostico`, `region`, `vertebra`, `imagen`, `anotacion` (PK compuesta), `vertice` (PK compuesta) | `spine_oltp.db` |
| Almacén | Copo de nieve, grano "vértebra anotada por imagen": `fact_vertebra_anotada` (PK compuesta por sus dimensiones), `dim_imagen → dim_dataset / dim_diagnostico`, `dim_vertebra → dim_region` | `spine_dw.db` |
| Visualización | Tablero con veredicto ajustable, cobertura imagen × vértebra, balance, progresión anatómica, atípicos y representatividad | `app.py` |

## 📌 Resultados

| Indicador | Valor |
|---|---|
| Imágenes completas L1–L5 | 33 de 50 |
| Razón máx/mín entre clases | 1,03 |
| Anotaciones atípicas | 5 de 169 (3 %) |
| Violaciones del orden L1→L5 | 0 |

**Veredicto:** anotaciones de buena calidad y anatómicamente coherentes, pero con 33 imágenes completas el dataset **no alcanza para entrenar** el detector del CDSS; sirve como conjunto piloto o de validación. Las 16 imágenes sin anotar son todas de escoliosis o del código «S»: el faltante no es aleatorio.

---

# 📘 TP1 — Ingesta y exploración de GDELT 2.0

Ingesta de un día de la tabla de eventos de GDELT 2.0 a partir de `masterfilelist.txt` (~96 archivos de 15 minutos), descarga en paralelo con `ThreadPoolExecutor`, lectura directa desde el ZIP y cálculo de métricas diarias, con gráficos de evolución temporal y un mapa por país.

📓 [`tp1_ID.ipynb`](./tp1_ID.ipynb)

---

# 📊 TP2 — Modelado OLTP + OLAP

Diseño de una base transaccional y un almacén de datos sobre GDELT 2.0 / CAMEO para responder cuatro preguntas del negocio periodístico: rendimiento e impacto (P1), sentimiento por tipo de actor (P2), frecuencia y temporalidad (P3) y cobertura multi-temática (P4).

- **Modelo entidad-relación:** una sola clave por entidad; tres claves foráneas de ubicación (Actor1Geo, Actor2Geo, ActionGeo); las relaciones M:N evento–código CAMEO y evento–artículo se resuelven con los puentes `Evento_CAMEO` y `Mencion`, de clave compuesta.
- **Esquema estrella:** `Fact_Cobertura` con grano día × país × tipo de actor × tema y **PK compuesta por sus dimensiones** (`Dim_Tiempo`, `Dim_Geografia`, `Dim_Tipo_Actor`, `Dim_Tema`); puente `Puente_Evento_Tema` para P4. Métricas aditivas, cada una vinculada a una pregunta.
- Incluye el script SQL y las consultas de P1–P4. La sección 0 del documento detalla las correcciones aplicadas a partir de la devolución del docente.

📄 [`TP2.md`](./TP2.md) · 🧩 [`TP2.drawio`](./TP2.drawio)

---

# 📈 TP3 — Análisis multivariante

Caracterización del ecosistema global de noticias con GDELT 2.0: extensión del almacén con actores, tipo de interacción, región, tono y escala Goldstein; vectores de medias por país, distancias entre países, matrices de correlación y Análisis de Componentes Principales con interpretación de las cargas.

📓 [`TP3.ipynb`](./TP3.ipynb)

---

# 🔎 TP4 — Detección de eventos atípicos

Búsqueda de eventos "raros" en la tabla de eventos de GDELT 2.0 de los últimos 7 días.

| Etapa | Qué se hace |
|---|---|
| Ingesta | Archivos de 15 minutos desde `masterfilelist.txt`, verificación MD5, One Big Table desnormalizada con los libros de códigos CAMEO/FIPS, guardada en Parquet |
| Nulos y ceros | Faltantes estructurales (evento sin Actor2) vs. reales, auditoría de consistencia lógica del codebook, imputación justificada por variable |
| Cardinalidad y dummies | Categorías con menos del 5 % → `OTHER`; variables indicadoras con categoría de referencia; control de varianza casi nula |
| ACP | Estandarización y selección del número mínimo de componentes (varianza acumulada, Kaiser, codo) |
| Atípicos | 10 métodos de 6 familias: distancia global (Z-score, Tukey), T² de Hotelling, SPE, K-Means, k-NN, LOF, DBSCAN, Isolation Forest y autoencoder; acuerdo por Jaccard y consenso por mayoría; exportación a Parquet/CSV |

📓 [`TP4.ipynb`](./TP4.ipynb)

---

# 📂 Estructura del repositorio

    Curso_Introduccion_Ingenieria_Datos/
    ├── Proyecto_final.ipynb          # 🎓 Entregable técnico del proyecto final
    ├── app.py                        # 🖥️ Tablero Streamlit
    ├── Proyecto_final_defensa.pdf    # 🎤 Presentación de la defensa
    ├── defensa/                      # Fuente LaTeX (Beamer) y figuras de la defensa
    ├── data/raw/                     # Dato crudo del proyecto final (CC BY 4.0)
    ├── tp1_ID.ipynb                  # 📘 TP1
    ├── TP2.md · TP2.drawio           # 📊 TP2
    ├── TP3.ipynb                     # 📈 TP3
    ├── TP4.ipynb                     # 🔎 TP4
    ├── notebooks/                    # Notebook de configuración del entorno
    ├── requirements.txt
    └── README.md

> Las bases `.db`, los archivos de staging y las descargas de GDELT **no se versionan**: se regeneran al ejecutar los notebooks.

---

# 🚀 Cómo reproducir

1. Abrir el notebook en Colab con el botón **Abrir** de la tabla del índice.
2. Ejecutar *Entorno de ejecución → Ejecutar todo*. No hace falta ninguna credencial.
3. En el proyecto final, el tablero aparece al final del notebook. Fuera de Colab: `pip install -r requirements.txt` y `streamlit run app.py` en la carpeta de trabajo que crea el notebook.

---

# 🤖 Declaración de uso de IA

Cada notebook incluye su propia declaración y su guía de instrucciones (*human-in-the-loop*). Resumen:

- **"DeepSeek"** para "comprender el formato de GDELT 2.0 y organizar el flujo de ingesta del TP1".
- **"Gemini 2.5 Pro"** para "asesorar la reimplementación del almacén de datos en el TP3".
- **"Claude Sonnet 4.5"** para "asistir en la redacción de celdas Markdown y justificaciones metodológicas".
- **"ChatGPT 4.5"** para "sugerir estructuras de esquemas SQLite en la primera versión del proyecto final".
- **"GitHub Copilot"** para "autocompletar parsing de anotaciones YOLO y gráficos con Plotly/Streamlit".
- **"Claude Opus 5.5"** para "reestructurar el proyecto final (extracción sin credenciales, control de calidad, modelos con claves compuestas, tablero y presentación de la defensa), aplicar las correcciones del TP2 y desarrollar el TP4".

Las decisiones metodológicas fueron definidas y validadas por el autor.

---

<div align="center">

**ITBA** · 2026  
*Introducción a la Ingeniería de Datos — Comisión A*

</div>
