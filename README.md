# Cardiología Analytics — Sistema Integral de Riesgo Coronario

> 🌐 *Read this in [English](README.en.md)*

> Proyecto de portafolio **end-to-end** que une Ciencia de Datos, Business Intelligence
> y automatización clínica sobre el dataset **Heart Failure Prediction** (918 pacientes).
> Desde la limpieza de datos hasta un dashboard ejecutivo y un sistema de alertas críticas.

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-RandomForest-F7931E?logo=scikitlearn&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-Dashboard-3F4F75?logo=plotly&logoColor=white)
![Power BI](https://img.shields.io/badge/Power%20BI-DAX-F2C811?logo=powerbi&logoColor=black)
![ROC--AUC](https://img.shields.io/badge/ROC--AUC-0.928-27AE60)

---

## El problema de negocio

Un hospital privado de cardiología necesita **priorizar la atención** de pacientes con
mayor riesgo coronario y, al mismo tiempo, **optimizar el gasto** en tratamientos. Este
proyecto entrega tres piezas que trabajan juntas:

1. **Modelo predictivo** que clasifica el riesgo coronario de cada paciente.
2. **Dashboard ejecutivo** de dos capas (clínica y financiera).
3. **Sistema de alertas** que notifica a la jefatura sobre pacientes críticos cada día.

---

## Resultados clave

| Métrica | Resultado |
|---|---|
| ROC-AUC (test) | **0.928** |
| Sensibilidad / Recall | **0.912** |
| Validación cruzada 5-fold (AUC) | 0.925 ± 0.026 |
| Pacientes de alto riesgo identificados | 517 de 918 |
| Costo total de cartera (simulado) | $16.89M |
| Tasa de detección temprana | 88.6% |

---

## 1. Modelo Predictivo — Clasificación de Riesgo Coronario

Random Forest interpretable con pipeline de codificación + validación cruzada
out-of-fold para asignar un score honesto (sin fuga de información) a cada paciente.

![Métricas del modelo](docs/img/fase2_metricas.png)

Las variables más predictivas (pendiente del ST, dolor asintomático, depresión ST)
coinciden con los marcadores clínicos clásicos de cardiopatía isquémica.

---

## 2. Dashboard "Control de Mando de Cardiología"

Dashboard interactivo de **dos capas** (versión HTML+Plotly autocontenida; también
incluye la guía completa de medidas DAX para Power BI en [`docs/`](docs/fase3_dashboard_powerbi.md)).

### Capa Operativa (Médicos)
Alertas de pacientes de alto riesgo, segmentación por tipo de dolor torácico y
dispersión Edad vs Colesterol coloreada por el riesgo predicho.

![Capa Operativa](docs/img/dashboard_operativa.png)

### Capa Ejecutiva / Financiera (Dirección)
Cruce del costo de tratamiento con los niveles de riesgo, modelo de ahorro por
prevención (parámetro de escenario) y tasa de éxito de intervención temprana.

![Capa Financiera](docs/img/dashboard_financiera.png)

---

## 3. Reporte Automatizado — Alertas de Pacientes Críticos

Proceso diario que corre el modelo sobre los ingresos de las últimas 24h, filtra los
pacientes con riesgo > 80% y genera un correo HTML con tabla priorizada para la
Jefatura de Cardiología (cateterismo urgente, valoración prioritaria, etc.).

![Correo de alerta](docs/img/correo_alerta.png)

---

## Arquitectura del proyecto

```
Fase 1: EDA + variables de negocio   ->  heart_preparado.csv
Fase 2: Random Forest + scoring      ->  heart_enriquecido.csv + modelo_rf.joblib
Fase 3: Dashboard de dos capas       ->  dashboard_cardiologia.html  (+ guía DAX)
Fase 4: Alertas críticas diarias     ->  correo HTML automatizado
```

## Stack técnico

- **Datos / ML:** Python, Pandas, NumPy, scikit-learn (Random Forest, Pipelines, CV).
- **Visualización:** Plotly (dashboard interactivo), Matplotlib/Seaborn (EDA), Power BI / DAX (guía).
- **Automatización:** joblib (persistencia del modelo), HTML/SMTP (alertas), cron.

## Cómo ejecutarlo

```bash
pip install -r requirements.txt

python notebooks/fase1_eda_preparacion.py     # EDA y preparación
python notebooks/fase2_modelo_riesgo.py       # Modelo + CSV enriquecido
python notebooks/build_dashboard.py           # Dashboard interactivo (HTML)
python notebooks/fase4_alertas_criticas.py    # Alertas de pacientes críticos
```

Cada fase tiene además su notebook ejecutado en [`notebooks/`](notebooks/).

## Estructura

```
cardiologia-analytics/
├── data/            dataset original + pacientes simulados (Fase 4)
├── notebooks/       scripts .py y notebooks .ipynb por fase
├── docs/            guía Power BI (DAX) + capturas
├── output/          CSVs, modelo, dashboard HTML, correo y gráficos
├── requirements.txt
└── README.md
```

---

## Nota de honestidad analítica

El `Costo_Tratamiento_USD` es una variable **simulada** con una fórmula ponderada por
severidad clínica y edad (documentada en la Fase 1), ya que el dataset público no
incluye datos financieros. Las métricas de "detección temprana" y "costo evitado" usan
la variable real de diagnóstico para demostrar el valor histórico del modelo; en
producción no se dispone de esa verdad para pacientes nuevos.

*Dataset: [Heart Failure Prediction (fedesoriano) — Kaggle](https://www.kaggle.com/datasets/fedesoriano/heart-failure-prediction).*
