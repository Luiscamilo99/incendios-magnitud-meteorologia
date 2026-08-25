"""
app/pages/2_actividad_FIRMS.py
Análisis de focos de calor y actividad satelital NASA FIRMS (Multi-satélite: MODIS + VIIRS).
"""

import sys
import os
import importlib
from pathlib import Path
from datetime import date, timedelta

# Asegurar que la raíz del proyecto esté en sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Forzar reload de src.firms para evitar versiones cacheadas en memoria
if "src.firms" in sys.modules:
    importlib.reload(sys.modules["src.firms"])

import pandas as pd
import streamlit as st

try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

try:
    import folium
    from folium.plugins import MarkerCluster, HeatMap
    from streamlit_folium import st_folium
    import shapely.geometry
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

from src.firms import (
    descargar_todos_sensores_firms,
    detectar_periodo_peak,
    es_fecha_historica,
    filtrar_puntos_cercanos,
    obtener_dias_con_actividad,
    SENSORES_NRT,
    SENSORES_HISTORICOS,
)
from src.incendios_data import (
    cargar_geopackage_incendios,
    extraer_info_incendio,
    filtrar_incendios,
    obtener_regiones_disponibles,
    obtener_temporadas_disponibles,
)


def get_firms_key() -> str:
    """Busca la clave en variables de entorno, .streamlit/secrets.toml, secrets.toml o .env."""
    key = os.getenv("FIRMS_MAP_KEY", "")
    if key:
        return key
    
    # Buscar en rutas locales del proyecto
    for ruta in [
        ROOT_DIR / ".streamlit" / "secrets.toml",
        ROOT_DIR / "secrets.toml",
        ROOT_DIR / ".env",
        ROOT_DIR / ".env.txt",
    ]:
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
    return ""


st.set_page_config(
    page_title="Actividad FIRMS | Incendios Forestales",
    page_icon="🛰️",
    layout="wide",
)

st.title("🛰️ Monitoreo Satelital de Focos de Calor (NASA FIRMS)")
st.markdown(
    "Consulta y superpone automáticamente anomalías térmicas y potencia radiativa (**FRP**, Fire Radiative Power) "
    "de **todos los sensores satelitales disponibles** (**VIIRS Suomi-NPP**, **VIIRS NOAA-20** y **MODIS Terra/Aqua**)."
)

# ==============================================================================
# CARGA DE BASE DE INCENDIOS
# ==============================================================================

@st.cache_data(show_spinner=False)
def get_gdf():
    try:
        return cargar_geopackage_incendios()
    except Exception:
        return None

gdf = get_gdf()

# ==============================================================================
# BARRA LATERAL: SELECCIÓN Y CONFIGURACIÓN
# ==============================================================================

st.sidebar.header("⚙️ Configuración y Filtros")

lat_sel = -38.7359
lon_sel = -72.5904
fecha_ini = date(2023, 2, 2)
nombre_inc = "Evento Seleccionado"
id_sel = "0"
geometria_sel = None
sup_ha_sel = 0.0

