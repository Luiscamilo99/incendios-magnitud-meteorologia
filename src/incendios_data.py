"""
src/incendios_data.py
Carga, filtrado y cálculo de centroides de incendios históricos de magnitud.
"""

from datetime import date, datetime
from pathlib import Path
import geopandas as gpd
import pandas as pd

RUTA_GPKG = Path(__file__).resolve().parent.parent / "data" / "raw" / "incendios" / "poligonos" / "if_magnitud_compilado.gpkg"


def _corregir_mojibake(texto: str) -> str:
    """Corrige caracteres mal codificados como Ã³ -> ó, Ã­ -> í, etc."""
    if not isinstance(texto, str):
        return str(texto)
    reemplazos = {
        "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú",
        "Ã": "Á", "Ã‰": "É", "Ã": "Í", "Ã“": "Ó", "Ãš": "Ú",
        "Ã±": "ñ", "Ã‘": "Ñ", "": "Ñ", "Ã¼": "ü", "Ãœ": "Ü",
    }
    res = texto
    for k, v in reemplazos.items():
        res = res.replace(k, v)
    return res


def cargar_geopackage_incendios(ruta_gpkg: str | Path = RUTA_GPKG) -> gpd.GeoDataFrame:
    """
    Carga el GeoPackage de incendios de magnitud compilado.
    Calcula centroides en WGS84 (EPSG:4326) para latitud y longitud.
    """
    ruta = Path(ruta_gpkg)
    if not ruta.exists():
        raise FileNotFoundError(f"No se encontró el archivo GeoPackage en: {ruta}")

    gdf = gpd.read_file(ruta)

    # Asegurar reproyección a EPSG:4326 para obtener latitud y longitud geográficas
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32719")

    # Centroides en CRS proyectado para cálculo geométrico correcto y luego a 4326
    centroides_wgs84 = gdf.geometry.centroid.to_crs("EPSG:4326")
    gdf["lon_centroide"] = centroides_wgs84.x
    gdf["lat_centroide"] = centroides_wgs84.y

    # Limpieza de fechas
    if "FECHA_INI" in gdf.columns:
        gdf["FECHA_INI_DT"] = pd.to_datetime(gdf["FECHA_INI"], errors="coerce")
    else:
        gdf["FECHA_INI_DT"] = pd.NaT

    if "FECHA_TER" in gdf.columns:
        gdf["FECHA_TER_DT"] = pd.to_datetime(gdf["FECHA_TER"], errors="coerce")
    else:
        gdf["FECHA_TER_DT"] = pd.NaT

    # Limpieza de nombres de incendio y regiones con corrección de codificación
    gdf["NOM_INCEN"] = gdf["NOM_INCEN"].fillna("Sin Nombre").astype(str).apply(_corregir_mojibake).str.strip()
    if "REGION" in gdf.columns:
        gdf["REGION"] = gdf["REGION"].fillna("No informada").astype(str).apply(_corregir_mojibake).str.strip()
    if "COMUNA" in gdf.columns:
        gdf["COMUNA"] = gdf["COMUNA"].fillna("No informada").astype(str).apply(_corregir_mojibake).str.strip()
    if "TEMPORADA" in gdf.columns:
        gdf["TEMPORADA"] = gdf["TEMPORADA"].fillna("Desconocida").astype(str).str.strip()

    # Superficie en hectáreas
    if "Superficie_ha" in gdf.columns and gdf["Superficie_ha"].notna().any():
        gdf["superficie_ha_clean"] = pd.to_numeric(gdf["Superficie_ha"], errors="coerce")
    elif "SUPERFICIE" in gdf.columns:
        gdf["superficie_ha_clean"] = pd.to_numeric(gdf["SUPERFICIE"], errors="coerce")
    else:
        gdf["superficie_ha_clean"] = 0.0

    return gdf


def obtener_temporadas_disponibles(gdf: gpd.GeoDataFrame) -> list[str]:
    """Retorna la lista ordenada de temporadas disponibles."""
    if "TEMPORADA" not in gdf.columns:
        return []
    temporadas = sorted([t for t in gdf["TEMPORADA"].unique() if t and t != "Desconocida"], reverse=True)
    return temporadas


def obtener_regiones_disponibles(gdf: gpd.GeoDataFrame) -> list[str]:
    """Retorna la lista ordenada de regiones disponibles."""
    if "REGION" not in gdf.columns:
        return []
    return sorted([r for r in gdf["REGION"].unique() if r and r != "No informada"])


def filtrar_incendios(
    gdf: gpd.GeoDataFrame,
    temporada: str | None = None,
    region: str | None = None,
    texto_busqueda: str | None = None,
) -> gpd.GeoDataFrame:
    """Filtra el GeoDataFrame de incendios por temporada, región o texto en nombre."""
    df_filtrado = gdf.copy()
    if temporada and temporada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["TEMPORADA"] == temporada]
    if region and region != "Todas":
        df_filtrado = df_filtrado[df_filtrado["REGION"] == region]
    if texto_busqueda:
        patron = texto_busqueda.strip().lower()
        df_filtrado = df_filtrado[df_filtrado["NOM_INCEN"].str.lower().str.contains(patron, na=False)]
    return df_filtrado


def extraer_info_incendio(fila: pd.Series) -> dict:
    """Extrae un diccionario con metadatos útiles para la interfaz y consulta meteorológica."""
    fecha_ini = fila.get("FECHA_INI_DT")
    fecha_ter = fila.get("FECHA_TER_DT")

    fecha_ini_date = fecha_ini.date() if pd.notna(fecha_ini) else None
    fecha_ter_date = fecha_ter.date() if pd.notna(fecha_ter) else None

    # Si no hay fecha de término o es anterior a la de inicio, usar ventana de 5 días
    if fecha_ini_date and (not fecha_ter_date or fecha_ter_date < fecha_ini_date):
        fecha_ter_date = fecha_ini_date + pd.Timedelta(days=5).to_pytimedelta()

    return {
        "id": fila.get("ID", ""),
        "nombre": fila.get("NOM_INCEN", "Sin Nombre"),
        "temporada": fila.get("TEMPORADA", ""),
        "region": fila.get("REGION", "No informada"),
        "comuna": fila.get("COMUNA", "No informada"),
        "provincia": fila.get("PROVINCIA", "No informada"),
        "causa": fila.get("CAUSA", "No especificada"),
        "superficie_ha": float(fila.get("superficie_ha_clean", 0.0) if pd.notna(fila.get("superficie_ha_clean")) else 0.0),
        "latitud": float(fila.get("lat_centroide", 0.0)),
        "longitud": float(fila.get("lon_centroide", 0.0)),
        "fecha_inicio": fecha_ini_date,
        "fecha_termino": fecha_ter_date,
    }
