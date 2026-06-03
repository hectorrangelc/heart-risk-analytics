"""
============================================================
FASE 1: EDA Y PREPARACION - Cardiologia Analytics
Dataset: Heart Failure Prediction (918 pacientes, 12 variables)
------------------------------------------------------------
Objetivo de la fase:
  1. Cargar e inspeccionar el dataset.
  2. Auditar la calidad de los datos (nulos, duplicados, ceros imposibles).
  3. Limpiar e imputar errores de captura clinicos.
  4. Crear etiquetas legibles para el dashboard (Power BI).
  5. Inyectar variables de negocio: ID_Paciente y Costo_Tratamiento_USD.
  6. Generar un reporte descriptivo con lectura clinico-hospitalaria.
  7. Exportar 'heart_preparado.csv' (base para la Fase 2).

Ejecucion:  python fase1_eda_preparacion.py
============================================================
"""

import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # backend sin ventana para guardar figuras en archivo
import matplotlib.pyplot as plt
import seaborn as sns

# ------------------------------------------------------------
# Configuracion global
# ------------------------------------------------------------
sns.set_theme(style="whitegrid", palette="Set2")
plt.rcParams["figure.figsize"] = (10, 5)
np.random.seed(42)  # reproducibilidad: los numeros no cambian entre corridas
pd.set_option("display.max_columns", None)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_IN = os.path.join(BASE_DIR, "data", "heart.csv")
DATA_OUT = os.path.join(BASE_DIR, "output", "heart_preparado.csv")
FIG_OUT = os.path.join(BASE_DIR, "output", "fase1_eda.png")


