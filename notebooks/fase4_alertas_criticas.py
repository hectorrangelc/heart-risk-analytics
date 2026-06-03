"""
============================================================
FASE 4: REPORTE AUTOMATIZADO - Alertas de Pacientes Criticos
------------------------------------------------------------
Simula un proceso automatizado diario (ej. 06:00 AM) que:
  1. Lee los registros de pacientes nuevos (ultimas 24h).
  2. Carga el modelo entrenado de la Fase 2 (modelo_rf.joblib).
  3. Calcula la probabilidad de riesgo coronario de cada paciente.
  4. Filtra EXCLUSIVAMENTE a los pacientes con riesgo > 80%.
  5. Genera un correo HTML estetico dirigido a Jefatura de Cardiologia.
  6. En modo SIMULADO guarda el HTML localmente (sin enviar).

Programacion real sugerida (no incluida): cron / Programador de tareas a las 06:00.
    0 6 * * *  /usr/bin/python3 .../fase4_alertas_criticas.py

Ejecucion:  python fase4_alertas_criticas.py
============================================================
"""

import os
from datetime import datetime
import numpy as np
import pandas as pd
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NUEVOS = os.path.join(BASE_DIR, "data", "nuevos_pacientes.csv")
MODELO = os.path.join(BASE_DIR, "output", "modelo_rf.joblib")
SALIDA_DIR = os.path.join(BASE_DIR, "output")

UMBRAL_CRITICO = 0.80          # solo pacientes por encima de este riesgo
DESTINATARIO = "Jefatura de Cardiologia"
ASUNTO = "URGENTE: Alerta de Pacientes Criticos Detectados en las Ultimas 24h"

NUMERICAS = ["Age", "RestingBP", "Cholesterol", "FastingBS", "MaxHR", "Oldpeak"]
CATEGORICAS = ["Sex", "ChestPainType", "RestingECG", "ExerciseAngina", "ST_Slope"]

# Traducciones para mostrar en el correo
CP_DESC = {"TA": "Angina tipica", "ATA": "Angina atipica",
           "NAP": "Dolor no anginoso", "ASY": "Asintomatico"}
SLOPE_DESC = {"Up": "Ascendente", "Flat": "Plano", "Down": "Descendente"}
SEX_DESC = {"M": "Hombre", "F": "Mujer"}


def accion_sugerida(prob):
    """Prioridad clinica segun el nivel de riesgo."""
    if prob >= 0.90:
        return "Cateterismo urgente + especialista hoy"
    if prob >= 0.85:
        return "Valoracion prioritaria < 24h"
    return "Evaluacion cardiologica < 48h"


def construir_html(criticos, total_evaluados, fecha):
    """Genera el cuerpo HTML del correo con una tabla limpia y estetica."""
    filas = ""
    for _, p in criticos.iterrows():
        prob_pct = "{:.0f}%".format(p["Probabilidad_Riesgo"] * 100)
        # color de la barra de riesgo
        color = "#C0392B" if p["Probabilidad_Riesgo"] >= 0.90 else "#E67E22"
        filas += """
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;font-weight:600;">{id}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;">{edad} / {sexo}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;">{dolor}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;">{st}, Oldpeak {oldpeak}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;text-align:center;">
            <span style="background:{color};color:#fff;padding:4px 10px;border-radius:12px;font-weight:700;">{prob}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #eee;color:#C0392B;font-weight:600;">{accion}</td>
        </tr>""".format(
            id=p["ID_Paciente"], edad=int(p["Age"]),
            sexo=SEX_DESC.get(p["Sex"], p["Sex"]),
            dolor=CP_DESC.get(p["ChestPainType"], p["ChestPainType"]),
            st=SLOPE_DESC.get(p["ST_Slope"], p["ST_Slope"]),
            oldpeak=p["Oldpeak"], color=color, prob=prob_pct,
            accion=accion_sugerida(p["Probabilidad_Riesgo"]))

    html = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="utf-8"></head>
