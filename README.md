# 🦴 Curso Introducción a la Ingeniería de Datos

**Alumno:** Marcos Kantor  
**Comisión:** (20262Q) DIA.04 — Introducción a la Ingeniería de Datos — Comisión A  
**Institución:** Universidad Nacional Arturo Jauretche  
**Tema de Tesis:** Diagnóstico por imágenes para el cálculo de **SINS** (*Spinal Instability Neoplastic Score*)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-2NF%20%2B%20DW-003B57?logo=sqlite&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?logo=streamlit&logoColor=white)
![Roboflow](https://img.shields.io/badge/Roboflow-Dataset-6706CE)

---

## 📖 Índice

- [🎓 Proyecto Final (entregable principal)](#-proyecto-final-entregable-principal)
- [📘 Unidad 1 — Herramientas de trabajo](#-unidad-1--herramientas-de-trabajo)
- [📊 TP2 — Modelado OLTP + OLAP](#-tp2--modelado-oltp--olap)
- [📂 Estructura del repositorio](#-estructura-del-repositorio)
- [🚀 Cómo reproducir](#-cómo-reproducir)

- # 🎓 Proyecto Final (entregable principal)

## 🩺 Pregunta de investigación

> **¿Es el dataset público de vértebras lumbares (L1–L5) apto, en términos de calidad, balance de clases y cobertura anatómica, para entrenar un sistema de soporte a la decisión clínica (CDSS) orientado al cálculo automatizado del SINS?**

## 🎯 Objetivo

Pipeline completo de Ingeniería de Datos sobre el dataset crudo de radiografías lumbares anotadas (polígonos L1–L5):

| # | Etapa | Artefacto |
|---|---|---|
| 1 | **Extracción** reproducible sin credenciales (copia CC BY 4.0 en `data/raw/`, verificada por SHA-256) | zip crudo YOLOv8 |
| 2 | **ETL**: inventario, parsing de polígonos, metadatos clínicos del nombre de archivo, carga optimizada, NAs, duplicados y atípicos | staging |
| 3 | **Base transaccional SQLite** normalizada (1FN–3FN, claves compuestas) | `spine_oltp.db` |
| 4 | **Almacén de datos SQLite** en copo de nieve, grano "vértebra anotada por imagen" | `spine_dw.db` |
| 5 | **Tablero Streamlit** con veredicto sobre la aptitud del dataset | `app.py` |

## 🔗 Links

| Recurso | URL |
|---|---|
| 🚀 **Notebook en Colab** | [Abrir en Colab](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb) |
| 📓 **Notebook en GitHub** | [`Proyecto_final.ipynb`](./Proyecto_final.ipynb) |
| 🖥️ **Tablero** | [`app.py`](./app.py) (se muestra al final del notebook vía proxy nativo de Colab) |
| 📊 **Dataset original** | [lumbar-spine-vpxwf (Roboflow Universe)](https://universe.roboflow.com/rp-team/lumbar-spine-vpxwf) |
| 📦 **Copia cruda usada** | [`data/raw/lumbar-spine-vpxwf-v1-yolov8.zip`](./data/raw/lumbar-spine-vpxwf-v1-yolov8.zip) |

## 🧬 Dataset

| Campo | Valor |
|---|---|
| **Nombre** | `rp-team/lumbar-spine-vpxwf`, versión 1 |
| **Tarea** | Segmentación de instancias (polígonos) |
| **Formato** | YOLOv8 (export crudo) |
| **Clases** | L1, L2, L3, L4, L5 |
| **Licencia** | CC BY 4.0 (permite redistribuir citando la fuente) |
| **Acceso** | URL pública de este repositorio — **sin API key** |
| **Contenido** | 50 radiografías (34 anotadas), 170 polígonos; diagnóstico, sexo y edad en el nombre de archivo |

## 🛠️ Pipeline implementado

- **Extracción:** descarga por URL pública, verificación SHA-256, idempotente. El SDK de Roboflow queda como alternativa opcional.
- **Carga optimizada:** `usecols` + tipado (`int8`, `int16`, `Int8` nullable, `float32`, `category`).
- **Faltantes:** imágenes sin anotar (se conservan marcadas), completitud L1–L5 por imagen, metadatos no identificables (nulos, sin imputar).
- **Duplicados:** una vértebra repetida en la misma imagen se resuelve por cercanía a la posición anatómica esperada.
- **Atípicos:** reglas geométricas (descarte), Tukey 2·IQR por vértebra tras Shapiro-Wilk, Mahalanobis robusta, y control del orden craneocaudal L1→L5 (marcados, no descartados).
- **Transaccional:** `dataset`, `diagnostico`, `region`, `vertebra`, `imagen`, `anotacion` (PK compuesta imagen+vértebra), `vertice` (PK compuesta; 1FN del polígono).
- **Almacén:** `fact_vertebra_anotada` con PK compuesta `(imagen_key, vertebra_key)`; dimensiones `dim_vertebra → dim_region`, `dim_imagen → dim_dataset`, `dim_imagen → dim_diagnostico`.
- **Tablero:** veredicto ajustable, cobertura imagen × vértebra, balance, progresión anatómica, calidad geométrica y representatividad (P1–P4).

## ✅ Requisitos de la consigna cubiertos

| Requisito | Dónde |
|---|---|
| Colab público en el repo, Markdown, reproducible con *Ejecutar todo* | `Proyecto_final.ipynb` |
| Declaración de uso de IA con el formato exigido | sección inicial del notebook |
| Instrucciones de la IA (*human-in-the-loop*) | sección inicial del notebook |
| Dataset crudo de fuente pública, afín a la tesis, sin credenciales | sección 1 |
| Carga optimizada (columnas + tipado) | sección 2 |
| NAs y atípicos con decisiones justificadas | sección 3 |
| SQLite transaccional ≥ 2FN | sección 4 |
| SQLite almacén (copo de nieve), hechos separados de dimensiones | sección 5 |
| Visualización interactiva con mensaje claro | sección 6 |

---

# 📘 Unidad 1 — Herramientas de trabajo

## 📌 Descripción

Trabajo práctico correspondiente a la **Unidad 1** del curso. Objetivos:

1. Generar un script en Python **asistido por IA (LLM)** para ingesta de datos desde fuente externa.
2. Identificar componentes fundamentales en scripts Python (librerías, variables, métodos, estructuras de control).
3. Aplicar principios de **modularización y buenas prácticas** (KISS, comentarios, docstrings).

El script descarga el dataset **"Lumbar Spine"** desde **Roboflow Universe**, lo procesa y genera resumen estadístico + visualizaciones de bounding boxes en radiografías de columna lumbar.

## 📓 Notebook

- [`tp1_ID.ipynb`](./tp1_ID.ipynb) — entregable de la Unidad 1

---

# 📊 TP2 — Modelado OLTP + OLAP

## 📌 Mapa de correspondencia con la consigna

| Punto del TP | Sección en este documento |
|---|---|
| 1) Diseño OLTP (ER + PK/FK + relaciones) | Sección 1 |
| 2) Modelo dimensional OLAP (Estrella + Dim_Tiempo + Bridge) | Sección 2 |
| 3) Implementación SQL (opcional) | Sección 5 |

## 🎯 Resumen ejecutivo

Este trabajo diseña dos modelos de datos complementarios sobre el flujo **GDELT 2.0 / CAMEO 1.1b3**:

- **Modelo OLTP (Sección 1):** captura cada noticia/evento con sus actores, ubicaciones, fuente y códigos CAMEO, incluyendo la tabla **Mentions** de GDELT 2.0 para trazabilidad de cobertura.
- **Modelo OLAP (Sección 2):** esquema estrella con tabla de hechos `Fact_Analisis_Medios` y dimensiones Tiempo, Ubicación, Actor, Fuente y CAMEO. Incluye **Bridge Table** para resolver la relación M:N entre eventos y múltiples códigos CAMEO (P4).
- **Preguntas de negocio cubiertas:** P1 (Rendimiento/Impacto), P2 (Sentimiento por tipo de actor), P3 (Frecuencia y Temporalidad), P4 (Cobertura multi-temática CAMEO).

## 📓 Entregables

- [`TP2.md`](./TP2.md) — documento de diseño
- [`TP2.drawio`](./TP2.drawio) — diagramas ER + estrella

---

# 📂 Estructura del repositorio

    Curso_Introduccion_Ingenieria_Datos/
    ├── Proyecto_final.ipynb        # 🎓 Entregable final (pipeline completo)
    ├── app.py                      # 🖥️ Dashboard Streamlit (SINS)
    ├── requirements.txt            # Dependencias
    ├── .gitignore
    ├── data/
    │   └── raw/lumbar-spine-vpxwf-v1-yolov8.zip   # dato crudo (CC BY 4.0)
    ├── notebooks/                  # Actividades previas
    ├── src/                        # Código auxiliar
    ├── tp1_ID.ipynb                # 📘 Entregable Unidad 1
    ├── TP2.md                      # 📊 Entregable TP2 (diseño)
    ├── TP2.drawio                  # 📊 Diagramas TP2
    └── README.md

> ⚠️ Las bases `.db` y los archivos de staging **no se versionan**: se regeneran al ejecutar el notebook.

---

# 🚀 Cómo reproducir

No hace falta ninguna credencial.

1. Abrir el notebook en Colab:
   👉 [Abrir `Proyecto_final.ipynb` en Colab](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb)
2. Ejecutar *Entorno de ejecución → Ejecutar todo*.
3. El tablero se muestra al final del notebook (proxy nativo de Colab, sin exponer puertos a internet).

---

# 📊 Preguntas que responde el dashboard

| Pregunta | Métrica |
|---|---|
| P1 · ¿Cuántas imágenes tienen L1–L5 completas y qué tan balanceadas están las clases? | imágenes completas, anotaciones por vértebra |
| P2 · ¿Qué anotaciones tienen tamaño o forma atípicos para su vértebra? | área relativa a sus vecinas, aspecto, relleno, marca de atípico |
| P3 · ¿Se respeta el orden L1→L5 y el aumento de tamaño hacia caudal? | posición vertical relativa, alto relativo, orden coherente |
| P4 · ¿Qué diagnósticos, sexos y edades cubre? | imágenes y completas por diagnóstico, sexo y grupo de edad |
| ¿Alcanza para entrenar el detector del CDSS? | veredicto con umbral ajustable |

---

# 🤖 Declaración de uso de IA

En cumplimiento del requisito de la cátedra, se declara el uso de herramientas de IA generativa:

- **"Claude Sonnet 4.5"** para "asistir en la redacción de celdas Markdown explicativas y justificaciones metodológicas".
- **"ChatGPT 4.5"** para "sugerir estructuras de esquemas SQLite (2NF y estrella/copo de nieve) a partir del análisis del dataset".
- **"GitHub Copilot"** para "autocompletar fragmentos de código Python relacionados con parsing de anotaciones YOLO y visualizaciones con Plotly/Streamlit".
- **"Claude Opus 5.5"** para "reestructurar el proyecto final (extracción sin credenciales, control de calidad, modelos con claves compuestas y tablero), aplicar correcciones del TP2 y desarrollar el TP4".

Todo el código fue revisado, adaptado y ejecutado por el autor. Las decisiones metodológicas son responsabilidad exclusiva del tesista.

---

<div align="center">

**Universidad Nacional Arturo Jauretche** · 2026  
*Introducción a la Ingeniería de Datos — Comisión A*

</div>
- [🤖 Declaración de uso de IA](#-declaración-de-uso-de-ia)

---