def main():
    # --------------------------------------------------------
    # 1) CARGA E INSPECCION
    # --------------------------------------------------------
    df = pd.read_csv(DATA_IN)
    print("=" * 60)
    print("1) CARGA E INSPECCION")
    print("=" * 60)
    print("Dimensiones: {} pacientes x {} variables".format(df.shape[0], df.shape[1]))
    print("\nPrimeras filas:")
    print(df.head())
    print("\nTipos de datos:")
    print(df.dtypes)

    # --------------------------------------------------------
    # 2) AUDITORIA DE CALIDAD
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("2) AUDITORIA DE CALIDAD")
    print("=" * 60)
    nulos = df.isnull().sum()
    print("Nulos por columna:")
    print(nulos[nulos > 0].to_string() if nulos.sum() else "   Sin nulos")
    print("\nDuplicados: {}".format(df.duplicated().sum()))
    print("Prevalencia de enfermedad (HeartDisease=1): {:.1f}%".format(
        df["HeartDisease"].mean() * 100))
    print("\nDetalle de calidad de ESTE dataset (ceros imposibles):")
    print("  Cholesterol = 0 (error de captura): {} casos".format(
        int((df["Cholesterol"] == 0).sum())))
    print("  RestingBP   = 0 (error de captura): {} casos".format(
        int((df["RestingBP"] == 0).sum())))

    # --------------------------------------------------------
    # 3) LIMPIEZA E IMPUTACION CLINICA
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("3) LIMPIEZA E IMPUTACION")
    print("=" * 60)
    df = df.drop_duplicates().reset_index(drop=True)
    # Un colesterol o presion de 0 es fisicamente imposible -> error de captura.
    # Se imputa con la mediana de los valores VALIDOS (robusta a outliers).
    for col in ["Cholesterol", "RestingBP"]:
        ceros = df[col] == 0
        if ceros.sum() > 0:
            mediana = df.loc[~ceros, col].median()
            df.loc[ceros, col] = mediana
            print("  {}: {} ceros imputados con mediana = {:.0f}".format(
                col, int(ceros.sum()), mediana))
    print("Dataset limpio: {} pacientes".format(df.shape[0]))

    # --------------------------------------------------------
    # 4) ETIQUETAS LEGIBLES (para Power BI y el EDA)
    # --------------------------------------------------------
    mapeos = {
        "Sex":            {"M": "Hombre", "F": "Mujer"},
        "ChestPainType":  {"TA": "Angina tipica", "ATA": "Angina atipica",
                           "NAP": "Dolor no anginoso", "ASY": "Asintomatico"},
        "RestingECG":     {"Normal": "Normal", "ST": "Anomalia ST-T",
                           "LVH": "Hipertrofia VI"},
        "ExerciseAngina": {"N": "No", "Y": "Si"},
        "ST_Slope":       {"Up": "Ascendente", "Flat": "Plano", "Down": "Descendente"},
        "FastingBS":      {0: "Glucosa Normal", 1: "Glucosa Alta"},
        "HeartDisease":   {0: "Sano", 1: "Enfermo"},
    }
    for col, mapa in mapeos.items():
        df[col + "_desc"] = df[col].map(mapa)

    # --------------------------------------------------------
    # 5) INYECCION DE VARIABLES DE NEGOCIO
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("5) VARIABLES DE NEGOCIO")
    print("=" * 60)
    # 5.1 ID_Paciente
    df["ID_Paciente"] = ["PAC-" + str(i).zfill(5) for i in range(1, len(df) + 1)]

    # 5.2 Costo_Tratamiento_USD (formula ponderada, cardiologia privada)
    #   Base diagnostico .................... 4000
    #   Enfermedad confirmada ............... +12000 (intervencion vs monitoreo)
    #   Severidad isquemica (Oldpeak) ....... +2500 por unidad de depresion ST
    #   Dolor ASINTOMATICO (ASY) ............ +3000 (deteccion tardia, mas grave)
    #   Angina por ejercicio (Y) ............ +2000 (prueba de esfuerzo positiva)
    #   ST_Slope anormal (Flat/Down) ........ +2500 (patron isquemico)
    #   Factor edad ......................... +120 por anio sobre 40
    #   Ruido de mercado .................... +/-15% (variabilidad de facturacion)
    base = 4000
    costo = (
        base
        + df["HeartDisease"] * 12000
        + df["Oldpeak"] * 2500
        + (df["ChestPainType"] == "ASY").astype(int) * 3000
        + (df["ExerciseAngina"] == "Y").astype(int) * 2000
        + df["ST_Slope"].isin(["Flat", "Down"]).astype(int) * 2500
        + np.maximum(df["Age"] - 40, 0) * 120
    )
    ruido = np.random.normal(1.0, 0.15, size=len(df))
    df["Costo_Tratamiento_USD"] = np.maximum(costo * ruido, base).round(-2)

    print("Costo simulado -> Min: ${:,.0f} | Media: ${:,.0f} | Max: ${:,.0f}".format(
        df["Costo_Tratamiento_USD"].min(),
        df["Costo_Tratamiento_USD"].mean(),
        df["Costo_Tratamiento_USD"].max()))
    print("\nValidacion de coherencia (costo medio por estado):")
    print(df.groupby("HeartDisease_desc")["Costo_Tratamiento_USD"].mean().round(0).to_string())

    # --------------------------------------------------------
    # 6) REPORTE DESCRIPTIVO CLINICO-HOSPITALARIO
    # --------------------------------------------------------
    print("\n" + "=" * 60)
    print("6) REPORTE DESCRIPTIVO CLINICO-HOSPITALARIO")
    print("=" * 60)
    print("\nPerfil de pacientes:")
    print("  Edad promedio: {:.0f} anios (rango {}-{})".format(
        df["Age"].mean(), int(df["Age"].min()), int(df["Age"].max())))
    print(df["Sex_desc"].value_counts().to_string())

    print("\nFactores de riesgo (media: Enfermo vs Sano):")
    print(df.groupby("HeartDisease_desc")[
        ["Age", "Cholesterol", "RestingBP", "MaxHR", "Oldpeak"]].mean().round(1).to_string())

    print("\nDolor toracico vs enfermedad:")
    print(pd.crosstab(df["ChestPainType_desc"], df["HeartDisease_desc"],
                      margins=True, margins_name="Total").to_string())

    print("\nImpacto financiero preliminar:")
    print("  Costo total de la cartera: ${:,.0f}".format(
        df["Costo_Tratamiento_USD"].sum()))
    print(df.groupby("HeartDisease_desc")["Costo_Tratamiento_USD"].mean().round(0).to_string())

    # --------------------------------------------------------
    # 7) VISUALIZACIONES
    # --------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    sns.histplot(df, x="Age", hue="HeartDisease_desc", kde=True, ax=axes[0, 0])
    axes[0, 0].set_title("Edad: Enfermo vs Sano")

    sns.countplot(df, x="ChestPainType_desc", hue="HeartDisease_desc", ax=axes[0, 1])
    axes[0, 1].set_title("Dolor toracico vs Enfermedad")
    axes[0, 1].tick_params(axis="x", rotation=20)

    sns.scatterplot(df, x="Age", y="Cholesterol", hue="HeartDisease_desc", ax=axes[1, 0])
    axes[1, 0].set_title("Edad vs Colesterol")

    sns.boxplot(df, x="HeartDisease_desc", y="Costo_Tratamiento_USD", ax=axes[1, 1])
    axes[1, 1].set_title("Costo de Tratamiento por estado")

    plt.tight_layout()
    plt.savefig(FIG_OUT, dpi=120)
    plt.close()
    print("\nFigura del EDA guardada en: {}".format(FIG_OUT))

    # --------------------------------------------------------
    # 8) EXPORTAR DATASET PREPARADO
    # --------------------------------------------------------
    df.to_csv(DATA_OUT, index=False)
    print("\n" + "=" * 60)
    print("ENTREGABLE: '{}' ({} columnas, {} pacientes)".format(
        os.path.basename(DATA_OUT), df.shape[1], df.shape[0]))
    print("=" * 60)


if __name__ == "__main__":
    main()