if gdf is not None and not gdf.empty:
    st.sidebar.subheader("Seleccionar Incendio")
    
    # Sincronizar filtros si hay un incendio activo en session_state
    temp_def_idx = 0
    reg_def_idx = 0
    temp_glob = st.session_state.get("temporada_incendio_seleccionado")
    reg_glob = st.session_state.get("region_incendio_seleccionado")
    
    temporadas = ["Todas"] + obtener_temporadas_disponibles(gdf)
    if temp_glob and temp_glob in temporadas:
        temp_def_idx = temporadas.index(temp_glob)
    temp_sel = st.sidebar.selectbox("Temporada", temporadas, index=temp_def_idx)

    regiones = ["Todas"] + obtener_regiones_disponibles(gdf)
    if reg_glob and reg_glob in regiones:
        reg_def_idx = regiones.index(reg_glob)
    reg_sel = st.sidebar.selectbox("Región", regiones, index=reg_def_idx)

    gdf_f = filtrar_incendios(gdf, temporada=temp_sel, region=reg_sel)
    
    if not gdf_f.empty:
        opciones = (gdf_f["NOM_INCEN"] + " (" + gdf_f["TEMPORADA"] + ")").tolist()
        
        # Sincronizar índice por ID del incendio si existe
        id_actual = st.session_state.get("id_incendio_seleccionado")
        idx_def = 0
        if id_actual and "ID" in gdf_f.columns:
            ids_lista = gdf_f["ID"].tolist()
            if id_actual in ids_lista:
                idx_def = ids_lista.index(id_actual)

        idx = st.sidebar.selectbox(
            "Incendio",
            range(len(opciones)),
            index=min(idx_def, len(opciones) - 1),
            format_func=lambda i: opciones[i],
        )
        fila_sel = gdf_f.iloc[idx]
        info = extraer_info_incendio(fila_sel)
        id_sel = info["id"]
        lat_sel = info["latitud"]
        lon_sel = info["longitud"]
        fecha_ini = info["fecha_inicio"] or date(2023, 2, 2)
        nombre_inc = info["nombre"]
        geometria_sel = fila_sel.geometry if hasattr(fila_sel, "geometry") else None
        sup_ha_sel = info["superficie_ha"]

        # Mantener sincronizado session_state
        st.session_state["id_incendio_seleccionado"] = info["id"]
        st.session_state["nombre_incendio_seleccionado"] = info["nombre"]
        st.session_state["temporada_incendio_seleccionado"] = info["temporada"]
        st.session_state["region_incendio_seleccionado"] = info["region"]
        st.session_state["lat_incendio"] = info["latitud"]
        st.session_state["lon_incendio"] = info["longitud"]
        st.session_state["fecha_inicio_incendio"] = info["fecha_inicio"]
        st.session_state["fecha_termino_incendio"] = info["fecha_termino"]
        st.session_state["superficie_incendio"] = info["superficie_ha"]

st.sidebar.markdown("---")
st.sidebar.subheader("📡 Parámetros de Búsqueda")

st.sidebar.info("🛰️ **Modo Multi-Satélite Activado**\n\nConsulta en simultáneo todos los sensores (**VIIRS S-NPP**, **VIIRS NOAA-20** y **MODIS**).")

dias_consulta = st.sidebar.slider("Ventana de días (máx 5 por consulta)", min_value=1, max_value=5, value=5)
radio_km = st.sidebar.slider("Radio de búsqueda (km)", min_value=1.0, max_value=30.0, value=10.0, step=1.0)

# Entrada de API Key de FIRMS en la barra lateral
firms_map_key = get_firms_key()

api_key_input = st.sidebar.text_input(
    "NASA FIRMS MAP_KEY",
    value=firms_map_key,
    type="password",
    help="Clave cargada automáticamente desde .streamlit/secrets.toml",
)
if api_key_input:
    os.environ["FIRMS_MAP_KEY"] = api_key_input

# ==============================================================================
# TARJETA DEL EVENTO + AVISO HISTÓRICO
# ==============================================================================

st.markdown(
    f"""
    <div style="background: #1E293B; border-radius: 12px; padding: 18px 24px; color: white; border: 1px solid #334155; margin-bottom: 16px;">
        <span style="background: #F59E0B; color: #0F172A; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; text-transform: uppercase;">Incendio Activo / Sincronizado</span>
        <h3 style="margin: 6px 0 4px 0; color: #FFFFFF;">{nombre_inc}</h3>
        <p style="margin: 0; color: #94A3B8; font-size: 14px;">Centroide: <b>({lat_sel:.4f}, {lon_sel:.4f})</b> | Fecha estimada: <b>{fecha_ini}</b> | Superficie: <b>{sup_ha_sel:,.1f} ha</b></p>
    </div>
    """,
    unsafe_allow_html=True,
)

fecha_es_historica = es_fecha_historica(fecha_ini)
if fecha_es_historica:
    st.info(
        f"📅 **Incendio histórico ({fecha_ini})** — Se consultan automáticamente los sensores de archivo histórico "
        f"(**VIIRS_SNPP_SP**, **VIIRS_NOAA20_SP** y **MODIS_SP**), cubriendo el registro histórico completo.",
        icon="🗄️",
    )

# ==============================================================================
# CONSULTA A LA API DE FIRMS (TODOS LOS SATÉLITES)
# ==============================================================================

