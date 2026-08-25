"""
src/graficos.py
Generación de gráficos meteorológicos interactivos (Plotly / Matplotlib) y diagramas Skew-T (Matplotlib)
para el análisis de condiciones de incendios forestales.
"""

import math
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd

# Importación condicional de Plotly para máxima resiliencia
try:
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False


# ==============================================================================
# 1. DIAGRAMA SKEW-T / SONDEO VERTICAL (MATPLOTLIB)
# ==============================================================================

def generar_skewt_diagram(
    df_perfil: pd.DataFrame,
    titulo: str = "Sondeo Vertical Atmosférico (Skew-T log-P)",
    subtitulo: str = "",
) -> plt.Figure:
    """
    Genera un diagrama Skew-T log-P termodinámico estándar con Matplotlib:
    - Eje Y logarítmico de presión (1000 hPa a 500 hPa).
    - Isotermas inclinadas a 45°.
    - Curva de Temperatura (rojo) y Punto de Rocío (verde).
    - Barbillas de viento en el costado derecho por nivel de presión.
    - Detección de capas de inversión térmica.
    """
    df = df_perfil.dropna(subset=["presion_hpa"]).sort_values("presion_hpa", ascending=False).copy()
    
    # Factor de inclinación (Skew factor)
    p0 = 1000.0
    skew = 35.0

    def skew_x(temp_c, p_hpa):
        return temp_c + skew * np.log(p0 / p_hpa)

    fig, ax = plt.subplots(figsize=(8.5, 8), dpi=100)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FAFAFC")

    # Configuración de límites y escala de presión (Y logarítmico invertido)
    p_min, p_max = 480.0, 1030.0
    t_min, t_max = -35.0, 45.0
    
    x_min = skew_x(t_min, p_max)
    x_max = skew_x(t_max, p_min)

    # 1. Trazar Isobaras de referencia (Líneas horizontales de presión)
    isobaras = [1000, 950, 925, 900, 850, 800, 700, 600, 500]
    for p in isobaras:
        if p_min <= p <= p_max:
            ax.axhline(p, color="#D0D5DD", linestyle="-", linewidth=0.8, alpha=0.8)

    # 2. Trazar Isotermas inclinadas de referencia
    isotermas = np.arange(-50, 60, 10)
    p_ref = np.linspace(p_min, p_max, 50)
    for t_iso in isotermas:
        x_iso = [skew_x(t_iso, p) for p in p_ref]
        color_iso = "#3B82F6" if t_iso == 0 else "#E2E8F0"
        lw = 1.5 if t_iso == 0 else 0.8
        ax.plot(x_iso, p_ref, color=color_iso, linestyle="--", linewidth=lw, alpha=0.85)

    # 3. Trazar Curva de Temperatura (T) y Punto de Rocío (Td)
    if "temperatura_c" in df.columns and df["temperatura_c"].notna().any():
        df_t = df.dropna(subset=["temperatura_c", "presion_hpa"])
        x_t = [skew_x(t, p) for t, p in zip(df_t["temperatura_c"], df_t["presion_hpa"])]
        ax.plot(x_t, df_t["presion_hpa"], color="#DC2626", linewidth=2.5, label="Temperatura (T)", marker="o", markersize=4)

    if "punto_rocio_c" in df.columns and df["punto_rocio_c"].notna().any():
        df_td = df.dropna(subset=["punto_rocio_c", "presion_hpa"])
        x_td = [skew_x(td, p) for td, p in zip(df_td["punto_rocio_c"], df_td["presion_hpa"])]
        ax.plot(x_td, df_td["presion_hpa"], color="#16A34A", linewidth=2.5, label="Pto. Rocío (Td)", marker="s", markersize=4)

    # 4. Sombreado de inversión térmica (cuando T aumenta con la altura / menor P)
    if "temperatura_c" in df.columns and len(df.dropna(subset=["temperatura_c"])) >= 2:
        df_t = df.dropna(subset=["temperatura_c", "presion_hpa"])
        for i in range(len(df_t) - 1):
            p_lower = df_t.iloc[i]["presion_hpa"]
            p_upper = df_t.iloc[i + 1]["presion_hpa"]
            t_lower = df_t.iloc[i]["temperatura_c"]
            t_upper = df_t.iloc[i + 1]["temperatura_c"]
            if t_upper > t_lower:  # Inversión térmica
                ax.axhspan(p_upper, p_lower, color="#FEF08A", alpha=0.25, label="Inversión Térmica" if i == 0 else "")

    # 5. Barbillas de viento en el margen derecho
    if "velocidad_viento_kmh" in df.columns and "direccion_viento_deg" in df.columns:
        df_viento = df.dropna(subset=["velocidad_viento_kmh", "direccion_viento_deg", "presion_hpa"])
        x_barb_pos = x_max - 5.0
        
        for _, row in df_viento.iterrows():
            p_val = row["presion_hpa"]
            spd_knots = row["velocidad_viento_kmh"] * 0.539957  # km/h a nudos
            dir_rad = math.radians(row["direccion_viento_deg"])
            
            u = -spd_knots * math.sin(dir_rad)
            v = -spd_knots * math.cos(dir_rad)
            
            ax.barbs(
                x_barb_pos,
                p_val,
                u,
                v,
                length=6.0,
                barbcolor="#1E293B",
                flagcolor="#DC2626",
                linewidth=1.0,
                sizes=dict(emptybarb=0.1, spacing=0.2, height=0.5),
            )

    # Configuración de ejes
    ax.set_yscale("log")
    ax.set_ylim(p_max, p_min)
    ax.set_yticks(isobaras)
    ax.get_yaxis().set_major_formatter(ticker.ScalarFormatter())
    ax.set_ylabel("Presión Atmosférica (hPa)", fontsize=11, fontweight="semibold", color="#334155")

    ticks_temp = np.arange(-30, 45, 10)
    ticks_x = [skew_x(t, p0) for t in ticks_temp]
    ax.set_xticks(ticks_x)
    ax.set_xticklabels([f"{t}°C" for t in ticks_temp], fontsize=9)
    ax.set_xlabel("Temperatura a 1000 hPa / Isotermas (°C)", fontsize=11, fontweight="semibold", color="#334155")
    ax.set_xlim(x_min, x_max)

    ax.set_title(f"{titulo}\n{subtitulo}" if subtitulo else titulo, fontsize=12, fontweight="bold", color="#0F172A", pad=12)
    
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    if by_label:
        ax.legend(by_label.values(), by_label.keys(), loc="upper left", framealpha=0.9, facecolor="#FFFFFF", edgecolor="#CBD5E1", fontsize=9)

    plt.tight_layout()
    return fig


