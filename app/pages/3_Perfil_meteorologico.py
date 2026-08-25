"""
app/pages/3_Perfil_meteorologico.py
Visualización meteorológica integral de incendios:
- Consulta por incendio histórico (GeoPackage) o por coordenadas/fechas libres.
- Series temporales de superficie (T°, HR, Viento, Ráfagas, Precipitación, Rosa de Vientos).
- Diagrama Skew-T log-P de perfil vertical atmosférico.
"""

import sys
from pathlib import Path
from datetime import date, datetime, timedelta

# Asegurar que la raíz del proyecto esté en sys.path
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import numpy as np
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
    generar_skewt_plotly,
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
    
    # Sincronizar filtros si hay un incendio global en session_state
    temp_def_idx = 0
    reg_def_idx = 0
    temp_glob = st.session_state.get("temporada_incendio_seleccionado")
    reg_glob = st.session_state.get("region_incendio_seleccionado")
    
    temporadas = ["Todas"] + obtener_temporadas_disponibles(gdf_incendios)
    if temp_glob and temp_glob in temporadas:
        temp_def_idx = temporadas.index(temp_glob)
    temporada_sel = st.sidebar.selectbox("Temporada", temporadas, index=temp_def_idx)

    regiones = ["Todas"] + obtener_regiones_disponibles(gdf_incendios)
    if reg_glob and reg_glob in regiones:
        reg_def_idx = regiones.index(reg_glob)
    region_sel = st.sidebar.selectbox("Región", regiones, index=reg_def_idx)

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
        
        # Sincronizar índice posicional si hay un incendio activo en session_state
        id_preseleccionado = st.session_state.get("id_incendio_seleccionado", None)
        index_default = 0
        if id_preseleccionado is not None and "ID" in gdf_filtrado.columns:
            ids_list = gdf_filtrado["ID"].tolist()
            if id_preseleccionado in ids_list:
                index_default = ids_list.index(id_preseleccionado)

        opciones_incendios = gdf_filtrado["etiqueta"].tolist()
        idx_elegido = st.sidebar.selectbox(
            f"Selecciona un Incendio ({len(opciones_incendios)} disponibles)",
            range(len(opciones_incendios)),
            format_func=lambda i: opciones_incendios[i],
            index=min(index_default, len(opciones_incendios) - 1),
        )

        fila_sel = gdf_filtrado.iloc[idx_elegido]
        info_incendio_sel = extraer_info_incendio(fila_sel)

        # Actualizar session_state
        st.session_state["id_incendio_seleccionado"] = info_incendio_sel["id"]
        st.session_state["nombre_incendio_seleccionado"] = info_incendio_sel["nombre"]
        st.session_state["temporada_incendio_seleccionado"] = info_incendio_sel["temporada"]
        st.session_state["region_incendio_seleccionado"] = info_incendio_sel["region"]
        st.session_state["lat_incendio"] = info_incendio_sel["latitud"]
        st.session_state["lon_incendio"] = info_incendio_sel["longitud"]
        st.session_state["fecha_inicio_incendio"] = info_incendio_sel["fecha_inicio"]
        st.session_state["fecha_termino_incendio"] = info_incendio_sel["fecha_termino"]
        st.session_state["superficie_incendio"] = info_incendio_sel["superficie_ha"]

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
# TAB 2: PERFIL VERTICAL SKEW-T (ESTILO WINDY SOUNDING)
# ------------------------------------------------------------------------------
with tab_skewt:
    st.subheader("🌪️ Sondeo Atmosférico Vertical (Skew-T log-P estilo Windy)")
    st.markdown(
        "Evalúa la **estabilidad atmosférica**, **capas de inversión térmica**, **sequedad en altura** "
        "y el perfil vertical de vientos (desde 1000 hPa hasta 200 hPa) asociados al comportamiento del incendio."
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

    # Métricas clave del sondeo para incendios forestales
    t_850_val = fila_hora.get("temperature_850hPa", np.nan)
    t_700_val = fila_hora.get("temperature_700hPa", np.nan)
    td_850_val = fila_hora.get("dew_point_850hPa", np.nan)
    ws_850_val = fila_hora.get("wind_speed_850hPa", np.nan)
    ws_10m_val = fila_hora.get("wind_speed_10m", np.nan)

    from src.meteorologia import calcular_indice_haines
    info_haines = calcular_indice_haines(t_850_val, t_700_val, td_850_val)

    # Detectar inversiones térmicas
    inv_detectadas = []
    df_t_check = df_perfil.dropna(subset=["temperatura_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
    if len(df_t_check) >= 2:
        for i in range(len(df_t_check) - 1):
            p_inf = df_t_check.iloc[i]["presion_hpa"]
            p_sup = df_t_check.iloc[i + 1]["presion_hpa"]
            t_inf = df_t_check.iloc[i]["temperatura_c"]
            t_sup = df_t_check.iloc[i + 1]["temperatura_c"]
            if t_sup > t_inf:
                inv_detectadas.append((int(p_inf), int(p_sup), t_sup - t_inf))

    # Franja de KPIs del sondeo vertical
    k_v1, k_v2, k_v3, k_v4 = st.columns(4)
    with k_v1:
        val_h = info_haines.get("haines", "N/A")
        cat_h = info_haines.get("categoria", "N/A")
        st.metric("🔥 Índice de Haines", f"{val_h}", help=f"Potencial de crecimiento convectivo/eruptivo: {cat_h}")
    with k_v2:
        if inv_detectadas:
            p_base, p_tope, delta_t = inv_detectadas[0]
            st.metric("⚠️ Inversión Térmica", f"+{delta_t:.1f} °C", help=f"Capa de atrapamiento entre {p_base} hPa y {p_tope} hPa")
        else:
            st.metric("🌤️ Inversión Térmica", "No detectada", help="Atmósfera libre de capas de inversión en niveles estándar")
    with k_v3:
        if pd.notna(ws_850_val) and pd.notna(ws_10m_val):
            cizalladura_baja = abs(ws_850_val - ws_10m_val)
            st.metric("💨 Cizalladura 0-1.5 km", f"{cizalladura_baja:.1f} km/h", help="Diferencia de velocidad de viento entre superficie y 850 hPa (~1500m)")
        else:
            st.metric("💨 Cizalladura 0-1.5 km", "-", help="Dato no disponible")
    with k_v4:
        if pd.notna(t_850_val) and pd.notna(td_850_val):
            depresion_850 = t_850_val - td_850_val
            st.metric("🌵 Sequedad a 850 hPa (T - Td)", f"{depresion_850:.1f} °C", help="Depresión del punto de rocío a ~1500m. >12°C indica aire muy seco en altura")
        else:
            st.metric("🌵 Sequedad a 850 hPa", "-")

    st.markdown("---")

    # Renderizar el gráfico Skew-T interactivo (Plotly) a pantalla completa
    subtitulo = f"{nombre_evento} | {dia_sel} {hora_sel} Local | Coords: ({lat_consulta:.3f}, {lon_consulta:.3f})"
    fig_skewt_plotly = generar_skewt_plotly(
        df_perfil,
        titulo=f"Perfil Vertical Atmosférico - {nombre_evento}",
        subtitulo=subtitulo,
    )
    if fig_skewt_plotly is not None:
        st.plotly_chart(fig_skewt_plotly, use_container_width=True)
    else:
        # Fallback Matplotlib si Plotly no disponible
        fig_skewt = generar_skewt_diagram(
            df_perfil,
            titulo=f"Perfil Vertical Atmosférico - {nombre_evento}",
            subtitulo=subtitulo,
        )
        st.pyplot(fig_skewt, use_container_width=True)

    st.markdown("---")

    # Tabla de niveles y resumen bajo el gráfico interactivo
    col_tabla, col_resumen = st.columns([3, 2])
    with col_tabla:
        st.markdown(f"#### 📊 Niveles Atmosféricos ({hora_sel} Local)")
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
            height=430,
        )
        st.caption("ℹ️ *Hover sobre los puntos de las curvas para ver T, Td, HR y viento en detalle. Doble clic para restablecer el zoom.*")

    with col_resumen:
        st.markdown("#### 🔎 Resumen de Diagnóstico")
        val_h = info_haines.get("haines", "N/A")
        cat_h = info_haines.get("categoria", "N/A")
        dt_h = info_haines.get("dt_850_700", np.nan)
        dpd_h = info_haines.get("dpd_850", np.nan)
        st.markdown(
            f"""
            | Parámetro | Valor |
            |:---|:---|
            | **Índice de Haines** | **{val_h}** — {cat_h} |
            | Inestabilidad T850-T700 | {f"{dt_h:.1f} °C" if pd.notna(dt_h) else "-"} |
            | Sequedad T850-Td850 | {f"{dpd_h:.1f} °C" if pd.notna(dpd_h) else "-"} |
            | Inversiones Térmicas | {len(inv_detectadas)} detectada(s) |
            """
        )
        if inv_detectadas:
            for p_b, p_t, dt_inv in inv_detectadas:
                st.warning(f"⚠️ Inversión entre {p_b} hPa y {p_t} hPa (+{dt_inv:.1f}°C)", icon=None)


    # ==============================================================================
    # GUÍA DE CONCEPTOS CLAVE DE METEOROLOGÍA VERTICAL PARA INCENDIOS FORESTALES
    # ==============================================================================
    st.markdown("---")
    st.subheader("📚 Conceptos Clave del Perfil Vertical en Incendios Forestales")
    st.markdown("Comprender la atmósfera en altura es fundamental para anticipar el **comportamiento extremo**, **fuegos eruptivos** y **columnas convectivas**.")

    exp1, exp2, exp3, exp4, exp5 = st.columns(1)[0], st.columns(1)[0], st.columns(1)[0], st.columns(1)[0], st.columns(1)[0]

    with st.expander("🌋 1. Estabilidad Atmosférica y Convección Violenta (Pirocúmulos / Pyro-Cb)", expanded=True):
        st.markdown(
            r"""
            - **¿Qué es?** La estabilidad atmosférica mide la resistencia del aire al movimiento vertical.
            - **En el gráfico Skew-T:** Si la curva de **Temperatura (roja)** desciende rápidamente con la altura (pendiente pronunciada hacia la izquierda, superando el gradiente adiabático seco de $9.8^\circ\text{C}/\text{km}$), la atmósfera es **altamente inestable**.
            - **Impacto en Incendios:** 
              - El calor liberado por el fuego asciende libremente y sin resistencia hasta la alta troposfera (10 - 15 km de altura).
              - Se forman **Pirocúmulos (PyroCu)** y **Pirocumulonimbus (PyroCb)**, capaces de generar sus propios vientos huracanados erráticos, tormentas de fuego y rayos pirogénicos que inician nuevos focos a kilómetros de distancia.
            """
        )

    with st.expander("🛡️ 2. Inversión Térmica y el 'Efecto Tapa' / Ruptura Vespertina (*Blow-up*)", expanded=True):
        st.markdown(
            r"""
            - **¿Qué es?** Ocurre cuando la temperatura **aumenta con la altura** en lugar de disminuir. Aparece marcada en el gráfico con una banda ámbar **⚠️ Inversión Térmica**.
            - **Efecto durante la noche y mañana:** La inversión actúa como un "techo" o tapa hermética que atrapa el humo, enfría el suelo y mantiene el fuego en calma relativa por falta de tiro y oxígeno.
            - **Ruptura de la inversión (*Inversion Break* / *Blow-up*):**
              - Durante la tarde (12:00 - 16:00), el calentamiento solar calienta la superficie hasta igualar la temperatura de la inversión.
              - La "tapa" se destruye súbitamente. El humo acumulado se disipa de golpe, el aire fresco y seco penetra a la superficie y el fuego experimenta un **estallido violento (*blow-up*)**, multiplicando su velocidad de propagación en minutos.
            """
        )

    with st.expander("📊 3. Índice de Haines (Potencial de Incendios Eruptivos / Convectivos)", expanded=True):
        st.markdown(
            r"""
            El **Índice de Haines** (o *Lower Atmosphere Severity Index*) es el estándar internacional para evaluar si la atmósfera favorecerá que un incendio desarrolle una columna convectiva descontrolada:
            
            $$\text{Haines} = \text{Componente de Estabilidad } (A) + \text{Componente de Sequedad } (B)$$
            
            - **Componente A (Estabilidad $T_{850} - T_{700}$):** Evalúa la diferencia térmica entre 1500m y 3000m. A mayor diferencia, mayor inestabilidad vertical (1 a 3 pts).
            - **Componente B (Humedad $T_{850} - Td_{850}$):** Mide la sequedad a 1500m mediante la depresión del punto de rocío. A mayor sequedad, mayor facilidad para el tiro convectivo (1 a 3 pts).
            
            | Valor Haines | Nivel de Riesgo | Comportamiento del Incendio |
            | :--- | :--- | :--- |
            | **2 - 3** | **Muy Bajo** | Fuego controlado por combustible y topografía, columna débil. |
            | **4** | **Bajo / Moderado** | Comportamiento normal a moderado. |
            | **5** | **Alto** | Alto potencial de columna convectiva activa y aceleración súbita. |
            | **6** | **Extremo / Muy Alto** | **Peligro crítico.** Probabilidad extrema de fuego eruptivo, pirocúmulos y focos secundarios múltiples. |
            """
        )

    with st.expander("🌪️ 4. Chorros de Bajo Nivel (Low-Level Jet) y Cizalladura Vertical (Wind Shear)"):
        st.markdown(
            """
            - **En el gráfico Skew-T:** Observa las **barbillas de viento** en el margen derecho entre los niveles de 925 hPa (~750m) y 700 hPa (~3000m).
            - **Chorro de Bajo Nivel (*LLJ*):** Cuando se observan vientos intensos (> 30-40 nudos / 60-80 km/h) a baja altura desacoplados de la superficie.
            - **Riesgo Operativo:** La turbulencia convectiva generada por el incendio puede romper el desacople e impulsar esos vientos violentos hacia el suelo, provocando ráfagas destructivas impredecibles en el frente de avance.
            """
        )

    with st.expander("🌵 5. Sequedad en Altura y Subsidencia Atmosférica"):
        st.markdown(
            """
            - **En el gráfico Skew-T:** Se observa en la **separación horizontal** entre la curva roja ($T$) y la curva cian ($T_d$), sombreada en color naranja/ámbar.
            - **Subsidencia anticiclónica:** Cuando masas de aire descienden desde la alta atmósfera, se comprimen y calientan adiabáticamente, colapsando su humedad relativa a valores inferiores al **5% - 10%**.
            - **Consecuencia:** Cuando este aire seco entra en contacto con las cumbres o desciende por laderas (vientos tipo Puelche / Raco en Chile), seca la vegetación viva y muerta de forma fulminante, dejando el bosque en condición de ignición inmediata.
            """
        )

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