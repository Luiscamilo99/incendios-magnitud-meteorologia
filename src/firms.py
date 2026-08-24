## Descarga y filtrados de púntos FIRMS

"""
firms.py
Descarga y filtrado de puntos FIRMS (NASA) para cruzar con incendios históricos.

Requiere un MAP_KEY gratuito: https://firms.modaps.eosdis.nasa.gov/api/map_key/
No lo hardcodees acá: guárdalo como variable de entorno FIRMS_MAP_KEY
(en Streamlit Cloud: st.secrets["FIRMS_MAP_KEY"]; en local: archivo .env).
"""

import os
from datetime import date, timedelta
from io import StringIO

import pandas as pd
import requests
from shapely.geometry import Point

FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY", "")

# Sensor/satélite disponibles en el API de área histórica de FIRMS.
# VIIRS_SNPP_NRT / VIIRS_NOAA20_NRT son casi tiempo real; para histórico
# conviene usar las versiones "SP" (Standard Processing) cuando existan.
SENSORES_DISPONIBLES = [
    "MODIS_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
]

BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def _validar_map_key() -> None:
    if not FIRMS_MAP_KEY:
        raise RuntimeError(
            "No se encontró FIRMS_MAP_KEY. Definila como variable de entorno "
            "o en .streamlit/secrets.toml antes de llamar a esta función."
        )


def descargar_puntos_firms(
    bbox: tuple[float, float, float, float],
    fecha_inicio: date,
    dias: int = 10,
    sensor: str = "VIIRS_SNPP_NRT",
) -> pd.DataFrame:
    """
    Descarga puntos FIRMS dentro de un bounding box para una ventana de días.

    bbox: (min_lon, min_lat, max_lon, max_lat)
    fecha_inicio: primer día de la ventana de consulta
    dias: cantidad de días a consultar (el API de área permite hasta 10 por request)

    Nota: el API "area/csv" da datos recientes (rango limitado hacia atrás).
    Para incendios antiguos (varios años), usar en su lugar el Archive Download
    (https://firms.modaps.eosdis.nasa.gov/download/) y leer el CSV/SHP local
    con pd.read_csv() en vez de esta función.
    """
    _validar_map_key()

    if sensor not in SENSORES_DISPONIBLES:
        raise ValueError(f"Sensor no reconocido: {sensor}")

    min_lon, min_lat, max_lon, max_lat = bbox
    url = (
        f"{BASE_URL}/{FIRMS_MAP_KEY}/{sensor}/"
        f"{min_lon},{min_lat},{max_lon},{max_lat}/{dias}/"
        f"{fecha_inicio.isoformat()}"
    )

    respuesta = requests.get(url, timeout=30)
    respuesta.raise_for_status()

    df = pd.read_csv(StringIO(respuesta.text))
    if df.empty:
        return df

    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"] + " " + df["acq_time"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M",
    )
    return df


def leer_archivo_historico(ruta_csv: str) -> pd.DataFrame:
    """
    Lee un CSV descargado manualmente desde el Archive Download de FIRMS.
    Útil para incendios de años anteriores, donde el API en vivo no alcanza.
    """
    df = pd.read_csv(ruta_csv)
    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"] + " " + df["acq_time"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M",
    )
    return df


def filtrar_puntos_cercanos(
    df_firms: pd.DataFrame,
    lat_incendio: float,
    lon_incendio: float,
    fecha_inicio_incendio: date,
    radio_km: float = 5.0,
    ventana_dias: int = 10,
) -> pd.DataFrame:
    """
    Filtra los puntos FIRMS cercanos a un incendio puntual, dentro de una
    ventana temporal desde su fecha de inicio.
    """
    fecha_fin = fecha_inicio_incendio + timedelta(days=ventana_dias)

    df = df_firms[
        (df_firms["acq_datetime"].dt.date >= fecha_inicio_incendio)
        & (df_firms["acq_datetime"].dt.date <= fecha_fin)
    ].copy()

    if df.empty:
        return df

    # Distancia aproximada en grados -> km (suficiente para radios chicos;
    # para mayor precisión, reproyectar a UTM antes de medir distancia).
    grados_por_km = 1 / 111.0
    radio_grados = radio_km * grados_por_km

    df["distancia_aprox_km"] = (
        (df["latitude"] - lat_incendio) ** 2 + (df["longitude"] - lon_incendio) ** 2
    ) ** 0.5 / grados_por_km

    return df[df["distancia_aprox_km"] <= radio_km].sort_values("acq_datetime")


def obtener_dias_con_actividad(
    df_puntos_cercanos: pd.DataFrame,
    columna_tiempo: str = "acq_datetime",
) -> list[date]:
    """
    Devuelve la lista ordenada de días (sin duplicados) en los que hubo al
    menos un punto FIRMS cercano al incendio. Útil para poblar un
    selector de días en la página de perfil vertical, y para pedirle a
    meteorologia.consultar_meteorologia_historica() el rango
    (primer día, último día) en una sola llamada.
    """
    if df_puntos_cercanos.empty:
        return []

    return sorted(df_puntos_cercanos[columna_tiempo].dt.date.unique())


def detectar_periodo_peak(
    df_puntos_cercanos: pd.DataFrame,
    columna_tiempo: str = "acq_datetime",
    columna_intensidad: str = "frp",
    ventana: str = "1D",
) -> pd.Timestamp | None:
    """
    Agrupa los puntos por ventana temporal (por defecto 1 día) y devuelve
    el timestamp del periodo con mayor actividad, según la suma de FRP
    (Fire Radiative Power). Si no hay columna 'frp' disponible, cae a conteo
    de puntos.
    """
    if df_puntos_cercanos.empty:
        return None

    serie = df_puntos_cercanos.set_index(columna_tiempo)

    if columna_intensidad in df_puntos_cercanos.columns:
        agrupado = serie[columna_intensidad].resample(ventana).sum()
    else:
        agrupado = serie.resample(ventana).size()

    if agrupado.empty or agrupado.max() == 0:
        return None

    return agrupado.idxmax()


if __name__ == "__main__":
    # Ejemplo rápido de uso (requiere FIRMS_MAP_KEY definido en el entorno)
    bbox_ejemplo = (-73.5, -39.5, -71.5, -38.0)  # Araucanía aprox.
    df = descargar_puntos_firms(bbox_ejemplo, date(2026, 2, 1), dias=10)
    print(f"Puntos descargados: {len(df)}")