# FASE 3 - Dashboard "Control de Mando de Cardiologia" (Power BI)

Guia de construccion completa. Fuente de datos: `output/heart_enriquecido.csv`
(918 pacientes, 23 columnas, salida de la Fase 2).

El dashboard tiene DOS capas estrictas, cada una en su propia pagina:
1. **Capa Operativa** (para medicos en clinica): el dia a dia clinico.
2. **Capa Ejecutiva / Financiera** (para direccion del hospital): optimizacion de recursos.

---

## 1. Importar los datos

1. Power BI Desktop -> **Obtener datos -> Texto/CSV** -> selecciona `heart_enriquecido.csv`.
2. En el editor de Power Query verifica los tipos:
   - `Age, RestingBP, Cholesterol, MaxHR` -> Numero entero.
   - `Oldpeak, Probabilidad_Riesgo, Costo_Tratamiento_USD` -> Numero decimal.
   - `HeartDisease, FastingBS, Prediccion_Final` -> Numero entero.
   - Columnas `*_desc`, `ID_Paciente` -> Texto.
3. **Cerrar y aplicar**. La tabla se llamara `heart_enriquecido`.

> Para slicers y ejes usa siempre las columnas `*_desc` (en espanol). Las columnas
> originales (`Sex`, `ChestPainType`, etc.) se quedan para calculo, no para mostrar.

---

## 2. Columnas calculadas (DAX)

Crea estas columnas con **Modelado -> Nueva columna**.

### 2.1 Banda de riesgo (segmenta el score continuo)

```DAX
Banda_Riesgo =
SWITCH(
    TRUE(),
    heart_enriquecido[Probabilidad_Riesgo] >= 0.80, "1. Critico",
    heart_enriquecido[Probabilidad_Riesgo] >= 0.50, "2. Alto",
    heart_enriquecido[Probabilidad_Riesgo] >= 0.20, "3. Moderado",
    "4. Bajo"
)
```

El prefijo numerico fuerza el orden correcto en los visuales.

### 2.2 Grupo de edad (para segmentacion clinica)

```DAX
Grupo_Edad =
SWITCH(
    TRUE(),
    heart_enriquecido[Age] < 40, "< 40",
    heart_enriquecido[Age] < 55, "40-54",
    heart_enriquecido[Age] < 65, "55-64",
    "65+"
)
```

### 2.3 Resultado del modelo vs realidad (para la capa financiera)

```DAX
Resultado_Modelo =
VAR Real = heart_enriquecido[HeartDisease]
VAR Pred = heart_enriquecido[Prediccion_Final]
RETURN
SWITCH(
    TRUE(),
    Pred = 1 && Real = 1, "Verdadero Positivo",
    Pred = 0 && Real = 1, "Falso Negativo",
    Pred = 1 && Real = 0, "Falso Positivo",
    "Verdadero Negativo"
)
```

---

## 3. Parametro What-If (para el modelo financiero)

**Modelado -> Nuevo parametro -> Campo numerico:**
- Nombre: `Factor_Complicacion`
- Minimo: 1.5 | Maximo: 4 | Incremento: 0.1 | Valor por defecto: 2.5

Supuesto de negocio: un evento cardiaco NO prevenido (infarto, cateterismo de
urgencia) cuesta `Factor_Complicacion` veces el costo del tratamiento preventivo.
Esto permite a la direccion simular escenarios moviendo un slider.

---

## 4. Medidas DAX - CAPA OPERATIVA

Crea una tabla de medidas o agregalas con **Modelado -> Nueva medida**.

```DAX
Total Pacientes = COUNTROWS(heart_enriquecido)

Pacientes Alto Riesgo =
CALCULATE([Total Pacientes], heart_enriquecido[Prediccion_Final] = 1)

Pacientes Criticos =
CALCULATE([Total Pacientes], heart_enriquecido[Probabilidad_Riesgo] > 0.80)

Tasa Alto Riesgo % =
DIVIDE([Pacientes Alto Riesgo], [Total Pacientes])

Probabilidad Riesgo Promedio =
AVERAGE(heart_enriquecido[Probabilidad_Riesgo])

Edad Promedio = AVERAGE(heart_enriquecido[Age])
```

