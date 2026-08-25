"""
app/pages/3_Perfil_meteorologico.py
Visualización meteorológica integral de incendios:
- Consulta por incendio histórico (GeoPackage) o por coordenadas/fechas libres.
- Series temporales de superficie (T°, HR, Viento, Ráfagas, Precipitación, Rosa de Vientos).
- Diagrama Skew-T log-P de perfil vertical atmosférico.
"""

from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st

from src.incendios_data import (
    cargar_geopackage_incendios,
    extraer_info_incendio,
    filtrar_incendios,
    obtener_regiones_disponibles,
    obtener_temporadas_disponibles,
)
from src.meteorologia import (
    armar_perfil_vertical,
    calcular_estadisticas_resumen,
    consultar_meteorologia_historica,
)
from src.graficos import (
    generar_grafico_precipitacion,
    generar_grafico_temperatura_humedad,
    generar_grafico_viento,
    generar_rosa_vientos,
    generar_skewt_diagram,
)


def mostrar_grafico(fig):
    """Muestra una figura ya sea de Plotly o Matplotlib de manera transparente."""
    if fig is None:
        return
    if hasattr(fig, "to_plotly_json"):
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.pyplot(fig, use_container_width=True)


st.set_page_config(
    page_title="Perfil Meteorológico | Incendios Forestales",
    page_icon="🌤️",
    layout="wide",
)

st.title("🌤️ Condiciones Meteorológicas y Perfil Skew-T")
st.markdown(
    "Analiza el comportamiento meteorológico en superficie y en altura (base **ERA5 / Open-Meteo**) "
    "para incendios históricos de magnitud en Chile o coordenadas personalizadas."
)

# ==============================================================================
# CARGA DE DATOS GEOPACKAGE (CACHEADA)
# ==============================================================================

@st.cache_data(show_spinner="Cargando base de incendios compilada...")
def get_incendios_gdf():
    try:
        return cargar_geopackage_incendios()
    except Exception as e:
        st.error(f"Error al cargar el GeoPackage de incendios: {e}")
        return None

gdf_incendios = get_incendios_gdf()

# ==============================================================================
# BARRA LATERAL: MODO DE CONSULTA
# ==============================================================================

st.sidebar.header("⚙️ Parámetros de Consulta")
modo_consulta = st.sidebar.radio(
    "Selecciona el modo de consulta:",
    ["🔥 Por Incendio Histórico", "🌐 Coordenadas y Fechas Libres"],
    index=0,
)

lat_consulta = -38.7359
lon_consulta = -72.5904
fecha_ini_consulta = date(2023, 2, 2)
fecha_fin_consulta = date(2023, 2, 5)
nombre_evento = "Coordenadas Libres"
info_incendio_sel = None