def generar_skewt_por_horas(dicc_perfiles: dict[str, pd.DataFrame], fecha: str = "") -> dict[str, plt.Figure]:
    """Genera un diccionario de figuras Skew-T por cada hora disponible."""
    figuras = {}
    for hora, df_perfil in dicc_perfiles.items():
        sub = f"Fecha: {fecha} | Hora: {hora} Local" if fecha else f"Hora: {hora} Local"
        figuras[hora] = generar_skewt_diagram(df_perfil, titulo="Perfil Vertical Atmosférico", subtitulo=sub)
    return figuras


# ==============================================================================
# 2. SERIES TEMPORALES DE SUPERFICIE (PLOTLY CON FALLBACK MATPLOTLIB)
# ==============================================================================

def generar_grafico_temperatura_humedad(df_horario: pd.DataFrame):
    """Gráfico de Temperatura (°C) y Humedad Relativa (%)."""
    if PLOTLY_AVAILABLE:
        fig = make_subplots(specs=[[{"secondary_y": True}]])

        fig.add_trace(
            go.Scatter(
                x=df_horario["time"],
                y=df_horario["temperature_2m"],
                name="Temperatura 2m (°C)",
                line=dict(color="#EF4444", width=2.5),
                mode="lines",
                hovertemplate="%{x|%d-%b %H:%M}<br><b>Temperatura:</b> %{y:.1f} °C<extra></extra>",
            ),
            secondary_y=False,
        )

        if "dew_point_2m" in df_horario.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_horario["time"],
                    y=df_horario["dew_point_2m"],
                    name="Pto. Rocío 2m (°C)",
                    line=dict(color="#10B981", width=1.5, dash="dot"),
                    mode="lines",
                    hovertemplate="%{x|%d-%b %H:%M}<br><b>Pto. Rocío:</b> %{y:.1f} °C<extra></extra>",
                ),
                secondary_y=False,
            )

        fig.add_trace(
            go.Scatter(
                x=df_horario["time"],
                y=df_horario["relative_humidity_2m"],
                name="Humedad Relativa (%)",
                line=dict(color="#3B82F6", width=2.5),
                mode="lines",
                hovertemplate="%{x|%d-%b %H:%M}<br><b>Humedad:</b> %{y:.1f} %<extra></extra>",
            ),
            secondary_y=True,
        )

        fig.add_hline(y=30, line_dash="dash", line_color="#F87171", line_width=1, annotation_text="Umbral 30°C", annotation_position="top right", secondary_y=False)
        fig.add_hline(y=30, line_dash="dash", line_color="#93C5FD", line_width=1, annotation_text="Umbral 30% HR", annotation_position="bottom right", secondary_y=True)

        fig.update_layout(
            title="<b>Evolución de Temperatura y Humedad Relativa en Superficie</b>",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            height=380,
        )

        fig.update_xaxes(title_text="Fecha y Hora Local", showgrid=True, gridcolor="#F1F5F9")
        fig.update_yaxes(title_text="<b>Temperatura (°C)</b>", title_font=dict(color="#EF4444"), tickfont=dict(color="#EF4444"), showgrid=True, gridcolor="#F1F5F9", secondary_y=False)
        fig.update_yaxes(title_text="<b>Humedad Relativa (%)</b>", title_font=dict(color="#3B82F6"), tickfont=dict(color="#3B82F6"), range=[0, 105], showgrid=False, secondary_y=True)
        return fig
    else:
        # Fallback Matplotlib
        fig, ax1 = plt.subplots(figsize=(10, 4), dpi=100)
        ax2 = ax1.twinx()
        ax1.plot(df_horario["time"], df_horario["temperature_2m"], color="#EF4444", label="T 2m (°C)")
        ax2.plot(df_horario["time"], df_horario["relative_humidity_2m"], color="#3B82F6", label="HR 2m (%)")
        ax1.set_ylabel("Temperatura (°C)", color="#EF4444")
        ax2.set_ylabel("Humedad Relativa (%)", color="#3B82F6")
        ax1.set_title("Temperatura y Humedad Relativa")
        return fig


