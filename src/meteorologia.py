"""
meteorologia.py
Consulta y procesamiento de datos meteorológicos históricos (Open-Meteo, base ERA5)
para análisis de incendios forestales y sondeos atmosféricos verticales (Skew-T).

API Reference: https://open-meteo.com/en/docs/historical-weather-api
"""

from datetime import date, timedelta
import math
import numpy as np
import pandas as pd
import requests

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Niveles de presión estándar en Open-Meteo (hPa)
NIVELES_PRESION_HPA = [1000, 975, 950, 925, 900, 850, 800, 700, 600, 500]

VARIABLES_SUPERFICIE = [
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "precipitation",
    "surface_pressure",
]


def calcular_punto_rocio(temperatura_c, humedad_relativa_pct):
    """
    Calcula la temperatura de punto de rocío (Dew Point) en °C
    usando la aproximación de Magnus-Tetens (a=17.27, b=237.7).
    """
    a = 17.27
    b = 237.7
    
    if isinstance(temperatura_c, (pd.Series, np.ndarray, list)):
        t = pd.to_numeric(pd.Series(temperatura_c), errors="coerce")
        hr = pd.to_numeric(pd.Series(humedad_relativa_pct), errors="coerce").clip(lower=1.0, upper=100.0)
        alpha = ((a * t) / (b + t)) + np.log(hr / 100.0)
        td = (b * alpha) / (a - alpha)
        return td
    else:
        if temperatura_c is None or humedad_relativa_pct is None or pd.isna(temperatura_c) or pd.isna(humedad_relativa_pct):
            return np.nan
        t = float(temperatura_c)
        hr = max(1.0, min(100.0, float(humedad_relativa_pct)))
        alpha = ((a * t) / (b + t)) + math.log(hr / 100.0)
        return (b * alpha) / (a - alpha)


def _variables_perfil_vertical(niveles: list[int]) -> list[str]:
    variables = []
    for nivel in niveles:
        variables += [
            f"temperature_{nivel}hPa",
            f"relative_humidity_{nivel}hPa",
            f"wind_speed_{nivel}hPa",
            f"wind_direction_{nivel}hPa",
        ]
    return variables