if modo_consulta == "🔥 Por Incendio Histórico" and gdf_incendios is not None:
    st.sidebar.subheader("Filtrar Incendios")
    
    temporadas = ["Todas"] + obtener_temporadas_disponibles(gdf_incendios)
    temporada_sel = st.sidebar.selectbox("Temporada", temporadas, index=0)

    regiones = ["Todas"] + obtener_regiones_disponibles(gdf_incendios)
    region_sel = st.sidebar.selectbox("Región", regiones, index=0)

    busqueda_txt = st.sidebar.text_input("Buscar por nombre", "")

    gdf_filtrado = filtrar_incendios(
        gdf_incendios,
        temporada=temporada_sel,
        region=region_sel,
        texto_busqueda=busqueda_txt,
    )

    if gdf_filtrado.empty:
        st.sidebar.warning("No se encontraron incendios con los filtros seleccionados.")
    else:
        # Formato de etiqueta para el selectbox
        gdf_filtrado["etiqueta"] = (
            gdf_filtrado["NOM_INCEN"]
            + " ("
            + gdf_filtrado["TEMPORADA"]
            + " | "
            + gdf_filtrado["REGION"]
            + ")"
        )
        
        # Verificar si hay uno preseleccionado en session_state
        id_preseleccionado = st.session_state.get("id_incendio_seleccionado", None)
        index_default = 0
        if id_preseleccionado is not None and "ID" in gdf_filtrado.columns:
            matches = gdf_filtrado.index[gdf_filtrado["ID"] == id_preseleccionado].tolist()
            if matches:
                index_default = matches[0]

        opciones_incendios = gdf_filtrado["etiqueta"].tolist()
        idx_elegido = st.sidebar.selectbox(
            f"Selecciona un Incendio ({len(gdf_filtrado)} disponibles)",
            range(len(opciones_incendios)),
            format_func=lambda i: opciones_incendios[i],
            index=min(index_default, len(opciones_incendios) - 1),
        )

        fila_sel = gdf_filtrado.iloc[idx_elegido]
        info_incendio_sel = extraer_info_incendio(fila_sel)

        lat_consulta = info_incendio_sel["latitud"]
        lon_consulta = info_incendio_sel["longitud"]
        nombre_evento = info_incendio_sel["nombre"]

        # Rango de fechas por defecto del incendio
        if info_incendio_sel["fecha_inicio"]:
            fecha_ini_consulta = info_incendio_sel["fecha_inicio"]
            fecha_fin_consulta = info_incendio_sel["fecha_termino"] or (fecha_ini_consulta + timedelta(days=5))
        else:
            fecha_ini_consulta = date(2023, 2, 2)
            fecha_fin_consulta = date(2023, 2, 5)

        # Ajuste de fechas opcional en sidebar
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 Rango de Fechas a Consultar")
        fechas_rango = st.sidebar.date_input(
            "Fechas del evento:",
            value=[fecha_ini_consulta, fecha_fin_consulta],
            max_value=date.today(),
        )
        if isinstance(fechas_rango, (list, tuple)) and len(fechas_rango) == 2:
            fecha_ini_consulta, fecha_fin_consulta = fechas_rango[0], fechas_rango[1]
        elif isinstance(fechas_rango, (list, tuple)) and len(fechas_rango) == 1:
            fecha_ini_consulta = fecha_fin_consulta = fechas_rango[0]

else:
    st.sidebar.subheader("📍 Coordenadas Geográficas (WGS84)")
    lat_consulta = st.sidebar.number_input("Latitud", value=-38.7359, min_value=-56.0, max_value=-17.0, step=0.01, format="%.4f")
    lon_consulta = st.sidebar.number_input("Longitud", value=-72.5904, min_value=-110.0, max_value=-65.0, step=0.01, format="%.4f")

    st.sidebar.subheader("📅 Rango Temporal")
    fechas_rango = st.sidebar.date_input(
        "Rango de Fechas:",
        value=[date(2023, 2, 2), date(2023, 2, 5)],
        max_value=date.today(),
    )
    if isinstance(fechas_rango, (list, tuple)) and len(fechas_rango) == 2:
        fecha_ini_consulta, fecha_fin_consulta = fechas_rango[0], fechas_rango[1]
    elif isinstance(fechas_rango, (list, tuple)) and len(fechas_rango) == 1:
        fecha_ini_consulta = fecha_fin_consulta = fechas_rango[0]

    nombre_evento = f"Punto ({lat_consulta:.3f}, {lon_consulta:.3f})"

# ==============================================================================
# TARJETA INFORMATIVA SUPERIOR
# ==============================================================================