def generar_grafico_viento(df_horario: pd.DataFrame):
    """Gráfico de Velocidad de Viento y Ráfagas a 10m."""
    if PLOTLY_AVAILABLE:
        fig = go.Figure()

        if "wind_gusts_10m" in df_horario.columns:
            fig.add_trace(
                go.Scatter(
                    x=df_horario["time"],
                    y=df_horario["wind_gusts_10m"],
                    name="Ráfagas 10m (km/h)",
                    line=dict(color="#F59E0B", width=1.5, dash="dash"),
                    hovertemplate="%{x|%d-%b %H:%M}<br><b>Ráfaga:</b> %{y:.1f} km/h<extra></extra>",
                )
            )

        fig.add_trace(
            go.Scatter(
                x=df_horario["time"],
                y=df_horario["wind_speed_10m"],
                name="Velocidad Viento 10m (km/h)",
                fill="tozeroy",
                fillcolor="rgba(14, 165, 233, 0.15)",
                line=dict(color="#0EA5E9", width=2.5),
                hovertemplate="%{x|%d-%b %H:%M}<br><b>Viento:</b> %{y:.1f} km/h<extra></extra>",
            )
        )

        fig.add_hline(y=30, line_dash="dash", line_color="#EF4444", line_width=1.2, annotation_text="Umbral Crítico 30 km/h", annotation_position="top right")

        fig.update_layout(
            title="<b>Velocidad y Ráfagas de Viento a 10m</b>",
            hovermode="x unified",
            template="plotly_white",
            yaxis_title="Velocidad (km/h)",
            xaxis_title="Fecha y Hora Local",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            height=320,
        )
        fig.update_xaxes(showgrid=True, gridcolor="#F1F5F9")
        fig.update_yaxes(showgrid=True, gridcolor="#F1F5F9")
        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 3.5), dpi=100)
        ax.plot(df_horario["time"], df_horario["wind_speed_10m"], color="#0EA5E9", label="Viento (km/h)")
        if "wind_gusts_10m" in df_horario.columns:
            ax.plot(df_horario["time"], df_horario["wind_gusts_10m"], color="#F59E0B", linestyle="--", label="Ráfagas (km/h)")
        ax.axhline(30, color="#EF4444", linestyle=":", label="Umbral 30 km/h")
        ax.set_ylabel("Velocidad (km/h)")
        ax.set_title("Viento y Ráfagas a 10m")
        ax.legend()
        return fig


