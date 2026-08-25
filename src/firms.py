## Descarga y filtrados de púntos FIRMS

"""
firms.py
Descarga y filtrado de puntos FIRMS (NASA) para cruzar con incendios históricos.

Requiere un MAP_KEY gratuito: https://firms.modaps.eosdis.nasa.gov/api/map_key/
No lo hardcodees acá: guárdalo como variable de entorno FIRMS_MAP_KEY
(en Streamlit Cloud: st.secrets["FIRMS_MAP_KEY"]; en local: archivo .env).
"""

import os
from datetime import date, timedelta, datetime
from io import StringIO
from pathlib import Path

import pandas as pd
import requests

# Sensores Near Real Time (solo últimos días)
SENSORES_NRT = [
    "MODIS_NRT",        # últimos 10 días
    "VIIRS_SNPP_NRT",   # últimos 10 días
    "VIIRS_NOAA20_NRT", # últimos 5 días
]

# Sensores de Archivo historico (Standard Processing) - cubren datos historicos
SENSORES_HISTORICOS = [
    "VIIRS_SNPP_SP",   # VIIRS Suomi-NPP SP - desde 2012
    "VIIRS_NOAA20_SP", # VIIRS NOAA-20 SP - desde 2018
    "MODIS_SP",        # MODIS Standard Processing - desde 2000
]

SENSORES_DISPONIBLES = SENSORES_NRT + SENSORES_HISTORICOS

# Limite de dias por sensor (la API FIRMS acepta maximo 5 dias)
LIMITE_DIAS = {
    "MODIS_NRT": 5,
    "VIIRS_SNPP_NRT": 5,
    "VIIRS_NOAA20_NRT": 5,
    "MODIS_SP": 5,
    "VIIRS_SNPP_SP": 5,
    "VIIRS_NOAA20_SP": 5,
}

BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"


def es_fecha_historica(fecha: date, umbral_dias: int = 7) -> bool:
    """Retorna True si la fecha es más antigua que `umbral_dias` desde hoy."""
    return (date.today() - fecha).days > umbral_dias


def sensor_recomendado(fecha: date, preferencia: str = "VIIRS_SNPP_NRT") -> str:
    """
    Devuelve el sensor más apropiado según la fecha.
    Si la fecha es histórica (>7 días), usa la variante de archivo.
    """
    if not es_fecha_historica(fecha):
        return preferencia
    # Mapeo NRT -> Archivo SP
    mapeo = {
        "MODIS_NRT": "MODIS_SP",
        "VIIRS_SNPP_NRT": "VIIRS_SNPP_SP",
        "VIIRS_NOAA20_NRT": "VIIRS_NOAA20_SP",
        "MODIS_SP": "MODIS_SP",
        "VIIRS_SNPP_SP": "VIIRS_SNPP_SP",
        "VIIRS_NOAA20_SP": "VIIRS_NOAA20_SP",
    }
    return mapeo.get(preferencia, "VIIRS_SNPP_SP")


def _leer_toml(ruta: Path) -> dict:
    """Lee un archivo TOML usando tomllib (Python 3.11+) o tomli como fallback."""
    try:
        import tomllib  # Python 3.11+
        with open(ruta, "rb") as f:
            return tomllib.load(f)
    except ImportError:
        pass
    try:
        import tomli
        with open(ruta, "rb") as f:
            return tomli.load(f)
    except ImportError:
        pass
    # Fallback manual: parseo línea a línea
    data = {}
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def obtener_map_key(map_key: str | None = None) -> str:
    """Obtiene la clave de FIRMS de parámetro, variable de entorno o secrets.toml."""
    if map_key and map_key.strip():
        return map_key.strip()

    key = os.getenv("FIRMS_MAP_KEY", "").strip()
    if key:
        return key

    # Intentar leer desde Streamlit secrets (sin lanzar excepción si no está disponible)
    try:
        import streamlit as st
        val = st.secrets.get("FIRMS_MAP_KEY", "")
        if val and str(val).strip():
            os.environ["FIRMS_MAP_KEY"] = str(val).strip()
            return str(val).strip()
    except Exception:
        pass

    # Buscar en archivos locales usando parser TOML correcto
    root_dir = Path(__file__).resolve().parent.parent
    toml_candidatos = [
        root_dir / ".streamlit" / "secrets.toml",
        root_dir / "secrets.toml",
    ]
    for ruta in toml_candidatos:
        if ruta.exists():
            try:
                data = _leer_toml(ruta)
                val = data.get("FIRMS_MAP_KEY", "")
                if val and str(val).strip():
                    os.environ["FIRMS_MAP_KEY"] = str(val).strip()
                    return str(val).strip()
            except Exception:
                pass

    # Fallback: .env y .env.txt
    env_candidatos = [root_dir / ".env", root_dir / ".env.txt"]
    for ruta in env_candidatos:
        if ruta.exists():
            try:
                for linea in ruta.read_text(encoding="utf-8").splitlines():
                    if "FIRMS_MAP_KEY" in linea and "=" in linea:
                        val = linea.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            os.environ["FIRMS_MAP_KEY"] = val
                            return val
            except Exception:
                pass

    raise RuntimeError(
        "No se encontró FIRMS_MAP_KEY. Defínela en .streamlit/secrets.toml o ingrésala en la interfaz."
    )