bbox_inc = (lon_sel - 0.2, lat_sel - 0.2, lon_sel + 0.2, lat_sel + 0.2)
clave_a_usar = (api_key_input or firms_map_key or "").strip()

cache_key = f"firms_multi_{id_sel}_{nombre_inc}_{fecha_ini}_{dias_consulta}_{radio_km}"

col_btn, col_help = st.columns([1.5, 3.5])
with col_btn:
    btn_consultar = st.button("🛰️ Consultar NASA FIRMS (Todos los Satélites)", type="primary", use_container_width=True)

# Auto-ejecución si hay clave y no se ha consultado este incendio aún
if (btn_consultar or cache_key not in st.session_state) and clave_a_usar:
    with st.spinner("Consultando constelación satelital (VIIRS S-NPP + NOAA-20 + MODIS)..."):
        os.environ["FIRMS_MAP_KEY"] = clave_a_usar
        try:
            df_descargado = descargar_todos_sensores_firms(
                bbox_inc,
                fecha_ini,
                dias=dias_consulta,
                map_key=clave_a_usar,
            )

            if not df_descargado.empty:
                df_puntos = filtrar_puntos_cercanos(
                    df_descargado,
                    lat_sel,
                    lon_sel,
                    fecha_ini,
                    radio_km=radio_km,
                    ventana_dias=dias_consulta,
                )
                st.session_state[cache_key] = df_puntos
                st.session_state["df_puntos_incendio"] = df_puntos
                st.session_state["ultimo_incendio_consultado"] = nombre_inc
                if not df_puntos.empty:
                    st.success(f"✅ Se detectaron {len(df_puntos)} anomalías térmicas totales combinando todos los satélites (radio: {radio_km} km).")
                else:
                    st.warning(f"No se encontraron focos en el radio de {radio_km} km (se descargaron {len(df_descargado)} detecciones en el cuadrante general).")
            else:
                st.session_state[cache_key] = pd.DataFrame()
                st.session_state["df_puntos_incendio"] = pd.DataFrame()
                st.warning("No se detectaron anomalías térmicas en la ventana y área consultadas.")
        except Exception as e:
            st.error(f"Error en la consulta FIRMS: {e}")
elif not clave_a_usar:
    st.warning("⚠️ Ingresa tu **NASA FIRMS MAP_KEY** en la barra lateral o configúrala en `.streamlit/secrets.toml` para consultar.")

df_puntos = st.session_state.get(cache_key, st.session_state.get("df_puntos_incendio", pd.DataFrame()))

# ==============================================================================
# VISOR CARTOGRÁFICO: POLÍGONO DEL INCENDIO + PUNTOS FIRMS MULTI-SATÉLITE
# ==============================================================================

st.subheader("🗺️ Mapa de Superposición: Perímetro del Incendio y Focos Térmicos Multi-Satélite")

