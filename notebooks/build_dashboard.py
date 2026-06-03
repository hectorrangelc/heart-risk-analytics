"""
============================================================
DASHBOARD "Control de Mando de Cardiologia" (HTML + Plotly)
Equivalente funcional del dashboard de la Fase 3, autocontenido.
------------------------------------------------------------
Lee:    output/heart_enriquecido.csv
Genera: output/dashboard_cardiologia.html  (un solo archivo, abre offline)

Dos capas:
  - Operativa (medicos)
  - Ejecutiva / Financiera (direccion)

Ejecucion:  python build_dashboard.py
============================================================
"""

import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_IN = os.path.join(BASE_DIR, "output", "heart_enriquecido.csv")
HTML_OUT = os.path.join(BASE_DIR, "output", "dashboard_cardiologia.html")

# Paleta de semaforo clinico
COLORS = {"1. Critico": "#C0392B", "2. Alto": "#E67E22",
          "3. Moderado": "#F1C40F", "4. Bajo": "#27AE60"}
ORDER = ["1. Critico", "2. Alto", "3. Moderado", "4. Bajo"]
PLOT_BG = "#ffffff"
FACTOR_COMPLICACION = 2.5  # supuesto: evento no prevenido cuesta 2.5x


def banda(p):
    if p >= 0.80:
        return "1. Critico"
    if p >= 0.50:
        return "2. Alto"
    if p >= 0.20:
        return "3. Moderado"
    return "4. Bajo"


def fig_div(fig):
    fig.update_layout(margin=dict(l=40, r=20, t=50, b=40), paper_bgcolor=PLOT_BG,
                      plot_bgcolor=PLOT_BG, font=dict(family="Arial", size=12))
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"displayModeBar": False})


def kpi_card(titulo, valor, color="#2c3e50", sub=""):
    return """
    <div class="kpi">
      <div class="kpi-title">{t}</div>
      <div class="kpi-value" style="color:{c}">{v}</div>
      <div class="kpi-sub">{s}</div>
    </div>""".format(t=titulo, v=valor, c=color, s=sub)


