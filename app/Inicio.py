"""
app/Inicio.py
Página principal de la plataforma de análisis geoespacial y meteorológico
para incendios de magnitud en Chile.
"""

<<<<<<< HEAD
import sys
from pathlib import Path
from datetime import date

# Asegurar que la raíz del proyecto esté en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

=======
from datetime import date
>>>>>>> incendios-magnitud-meteorologia/master
import streamlit as st

from src.incendios_data import (
    cargar_geopackage_incendios,
    obtener_regiones_disponibles,
    obtener_temporadas_disponibles,
)

st.set_page_config(
    page_title="Incendios de Magnitud & Meteorología | Chile",
    page_icon="🔥",
    layout="wide",
)

# ==============================================================================
# CABECERA & HERO
# ==============================================================================

st.markdown(
    """
    <div style="background: linear-gradient(135deg, #0F172A 0%, #1E293B 50%, #334155 100%); padding: 36px 32px; border-radius: 16px; margin-bottom: 28px; color: white; border: 1px solid #475569;">
        <div style="max-width: 900px;">
            <span style="background: #EF4444; color: white; padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px;">Plataforma Geoespacial & Meteorológica</span>
            <h1 style="margin: 12px 0 10px 0; font-size: 36px; font-weight: 800; color: #FFFFFF; line-height: 1.2;">
                Incendios de Magnitud & Análisis Meteorológico
            </h1>
            <p style="font-size: 17px; color: #CBD5E1; margin: 0 0 16px 0; line-height: 1.5;">
                Plataforma interactiva para el estudio ambiental, espacial y vertical de las condiciones meteorológicas asociadas a los grandes incendios forestales en Chile (2013-2025).
            </p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==============================================================================
# CARGA DE RESUMEN DEL DATASET
# ==============================================================================

@st.cache_data(show_spinner=False)
def load_dataset_summary():
    try:
        gdf = cargar_geopackage_incendios()
        total_incendios = len(gdf)
        sup_total = gdf["superficie_ha_clean"].sum()
        temporadas = obtener_temporadas_disponibles(gdf)
        regiones = obtener_regiones_disponibles(gdf)
        return {
            "total_incendios": total_incendios,
            "sup_total": sup_total,
            "temporadas_count": len(temporadas),
            "temporada_min": temporadas[-1] if temporadas else "-",
            "temporada_max": temporadas[0] if temporadas else "-",
            "regiones_count": len(regiones),
        }
    except Exception:
        return None

summary = load_dataset_summary()

if summary:
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("🔥 Incendios de Magnitud", f"{summary['total_incendios']:,}", help="Total de polígonos compilados")
    with col2:
        st.metric("🌲 Superficie Total Afectada", f"{summary['sup_total']:,.0f} ha", help="Suma de hectáreas quemadas")
    with col3:
        st.metric("📅 Rango de Temporadas", f"{summary['temporada_min']} a {summary['temporada_max']}", help="Período histórico cubierto")
    with col4:
        st.metric("🗺️ Cobertura Regional", f"{summary['regiones_count']} Regiones", help="Regiones con incendios de magnitud")

st.markdown("---")

# ==============================================================================
# MÓDULOS DE LA PLATAFORMA
# ==============================================================================

st.subheader("🧭 Módulos Disponibles")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown(
        """
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; height: 100%;">
            <h3 style="color: #0F172A; margin-top: 0;">🗺️ 1. Mapa de Incendios</h3>
            <p style="color: #64748B; font-size: 14px; line-height: 1.5;">
                Explora la distribución espacial de los polígonos y puntos de inicio de incendios por temporada y región sobre capas cartográficas interactivas.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        """
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 20px; height: 100%;">
            <h3 style="color: #0F172A; margin-top: 0;">🛰️ 2. Actividad FIRMS</h3>
            <p style="color: #64748B; font-size: 14px; line-height: 1.5;">
                Monitoreo de anomalías térmicas y puntos de calor de sensores satelitales (VIIRS / MODIS) para identificar picos de propagación y ventanas de actividad.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        """
        <div style="background: #F0FDF4; border: 1px solid #BBF7D0; border-radius: 12px; padding: 20px; height: 100%;">
            <h3 style="color: #166534; margin-top: 0;">🌤️ 3. Perfil Meteorológico</h3>
            <p style="color: #15803D; font-size: 14px; line-height: 1.5;">
                <b>¡Módulo Activo!</b> Consulta series horarias de T°, HR, viento, ráfagas, precipitación y genera sondeos termodinámicos verticales <b>Skew-T log-P</b> vía Open-Meteo.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Call to action
st.info("👉 Para comenzar con el análisis meteorológico y sondeos Skew-T, selecciona la página **`3_Perfil_meteorologico`** en la barra lateral izquierda.")