def consultar_meteorologia_historica(
    lat: float,
    lon: float,
    fecha_inicio: date,
    fecha_fin: date | None = None,
    niveles_presion: list[int] | None = None,
    timezone: str = "America/Santiago",
) -> pd.DataFrame:
    """
    Devuelve un DataFrame horario con variables de superficie y perfil
    vertical para una coordenada y rango de fechas.
    """
    fecha_fin = fecha_fin or fecha_inicio
    niveles_presion = niveles_presion or NIVELES_PRESION_HPA
    variables = VARIABLES_SUPERFICIE + _variables_perfil_vertical(niveles_presion)

    params = {
        "latitude": round(lat, 4),
        "longitude": round(lon, 4),
        "start_date": fecha_inicio.isoformat(),
        "end_date": fecha_fin.isoformat(),
        "hourly": ",".join(variables),
        "timezone": timezone,
        "wind_speed_unit": "kmh",
    }

    respuesta = requests.get(BASE_URL, params=params, timeout=40)
    respuesta.raise_for_status()
    datos = respuesta.json()

    if "hourly" not in datos or not datos["hourly"].get("time"):
        return pd.DataFrame()

    df = pd.DataFrame(datos["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    
    # Calcular punto de rocío en superficie
    if "temperature_2m" in df.columns and "relative_humidity_2m" in df.columns:
        df["dew_point_2m"] = calcular_punto_rocio(df["temperature_2m"], df["relative_humidity_2m"])

    # Calcular punto de rocío para cada nivel de presión
    for nivel in niveles_presion:
        t_col = f"temperature_{nivel}hPa"
        rh_col = f"relative_humidity_{nivel}hPa"
        if t_col in df.columns and rh_col in df.columns:
            df[f"dew_point_{nivel}hPa"] = calcular_punto_rocio(df[t_col], df[rh_col])

    # Regla 30-30-30 de incendios forestales
    t_critica = df["temperature_2m"] >= 30.0
    rh_critica = df["relative_humidity_2m"] <= 30.0
    viento_critico = (df["wind_speed_10m"] >= 30.0) | (df.get("wind_gusts_10m", 0.0) >= 30.0)
    df["alerta_30_30_30"] = t_critica & rh_critica & viento_critico

    df["fecha"] = df["time"].dt.date
    df["hora"] = df["time"].dt.strftime("%H:%M")

    return df


def calcular_estadisticas_resumen(df_horario: pd.DataFrame) -> dict:
    """Calcula métricas clave y extremos del período."""
    if df_horario.empty:
        return {}

    t_max = df_horario["temperature_2m"].max()
    t_min = df_horario["temperature_2m"].min()
    rh_min = df_horario["relative_humidity_2m"].min()
    viento_max = df_horario["wind_speed_10m"].max()
    rafaga_max = df_horario["wind_gusts_10m"].max() if "wind_gusts_10m" in df_horario.columns else 0.0
    precip_total = df_horario["precipitation"].sum() if "precipitation" in df_horario.columns else 0.0
    horas_30_30_30 = int(df_horario["alerta_30_30_30"].sum()) if "alerta_30_30_30" in df_horario.columns else 0

    return {
        "temp_max": t_max,
        "temp_min": t_min,
        "hr_min": rh_min,
        "viento_max": viento_max,
        "rafaga_max": rafaga_max,
        "precip_total": precip_total,
        "horas_30_30_30": horas_30_30_30,
        "dias_totales": df_horario["fecha"].nunique(),
        "total_registros": len(df_horario),
    }


def extraer_condiciones_cada_6h(
    df_horario: pd.DataFrame,
) -> dict[str, dict[str, pd.Series]]:
    """
    Devuelve un diccionario estructurado por día y por hora (00:00, 06:00, 12:00, 18:00):
    { '2024-02-01': {'00:00': fila, '06:00': fila, ...} }
    """
    df_horario = df_horario.copy()
    horas_objetivo = [0, 6, 12, 18]
    resultado: dict[str, dict[str, pd.Series]] = {}

    for fecha, grupo_dia in df_horario.groupby("fecha"):
        condiciones_dia = {}
        for hora in horas_objetivo:
            filas_hora = grupo_dia[grupo_dia["time"].dt.hour == hora]
            if not filas_hora.empty:
                etiqueta_hora = f"{hora:02d}:00"
                condiciones_dia[etiqueta_hora] = filas_hora.iloc[0]
        if condiciones_dia:
            resultado[fecha.isoformat()] = condiciones_dia

    return resultado


def armar_perfil_vertical(
    fila_hora: pd.Series, niveles_presion: list[int] | None = None
) -> pd.DataFrame:
    """
    Convierte la fila horaria plana a un DataFrame vertical de niveles de presión
    listo para construir el gráfico Skew-T.
    """
    niveles_presion = niveles_presion or NIVELES_PRESION_HPA
    filas = []
    
    for nivel in niveles_presion:
        t = fila_hora.get(f"temperature_{nivel}hPa")
        rh = fila_hora.get(f"relative_humidity_{nivel}hPa")
        ws = fila_hora.get(f"wind_speed_{nivel}hPa")
        wd = fila_hora.get(f"wind_direction_{nivel}hPa")
        td = fila_hora.get(f"dew_point_{nivel}hPa")
        
        if pd.isna(td) and pd.notna(t) and pd.notna(rh):
            td = calcular_punto_rocio(float(t), float(rh))

        filas.append(
            {
                "presion_hpa": float(nivel),
                "temperatura_c": float(t) if pd.notna(t) else np.nan,
                "punto_rocio_c": float(td) if pd.notna(td) else np.nan,
                "humedad_relativa": float(rh) if pd.notna(rh) else np.nan,
                "velocidad_viento_kmh": float(ws) if pd.notna(ws) else np.nan,
                "direccion_viento_deg": float(wd) if pd.notna(wd) else np.nan,
            }
        )

    df_perfil = pd.DataFrame(filas).sort_values("presion_hpa", ascending=False).reset_index(drop=True)
    return df_perfil