"""
src/incendios_data.py
<<<<<<< HEAD
Carga, filtrado y calculo de centroides de incendios historicos de magnitud.
=======
Carga, filtrado y cálculo de centroides de incendios históricos de magnitud.
>>>>>>> incendios-magnitud-meteorologia/master
"""

from datetime import date, datetime
from pathlib import Path
<<<<<<< HEAD
import re
import unicodedata
import geopandas as gpd
import pandas as pd

RUTA_GPKG = (
    Path(__file__).resolve().parent.parent
    / "data" / "raw" / "incendios" / "poligonos" / "if_magnitud_compilado.gpkg"
)


def _corregir_encoding(texto: str) -> str:
    """
    Corrige caracteres mal codificados en strings Python.
    Maneja bytes latin-1 / Windows-1252 embebidos en unicode.
    """
    if not isinstance(texto, str):
        return str(texto)
    # Intento: re-codificar como latin-1 y decodificar como utf-8
    try:
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    # Intento: Windows-1252 -> utf-8
    try:
        return texto.encode("cp1252").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return texto


# Mapa exhaustivo de todos los valores de REGION observados en el GPKG
# Clave: valor raw (lowercase despues de _corregir_encoding + strip)
# Valor: nombre canonico
_MAPA_REGIONES = {
    # Aysen / Aisen
    "aysen": "Aysen",
    "aisen": "Aysen",
    "aysén": "Aysen",
    "regi1n de aysen": "Aysen",
    "region de aysen": "Aysen",
    "región del general carlos ibañez del campo": "Aysen",
    # Araucania
    "araucania": "La Araucania",
    "araucanía": "La Araucania",
    "la araucania": "La Araucania",
    "la araucanía": "La Araucania",
    "la araucania": "La Araucania",
    "r.la araucania": "La Araucania",
    "r.la araucanla": "La Araucania",
    "r.la araucanna": "La Araucania",
    "r.la araucansa": "La Araucania",
    "r.la araucanta": "La Araucania",
    "region de la araucania": "La Araucania",
    "región de la araucanía": "La Araucania",
    # Biobio
    "biobio": "Biobio",
    "biobío": "Biobio",
    "bio bio": "Biobio",
    "r.biobio": "Biobio",
    "region del biobio": "Biobio",
    "región del biobío": "Biobio",
    # Ñuble
    "nuble": "Nuble",
    "ñuble": "Nuble",
    "r.guble": "Nuble",
    "r.nuble": "Nuble",
    "region del euble": "Nuble",
    "region del nuble": "Nuble",
    # Maule
    "maule": "Maule",
    "r.maule": "Maule",
    "region del maule": "Maule",
    "región del maule": "Maule",
    # Metropolitana
    "metropolitana": "Metropolitana",
    "r.metropolitana": "Metropolitana",
    "regi1n metropolitana": "Metropolitana",
    "regi4n metropolitana": "Metropolitana",
    "region metropolitana": "Metropolitana",
    "región metropolitana": "Metropolitana",
    "región metropolitana de santiago": "Metropolitana",
    # O'Higgins
    "ohiggins": "O'Higgins",
    "o'higgins": "O'Higgins",
    "r.o'higgins": "O'Higgins",
    "region de ohiggins": "O'Higgins",
    "región del libertador general bernardo o'higgins": "O'Higgins",
    # Los Lagos
    "los lagos": "Los Lagos",
    "r.los lagos": "Los Lagos",
    "region de los lagos": "Los Lagos",
    "región de los lagos": "Los Lagos",
    # Los Rios
    "los rios": "Los Rios",
    "los ríos": "Los Rios",
    # Valparaiso
    "valparaiso": "Valparaiso",
    "valparaíso": "Valparaiso",
    "r.valparaiso": "Valparaiso",
    "region de valparaiso": "Valparaiso",
    "region del valparaiso": "Valparaiso",
    "región de valparaíso": "Valparaiso",
    # Magallanes
    "magallanes": "Magallanes",
    "r.magallanes": "Magallanes",
    # Coquimbo
    "coquimbo": "Coquimbo",
    "región de coquimbo": "Coquimbo",
    # Tarapaca
    "tarapaca": "Tarapaca",
    "tarapacá": "Tarapaca",
}


