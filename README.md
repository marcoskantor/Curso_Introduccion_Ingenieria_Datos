# Proyecto Final — Introducción a la Ingeniería de Datos

**Alumno:** Marcos Kantor  
**Comisión:** (20262Q) DIA.04 — Introducción a la Ingeniería de Datos — Comisión A  
**Institución:** Universidad Nacional Arturo Jauretche  
**Tema de Tesis:** Diagnóstico por imágenes para el cálculo de SINS (*Spinal Instability Neoplastic Score*)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb)

---

## 📌 Pregunta de investigación

¿Es el dataset público de vértebras lumbares (L1–L5) apto, en términos de calidad, balance de clases y cobertura anatómica, para entrenar un sistema de soporte a la decisión clínica (CDSS) orientado al cálculo automatizado del **SINS**?

---

## 🎯 Objetivo

Implementar un pipeline completo de Ingeniería de Datos sobre un dataset crudo de imágenes médicas anotadas con bounding boxes, que incluya:

1. **ETL** hacia una base transaccional SQLite normalizada en **2NF**.
2. **Modelado dimensional** en SQLite (esquema estrella + copo de nieve).
3. **Interfaz interactiva** (Streamlit) que transmita el mensaje clínico de la investigación.

---

## 🔗 Links

| Recurso | URL |
|---|---|
| **Notebook (Colab)** | [Abrir en Colab](https://colab.research.google.com/github/marcoskantor/Curso_Introduccion_Ingenieria_Datos/blob/main/Proyecto_final.ipynb) |
| **Notebook (GitHub)** | [`Proyecto_final.ipynb`](./Proyecto_final.ipynb) |
| **Dashboard** | `app.py` (se levanta desde el notebook vía proxy nativo de Colab) |
| **Dataset** | [lumbar-spine-vpxwf (Roboflow Universe)](https://universe.roboflow.com/rp-team/lumbar-spine-vpxwf) |

---

## 📂 Estructura del repositorio