if FOLIUM_AVAILABLE:
    m = folium.Map(
        location=[lat_sel, lon_sel],
        zoom_start=12,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery",
        name="Satélite (Esri)",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="CartoDB dark_matter",
        name="CartoDB Oscuro",
        overlay=False,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="CartoDB positron",
        name="CartoDB Claro",
        overlay=False,
        control=True,
    ).add_to(m)

    # 1. Dibujar Polígono Oficial del Incendio
    if geometria_sel is not None:
        try:
            import shapely.geometry
            geojson_geom = shapely.geometry.mapping(geometria_sel)
            
            popup_poligono_html = f"""
            <div style="font-family: sans-serif; font-size: 13px; width: 220px;">
                <b style="color: #DC2626; font-size: 14px;">🔥 {nombre_inc}</b><br>
                <b>Superficie:</b> {sup_ha_sel:,.1f} ha<br>
                <b>Fecha inicio:</b> {fecha_ini}<br>
                <b>Centroide:</b> {lat_sel:.4f}, {lon_sel:.4f}
            </div>
            """

            folium.GeoJson(
                geojson_geom,
                name="Perímetro Oficial (CONAF)",
                style_function=lambda x: {
                    "fillColor": "#DC2626",
                    "color": "#991B1B",
                    "weight": 2.5,
                    "fillOpacity": 0.35,
                },
                popup=folium.Popup(popup_poligono_html, max_width=250),
                tooltip=f"Perímetro: {nombre_inc} ({sup_ha_sel:,.0f} ha)",
            ).add_to(m)
        except Exception as e:
            st.warning(f"No se pudo graficar el polígono: {e}")

    # 2. Círculo que delimita el radio de búsqueda
    folium.Circle(
        location=[lat_sel, lon_sel],
        radius=radio_km * 1000,
        color="#3B82F6",
        weight=1.5,
        dash_array="5, 5",
        fill=True,
        fill_color="#3B82F6",
        fill_opacity=0.06,
        name=f"Radio de Búsqueda ({radio_km} km)",
        tooltip=f"Área de búsqueda ({radio_km} km)",
    ).add_to(m)

    # 3. Marcador del Centroide del Incendio
    folium.Marker(
        location=[lat_sel, lon_sel],
        popup=folium.Popup(f"<b>Centroide:</b> {nombre_inc}<br>Lat: {lat_sel:.4f}, Lon: {lon_sel:.4f}", max_width=200),
        tooltip=f"Centroide {nombre_inc}",
        icon=folium.Icon(color="red", icon="fire", prefix="fa"),
    ).add_to(m)

    # 4. Superponer Focos FIRMS de todos los satélites
    if df_puntos is not None and not df_puntos.empty:
        fg_firms = folium.FeatureGroup(name=f"Focos de Calor FIRMS ({len(df_puntos)})")

        for _, pt in df_puntos.iterrows():
            p_lat = pt["latitude"]
            p_lon = pt["longitude"]
            frp_val = float(pt.get("frp", 0.0)) if pd.notna(pt.get("frp")) else 0.0
            conf_val = pt.get("confidence", "N/A")
            hora_val = str(pt.get("acq_datetime", pt.get("acq_date", "")))
            sat_nombre = pt.get("satelite_nombre", pt.get("satellite", pt.get("sensor_usado", "Satélite")))
            sensor_code = pt.get("sensor_codigo", pt.get("sensor_usado", "-"))
            bright_val = pt.get("bright_ti4", pt.get("brightness", "-"))
            daynight_val = "Día" if str(pt.get("daynight", "")).upper() == "D" else "Noche" if str(pt.get("daynight", "")).upper() == "N" else "-"

            # Estilo por intensidad de FRP
            if frp_val >= 50:
                color_pt = "#991B1B"
                fill_pt = "#EF4444"
                r_size = 9
            elif frp_val >= 15:
                color_pt = "#C2410C"
                fill_pt = "#F97316"
                r_size = 7
            else:
                color_pt = "#B45309"
                fill_pt = "#FBBF24"
                r_size = 5

            popup_content = f"""
            <div style="font-family: sans-serif; font-size: 12px; width: 210px;">
                <b style="color: #DC2626; font-size: 13px;">🔥 Foco Térmico Satelital</b><br>
                <b>Satélite:</b> <span style="color:#2563EB; font-weight:bold;">{sat_nombre}</span> ({sensor_code})<br>
                <b>Fecha/Hora:</b> {hora_val}<br>
                <b>FRP:</b> <span style="color:#EF4444; font-weight:bold;">{frp_val:.1f} MW</span><br>
                <b>Confianza:</b> {conf_val}<br>
                <b>Brillo:</b> {bright_val} K<br>
                <b>Paso:</b> {daynight_val}
            </div>
            """

            folium.CircleMarker(
                location=[p_lat, p_lon],
                radius=r_size,
                color=color_pt,
                weight=1.5,
                fill=True,
                fill_color=fill_pt,
                fill_opacity=0.85,
                popup=folium.Popup(popup_content, max_width=250),
                tooltip=f"{sat_nombre} | FRP: {frp_val:.1f} MW | {hora_val}",
            ).add_to(fg_firms)

        fg_firms.add_to(m)

    folium.LayerControl(position="topright", collapsed=False).add_to(m)
    st_folium(m, width="100%", height=530, returned_objects=[])

    # Leyenda explicativa bajo el mapa
    st.markdown(
        """
        <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 13px; color: #94A3B8; background: #0F172A; padding: 10px 16px; border-radius: 8px; border: 1px solid #334155; margin-top: 8px;">
            <span><b style="color:#DC2626;">■</b> Polígono Oficial CONAF</span>
            <span><b style="color:#3B82F6;">◌</b> Radio de Búsqueda</span>
            <span><b style="color:#FBBF24;">●</b> FRP &lt; 15 MW</span>
            <span><b style="color:#F97316;">●</b> FRP 15 - 50 MW</span>
            <span><b style="color:#EF4444;">●</b> FRP &gt; 50 MW (Alta intensidad)</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

elif PLOTLY_AVAILABLE and df_puntos is not None and not df_puntos.empty:
    fig_map = px.scatter_mapbox(
        df_puntos,
        lat="latitude",
        lon="longitude",
        size="frp" if "frp" in df_puntos.columns else None,
        color="satelite_nombre" if "satelite_nombre" in df_puntos.columns else "frp",
        hover_name="acq_datetime",
        zoom=11,
        center={"lat": lat_sel, "lon": lon_sel},
        mapbox_style="carto-positron",
        height=520,
    )
    st.plotly_chart(fig_map, use_container_width=True)

# ==============================================================================
# MÉTRICAS Y ANÁLISIS MULTI-SATÉLITE
# ==============================================================================

if df_puntos is not None and not df_puntos.empty:
    st.markdown("---")
    st.subheader("📊 Análisis y Desglose por Constelación Satelital")
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("🔥 Total Focos (Todos los Sensores)", len(df_puntos))
    with k2:
        frp_max = df_puntos["frp"].max() if "frp" in df_puntos.columns else 0.0
        st.metric("⚡ FRP Máximo", f"{frp_max:.1f} MW")
    with k3:
        frp_sum = df_puntos["frp"].sum() if "frp" in df_puntos.columns else 0.0
        st.metric("💥 FRP Acumulado", f"{frp_sum:,.0f} MW")
    with k4:
        dias_act = obtener_dias_con_actividad(df_puntos)
        st.metric("📅 Días con Actividad", len(dias_act))

    # Métricas de desglose por satélite
    if "satelite_nombre" in df_puntos.columns:
        conteo_sat = df_puntos["satelite_nombre"].value_counts()
        cols_sat = st.columns(len(conteo_sat))
        for col, (sat, cnt) in zip(cols_sat, conteo_sat.items()):
            with col:
                st.metric(f"🛰️ {sat}", f"{cnt} focos")

    col_grafico, col_tabla = st.columns([3, 2])

    with col_grafico:
        if PLOTLY_AVAILABLE and "acq_datetime" in df_puntos.columns:
            fig_frp = px.scatter(
                df_puntos,
                x="acq_datetime",
                y="frp" if "frp" in df_puntos.columns else "confidence",
                size="frp" if "frp" in df_puntos.columns else None,
                color="satelite_nombre" if "satelite_nombre" in df_puntos.columns else "confidence",
                title="<b>Evolución Temporal de FRP por Satélite</b>",
                labels={"acq_datetime": "Fecha y Hora Satelital", "frp": "FRP (MW)", "satelite_nombre": "Satélite"},
                template="plotly_white",
            )
            st.plotly_chart(fig_frp, use_container_width=True)

    with col_tabla:
        st.subheader("📋 Tabla Consolidada de Focos")
        
        columnas_mostrar = [
            c for c in ["satelite_nombre", "acq_datetime", "frp", "confidence", "daynight", "latitude", "longitude", "bright_ti4", "brightness"]
            if c in df_puntos.columns
        ]
        st.dataframe(df_puntos[columnas_mostrar] if columnas_mostrar else df_puntos, use_container_width=True, height=350)
        
        csv_puntos = df_puntos.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Descargar Focos FIRMS Consolidados (CSV)",
            data=csv_puntos,
            file_name=f"firms_todos_satelites_{nombre_inc.replace(' ', '_')}_{fecha_ini}.csv",
            mime="text/csv",
            use_container_width=True,
        )
else:
    st.markdown("---")
    st.info(
        "💡 **Instrucciones:**\n"
        "1. Selecciona un incendio en cualquier pestaña; se sincronizará automáticamente.\n"
        "2. Haz clic en **`🛰️ Consultar NASA FIRMS`** (o se consultará automáticamente al entrar) para obtener las detecciones de **todos los satélites combinados**."
    )