Medida con formato condicional (semaforo) para tarjetas:

```DAX
Color Alerta Critico =
SWITCH(
    TRUE(),
    [Pacientes Criticos] >= 300, "#C0392B",   -- rojo
    [Pacientes Criticos] >= 150, "#E67E22",   -- naranja
    "#27AE60"                                   -- verde
)
```

### Visualizaciones - Capa Operativa

| KPI / Elemento | Visual | Campos | Notas |
|---|---|---|---|
| Total Pacientes | Tarjeta | `[Total Pacientes]` | |
| Pacientes Alto Riesgo | Tarjeta | `[Pacientes Alto Riesgo]` | |
| Pacientes Criticos | Tarjeta KPI | `[Pacientes Criticos]` | Formato condicional con `[Color Alerta Critico]` |
| Tasa Alto Riesgo % | Tarjeta | `[Tasa Alto Riesgo %]` | Formato porcentaje |
| Distribucion por riesgo | Grafico de anillo | Leyenda: `Banda_Riesgo`, Valores: `[Total Pacientes]` | |
| Riesgo por tipo de dolor | Barras apiladas | Eje: `ChestPainType_desc`, Leyenda: `Banda_Riesgo` | Cumple el requisito de segmentar por dolor toracico (cp) |
| Edad vs Colesterol | **Grafico de dispersion** | X: `Age`, Y: `Cholesterol`, Saturacion de color: `Probabilidad_Riesgo`, Detalles: `ID_Paciente` | El color codifica el riesgo predicho (requisito explicito) |
| Lista de criticos | Tabla | `ID_Paciente, Age, ChestPainType_desc, Probabilidad_Riesgo, Costo_Tratamiento_USD` | Filtro de visual: `Probabilidad_Riesgo > 0.8`, orden descendente |
| Filtros | Segmentaciones | `Sex_desc`, `ChestPainType_desc`, `ST_Slope_desc`, `Grupo_Edad` | |

---

## 5. Medidas DAX - CAPA EJECUTIVA / FINANCIERA

```DAX
Costo Total = SUM(heart_enriquecido[Costo_Tratamiento_USD])

Costo Promedio Paciente =
DIVIDE([Costo Total], [Total Pacientes])

Costo Alto Riesgo =
CALCULATE([Costo Total], heart_enriquecido[Prediccion_Final] = 1)

Costo Bajo Riesgo =
CALCULATE([Costo Total], heart_enriquecido[Prediccion_Final] = 0)

Costo Medio Alto Riesgo =
CALCULATE([Costo Promedio Paciente], heart_enriquecido[Prediccion_Final] = 1)

Costo Medio Bajo Riesgo =
CALCULATE([Costo Promedio Paciente], heart_enriquecido[Prediccion_Final] = 0)
```

### Modelo de prevencion (usa el parametro What-If)

```DAX
-- Costo si los enfermos detectados a tiempo NO se hubieran tratado
-- (se habrian complicado y costado Factor_Complicacion veces mas).
Costo Evitado (Prevencion) =
VAR CostoVP =
    CALCULATE(
        [Costo Total],
        heart_enriquecido[Resultado_Modelo] = "Verdadero Positivo"
    )
RETURN
    CostoVP * ( SELECTEDVALUE('Factor_Complicacion'[Factor_Complicacion Value], 2.5) - 1 )

ROI Prevencion % =
DIVIDE([Costo Evitado (Prevencion)], [Costo Alto Riesgo])
```

### Tasa de exito de intervencion temprana

```DAX
-- % de enfermos reales que el modelo detecto a tiempo (sensibilidad operativa).
Tasa Deteccion Temprana =
VAR VP = CALCULATE([Total Pacientes], heart_enriquecido[Resultado_Modelo] = "Verdadero Positivo")
VAR FN = CALCULATE([Total Pacientes], heart_enriquecido[Resultado_Modelo] = "Falso Negativo")
RETURN DIVIDE(VP, VP + FN)
```