def main():
    df = pd.read_csv(DATA_IN)
    df["Banda_Riesgo"] = df["Probabilidad_Riesgo"].apply(banda)

    # ----- Metricas -----
    total = len(df)
    alto = int((df["Prediccion_Final"] == 1).sum())
    criticos = int((df["Probabilidad_Riesgo"] > 0.80).sum())
    tasa_alto = alto / total
    costo_total = df["Costo_Tratamiento_USD"].sum()
    costo_prom = df["Costo_Tratamiento_USD"].mean()
    costo_alto = df.loc[df["Prediccion_Final"] == 1, "Costo_Tratamiento_USD"].sum()
    costo_medio_alto = df.loc[df["Prediccion_Final"] == 1, "Costo_Tratamiento_USD"].mean()
    costo_medio_bajo = df.loc[df["Prediccion_Final"] == 0, "Costo_Tratamiento_USD"].mean()
    vp = ((df["Prediccion_Final"] == 1) & (df["HeartDisease"] == 1)).sum()
    fn = ((df["Prediccion_Final"] == 0) & (df["HeartDisease"] == 1)).sum()
    tasa_deteccion = vp / (vp + fn)
    costo_vp = df.loc[(df["Prediccion_Final"] == 1) & (df["HeartDisease"] == 1),
                      "Costo_Tratamiento_USD"].sum()
    costo_evitado = costo_vp * (FACTOR_COMPLICACION - 1)
    roi_prev = costo_evitado / costo_alto

    # =========================================================
    # CAPA OPERATIVA
    # =========================================================
    # Donut por banda
    cnt = df["Banda_Riesgo"].value_counts().reindex(ORDER).fillna(0)
    f_donut = go.Figure(go.Pie(labels=cnt.index, values=cnt.values, hole=.55,
                               marker=dict(colors=[COLORS[b] for b in cnt.index])))
    f_donut.update_layout(title="Distribucion de pacientes por nivel de riesgo")

    # Barras apiladas dolor x banda
    ct = (df.groupby(["ChestPainType_desc", "Banda_Riesgo"]).size()
          .reset_index(name="n"))
    f_dolor = px.bar(ct, x="ChestPainType_desc", y="n", color="Banda_Riesgo",
                     category_orders={"Banda_Riesgo": ORDER}, color_discrete_map=COLORS,
                     title="Riesgo por tipo de dolor toracico",
                     labels={"ChestPainType_desc": "Tipo de dolor", "n": "Pacientes",
                             "Banda_Riesgo": "Riesgo"})

    # Scatter Edad vs Colesterol coloreado por probabilidad
    f_scatter = px.scatter(df, x="Age", y="Cholesterol", color="Probabilidad_Riesgo",
                           color_continuous_scale="RdYlGn_r", hover_data=["ID_Paciente"],
                           title="Edad vs Colesterol (color = riesgo predicho)",
                           labels={"Age": "Edad", "Cholesterol": "Colesterol"})

    # Tabla criticos
    tcrit = (df[df["Probabilidad_Riesgo"] > 0.80]
             .sort_values("Probabilidad_Riesgo", ascending=False)
             .head(15)[["ID_Paciente", "Age", "Sex_desc", "ChestPainType_desc",
                        "Probabilidad_Riesgo", "Costo_Tratamiento_USD"]])
    f_tabla = go.Figure(go.Table(
        header=dict(values=["ID", "Edad", "Sexo", "Dolor", "Riesgo", "Costo USD"],
                    fill_color="#2c3e50", font=dict(color="white"), align="left"),
        cells=dict(values=[
            tcrit["ID_Paciente"], tcrit["Age"], tcrit["Sex_desc"],
            tcrit["ChestPainType_desc"],
            (tcrit["Probabilidad_Riesgo"] * 100).round(0).astype(int).astype(str) + "%",
            "$" + tcrit["Costo_Tratamiento_USD"].map("{:,.0f}".format)],
            align="left", height=26)))
    f_tabla.update_layout(title="Top 15 pacientes criticos (riesgo > 80%)")

    # =========================================================
    # CAPA EJECUTIVA / FINANCIERA
    # =========================================================
    # Costo por banda
    cb = df.groupby("Banda_Riesgo")["Costo_Tratamiento_USD"].sum().reindex(ORDER).fillna(0)
    f_costo_banda = go.Figure(go.Bar(x=cb.index, y=cb.values,
                                     marker_color=[COLORS[b] for b in cb.index]))
    f_costo_banda.update_layout(title="Costo total por nivel de riesgo",
                                yaxis_title="USD")

    # Cascada de costos
    f_wf = go.Figure(go.Waterfall(
        x=cb.index, y=cb.values, measure=["relative"] * len(cb),
        connector={"line": {"color": "#bbb"}}))
    f_wf.update_layout(title="Composicion del costo de la cartera (cascada)",
                       yaxis_title="USD")

    # Treemap por tipo de dolor
    cd = df.groupby("ChestPainType_desc")["Costo_Tratamiento_USD"].sum().reset_index()
    f_tree = px.treemap(cd, path=["ChestPainType_desc"], values="Costo_Tratamiento_USD",
                        title="Costo por tipo de dolor toracico",
                        color="Costo_Tratamiento_USD", color_continuous_scale="Oranges")

    # Costo medio alto vs bajo
    f_cmp = go.Figure(go.Bar(
        x=["Alto Riesgo", "Bajo Riesgo"], y=[costo_medio_alto, costo_medio_bajo],
        marker_color=["#C0392B", "#27AE60"],
        text=["${:,.0f}".format(costo_medio_alto), "${:,.0f}".format(costo_medio_bajo)],
        textposition="outside"))
    f_cmp.update_layout(title="Costo medio por paciente: Alto vs Bajo riesgo",
                        yaxis_title="USD")

    # Medidor tasa de deteccion
    f_gauge = go.Figure(go.Indicator(
        mode="gauge+number", value=tasa_deteccion * 100,
        number={"suffix": "%"},
        gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#2c3e50"},
               "steps": [{"range": [0, 70], "color": "#f8d7da"},
                         {"range": [70, 90], "color": "#fff3cd"},
                         {"range": [90, 100], "color": "#d4edda"}],
               "threshold": {"line": {"color": "#C0392B", "width": 3},
                             "value": 90}},
        title={"text": "Tasa de deteccion temprana"}))

    # ----- Ensamblar HTML -----
    op_kpis = (
        kpi_card("Total Pacientes", "{:,}".format(total))
        + kpi_card("Alto Riesgo", "{:,}".format(alto), "#E67E22")
        + kpi_card("Criticos (>80%)", "{:,}".format(criticos), "#C0392B")
        + kpi_card("Tasa Alto Riesgo", "{:.1f}%".format(tasa_alto * 100), "#E67E22"))
    fin_kpis = (
        kpi_card("Costo Total Cartera", "${:,.0f}".format(costo_total))
        + kpi_card("Costo Promedio", "${:,.0f}".format(costo_prom))
        + kpi_card("Costo Evitado (Prev.)", "${:,.0f}".format(costo_evitado), "#27AE60",
                   "Factor {}x".format(FACTOR_COMPLICACION))
        + kpi_card("ROI Prevencion", "{:.0f}%".format(roi_prev * 100), "#27AE60"))

    html = TEMPLATE.format(
        plotlyjs=get_plotlyjs(),
        op_kpis=op_kpis, fin_kpis=fin_kpis,
        donut=fig_div(f_donut), dolor=fig_div(f_dolor),
        scatter=fig_div(f_scatter), tabla=fig_div(f_tabla),
        costo_banda=fig_div(f_costo_banda), waterfall=fig_div(f_wf),
        treemap=fig_div(f_tree), comparativo=fig_div(f_cmp), gauge=fig_div(f_gauge),
        n_no_detectados=int(fn))

    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)

    print("Dashboard generado: {}".format(HTML_OUT))
    print("Capa Operativa  -> Total {}, Alto {}, Criticos {}".format(total, alto, criticos))
    print("Capa Financiera -> Costo total ${:,.0f}, Evitado ${:,.0f}, ROI {:.0f}%".format(
        costo_total, costo_evitado, roi_prev * 100))


TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Control de Mando de Cardiologia</title>
<script>{plotlyjs}</script>
<style>
  body {{ margin:0; background:#eef1f4; font-family:Arial,Helvetica,sans-serif; color:#2c3e50; }}
  header {{ background:#2c3e50; color:#fff; padding:18px 28px; }}
  header h1 {{ margin:0; font-size:20px; }}
  header span {{ font-size:13px; opacity:.8; }}
  .tabs {{ display:flex; background:#34495e; }}
  .tab {{ padding:14px 26px; color:#cfd8e3; cursor:pointer; font-weight:600; border:none;
          background:none; font-size:14px; }}
  .tab.active {{ background:#eef1f4; color:#2c3e50; }}
  .page {{ display:none; padding:20px 28px; }}
  .page.active {{ display:block; }}
  .kpi-row {{ display:flex; gap:16px; margin-bottom:18px; flex-wrap:wrap; }}
  .kpi {{ flex:1; min-width:180px; background:#fff; border-radius:10px; padding:16px 18px;
          box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  .kpi-title {{ font-size:12px; color:#7f8c8d; text-transform:uppercase; letter-spacing:.5px; }}
  .kpi-value {{ font-size:30px; font-weight:700; margin-top:6px; }}
  .kpi-sub {{ font-size:11px; color:#95a5a6; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
  .card {{ background:#fff; border-radius:10px; padding:8px; box-shadow:0 1px 4px rgba(0,0,0,.08); }}
  .full {{ grid-column:1 / -1; }}
  .note {{ font-size:12px; color:#7f8c8d; margin-top:14px; }}
</style>
</head>
<body>
<header>
  <h1>Control de Mando de Cardiologia</h1>
  <span>Modelo de Clasificacion de Riesgo Coronario &middot; 918 pacientes</span>
</header>
<div class="tabs">
  <button class="tab active" onclick="show(0)">Capa Operativa (Medicos)</button>
  <button class="tab" onclick="show(1)">Capa Ejecutiva / Financiera (Direccion)</button>
</div>

<div class="page active" id="p0">
  <div class="kpi-row">{op_kpis}</div>
  <div class="grid">
    <div class="card">{donut}</div>
    <div class="card">{dolor}</div>
    <div class="card full">{scatter}</div>
    <div class="card full">{tabla}</div>
  </div>
</div>

<div class="page" id="p1">
  <div class="kpi-row">{fin_kpis}</div>
  <div class="grid">
    <div class="card">{costo_banda}</div>
    <div class="card">{waterfall}</div>
    <div class="card">{treemap}</div>
    <div class="card">{comparativo}</div>
    <div class="card full">{gauge}</div>
  </div>
  <p class="note">Nota: la tasa de deteccion y el costo evitado se calculan con la
  variable real de diagnostico para demostrar el valor historico del modelo. En
  produccion, {n_no_detectados} enfermos quedaron como falsos negativos (no detectados).
  El costo evitado asume que un evento no prevenido cuesta 2.5x el tratamiento preventivo.</p>
</div>

<script>
function show(i) {{
  document.querySelectorAll('.page').forEach((p,idx)=>p.classList.toggle('active',idx===i));
  document.querySelectorAll('.tab').forEach((t,idx)=>t.classList.toggle('active',idx===i));
  window.dispatchEvent(new Event('resize'));
}}
</script>
</body>
</html>"""


if __name__ == "__main__":
    main()