if info_incendio_sel:
    with st.container():
        st.markdown(
            f"""
            <div style="background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%); padding: 18px 24px; border-radius: 12px; margin-bottom: 20px; color: white; border: 1px solid #334155;">
                <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                    <div>
                        <span style="background: #DC2626; color: white; padding: 3px 10px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase;">Incendio Histórico</span>
                        <h2 style="margin: 6px 0 2px 0; color: #FFFFFF; font-size: 24px;">{info_incendio_sel['nombre']}</h2>
                        <p style="margin: 0; color: #94A3B8; font-size: 14px;">Temporada: <b>{info_incendio_sel['temporada']}</b> | Región: <b>{info_incendio_sel['region']}</b> | Comuna: <b>{info_incendio_sel['comuna']}</b></p>
                    </div>
                    <div style="text-align: right; margin-top: 8px;">
                        <span style="font-size: 13px; color: #94A3B8;">Superficie Afectada:</span>
                        <h3 style="margin: 0; color: #F59E0B; font-size: 22px;">{info_incendio_sel['superficie_ha']:,.1f} ha</h3>
                        <span style="font-size: 12px; color: #64748B;">Causa: {info_incendio_sel['causa']}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.info(f"📍 **Consulta libre:** Coordenadas `({lat_consulta:.4f}, {lon_consulta:.4f})` | Período: `{fecha_ini_consulta}` al `{fecha_fin_consulta}`")

# ==============================================================================
# CONSULTA A OPEN-METEO API
# ==============================================================================

@st.cache_data(ttl=3600, show_spinner="Consultando datos meteorológicos históricos en Open-Meteo...")
def fetch_meteo_data(lat, lon, f_ini, f_fin):
    return consultar_meteorologia_historica(lat, lon, f_ini, f_fin)

try:
    df_meteo = fetch_meteo_data(lat_consulta, lon_consulta, fecha_ini_consulta, fecha_fin_consulta)
except Exception as e:
    st.error(f"Error al consultar la API de Open-Meteo: {e}")
    st.stop()

if df_meteo.empty:
    st.warning("No se obtuvieron registros meteorológicos para las coordenadas y rango de fechas especificados.")
    st.stop()

# ==============================================================================
# RESUMEN EJECUTIVO / KPIs
# ==============================================================================

stats = calcular_estadisticas_resumen(df_meteo)

kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
with kpi1:
    st.metric("🌡️ T° Máxima", f"{stats['temp_max']:.1f} °C", help="Temperatura máxima registrada a 2m")
with kpi2:
    st.metric("💧 Humedad Mínima", f"{stats['hr_min']:.1f} %", help="Humedad relativa mínima registrada a 2m")
with kpi3:
    st.metric("💨 Viento Máximo", f"{stats['viento_max']:.1f} km/h", help="Velocidad sostenida máxima a 10m")
with kpi4:
    st.metric("🌪️ Ráfaga Máxima", f"{stats['rafaga_max']:.1f} km/h", help="Ráfaga máxima registrada a 10m")
with kpi5:
    horas_crit = stats.get("horas_30_30_30", 0)
    color_badge = "🔥" if horas_crit > 0 else "✅"
    st.metric(f"{color_badge} Horas Regla 30-30-30", f"{horas_crit} hrs", help="Horas con T > 30°C, HR < 30% y Viento > 30 km/h simultáneos")

st.markdown("---")

# ==============================================================================
# PESTAÑAS PRINCIPALES DE VISUALIZACIÓN
# ==============================================================================

tab_superficie, tab_skewt, tab_datos = st.tabs([
    "📊 Series Temporales de Superficie",
    "🌪️ Perfil Vertical Atmosférico (Skew-T)",
    "📋 Datos Horarios & Descarga",
])

# ------------------------------------------------------------------------------
# TAB 1: CONDICIONES DE SUPERFICIE
# ------------------------------------------------------------------------------
with tab_superficie:
    st.subheader("Evolución de Variables Meteorológicas en Superficie")
    
    # 1. Gráfico Temperatura y Humedad Relativa
    fig_th = generar_grafico_temperatura_humedad(df_meteo)
    mostrar_grafico(fig_th)

    # 2. Columnas para Viento y Rosa de Vientos
    col_viento, col_rosa = st.columns([3, 2])
    with col_viento:
        fig_viento = generar_grafico_viento(df_meteo)
        mostrar_grafico(fig_viento)
    with col_rosa:
        fig_rosa = generar_rosa_vientos(df_meteo)
        mostrar_grafico(fig_rosa)

    # 3. Gráfico de Precipitación
    fig_precip = generar_grafico_precipitacion(df_meteo)
    mostrar_grafico(fig_precip)

# ------------------------------------------------------------------------------
# TAB 2: PERFIL VERTICAL SKEW-T
# ------------------------------------------------------------------------------
with tab_skewt:
    st.subheader("Sondeo Atmosférico Vertical (Skew-T log-P)")
    st.markdown(
        "Permite evaluar la estabilidad atmosférica, capas de inversión térmica "
        "y el perfil vertical de vientos (desde 1000 hPa hasta 500 hPa)."
    )

    # Selectores de Día y Hora
    dias_disponibles = sorted(df_meteo["fecha"].unique())
    
    col_sel_dia, col_sel_hora = st.columns([2, 2])
    with col_sel_dia:
        dia_sel = st.select_slider(
            "Selecciona el Día:",
            options=dias_disponibles,
            format_func=lambda d: d.strftime("%A, %d de %B de %Y") if hasattr(d, "strftime") else str(d),
            value=dias_disponibles[0],
        )

    # Filtrar horas del día seleccionado
    df_dia = df_meteo[df_meteo["fecha"] == dia_sel]
    horas_disponibles = df_dia["hora"].tolist()

    with col_sel_hora:
        # Preseleccionar 12:00 o 18:00 si están disponibles
        idx_hora_default = 0
        for h_cand in ["12:00", "15:00", "18:00", "00:00"]:
            if h_cand in horas_disponibles:
                idx_hora_default = horas_disponibles.index(h_cand)
                break

        hora_sel = st.selectbox(
            "Selecciona la Hora (Local):",
            horas_disponibles,
            index=idx_hora_default,
        )

    # Extraer la fila correspondiente
    fila_hora = df_dia[df_dia["hora"] == hora_sel].iloc[0]
    df_perfil = armar_perfil_vertical(fila_hora)

    # Renderizar el gráfico Skew-T y la tabla al lado
    col_skewt_plot, col_skewt_table = st.columns([3, 2])
    
    with col_skewt_plot:
        subtitulo = f"{nombre_evento} | {dia_sel} {hora_sel} Local | Coords: ({lat_consulta:.3f}, {lon_consulta:.3f})"
        fig_skewt = generar_skewt_diagram(
            df_perfil,
            titulo=f"Perfil Vertical - {nombre_evento}",
            subtitulo=subtitulo,
        )
        st.pyplot(fig_skewt, use_container_width=True)

    with col_skewt_table:
        st.markdown(f"#### 📊 Niveles Atmosféricos ({hora_sel} Local)")
        
        # Formatear tabla de niveles
        df_mostrar = df_perfil.copy()
        df_mostrar["presion_hpa"] = df_mostrar["presion_hpa"].astype(int)
        df_mostrar = df_mostrar.rename(
            columns={
                "presion_hpa": "Nivel (hPa)",
                "temperatura_c": "T (°C)",
                "punto_rocio_c": "Td (°C)",
                "humedad_relativa": "HR (%)",
                "velocidad_viento_kmh": "Viento (km/h)",
                "direccion_viento_deg": "Dir (°)",
            }
        )
        st.dataframe(
            df_mostrar.style.format(
                {
                    "T (°C)": "{:.1f}",
                    "Td (°C)": "{:.1f}",
                    "HR (%)": "{:.1f}",
                    "Viento (km/h)": "{:.1f}",
                    "Dir (°)": "{:.0f}",
                },
                na_rep="-",
            ),
            use_container_width=True,
            hide_index=True,
            height=400,
        )
        
        st.caption("ℹ️ *Barbillas de viento: pluma larga = 10 nudos, pluma corta = 5 nudos, banderola = 50 nudos.*")

# ------------------------------------------------------------------------------
# TAB 3: DATOS HORARIOS Y EXPORTACIÓN
# ------------------------------------------------------------------------------
with tab_datos:
    st.subheader("Tabla de Registros Horarios")
    
    cols_mostrar = [
        "time",
        "temperature_2m",
        "dew_point_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "wind_gusts_10m",
        "wind_direction_10m",
        "precipitation",
        "surface_pressure",
        "alerta_30_30_30",
    ]
    cols_existentes = [c for c in cols_mostrar if c in df_meteo.columns]
    
    df_tabla = df_meteo[cols_existentes].copy()
    df_tabla = df_tabla.rename(
        columns={
            "time": "Fecha y Hora",
            "temperature_2m": "T 2m (°C)",
            "dew_point_2m": "Td 2m (°C)",
            "relative_humidity_2m": "HR 2m (%)",
            "wind_speed_10m": "Viento 10m (km/h)",
            "wind_gusts_10m": "Ráfaga 10m (km/h)",
            "wind_direction_10m": "Dir 10m (°)",
            "precipitation": "Precipitación (mm)",
            "surface_pressure": "Presión Sup (hPa)",
            "alerta_30_30_30": "Regla 30-30-30",
        }
    )

    st.dataframe(df_tabla, use_container_width=True, height=450)

    # Botón de Descarga
    csv_data = df_meteo.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Descargar Serie Horaria Completa (CSV)",
        data=csv_data,
        file_name=f"meteorologia_{nombre_evento.replace(' ', '_')}_{fecha_ini_consulta}_{fecha_fin_consulta}.csv",
        mime="text/csv",
    )