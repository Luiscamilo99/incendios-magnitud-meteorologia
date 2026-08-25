"""
app/pages/1_mapa_de_incendios.py
Visor cartográfico e interactivo de incendios de magnitud en Chile.
"""

import sys
from pathlib import Path

# Asegurar que la raíz del proyecto esté en sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import streamlit as st

# Importación condicional de librerías de mapas para máxima resiliencia
try:
    import folium
    from folium.plugins import MarkerCluster
    from streamlit_folium import st_folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

from src.incendios_data import (
    cargar_geopackage_incendios,
    extraer_info_incendio,
    filtrar_incendios,
    obtener_regiones_disponibles,
    obtener_temporadas_disponibles,
)

st.set_page_config(
    page_title="Mapa de Incendios | Incendios Forestales",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Mapa y Distribución Espacial de Incendios")
st.markdown(
    "Explora los incendios de magnitud en Chile (2013-2025). Filtra por temporada o región, "
    "analiza su distribución geográfica y selecciona cualquier incendio para consultar su perfil meteorológico."
)

# ==============================================================================
# CARGA DE DATOS (CACHEADA)
# ==============================================================================

@st.cache_data(show_spinner="Cargando base cartográfica de incendios...")
def get_gdf():
    try:
        return cargar_geopackage_incendios()
    except Exception as e:
        st.error(f"Error al cargar GeoPackage: {e}")
        return None

gdf = get_gdf()

if gdf is None or gdf.empty:
    st.error("No se pudo cargar la base de incendios.")
    st.stop()

# ==============================================================================
# FILTROS LATERALES
# ==============================================================================

st.sidebar.header("🔍 Filtros de Búsqueda")

temporadas = ["Todas"] + obtener_temporadas_disponibles(gdf)
temporada_sel = st.sidebar.selectbox("Temporada", temporadas, index=0)

regiones = ["Todas"] + obtener_regiones_disponibles(gdf)
region_sel = st.sidebar.selectbox("Región", regiones, index=0)

busqueda = st.sidebar.text_input("Buscar por nombre o comuna", "")

gdf_filtrado = filtrar_incendios(
    gdf,
    temporada=temporada_sel,
    region=region_sel,
    texto_busqueda=busqueda,
)

st.sidebar.markdown(f"**Incendios encontrados:** `{len(gdf_filtrado)}`")

# ==============================================================================
# TARJETAS DE RESUMEN
# ==============================================================================

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("🔥 Incendios Filtrados", f"{len(gdf_filtrado):,}")
with m2:
    sup_total = gdf_filtrado["superficie_ha_clean"].sum() if not gdf_filtrado.empty else 0.0
    st.metric("🌲 Superficie Afectada", f"{sup_total:,.0f} ha")
with m3:
    sup_prom = gdf_filtrado["superficie_ha_clean"].mean() if not gdf_filtrado.empty else 0.0
    st.metric("📏 Superficie Promedio", f"{sup_prom:,.0f} ha")
with m4:
    sup_max = gdf_filtrado["superficie_ha_clean"].max() if not gdf_filtrado.empty else 0.0
    st.metric("💥 Mayor Incendio", f"{sup_max:,.0f} ha")

st.markdown("---")

# ==============================================================================
# MAPA INTERACTIVO Y DETALLE
# ==============================================================================

col_mapa, col_detalle = st.columns([3, 2])

with col_mapa:
    st.subheader("Visualización en Mapa")

    df_mapa = gdf_filtrado.dropna(subset=["lat_centroide", "lon_centroide"]).copy()

    if df_mapa.empty:
        st.warning("No hay coordenadas disponibles para los filtros seleccionados.")
    else:
        # Prioridad 1: Folium si está disponible
        if FOLIUM_AVAILABLE:
            lat_c = df_mapa["lat_centroide"].mean()
            lon_c = df_mapa["lon_centroide"].mean()
            
            m = folium.Map(
                location=[lat_c, lon_c],
                zoom_start=6 if len(df_mapa) > 5 else 8,
                tiles="CartoDB positron",
            )
            marker_cluster = MarkerCluster(name="Incendios").add_to(m)

            for _, row in df_mapa.head(300).iterrows():
                lat = row["lat_centroide"]
                lon = row["lon_centroide"]
                nom = row.get("NOM_INCEN", "Sin Nombre")
                sup = row.get("superficie_ha_clean", 0.0)
                temp = row.get("TEMPORADA", "-")
                com = row.get("COMUNA", "-")
                fini = str(row.get("FECHA_INI", "-"))[:10]

                popup_html = f"""
                <div style="font-family: sans-serif; font-size: 13px; width: 220px;">
                    <b style="color: #DC2626; font-size: 14px;">{nom}</b><br>
                    <b>Temporada:</b> {temp}<br>
                    <b>Comuna:</b> {com}<br>
                    <b>Superficie:</b> {sup:,.1f} ha<br>
                    <b>Fecha Inicio:</b> {fini}
                </div>
                """
                color_mk = "#EF4444" if sup >= 10000 else "#F59E0B" if sup >= 1000 else "#3B82F6"
                folium.CircleMarker(
                    location=[lat, lon],
                    radius=5 if sup < 1000 else 8 if sup < 10000 else 12,
                    color=color_mk,
                    fill=True,
                    fill_color=color_mk,
                    fill_opacity=0.75,
                    popup=folium.Popup(popup_html, max_width=250),
                    tooltip=f"{nom} ({sup:,.0f} ha)",
                ).add_to(marker_cluster)

            st_folium(m, width="100%", height=520, returned_objects=[])

        # Prioridad 2: Plotly Mapbox si Folium no está disponible
        elif PLOTLY_AVAILABLE:
            fig_map = px.scatter_mapbox(
                df_mapa,
                lat="lat_centroide",
                lon="lon_centroide",
                size="superficie_ha_clean",
                color="TEMPORADA",
                hover_name="NOM_INCEN",
                hover_data={"COMUNA": True, "superficie_ha_clean": ":,.1f ha", "FECHA_INI": True},
                zoom=5,
                mapbox_style="carto-positron",
                height=520,
            )
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            # Fallback nativo Streamlit
            df_st_map = df_mapa.rename(columns={"lat_centroide": "lat", "lon_centroide": "lon"})
            st.map(df_st_map[["lat", "lon"]], zoom=5)

with col_detalle:
    st.subheader("Ficha del Incendio")

    if not gdf_filtrado.empty:
        gdf_filtrado["etiqueta_sel"] = (
            gdf_filtrado["NOM_INCEN"]
            + " | "
            + gdf_filtrado["TEMPORADA"]
            + " ("
            + gdf_filtrado["superficie_ha_clean"].map("{:,.0f} ha".format)
            + ")"
        )
        opciones = gdf_filtrado["etiqueta_sel"].tolist()
        
        # Sincronizar índice si ya hay un incendio activo en session_state
        id_actual = st.session_state.get("id_incendio_seleccionado")
        idx_def = 0
        if id_actual and "ID" in gdf_filtrado.columns:
            ids_lista = gdf_filtrado["ID"].tolist()
            if id_actual in ids_lista:
                idx_def = ids_lista.index(id_actual)

        idx_elegido = st.selectbox(
            "Selecciona un incendio para ver detalle:",
            range(len(opciones)),
            index=min(idx_def, len(opciones) - 1),
            format_func=lambda i: opciones[i],
        )

        fila_sel = gdf_filtrado.iloc[idx_elegido]
        info = extraer_info_incendio(fila_sel)

        # Sincronizar automáticamente con todas las páginas de la app
        st.session_state["id_incendio_seleccionado"] = info["id"]
        st.session_state["nombre_incendio_seleccionado"] = info["nombre"]
        st.session_state["temporada_incendio_seleccionado"] = info["temporada"]
        st.session_state["region_incendio_seleccionado"] = info["region"]
        st.session_state["lat_incendio"] = info["latitud"]
        st.session_state["lon_incendio"] = info["longitud"]
        st.session_state["fecha_inicio_incendio"] = info["fecha_inicio"]
        st.session_state["fecha_termino_incendio"] = info["fecha_termino"]
        st.session_state["superficie_incendio"] = info["superficie_ha"]

        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); border-radius: 12px; padding: 20px; color: white; border: 1px solid #334155; margin-bottom: 15px;">
                <span style="background: #DC2626; color: white; padding: 2px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; text-transform: uppercase;">ID: {info['id'] or '-'}</span>
                <h3 style="color: #FFFFFF; margin: 8px 0 10px 0;">{info['nombre']}</h3>
                <p style="margin: 3px 0; color: #CBD5E1; font-size: 14px;"><b>Temporada:</b> {info['temporada']}</p>
                <p style="margin: 3px 0; color: #CBD5E1; font-size: 14px;"><b>Región:</b> {info['region']}</p>
                <p style="margin: 3px 0; color: #CBD5E1; font-size: 14px;"><b>Comuna:</b> {info['comuna']}</p>
                <p style="margin: 3px 0; color: #CBD5E1; font-size: 14px;"><b>Causa:</b> {info['causa']}</p>
                <p style="margin: 3px 0; color: #CBD5E1; font-size: 14px;"><b>Superficie:</b> <span style="color: #F59E0B; font-weight: bold; font-size: 17px;">{info['superficie_ha']:,.1f} ha</span></p>
                <p style="margin: 3px 0; color: #CBD5E1; font-size: 14px;"><b>Fecha Inicio:</b> {info['fecha_inicio'] or 'No registrada'}</p>
                <p style="margin: 3px 0; color: #94A3B8; font-size: 13px;"><b>Coordenadas:</b> ({info['latitud']:.4f}, {info['longitud']:.4f})</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info("💡 Este incendio quedó **fijado automáticamente**. Al cambiar a las pestañas **'Actividad FIRMS'** o **'Perfil meteorológico'**, ya estará seleccionado y analizado.")
    else:
        st.warning("No hay incendios con los filtros seleccionados.")

# ==============================================================================
# TABLA DE DATOS EXPANDIBLE
# ==============================================================================

with st.expander("📋 Ver Tabla Completa de Incendios Filtrados"):
    columnas = ["NOM_INCEN", "TEMPORADA", "REGION", "COMUNA", "CAUSA", "superficie_ha_clean", "FECHA_INI", "lat_centroide", "lon_centroide"]
    cols_ok = [c for c in columnas if c in gdf_filtrado.columns]
    df_ver = gdf_filtrado[cols_ok].rename(
        columns={
            "NOM_INCEN": "Nombre",
            "TEMPORADA": "Temporada",
            "REGION": "Región",
            "COMUNA": "Comuna",
            "CAUSA": "Causa",
            "superficie_ha_clean": "Superficie (ha)",
            "FECHA_INI": "Fecha Inicio",
            "lat_centroide": "Latitud",
            "lon_centroide": "Longitud",
        }
    )
    st.dataframe(df_ver, use_container_width=True, height=280)
    
    csv_bytes = df_ver.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Descargar Tabla Filtrada (CSV)", csv_bytes, "incendios_filtrados.csv", "text/csv")