def generar_grafico_precipitacion(df_horario: pd.DataFrame):
    """Gráfico de barras de Precipitación Horaria (mm) y acumulada."""
    if PLOTLY_AVAILABLE:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        precip_acum = df_horario["precipitation"].cumsum()

        fig.add_trace(
            go.Bar(
                x=df_horario["time"],
                y=df_horario["precipitation"],
                name="Precipitación Horaria (mm)",
                marker_color="#38BDF8",
                hovertemplate="%{x|%d-%b %H:%M}<br><b>Precipitación:</b> %{y:.2f} mm<extra></extra>",
            ),
            secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=df_horario["time"],
                y=precip_acum,
                name="Acumulada (mm)",
                line=dict(color="#0369A1", width=2),
                hovertemplate="%{x|%d-%b %H:%M}<br><b>Acumulada:</b> %{y:.2f} mm<extra></extra>",
            ),
            secondary_y=True,
        )

        fig.update_layout(
            title="<b>Precipitación Horaria y Acumulada</b>",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            height=280,
        )
        fig.update_xaxes(title_text="Fecha y Hora Local", showgrid=True, gridcolor="#F1F5F9")
        fig.update_yaxes(title_text="Horaria (mm)", showgrid=True, gridcolor="#F1F5F9", secondary_y=False)
        fig.update_yaxes(title_text="Acumulada (mm)", showgrid=False, secondary_y=True)
        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 3), dpi=100)
        ax.bar(df_horario["time"], df_horario["precipitation"], color="#38BDF8", label="Precipitación (mm)")
        ax.set_ylabel("mm")
        ax.set_title("Precipitación")
        return fig


# ==============================================================================
# 3. ROSA DE VIENTOS POLAR (PLOTLY / MATPLOTLIB)
# ==============================================================================

def generar_rosa_vientos(df_horario: pd.DataFrame):
    """Genera una rosa de los vientos en coordenadas polares."""
    if "wind_direction_10m" not in df_horario.columns or "wind_speed_10m" not in df_horario.columns:
        return None

    df = df_horario.dropna(subset=["wind_direction_10m", "wind_speed_10m"]).copy()
    if df.empty:
        return None

    direcciones = [
        "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
        "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
    ]
    
    def deg_to_dir(deg):
        idx = int((deg + 11.25) / 22.5) % 16
        return direcciones[idx]

    df["dir_sector"] = df["wind_direction_10m"].apply(deg_to_dir)
    bins = [0, 10, 20, 30, 45, 150]
    labels_speed = ["0 - 10 km/h", "10 - 20 km/h", "20 - 30 km/h", "30 - 45 km/h", "> 45 km/h"]
    colores_speed = ["#BAE6FD", "#38BDF8", "#FBBF24", "#F97316", "#EF4444"]
    
    df["rango_viento"] = pd.cut(df["wind_speed_10m"], bins=bins, labels=labels_speed, right=False)
    conteo = df.groupby(["dir_sector", "rango_viento"], observed=False).size().unstack(fill_value=0)
    conteo_pct = (conteo / len(df)) * 100.0
    conteo_pct = conteo_pct.reindex(direcciones, fill_value=0)

    if PLOTLY_AVAILABLE:
        fig = go.Figure()
        for rango, color in zip(labels_speed, colores_speed):
            if rango in conteo_pct.columns:
                fig.add_trace(
                    go.Barpolar(
                        r=conteo_pct[rango],
                        theta=conteo_pct.index,
                        name=rango,
                        marker_color=color,
                        hovertemplate="<b>Dirección:</b> %{theta}<br><b>Frecuencia:</b> %{r:.1f}%<br><b>Rango:</b> " + rango + "<extra></extra>",
                    )
                )

        fig.update_layout(
            title="<b>Rosa de Vientos a 10m (Frecuencia por Dirección y Velocidad)</b>",
            template="plotly_white",
            polar=dict(
                radialaxis=dict(ticksuffix="%", angle=45, dtick=5, showline=True, gridcolor="#E2E8F0"),
                angularaxis=dict(direction="clockwise", period=16, gridcolor="#E2E8F0"),
            ),
            legend=dict(title="Velocidad 10m", orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.05),
            margin=dict(l=40, r=40, t=60, b=40),
            height=380,
        )
        return fig
    else:
        # Fallback Matplotlib polar
        fig, ax = plt.subplots(figsize=(6, 6), subplot_kw=dict(projection="polar"), dpi=100)
        ax.set_theta_zero_location("N")
        ax.set_theta_direction(-1)
        thetas = np.linspace(0, 2 * np.pi, 16, endpoint=False)
        bottom = np.zeros(16)
        for rango, color in zip(labels_speed, colores_speed):
            if rango in conteo_pct.columns:
                values = conteo_pct[rango].values
                ax.bar(thetas, values, width=2 * np.pi / 16, bottom=bottom, color=color, label=rango, edgecolor="white")
                bottom += values
        ax.set_xticks(thetas)
        ax.set_xticklabels(direcciones)
        ax.set_title("Rosa de Vientos 10m")
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
        return fig