```DAX
-- Enfermos que se ESCAPARON del cribado (riesgo clinico y futuro costo).
Pacientes No Detectados =
CALCULATE([Total Pacientes], heart_enriquecido[Resultado_Modelo] = "Falso Negativo")
```

### Visualizaciones - Capa Ejecutiva

| KPI / Elemento | Visual | Campos | Notas |
|---|---|---|---|
| Costo Total Cartera | Tarjeta | `[Costo Total]` | Formato moneda USD |
| Costo Promedio Paciente | Tarjeta | `[Costo Promedio Paciente]` | |
| Costo Evitado por Prevencion | Tarjeta | `[Costo Evitado (Prevencion)]` | El numero estrella para direccion |
| ROI Prevencion % | Tarjeta KPI / Medidor | `[ROI Prevencion %]` | |
| Tasa Deteccion Temprana | Medidor (gauge) | `[Tasa Deteccion Temprana]` | Objetivo: 0.90 |
| Costo por banda de riesgo | Columnas | Eje: `Banda_Riesgo`, Valor: `[Costo Total]` | Muestra donde se concentra el gasto |
| Composicion del costo | **Cascada (waterfall)** | Categoria: `Banda_Riesgo`, Valor: `[Costo Total]` | Bajo -> Moderado -> Alto -> Critico |
| Costo por tipo de dolor | Treemap | Grupo: `ChestPainType_desc`, Valor: `[Costo Total]` | |
| Alto vs Bajo riesgo | Barras | Comparar `[Costo Medio Alto Riesgo]` vs `[Costo Medio Bajo Riesgo]` | Justifica priorizar recursos |
| Slider de escenario | Segmentacion | `Factor_Complicacion` | Recalcula el ahorro en vivo |

---

## 6. Cifras de referencia (para validar tus medidas)

Al construir, tus medidas deben dar aproximadamente:

| Medida | Valor esperado |
|---|---|
| Total Pacientes | 918 |
| Pacientes Alto Riesgo | 517 |
| Pacientes Criticos (>0.80) | 326 |
| Tasa Alto Riesgo % | 56.3% |
| Costo Total | $16,892,000 |
| Costo Alto Riesgo | $13,243,800 |
| Tasa Deteccion Temprana | 0.886 (450 VP / 508 enfermos) |
| Pacientes No Detectados (FN) | 58 |
| Costo Evitado (Factor 2.5) | ~ Costo de los VP x 1.5 |

> Nota de honestidad analitica: la "Tasa de Deteccion" y el "Costo Evitado" usan la
> columna real `HeartDisease` para evaluar al modelo. En produccion no tendrias la
> verdad de los pacientes nuevos; estas medidas sirven para demostrar el VALOR
> historico del modelo a la direccion, no para operar en tiempo real.

---

## 7. Diseno y layout sugerido

- **Pagina 1 - Operativa (medicos):** fila superior de 4 tarjetas KPI; debajo a la
  izquierda el scatter Edad vs Colesterol; a la derecha barras apiladas por dolor
  toracico; franja inferior con la tabla de pacientes criticos. Slicers a la izquierda.
- **Pagina 2 - Ejecutiva (direccion):** fila de 4 tarjetas financieras; cascada de
  costos al centro; treemap por tipo de dolor; medidor de tasa de deteccion; slider
  `Factor_Complicacion` arriba a la derecha.
- Paleta sugerida: rojo `#C0392B` (critico), naranja `#E67E22` (alto), amarillo
  `#F1C40F` (moderado), verde `#27AE60` (bajo). Consistente con los semaforos clinicos.
- Agrega un boton de navegacion entre ambas paginas (Insertar -> Boton).

---

## Checkpoint Fase 3

Entregable: este documento + el CSV `heart_enriquecido.csv` ya listo para importar.
Al terminar de montar las dos paginas, comparte capturas o dudas. Luego pasamos a la
Fase 4 (alertas automatizadas por correo).