def _normalizar_region(texto: str) -> str:
    """
    Normaliza un valor raw de REGION a nombre canonico.
    1. Corrige encoding (latin-1 embebido)
    2. Quita tildes para busqueda en el mapa
    3. Aplica mapa de normalizacion
    """
    if not isinstance(texto, str):
        return "No informada"

    # Paso 1: corregir encoding
    corregido = _corregir_encoding(texto).strip()

    # Paso 2: normalizar para busqueda (minusculas, sin tildes)
    sin_tildes = unicodedata.normalize("NFD", corregido.lower())
    sin_tildes = "".join(c for c in sin_tildes if unicodedata.category(c) != "Mn")
    sin_tildes = sin_tildes.strip()

    # Paso 3: buscar en mapa por valor sin tildes
    for clave, canon in _MAPA_REGIONES.items():
        clave_norm = unicodedata.normalize("NFD", clave.lower())
        clave_norm = "".join(c for c in clave_norm if unicodedata.category(c) != "Mn")
        if sin_tildes == clave_norm:
            return canon

    # Si no encontro, devolver corregido
    return corregido
=======
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
>>>>>>> incendios-magnitud-meteorologia/master


def cargar_geopackage_incendios(ruta_gpkg: str | Path = RUTA_GPKG) -> gpd.GeoDataFrame:
    """
    Carga el GeoPackage de incendios de magnitud compilado.
    Calcula centroides en WGS84 (EPSG:4326) para latitud y longitud.
    """
    ruta = Path(ruta_gpkg)
    if not ruta.exists():
<<<<<<< HEAD
        raise FileNotFoundError(f"No se encontro el archivo GeoPackage en: {ruta}")

    gdf = gpd.read_file(ruta)

    # Asegurar CRS
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32719")

    # Centroides precisos calculados en CRS proyectado y luego pasados a WGS84
=======
        raise FileNotFoundError(f"No se encontró el archivo GeoPackage en: {ruta}")

    gdf = gpd.read_file(ruta)

    # Asegurar reproyección a EPSG:4326 para obtener latitud y longitud geográficas
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:32719")

    # Centroides en CRS proyectado para cálculo geométrico correcto y luego a 4326
>>>>>>> incendios-magnitud-meteorologia/master
    centroides_wgs84 = gdf.geometry.centroid.to_crs("EPSG:4326")
    gdf["lon_centroide"] = centroides_wgs84.x
    gdf["lat_centroide"] = centroides_wgs84.y

<<<<<<< HEAD
    # Reproyectar geometrías a EPSG:4326 (WGS84) para visualización web / Folium
    gdf = gdf.to_crs("EPSG:4326")

    # Fechas
=======
    # Limpieza de fechas
>>>>>>> incendios-magnitud-meteorologia/master
    if "FECHA_INI" in gdf.columns:
        gdf["FECHA_INI_DT"] = pd.to_datetime(gdf["FECHA_INI"], errors="coerce")
    else:
        gdf["FECHA_INI_DT"] = pd.NaT

    if "FECHA_TER" in gdf.columns:
        gdf["FECHA_TER_DT"] = pd.to_datetime(gdf["FECHA_TER"], errors="coerce")
    else:
        gdf["FECHA_TER_DT"] = pd.NaT

<<<<<<< HEAD
    # Nombres y regiones
    gdf["NOM_INCEN"] = (
        gdf["NOM_INCEN"].fillna("Sin Nombre").astype(str)
        .apply(_corregir_encoding).str.strip()
    )
    if "REGION" in gdf.columns:
        gdf["REGION"] = gdf["REGION"].fillna("No informada").astype(str).apply(_normalizar_region)
    if "COMUNA" in gdf.columns:
        gdf["COMUNA"] = (
            gdf["COMUNA"].fillna("No informada").astype(str)
            .apply(_corregir_encoding).str.strip()
        )
    if "TEMPORADA" in gdf.columns:
        gdf["TEMPORADA"] = gdf["TEMPORADA"].fillna("Desconocida").astype(str).str.strip()

    # Superficie
