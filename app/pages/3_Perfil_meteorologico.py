"""
app/pages/3_Perfil_meteorologico.py
Muestra el perfil vertical (skew-T) del incendio seleccionado, navegable
por día y, dentro de cada día, por hora cada 6 horas (00:00, 06:00, 12:00,
18:00, hora local).
"""

import streamlit as st

from src.firms import obtener_dias_con_actividad
from src.meteorologia import (
    armar_perfil_vertical,
    consultar_meteorologia_historica,
    extraer_condiciones_cada_6h,
)
from src.graficos import generar_skewt_por_horas

st.title("Perfil vertical del incendio")

# --- Estos valores vendrían de la selección del usuario en la página de
# Mapa de incendios (coordenadas + puntos FIRMS ya filtrados para ese
# incendio). Se dejan en session_state como ejemplo mientras se conecta
# el flujo completo.
lat_incendio = st.session_state.get("lat_incendio", -38.7359)
lon_incendio = st.session_state.get("lon_incendio", -72.5904)
df_puntos_incendio = st.session_state.get("df_puntos_incendio")  # de firms.py

if df_puntos_incendio is None or df_puntos_incendio.empty:
    st.warning("Selecciona primero un incendio en la página de Mapa de incendios.")
    st.stop()

dias_con_actividad = obtener_dias_con_actividad(df_puntos_incendio)
if not dias_con_actividad:
    st.error("No se encontraron días con actividad FIRMS para este incendio.")
    st.stop()

# Consulta meteorológica de una sola vez para todo el rango de días con
# actividad (evita pedirle a Open-Meteo día por día).
df_horario = consultar_meteorologia_historica(
    lat_incendio, lon_incendio, dias_con_actividad[0], dias_con_actividad[-1]
)
condiciones_por_dia = extraer_condiciones_cada_6h(df_horario)

dias_disponibles = list(condiciones_por_dia.keys())
dia_seleccionado = st.select_slider(
    "Día", options=dias_disponibles, value=dias_disponibles[0]
)

horas_disponibles = list(condiciones_por_dia[dia_seleccionado].keys())
hora_seleccionada = st.radio(
    "Hora (local)",
    horas_disponibles,
    horizontal=True,
    index=len(horas_disponibles) // 2,
)

fila = condiciones_por_dia[dia_seleccionado][hora_seleccionada]
df_perfil = armar_perfil_vertical(fila)

figuras = generar_skewt_por_horas({hora_seleccionada: df_perfil}, fecha=dia_seleccionado)
st.pyplot(figuras[hora_seleccionada])

with st.expander("Ver datos del perfil"):
    st.dataframe(df_perfil, use_container_width=True)