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

Implementar un pipeline completo de Ingeniería de Datos sobre un dataset crudo de imágenes médicas anotadas con bounding boxes:

| # | Etapa | Artefacto |
|---|---|---|
| 1 | **ETL** hacia base transaccional SQLite normalizada en **2NF** | `spine_transaccional.db` |
| 2 | **Modelado dimensional** (estrella + copo de nieve) | `spine_dw.db` |
| 3 | **Dashboard interactivo** con mensaje clínico | `app.py` (Streamlit) |

## 🔗 Links

| Recurso | URL |
|---|---|
| 🚀 **Notebook en Colab** | [Abrir en Colab](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb) |
| 📓 **Notebook en GitHub** | [`Proyecto_final.ipynb`](./Proyecto_final.ipynb) |
| 🖥️ **Dashboard** | `app.py` (se renderiza al final del notebook vía proxy nativo de Colab) |
| 📊 **Dataset** | [lumbar-spine-vpxwf (Roboflow Universe)](https://universe.roboflow.com/rp-team/lumbar-spine-vpxwf) |

## 🧬 Dataset

| Campo | Valor |
|---|---|
| **Nombre** | `lumbar-spine-vpxwf` |
| **Plataforma** | Roboflow Universe |
| **Workspace** | `rp-team` |
| **Tipo de tarea** | Object Detection |
| **Formato** | YOLOv8 |
| **Clases** | L1, L2, L3, L4, L5 |
| **Licencia** | CC BY 4.0 |
| **Acceso** | Público (vía SDK oficial de Roboflow) |
| **Split** | train: 50 imgs / 170 anotaciones |

---
## 🛠️ Pipeline implementado

### 1️⃣ Extracción

Descarga automática vía SDK oficial de Roboflow, sin archivos manuales ni rutas privadas.

### 2️⃣ Transformación

- **Parser robusto** que soporta bounding boxes YOLO *y* polígonos.
- Desnormalización de coordenadas a píxeles.
- **EDA**: balance de clases, distribución geométrica (área, aspect ratio).
- **Tratamiento de NAs/outliers**: área mínima, bboxes fuera de imagen, aspect ratio extremo.
- **Carga optimizada**: selección de columnas + tipado (`int8`, `int16`, `float32`, `category`) con **85.9 % de ahorro de memoria**.

### 3️⃣ Carga transaccional (2NF)

Esquema SQLite normalizado:

    datasets ──< images ──< annotations >── classes

- Cada tabla con PK surrogate propia.
- Cero dependencias parciales (2NF garantizada).

### 4️⃣ Modelado dimensional (copo de nieve)

    dim_region
        │
        ▼
    dim_dataset   dim_class   dim_split   dim_image
          \           │          │          /
           ▼          ▼          ▼         ▼
                fact_annotations

- Jerarquía `dim_region → dim_class` = escalable a cervical/torácica.
- Métricas: `area`, `area_ratio`, `aspect_ratio`, `bbox_*`.

### 5️⃣ Dashboard clínico

Aplicación **Streamlit** con Plotly que responde a la pregunta de investigación:

- 📊 KPIs clínicos (cobertura anatómica, balance, calidad geométrica).
- ⚖️ Veredicto automático de aptitud del dataset.
- 🎯 Mensaje explícito sobre **SINS** e inestabilidad espinal.

## ✅ Requisitos de la consigna cubiertos

| Requisito | Cumplimiento |
|---|---|
| Cuaderno Colab público en repo GitHub | ✅ |
| Documentado con celdas Markdown | ✅ |
| Declaración IA formato `"[IA versión]" para "[propósito]"` | ✅ |
| Dataset desde fuente pública (API) | ✅ Roboflow SDK |
| NAs/NULLs y outliers justificados | ✅ Celda 10 + 11 |
| SQLite transaccional 2NF | ✅ Celda 12 |
| SQLite DW (estrella + copo de nieve) | ✅ Celda 13 |
| Interfaz interactiva (Streamlit) | ✅ Celda final |
| Mensaje claro sobre la investigación | ✅ Dashboard + conclusiones |
| Carga optimizada (selección + tipado) | ✅ Celda intermedia |

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
    ├── data/                       # Artefactos regenerables (ignorados por Git)
    │   ├── spine_annotations.csv
    │   ├── spine_transaccional.db
    │   ├── spine_dw.db
    │   └── spine_dataset/
    ├── notebooks/                  # Actividades previas
    ├── src/                        # Código auxiliar
    ├── tp1_ID.ipynb                # 📘 Entregable Unidad 1
    ├── TP2.md                      # 📊 Entregable TP2 (diseño)
    ├── TP2.drawio                  # 📊 Diagramas TP2
    └── README.md

> ⚠️ Los archivos `.db` y `.csv` **no se versionan**: se regeneran al ejecutar el notebook.

---

# 🚀 Cómo reproducir

## Requisitos previos — Colab Secrets

Configurar en el panel 🔑 de Colab:

| Secret | Descripción |
|---|---|
| `ROBOFLOW_API_KEY` | API key de Roboflow ([obtener](https://app.roboflow.com/settings/api)) |
| `GITHUB_TOKEN` | Personal Access Token (scope: `repo`) |
| `NGROK_AUTH_TOKEN` | *(opcional, si se usa ngrok en vez del proxy nativo)* |

## Pasos

1. Abrir el notebook en Colab:  
   👉 [Abrir `Proyecto_final.ipynb` en Colab](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb)
2. Configurar los Secrets (panel 🔑).
3. Ejecutar `Runtime → Run all`.
4. El dashboard se renderiza al final del notebook (sin exponer puertos a internet).

---

# 📊 Preguntas que responde el dashboard

| Pregunta | Métrica |
|---|---|
| ¿Hay cobertura anatómica completa? | Vértebras únicas cubiertas (L1–L5) |
| ¿El dataset está balanceado? | Ratio max/min entre clases |
| ¿Las anotaciones son geométricamente coherentes? | `bbox_w` vs `bbox_h`, área por clase |
| ¿Es apto para entrenar un CDSS de SINS? | Veredicto automático según umbrales clínicos |

---

# 🤖 Declaración de uso de IA

En cumplimiento del requisito de la cátedra, se declara el uso de herramientas de IA generativa:

- **"Claude Sonnet 4.5"** para "asistir en la redacción de celdas Markdown explicativas y justificaciones metodológicas".
- **"ChatGPT 4.5"** para "sugerir estructuras de esquemas SQLite (2NF y estrella/copo de nieve) a partir del análisis del dataset".
- **"GitHub Copilot"** para "autocompletar fragmentos de código Python relacionados con parsing de anotaciones YOLO y visualizaciones con Plotly/Streamlit".

Todo el código fue revisado, adaptado y ejecutado por el autor. Las decisiones metodológicas son responsabilidad exclusiva del tesista.

---

<div align="center">

**Universidad Nacional Arturo Jauretche** · 2026  
*Introducción a la Ingeniería de Datos — Comisión A*

</div>
- [🤖 Declaración de uso de IA](#-declaración-de-uso-de-ia)

---
