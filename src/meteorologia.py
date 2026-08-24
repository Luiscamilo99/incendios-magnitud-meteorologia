"""
meteorologia.py
Consulta de datos meteorológicos históricos (Open-Meteo, base ERA5) para
el periodo de mayor actividad FIRMS de un incendio.

No requiere API key. Límite orientativo: ~10.000 llamadas/día en uso no
comercial. https://open-meteo.com/en/docs/historical-weather-api
"""

from datetime import date, timedelta

import pandas as pd
import requests

BASE_URL = "https://archive-api.open-meteo.com/v1/archive"

# Niveles de presión disponibles en Open-Meteo (hPa). Cubren desde superficie
# hasta ~90 hPa; para incendios, 1000-700 hPa suele ser el rango más útil
# (capa límite atmosférica e inversión térmica).
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
) -> pd.DataFrame:
    """
    Devuelve un DataFrame horario con variables de superficie y perfil
    vertical, para una coordenada y un rango de fechas (una fila por hora
    por cada día del rango, en hora local).

    Si fecha_fin es None, consulta solo fecha_inicio (comportamiento de
    un solo día). Para navegar entre varios días de actividad de un
    incendio, pasa el primer y último día con puntos FIRMS relevantes
    (ver firms.obtener_dias_con_actividad()).
    """
    fecha_fin = fecha_fin or fecha_inicio
    niveles_presion = niveles_presion or NIVELES_PRESION_HPA
    variables = VARIABLES_SUPERFICIE + _variables_perfil_vertical(niveles_presion)

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": fecha_inicio.isoformat(),
        "end_date": fecha_fin.isoformat(),
        "hourly": ",".join(variables),
        "timezone": "America/Santiago",
    }

    respuesta = requests.get(BASE_URL, params=params, timeout=30)
    respuesta.raise_for_status()
    datos = respuesta.json()

    df = pd.DataFrame(datos["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


def extraer_condiciones_en_hora_peak(
    df_horario: pd.DataFrame, hora_peak: pd.Timestamp
) -> pd.Series:
    """
    De las 24 filas horarias del día, devuelve la fila más cercana a la
    hora exacta del peak de actividad FIRMS.
    """
    df_horario = df_horario.copy()
    df_horario["diferencia"] = (df_horario["time"] - hora_peak).abs()
    fila = df_horario.sort_values("diferencia").iloc[0]
    return fila.drop("diferencia")


def extraer_condiciones_cada_6h(
    df_horario: pd.DataFrame,
) -> dict[str, dict[str, pd.Series]]:
    """
    De un DataFrame horario que puede abarcar varios días (ya en hora
    local, ver timezone en consultar_meteorologia_historica), devuelve un
    diccionario anidado por día y luego por hora:

        {
            '2026-02-01': {'00:00': fila, '06:00': fila, '12:00': fila, '18:00': fila},
            '2026-02-02': {...},
            ...
        }

    Las llaves de día y hora quedan como strings listos para usar directo
    en selectbox/radio de Streamlit (día primero, hora después).
    """
    df_horario = df_horario.copy()
    df_horario["fecha_local"] = df_horario["time"].dt.date
    df_horario["hora_local"] = df_horario["time"].dt.hour

    horas_objetivo = [0, 6, 12, 18]
    resultado: dict[str, dict[str, pd.Series]] = {}

    for fecha, grupo_dia in df_horario.groupby("fecha_local"):
        condiciones_dia = {}
        for hora in horas_objetivo:
            fila = grupo_dia[grupo_dia["hora_local"] == hora]
            if not fila.empty:
                etiqueta_hora = f"{hora:02d}:00"
                condiciones_dia[etiqueta_hora] = fila.iloc[0]
        if condiciones_dia:
            resultado[fecha.isoformat()] = condiciones_dia

    return resultado


def armar_perfil_vertical(
    fila_peak: pd.Series, niveles_presion: list[int] | None = None
) -> pd.DataFrame:
    """
    Reorganiza la fila horaria (formato ancho: temperature_850hPa, etc.)
    a formato largo, listo para graficar el perfil vertical con plotly.
    """
    niveles_presion = niveles_presion or NIVELES_PRESION_HPA
    filas = []
    for nivel in niveles_presion:
        filas.append(
            {
                "nivel_hpa": nivel,
                "temperatura": fila_peak.get(f"temperature_{nivel}hPa"),
                "humedad_relativa": fila_peak.get(f"relative_humidity_{nivel}hPa"),
                "velocidad_viento": fila_peak.get(f"wind_speed_{nivel}hPa"),
                "direccion_viento": fila_peak.get(f"wind_direction_{nivel}hPa"),
            }
        )
    return pd.DataFrame(filas).sort_values("nivel_hpa", ascending=False)


if __name__ == "__main__":
    # Ejemplo rápido: condiciones en Temuco para una fecha de prueba
    df = consultar_meteorologia_historica(-38.7359, -72.5904, date(2026, 2, 1))
    print(df.head())