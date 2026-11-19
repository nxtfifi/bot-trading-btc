import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

VENTANA = 20
LAGS = [f"lag_{k}" for k in range(VENTANA)]
CONTRATO = {"version": "lineal-20-rezagos-v1", "variables": LAGS, "objetivo": "close[t+1]/close[t] - 1"}


def indicadores(df):
    r = df.close / df.close.shift(1) - 1
    sma20 = df.close.rolling(20).mean()
    return pd.DataFrame({"distancia_sma20": df.close / sma20 - 1, "volatilidad20": r.rolling(20).std()}, index=df.index)


def pronosticar(df):
    r = df.close / df.close.shift(1) - 1
    x = pd.DataFrame({f"lag_{k}": r.shift(k) for k in range(VENTANA)})
    y = df.close.shift(-1) / df.close - 1
    entrenamiento = pd.concat([x, y.rename("y")], axis=1).dropna()
    if len(entrenamiento) < 500:
        raise ValueError(f"Historia insuficiente: {len(entrenamiento)} ejemplos (mínimo 500)")
    modelo = make_pipeline(StandardScaler(), LinearRegression()).fit(entrenamiento[LAGS], entrenamiento.y)
    ultima = x.iloc[[-1]]
    if ultima.isna().any().any():
        raise ValueError("La última vela no tiene 20 rendimientos previos")
    pred = float(modelo.predict(ultima)[0])
    if not np.isfinite(pred):
        raise ValueError("Pronóstico no finito")
    return pred, len(entrenamiento)