=======
    # Limpieza de nombres de incendio y regiones con corrección de codificación
    gdf["NOM_INCEN"] = gdf["NOM_INCEN"].fillna("Sin Nombre").astype(str).apply(_corregir_mojibake).str.strip()
    if "REGION" in gdf.columns:
        gdf["REGION"] = gdf["REGION"].fillna("No informada").astype(str).apply(_corregir_mojibake).str.strip()
    if "COMUNA" in gdf.columns:
        gdf["COMUNA"] = gdf["COMUNA"].fillna("No informada").astype(str).apply(_corregir_mojibake).str.strip()
    if "TEMPORADA" in gdf.columns:
        gdf["TEMPORADA"] = gdf["TEMPORADA"].fillna("Desconocida").astype(str).str.strip()

    # Superficie en hectáreas
>>>>>>> incendios-magnitud-meteorologia/master
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
<<<<<<< HEAD
    return sorted(
        [t for t in gdf["TEMPORADA"].unique() if t and t != "Desconocida"],
        reverse=True,
    )
=======
    temporadas = sorted([t for t in gdf["TEMPORADA"].unique() if t and t != "Desconocida"], reverse=True)
    return temporadas
>>>>>>> incendios-magnitud-meteorologia/master


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
<<<<<<< HEAD
    """Filtra el GeoDataFrame de incendios por temporada, region o texto en nombre."""
=======
    """Filtra el GeoDataFrame de incendios por temporada, región o texto en nombre."""
>>>>>>> incendios-magnitud-meteorologia/master
    df_filtrado = gdf.copy()
    if temporada and temporada != "Todas":
        df_filtrado = df_filtrado[df_filtrado["TEMPORADA"] == temporada]
    if region and region != "Todas":
        df_filtrado = df_filtrado[df_filtrado["REGION"] == region]
    if texto_busqueda:
        patron = texto_busqueda.strip().lower()
<<<<<<< HEAD
        df_filtrado = df_filtrado[
            df_filtrado["NOM_INCEN"].str.lower().str.contains(patron, na=False)
        ]
=======
        df_filtrado = df_filtrado[df_filtrado["NOM_INCEN"].str.lower().str.contains(patron, na=False)]
>>>>>>> incendios-magnitud-meteorologia/master
    return df_filtrado


def extraer_info_incendio(fila: pd.Series) -> dict:
<<<<<<< HEAD
    """Extrae un diccionario con metadatos utiles para la interfaz y consulta meteorologica."""
=======
    """Extrae un diccionario con metadatos útiles para la interfaz y consulta meteorológica."""
>>>>>>> incendios-magnitud-meteorologia/master
    fecha_ini = fila.get("FECHA_INI_DT")
    fecha_ter = fila.get("FECHA_TER_DT")

    fecha_ini_date = fecha_ini.date() if pd.notna(fecha_ini) else None
    fecha_ter_date = fecha_ter.date() if pd.notna(fecha_ter) else None

<<<<<<< HEAD
=======
    # Si no hay fecha de término o es anterior a la de inicio, usar ventana de 5 días
>>>>>>> incendios-magnitud-meteorologia/master
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
<<<<<<< HEAD
        "superficie_ha": float(
            fila.get("superficie_ha_clean", 0.0)
            if pd.notna(fila.get("superficie_ha_clean"))
            else 0.0
        ),
=======
        "superficie_ha": float(fila.get("superficie_ha_clean", 0.0) if pd.notna(fila.get("superficie_ha_clean")) else 0.0),
>>>>>>> incendios-magnitud-meteorologia/master
        "latitud": float(fila.get("lat_centroide", 0.0)),
        "longitud": float(fila.get("lon_centroide", 0.0)),
        "fecha_inicio": fecha_ini_date,
        "fecha_termino": fecha_ter_date,
    }
