"""
============================================================
FASE 2: MODELO PREDICTIVO - Clasificacion de Riesgo Coronario
Modelo: Random Forest (interpretable via feature importance)
------------------------------------------------------------
Lee:    output/heart_preparado.csv   (salida de la Fase 1)
Genera: output/heart_enriquecido.csv (base del dashboard, Fase 3)
        output/modelo_rf.joblib       (modelo entrenado, para la Fase 4)
        output/fase2_metricas.png      (matriz de confusion + ROC + importancias)

Objetivos:
  1. Preparar X (11 variables clinicas) e y (HeartDisease).
  2. Pipeline: OneHotEncoder para categoricas + RandomForest.
  3. Evaluar con conjunto de prueba estratificado + validacion cruzada.
  4. Reportar metricas CLINICAS (con enfasis en sensibilidad / recall).
  5. Interpretar el modelo (importancia de variables).
  6. Asignar score honesto a TODOS los pacientes (cross_val_predict out-of-fold).
  7. Exportar CSV enriquecido con Probabilidad_Riesgo y Prediccion_Final.

Ejecucion:  python fase2_modelo_riesgo.py
============================================================
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import joblib

from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import (
    train_test_split, cross_val_score, cross_val_predict, StratifiedKFold)
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report, roc_curve)

sns.set_theme(style="whitegrid", palette="Set2")
np.random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_IN = os.path.join(BASE_DIR, "output", "heart_preparado.csv")
DATA_OUT = os.path.join(BASE_DIR, "output", "heart_enriquecido.csv")
MODEL_OUT = os.path.join(BASE_DIR, "output", "modelo_rf.joblib")
FIG_OUT = os.path.join(BASE_DIR, "output", "fase2_metricas.png")

# Variables predictoras (las 11 clinicas) y objetivo
NUMERICAS = ["Age", "RestingBP", "Cholesterol", "FastingBS", "MaxHR", "Oldpeak"]
CATEGORICAS = ["Sex", "ChestPainType", "RestingECG", "ExerciseAngina", "ST_Slope"]
TARGET = "HeartDisease"


def construir_pipeline():
    """Pipeline: OneHot para categoricas, numericas sin transformar
    (Random Forest no requiere escalado) + RandomForest."""
    pre = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAS),
            ("num", "passthrough", NUMERICAS),
        ]
    )
    modelo = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        min_samples_leaf=5,        # regularizacion suave: evita sobreajuste
        class_weight="balanced",   # sensible a la clase enferma (cribado clinico)
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("pre", pre), ("rf", modelo)])


def main():
    df = pd.read_csv(DATA_IN)
    X = df[NUMERICAS + CATEGORICAS]
    y = df[TARGET]

    print("=" * 60)
    print("1) DATOS DE ENTRADA")
    print("=" * 60)
    print("Pacientes: {} | Variables predictoras: {}".format(len(df), X.shape[1]))
    print("Prevalencia (HeartDisease=1): {:.1f}%".format(y.mean() * 100))

    # --------------------------------------------------------
    # 2) EVALUACION CON CONJUNTO DE PRUEBA ESTRATIFICADO
    # --------------------------------------------------------
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42)

    pipe = construir_pipeline()
    pipe.fit(X_train, y_train)

    y_pred = pipe.predict(X_test)
    y_proba = pipe.predict_proba(X_test)[:, 1]

    print("\n" + "=" * 60)
    print("2) METRICAS EN CONJUNTO DE PRUEBA (20% no visto)")
    print("=" * 60)
    print("Accuracy   : {:.3f}".format(accuracy_score(y_test, y_pred)))
    print("Precision  : {:.3f}".format(precision_score(y_test, y_pred)))
    print("Recall/Sens: {:.3f}  <- clave en cribado: no dejar enfermos sin detectar".format(
        recall_score(y_test, y_pred)))
    print("F1-score   : {:.3f}".format(f1_score(y_test, y_pred)))
    print("ROC-AUC    : {:.3f}".format(roc_auc_score(y_test, y_proba)))
    print("\nReporte por clase:")
    print(classification_report(y_test, y_pred, target_names=["Sano", "Enfermo"]))

    cm = confusion_matrix(y_test, y_pred)
    tn, fp, fn, tp = cm.ravel()
    print("Matriz de confusion (test):")
    print("  Verdaderos Negativos (sanos ok)   : {}".format(tn))
    print("  Falsos Positivos (falsa alarma)   : {}".format(fp))
    print("  Falsos Negativos (enfermo perdido): {}  <- el error mas costoso clinicamente".format(fn))
    print("  Verdaderos Positivos (enfermo ok) : {}".format(tp))

    # --------------------------------------------------------
    # 3) VALIDACION CRUZADA (robustez del modelo)
    # --------------------------------------------------------
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    auc_cv = cross_val_score(construir_pipeline(), X, y, cv=cv, scoring="roc_auc")
    rec_cv = cross_val_score(construir_pipeline(), X, y, cv=cv, scoring="recall")
    print("\n" + "=" * 60)
    print("3) VALIDACION CRUZADA 5-FOLD (sobre todo el dataset)")
    print("=" * 60)
    print("ROC-AUC: {:.3f} +/- {:.3f}".format(auc_cv.mean(), auc_cv.std()))
    print("Recall : {:.3f} +/- {:.3f}".format(rec_cv.mean(), rec_cv.std()))

    # --------------------------------------------------------
    # 4) INTERPRETABILIDAD: importancia de variables
    # --------------------------------------------------------
    pipe.fit(X, y)  # reajuste sobre todo el dataset para importancias y modelo final
    ohe = pipe.named_steps["pre"].named_transformers_["cat"]
    nombres = list(ohe.get_feature_names_out(CATEGORICAS)) + NUMERICAS
    importancias = pipe.named_steps["rf"].feature_importances_
    imp = pd.Series(importancias, index=nombres).sort_values(ascending=False)
    print("\n" + "=" * 60)
    print("4) IMPORTANCIA DE VARIABLES (top 10)")
    print("=" * 60)
    print(imp.head(10).round(3).to_string())

    # --------------------------------------------------------
    # 5) SCORE HONESTO PARA TODOS (out-of-fold, sin leakage)
    # --------------------------------------------------------
    proba_oof = cross_val_predict(
        construir_pipeline(), X, y, cv=cv, method="predict_proba")[:, 1]
    df["Probabilidad_Riesgo"] = proba_oof.round(4)
    df["Prediccion_Final"] = (proba_oof >= 0.5).astype(int)

    print("\n" + "=" * 60)
    print("5) SCORES ASIGNADOS A LOS 918 PACIENTES (out-of-fold)")
    print("=" * 60)
    print("Probabilidad media: {:.3f}".format(df["Probabilidad_Riesgo"].mean()))
    print("Pacientes clasificados Alto Riesgo (Prediccion_Final=1): {}".format(
        int(df["Prediccion_Final"].sum())))
    print("Pacientes criticos (Probabilidad > 0.80): {}".format(
        int((df["Probabilidad_Riesgo"] > 0.80).sum())))

    # --------------------------------------------------------
    # 6) GRAFICOS DE DIAGNOSTICO
    # --------------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=["Sano", "Enfermo"], yticklabels=["Sano", "Enfermo"], ax=axes[0])
    axes[0].set_title("Matriz de Confusion (test)")
    axes[0].set_xlabel("Prediccion"); axes[0].set_ylabel("Real")

    fpr, tpr, _ = roc_curve(y_test, y_proba)
    axes[1].plot(fpr, tpr, label="AUC = {:.3f}".format(roc_auc_score(y_test, y_proba)))
    axes[1].plot([0, 1], [0, 1], "--", color="gray")
    axes[1].set_title("Curva ROC"); axes[1].set_xlabel("Falsos Positivos")
    axes[1].set_ylabel("Verdaderos Positivos"); axes[1].legend()

    imp.head(10).sort_values().plot(kind="barh", ax=axes[2], color="#5b9279")
    axes[2].set_title("Top 10 Variables Importantes")
    plt.tight_layout()
    plt.savefig(FIG_OUT, dpi=120)
    plt.close()
    print("\nFigura guardada: {}".format(FIG_OUT))

    # --------------------------------------------------------
    # 7) EXPORTAR ENTREGABLES
    # --------------------------------------------------------
    df.to_csv(DATA_OUT, index=False)
    joblib.dump(pipe, MODEL_OUT)
    print("\n" + "=" * 60)
    print("ENTREGABLES")
    print("=" * 60)
    print("CSV enriquecido: {} ({} columnas)".format(os.path.basename(DATA_OUT), df.shape[1]))
    print("Modelo entrenado: {}".format(os.path.basename(MODEL_OUT)))


if __name__ == "__main__":
    main()