_obtener_map_key = obtener_map_key


def descargar_puntos_firms(
    bbox: tuple[float, float, float, float],
    fecha_inicio: date,
    dias: int = 10,
    sensor: str = "VIIRS_SNPP_NRT",
    map_key: str | None = None,
    auto_historico: bool = True,
) -> pd.DataFrame:
    """
    Descarga puntos FIRMS dentro de un bounding box para una ventana de días.

    Si `auto_historico=True` (por defecto), detecta automáticamente si la fecha
    es histórica y cambia al sensor de archivo equivalente (ej. VIIRS_SNPP_SP).
    """
    key = _obtener_map_key(map_key)

    # Auto-selección de sensor para datos históricos
    if auto_historico:
        sensor = sensor_recomendado(fecha_inicio, preferencia=sensor)

    if sensor not in SENSORES_DISPONIBLES:
        raise ValueError(f"Sensor no reconocido: {sensor}. Disponibles: {SENSORES_DISPONIBLES}")

    # Respetar límite de días por sensor
    dias = min(dias, LIMITE_DIAS.get(sensor, 10))

    min_lon, min_lat, max_lon, max_lat = bbox
    # Redondear coordenadas a 4 decimales para evitar URLs muy largas
    min_lon, min_lat = round(min_lon, 4), round(min_lat, 4)
    max_lon, max_lat = round(max_lon, 4), round(max_lat, 4)

    url = (
        f"{BASE_URL}/{key}/{sensor}/"
        f"{min_lon},{min_lat},{max_lon},{max_lat}/{dias}/"
        f"{fecha_inicio.isoformat()}"
    )

    respuesta = requests.get(url, timeout=30)
    respuesta.raise_for_status()

    texto = respuesta.text.strip()
    if not texto:
        return pd.DataFrame()

    if "Invalid MAP_KEY" in texto or "Invalid key" in texto:
        raise ValueError("NASA FIRMS: La clave MAP_KEY ingresada no es válida o aún no está activada por NASA.")

    if "Invalid" in texto and "\n" not in texto:
        return pd.DataFrame()

    if "No data" in texto and len(texto) < 200:
        return pd.DataFrame()

    try:
        df = pd.read_csv(StringIO(texto))
    except Exception:
        return pd.DataFrame()

    if df.empty or "acq_date" not in df.columns:
        return pd.DataFrame()

    df["acq_datetime"] = pd.to_datetime(
        df["acq_date"].astype(str) + " " + df["acq_time"].astype(str).str.zfill(4),
        format="%Y-%m-%d %H%M",
        errors="coerce",
    )
    df["sensor_usado"] = sensor
    return df.dropna(subset=["acq_datetime"])


def descargar_todos_sensores_firms(
    bbox: tuple[float, float, float, float],
    fecha_inicio: date,
    dias: int = 5,
    map_key: str | None = None,
) -> pd.DataFrame:
    """
    Descarga puntos FIRMS consultando TODOS los sensores satelitales disponibles
    (VIIRS Suomi-NPP, VIIRS NOAA-20 y MODIS Terra/Aqua).
    Detecta automáticamente si la fecha es histórica (Standard Processing) o reciente (NRT).
    Combina los resultados, normaliza las columnas y los ordena cronológicamente.
    """
    key = _obtener_map_key(map_key)
    es_hist = es_fecha_historica(fecha_inicio)

    sensores = (
        ["VIIRS_SNPP_SP", "VIIRS_NOAA20_SP", "MODIS_SP"]
        if es_hist
        else ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "MODIS_NRT"]
    )

    dfs = []
    for s in sensores:
        try:
            df_s = descargar_puntos_firms(
                bbox,
                fecha_inicio,
                dias=dias,
                sensor=s,
                map_key=key,
                auto_historico=False,
            )
            if not df_s.empty:
                if "VIIRS" in s:
                    sat_etiqueta = "VIIRS (Suomi-NPP)" if "SNPP" in s else "VIIRS (NOAA-20)"
                else:
                    sat_etiqueta = "MODIS (Terra/Aqua)"
                df_s["satelite_nombre"] = sat_etiqueta
                df_s["sensor_codigo"] = s
                dfs.append(df_s)
        except Exception:
            continue

    if not dfs:
        return pd.DataFrame()

    df_total = pd.concat(dfs, ignore_index=True)
    if "acq_datetime" in df_total.columns:
        df_total = df_total.sort_values("acq_datetime").reset_index(drop=True)
    return df_total


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