<body style="margin:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#2c3e50;">
  <div style="max-width:760px;margin:24px auto;background:#fff;border-radius:10px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.08);">

    <div style="background:#C0392B;color:#fff;padding:22px 28px;">
      <div style="font-size:13px;letter-spacing:1px;opacity:.9;">CONTROL DE MANDO DE CARDIOLOGIA</div>
      <div style="font-size:21px;font-weight:700;margin-top:4px;">Alerta de Pacientes Criticos</div>
    </div>

    <div style="padding:24px 28px;">
      <p style="margin:0 0 4px;">Para: <strong>{destinatario}</strong></p>
      <p style="margin:0 0 16px;color:#7f8c8d;font-size:13px;">Generado automaticamente el {fecha}</p>

      <p style="margin:0 0 18px;line-height:1.5;">
        El sistema de Clasificacion de Riesgo Coronario evaluo <strong>{total}</strong>
        pacientes ingresados en las ultimas 24 horas y detecto
        <strong style="color:#C0392B;">{n_criticos}</strong> con riesgo critico
        (probabilidad superior al {umbral}%). Se requiere priorizar su atencion.
      </p>

      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <thead>
          <tr style="background:#2c3e50;color:#fff;text-align:left;">
            <th style="padding:10px 12px;">ID Paciente</th>
            <th style="padding:10px 12px;">Edad / Sexo</th>
            <th style="padding:10px 12px;">Dolor toracico</th>
            <th style="padding:10px 12px;">Marcadores ST</th>
            <th style="padding:10px 12px;text-align:center;">Riesgo</th>
            <th style="padding:10px 12px;">Accion sugerida</th>
          </tr>
        </thead>
        <tbody>{filas}
        </tbody>
      </table>

      <p style="margin:22px 0 0;font-size:12px;color:#7f8c8d;line-height:1.5;">
        Aviso: reporte generado por un modelo predictivo (Random Forest) con fines de
        priorizacion. No sustituye el juicio clinico del especialista. Sensibilidad del
        modelo validada en 0.89.
      </p>
    </div>

    <div style="background:#ecf0f1;padding:14px 28px;font-size:12px;color:#95a5a6;">
      Cardiologia Analytics - Sistema automatizado de alertas | {fecha}
    </div>
  </div>
</body>
</html>""".format(
        destinatario=DESTINATARIO, fecha=fecha, total=total_evaluados,
        n_criticos=len(criticos), umbral=int(UMBRAL_CRITICO * 100), filas=filas)
    return html


def main():
    print("=" * 60)
    print("PROCESO DIARIO DE ALERTAS - {}".format(
        datetime.now().strftime("%Y-%m-%d %H:%M")))
    print("=" * 60)

    # 1) Cargar pacientes nuevos
    df = pd.read_csv(NUEVOS)
    print("Pacientes nuevos (ultimas 24h): {}".format(len(df)))

    # 2) Cargar modelo entrenado de la Fase 2
    modelo = joblib.load(MODELO)
    print("Modelo cargado: {}".format(os.path.basename(MODELO)))

    # 3) Predecir probabilidad de riesgo
    X = df[NUMERICAS + CATEGORICAS]
    df["Probabilidad_Riesgo"] = modelo.predict_proba(X)[:, 1]
    # ID temporal para el reporte del dia
    df["ID_Paciente"] = ["NUEVO-" + str(i).zfill(3) for i in range(1, len(df) + 1)]

    # 4) Filtrar EXCLUSIVAMENTE criticos (> 80%)
    criticos = df[df["Probabilidad_Riesgo"] > UMBRAL_CRITICO].copy()
    criticos = criticos.sort_values("Probabilidad_Riesgo", ascending=False)
    print("Pacientes CRITICOS (> {:.0f}%): {}".format(
        UMBRAL_CRITICO * 100, len(criticos)))

    if criticos.empty:
        print("Sin pacientes criticos hoy. No se genera correo.")
        return

    for _, p in criticos.iterrows():
        print("  {} | {:.0f} anios | {} | riesgo {:.0%}".format(
            p["ID_Paciente"], p["Age"], p["ChestPainType"], p["Probabilidad_Riesgo"]))

    # 5) Construir el correo HTML
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    html = construir_html(criticos, len(df), fecha)

    # 6) MODO SIMULADO: guardar el HTML localmente (sin enviar)
    nombre = "alerta_criticos_{}.html".format(datetime.now().strftime("%Y%m%d"))
    ruta = os.path.join(SALIDA_DIR, nombre)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(html)

    print("\n" + "=" * 60)
    print("CORREO GENERADO (modo simulado)")
    print("=" * 60)
    print("Para   : {}".format(DESTINATARIO))
    print("Asunto : {}".format(ASUNTO))
    print("Archivo: {}".format(ruta))
    print("\nPara envio real: configurar smtplib/Gmail (ver README, no activado).")


if __name__ == "__main__":
    main()
