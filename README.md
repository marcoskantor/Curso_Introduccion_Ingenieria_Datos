# Curso Introducción a la Ingeniería de Datos

## Actividad Unidad 1 – Herramientas de trabajo

**Alumno:** Marcos Kantor  
**Comisión:** (20262Q) DIA.04 - Introducción a la Ingeniería de Datos - Comisión A  
**Tema de Tesis:** Diagnóstico por imágenes para el cálculo de SINS (Spinal Instability Neoplastic Score)  

---

## 📌 Descripción del proyecto

Este repositorio contiene el trabajo práctico correspondiente a la **Unidad 1** del curso. El objetivo es demostrar la capacidad de:

1. Generar un script en Python asistido por IA (LLM) para la ingesta de datos desde una fuente externa.
2. Identificar componentes fundamentales en scripts de Python (librerías, variables, métodos, estructuras de control).
3. Aplicar principios de modularización y buenas prácticas (KISS, comentarios, docstrings).

El script desarrollado descarga el dataset **"Lumbar Spine"** desde **Roboflow Universe**, lo procesa y genera un resumen estadístico junto con visualizaciones de las anotaciones (bounding boxes) en imágenes de rayos X de columna lumbar.

---
---

## 📌 Mapa de correspondencia con la consigna TP2

| Punto del TP | Sección en este documento |
|---|---|
| 1) Diseño OLTP (ER + PK/FK + relaciones) | Sección 1 |
| 2) Modelo dimensional OLAP (Estrella + Dim_Tiempo + Bridge) | Sección 2 |
| 3) Implementación SQL (opcional) | Sección 5 |

---

## 🎯 Resumen ejecutivo

Este trabajo diseña dos modelos de datos complementarios sobre el flujo **GDELT 2.0 / CAMEO 1.1b3**:

- **Modelo OLTP (Sección 1):** captura cada noticia/evento con sus actores, ubicaciones, fuente y códigos CAMEO, incluyendo la tabla **Mentions** de GDELT 2.0 para trazabilidad de cobertura.
- **Modelo OLAP (Sección 2):** esquema estrella con tabla de hechos `Fact_Analisis_Medios` y dimensiones Tiempo, Ubicación, Actor, Fuente y CAMEO. Incluye **Bridge Table** para resolver la relación M:N entre eventos y múltiples códigos CAMEO (P4).
- **Preguntas de negocio cubiertas:** P1 (Rendimiento/Impacto), P2 (Sentimiento por tipo de actor), P3 (Frecuencia y Temporalidad), P4 (Cobertura multi-temática CAMEO).

---

## 📂 Estructura del repositorio
