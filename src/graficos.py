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
<<<<<<< HEAD
    Genera un diagrama termodinámico Skew-T log-P con estética moderna estilo Windy Sounding:
    - Fondo oscuro / Slate de alto contraste (#0F172A / #1E293B).
    - Eje Y logarítmico invertido de presión (1050 hPa a 200 hPa).
    - Isotermas inclinadas a 45° con isoterma 0°C resaltada (Línea de congelación).
    - Adiabáticas secas (θ) en naranja tenue y pseudoadiabáticas húmedas (θe) en verde tenue.
    - Curva de Temperatura T en rojo intenso (#EF4444) y Punto de Rocío Td en cian (#06B6D4).
    - Sombreado de sequedad/humedad entre T y Td (área de depresión).
    - Detección visual de capas de Inversión Térmica con bandas ámbar (#FBBF24).
    - Barbillas de viento y etiquetas de velocidad/dirección (kt / km/h) en el margen derecho.
    - Cuadro diagnóstico de incendio (Índice de Haines, Estabilidad, Sequedad).
=======
    Genera un diagrama Skew-T log-P termodinámico estándar con Matplotlib:
    - Eje Y logarítmico de presión (1000 hPa a 500 hPa).
    - Isotermas inclinadas a 45°.
    - Curva de Temperatura (rojo) y Punto de Rocío (verde).
    - Barbillas de viento en el costado derecho por nivel de presión.
    - Detección de capas de inversión térmica.
>>>>>>> incendios-magnitud-meteorologia/master
    """
    df = df_perfil.dropna(subset=["presion_hpa"]).sort_values("presion_hpa", ascending=False).copy()
    
    # Factor de inclinación (Skew factor)
    p0 = 1000.0
<<<<<<< HEAD
    skew = 32.0
=======
    skew = 35.0
>>>>>>> incendios-magnitud-meteorologia/master

    def skew_x(temp_c, p_hpa):
        return temp_c + skew * np.log(p0 / p_hpa)

<<<<<<< HEAD
    fig, ax = plt.subplots(figsize=(9.5, 9.0), dpi=120)
    fig.patch.set_facecolor("#0F172A")
    ax.set_facecolor("#1E293B")

    # Configuración de límites y escala de presión (1050 a 200 hPa)
    p_min, p_max = 180.0, 1050.0
    t_min, t_max = -55.0, 50.0
    
    x_min = skew_x(-35.0, p_max)
    x_max = skew_x(40.0, 300.0)

    # 1. Trazar Isobaras de referencia horizontales
    isobaras_principales = [1000, 925, 850, 700, 500, 400, 300, 200]
    isobaras_todas = [1000, 975, 950, 925, 900, 850, 800, 700, 600, 500, 400, 300, 250, 200]
    
    for p in isobaras_todas:
        if p_min <= p <= p_max:
            lw = 0.8 if p in isobaras_principales else 0.4
            color = "#334155" if p in isobaras_principales else "#1E293B"
            ax.axhline(p, color="#334155", linestyle="-", linewidth=lw, alpha=0.7)

    # 2. Trazar Adiabáticas Secas (Líneas θ en Kelvin)
    p_adiabat = np.linspace(200, 1050, 100)
    thetas = np.arange(260, 420, 20)
    for theta_k in thetas:
        # T_c = theta_k * (p / 1000)^(R/Cp) - 273.15  (R/Cp = 0.286)
        t_c_adiabat = theta_k * ((p_adiabat / 1000.0) ** 0.286) - 273.15
        x_adiabat = [skew_x(t, p) for t, p in zip(t_c_adiabat, p_adiabat)]
        ax.plot(x_adiabat, p_adiabat, color="#F97316", linestyle="--", linewidth=0.6, alpha=0.25)

    # 3. Trazar Isotermas inclinadas a 45°
    isotermas = np.arange(-70, 70, 10)
    p_ref = np.linspace(p_min, p_max, 50)
    for t_iso in isotermas:
        x_iso = [skew_x(t_iso, p) for p in p_ref]
        if t_iso == 0:
            # Isoterma 0°C resaltada (Nivel de congelamiento)
            ax.plot(x_iso, p_ref, color="#38BDF8", linestyle="--", linewidth=1.5, alpha=0.9, label="Isoterma 0°C (Congelación)")
        else:
            ax.plot(x_iso, p_ref, color="#475569", linestyle=":", linewidth=0.6, alpha=0.5)

    # 4. Sombreado de Inversiones Térmicas (T aumenta al subir / menor P)
    df_t = df.dropna(subset=["temperatura_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
    inversiones_encontradas = []
    if len(df_t) >= 2:
        for i in range(len(df_t) - 1):
            p_low = df_t.iloc[i]["presion_hpa"]
            p_high = df_t.iloc[i + 1]["presion_hpa"]
            t_low = df_t.iloc[i]["temperatura_c"]
            t_high = df_t.iloc[i + 1]["temperatura_c"]
            if t_high > t_low:
                delta_inv = t_high - t_low
                ax.axhspan(p_high, p_low, color="#FBBF24", alpha=0.18)
                inversiones_encontradas.append((p_low, p_high, delta_inv))
                ax.text(
                    x_min + 3.0,
                    (p_low + p_high) / 2.0,
                    f"⚠️ Inversión Térmica (+{delta_inv:.1f}°C)",
                    color="#FDE047",
                    fontsize=8.5,
                    fontweight="bold",
                    va="center",
                    bbox=dict(boxstyle="round,pad=0.2", facecolor="#713F12", edgecolor="#CA8A04", alpha=0.8),
                )

    # 5. Sombreado de sequedad atmosférica (entre T y Td)
    df_ambos = df.dropna(subset=["temperatura_c", "punto_rocio_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
    if len(df_ambos) >= 2:
        x_t_vals = [skew_x(t, p) for t, p in zip(df_ambos["temperatura_c"], df_ambos["presion_hpa"])]
        x_td_vals = [skew_x(td, p) for td, p in zip(df_ambos["punto_rocio_c"], df_ambos["presion_hpa"])]
        ax.fill_betweenx(df_ambos["presion_hpa"], x_td_vals, x_t_vals, color="#EA580C", alpha=0.12, label="Depresión T - Td (Sequedad)")

    # 6. Trazar Curva de Punto de Rocío (Td - Cyan/Esmeralda)
    if "punto_rocio_c" in df.columns and df["punto_rocio_c"].notna().any():
        df_td = df.dropna(subset=["punto_rocio_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
        x_td = [skew_x(td, p) for td, p in zip(df_td["punto_rocio_c"], df_td["presion_hpa"])]
        ax.plot(
            x_td,
            df_td["presion_hpa"],
            color="#06B6D4",
            linewidth=2.8,
            marker="o",
            markersize=5,
            markeredgecolor="#083344",
            label="Pto. Rocío (Td)",
            zorder=5,
        )

    # 7. Trazar Curva de Temperatura (T - Rojo Intenso)
    if "temperatura_c" in df.columns and df["temperatura_c"].notna().any():
        df_t_plot = df.dropna(subset=["temperatura_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
        x_t = [skew_x(t, p) for t, p in zip(df_t_plot["temperatura_c"], df_t_plot["presion_hpa"])]
        ax.plot(
            x_t,
            df_t_plot["presion_hpa"],
            color="#EF4444",
            linewidth=3.0,
            marker="o",
            markersize=5,
            markeredgecolor="#450A0A",
            label="Temperatura (T)",
            zorder=6,
        )

        # Anotaciones numéricas en niveles clave (850, 700, 500 hPa)
        for _, r in df_t_plot.iterrows():
            p_val = r["presion_hpa"]
            if p_val in [925, 850, 700, 500]:
                t_val = r["temperatura_c"]
                td_val = r.get("punto_rocio_c", np.nan)
                xt = skew_x(t_val, p_val)
                label_txt = f"{t_val:.1f}°" if pd.isna(td_val) else f"{t_val:.1f}° / {td_val:.1f}°"
                ax.text(
                    xt + 1.2,
                    p_val,
                    label_txt,
                    color="#F8FAFC",
                    fontsize=8,
                    fontweight="bold",
                    va="center",
                    zorder=7,
                )

    # 8. Barbillas de viento y etiquetas de velocidad en el margen derecho
    if "velocidad_viento_kmh" in df.columns and "direccion_viento_deg" in df.columns:
        df_viento = df.dropna(subset=["velocidad_viento_kmh", "direccion_viento_deg", "presion_hpa"])
        x_barb_col = x_max - 8.0
        
        for _, row in df_viento.iterrows():
            p_val = row["presion_hpa"]
            spd_kmh = row["velocidad_viento_kmh"]
            spd_knots = spd_kmh * 0.539957  # nudos
            dir_deg = row["direccion_viento_deg"]
            dir_rad = math.radians(dir_deg)
=======
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
>>>>>>> incendios-magnitud-meteorologia/master
            
            u = -spd_knots * math.sin(dir_rad)
            v = -spd_knots * math.cos(dir_rad)
            
<<<<<<< HEAD
            # Barbilla de viento
            ax.barbs(
                x_barb_col,
=======
            ax.barbs(
                x_barb_pos,
>>>>>>> incendios-magnitud-meteorologia/master
                p_val,
                u,
                v,
                length=6.0,
<<<<<<< HEAD
                barbcolor="#F8FAFC",
                flagcolor="#EF4444",
                linewidth=1.2,
                sizes=dict(emptybarb=0.1, spacing=0.2, height=0.5),
                zorder=7,
            )
            
            # Etiqueta de velocidad si es un nivel principal
            if p_val in [1000, 925, 850, 700, 600, 500, 400, 300, 200]:
                ax.text(
                    x_max - 1.5,
                    p_val,
                    f"{spd_knots:.0f}kt",
                    color="#94A3B8",
                    fontsize=7.5,
                    ha="right",
                    va="center",
                    zorder=7,
                )

    # 9. Cálculo del Índice de Haines para tarjeta informativa integrada
    t_850_row = df[df["presion_hpa"] == 850]
    t_700_row = df[df["presion_hpa"] == 700]
    haines_val = None
    haines_color = "#22C55E"
    haines_cat = "Bajo"
    
    if not t_850_row.empty and not t_700_row.empty:
        t850 = t_850_row.iloc[0]["temperatura_c"]
        t700 = t_700_row.iloc[0]["temperatura_c"]
        td850 = t_850_row.iloc[0].get("punto_rocio_c", np.nan)
        if pd.notna(t850) and pd.notna(t700) and pd.notna(td850):
            # A (estabilidad): T850 - T700
            dt = t850 - t700
            a_idx = 1 if dt <= 5.5 else 2 if dt <= 10.5 else 3
            # B (humedad): T850 - Td850
            dpd = t850 - td850
            b_idx = 1 if dpd <= 5.5 else 2 if dpd <= 12.5 else 3
            haines_val = a_idx + b_idx
            if haines_val == 6:
                haines_color = "#DC2626"
                haines_cat = "6 - EXTREMO"
            elif haines_val == 5:
                haines_color = "#EA580C"
                haines_cat = "5 - ALTO"
            elif haines_val == 4:
                haines_color = "#F59E0B"
                haines_cat = "4 - MODERADO"
            else:
                haines_color = "#16A34A"
                haines_cat = f"{haines_val} - BAJO"

    if haines_val:
        ax.text(
            x_min + 3.0,
            240.0,
            f"Índice de Haines: {haines_cat}\n(Inestabilidad A={a_idx} + Sequedad B={b_idx})",
            color="#FFFFFF",
            fontsize=9.0,
            fontweight="bold",
            va="top",
            bbox=dict(boxstyle="round,pad=0.4", facecolor=haines_color, edgecolor="#FFFFFF", alpha=0.9),
            zorder=10,
        )

    # Configuración de Ejes y Escala Logarítmica
    ax.set_yscale("log")
    ax.set_ylim(p_max, p_min)
    ax.set_yticks(isobaras_principales)
    
    # Etiquetas de presión con altitud aproximada
    altitudes_aprox = {
        1000: "1000 hPa (~100m)",
        925: "925 hPa (~750m)",
        850: "850 hPa (~1.5km)",
        700: "700 hPa (~3.0km)",
        500: "500 hPa (~5.6km)",
        400: "400 hPa (~7.2km)",
        300: "300 hPa (~9.2km)",
        200: "200 hPa (~11.8km)",
    }
    ax.set_yticklabels([altitudes_aprox.get(p, f"{p} hPa") for p in isobaras_principales], fontsize=8.5, color="#94A3B8")
    ax.set_ylabel("Presión Atmosférica (hPa) / Altitud aprox.", fontsize=10, fontweight="bold", color="#F8FAFC", labelpad=8)

    ticks_temp = np.arange(-40, 45, 10)
    ticks_x = [skew_x(t, p0) for t in ticks_temp]
    ax.set_xticks(ticks_x)
    ax.set_xticklabels([f"{t}°C" for t in ticks_temp], fontsize=8.5, color="#94A3B8")
    ax.set_xlabel("Temperatura a 1000 hPa / Isotermas Inclinadas (°C)", fontsize=10, fontweight="bold", color="#F8FAFC", labelpad=8)
    ax.set_xlim(x_min, x_max)

    # Bordes y espinas
    for spine in ax.spines.values():
        spine.set_color("#475569")
        spine.set_linewidth(1.2)

    # Títulos
    ax.set_title(titulo, fontsize=13, fontweight="bold", color="#F8FAFC", pad=16)
    if subtitulo:
        ax.text(0.5, 1.015, subtitulo, transform=ax.transAxes, fontsize=9.5, color="#94A3B8", ha="center", va="bottom")

    # Leyenda
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    if by_label:
        ax.legend(
            by_label.values(),
            by_label.keys(),
            loc="upper right",
            framealpha=0.85,
            facecolor="#0F172A",
            edgecolor="#334155",
            fontsize=8.5,
            labelcolor="#F8FAFC",
        )
=======
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
>>>>>>> incendios-magnitud-meteorologia/master

    plt.tight_layout()
    return fig


def generar_skewt_por_horas(dicc_perfiles: dict[str, pd.DataFrame], fecha: str = "") -> dict[str, plt.Figure]:
    """Genera un diccionario de figuras Skew-T por cada hora disponible."""
    figuras = {}
    for hora, df_perfil in dicc_perfiles.items():
        sub = f"Fecha: {fecha} | Hora: {hora} Local" if fecha else f"Hora: {hora} Local"
<<<<<<< HEAD
        figuras[hora] = generar_skewt_diagram(df_perfil, titulo="Perfil Vertical Atmosférico (Skew-T)", subtitulo=sub)
=======
        figuras[hora] = generar_skewt_diagram(df_perfil, titulo="Perfil Vertical Atmosférico", subtitulo=sub)
>>>>>>> incendios-magnitud-meteorologia/master
    return figuras


# ==============================================================================
<<<<<<< HEAD
# 2. DIAGRAMA SKEW-T INTERACTIVO (PLOTLY)
# ==============================================================================

def generar_skewt_plotly(
    df_perfil: pd.DataFrame,
    titulo: str = "Sondeo Atmosférico Vertical (Skew-T log-P)",
    subtitulo: str = "",
):
    """
    Genera un diagrama Skew-T log-P completamente INTERACTIVO con Plotly.

    NOTA TÉCNICA: El eje Y usa transformación manual -log10(presión) en un eje LINEAL.
    Esto evita los bugs de Plotly al combinar type='log' con add_hrect/add_hline.
    Los ticks son personalizados para mostrar las etiquetas correctas de presión/altitud.
    """
    if not PLOTLY_AVAILABLE:
        return None

    df = df_perfil.dropna(subset=["presion_hpa"]).sort_values("presion_hpa", ascending=False).copy()
    if df.empty:
        return None

    # ── Parámetros del Skew-T ────────────────────────────────────────────────
    skew = 32.0
    p0 = 1000.0
    P_MIN, P_MAX = 190.0, 1050.0   # rango de presión (hPa)

    def skew_x(temp_c, p_hpa):
        """Coordenada X inclinada en el espacio del Skew-T."""
        return float(temp_c) + skew * math.log(p0 / float(p_hpa))

    def p_to_y(p_hpa):
        """Presión (hPa) → coordenada Y lineal con escala logarítmica inversa.
        1050 hPa → y ≈ -3.02  (fondo)
        200  hPa → y ≈ -2.30  (cima)
        """
        return -math.log10(float(p_hpa))

    # Límites del eje X
    x_left  = skew_x(-40.0, P_MAX)
    x_right = skew_x(42.0,  300.0)
    y_bot   = p_to_y(P_MAX)      # ≈ -3.021  (1050 hPa)
    y_top   = p_to_y(P_MIN)      # ≈ -2.279  (190 hPa)

    # Isobaras principales para ticks y líneas
    isobaras_principales = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200]
    altitudes = {
        1000: "1000 hPa  (~0.1 km)",
        925:  "925 hPa  (~0.8 km)",
        850:  "850 hPa  (~1.5 km)",
        700:  "700 hPa  (~3.0 km)",
        600:  "600 hPa  (~4.2 km)",
        500:  "500 hPa  (~5.6 km)",
        400:  "400 hPa  (~7.2 km)",
        300:  "300 hPa  (~9.2 km)",
        250:  "250 hPa (~10.4 km)",
        200:  "200 hPa (~11.8 km)",
    }

    def deg_to_dir(deg):
        dirs = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]
        return dirs[int((float(deg) + 22.5) / 45) % 8]

    fig = go.Figure()

    # ─── 1. Adiabáticas Secas (θ) ──────────────────────────────────────────
    p_arr = np.linspace(P_MIN, P_MAX, 120)
    y_arr = [p_to_y(p) for p in p_arr]
    for theta_k in np.arange(260, 430, 20):
        t_c = theta_k * ((p_arr / 1000.0) ** 0.286) - 273.15
        x_ad = [skew_x(t, p) for t, p in zip(t_c, p_arr)]
        fig.add_trace(go.Scatter(
            x=x_ad, y=y_arr,
            mode="lines",
            line=dict(color="rgba(249,115,22,0.18)", width=0.9, dash="dash"),
            hoverinfo="skip", showlegend=False, legendgroup="bg",
        ))

    # ─── 2. Isotermas inclinadas ───────────────────────────────────────────
    p_ref = np.linspace(P_MIN, P_MAX, 80)
    y_ref = [p_to_y(p) for p in p_ref]
    for t_iso in np.arange(-80, 80, 10):
        x_iso = [skew_x(float(t_iso), p) for p in p_ref]
        is_zero = bool(t_iso == 0)
        fig.add_trace(go.Scatter(
            x=x_iso, y=y_ref,
            mode="lines",
            line=dict(
                color="rgba(56,189,248,0.90)" if is_zero else "rgba(71,85,105,0.50)",
                width=1.5 if is_zero else 0.55,
                dash="dash" if is_zero else "dot",
            ),
            name="Isoterma 0°C (Congelación)" if is_zero else "",
            showlegend=is_zero,
            legendgroup="isoterma",
            hoverinfo="skip",
        ))

    # ─── 3. Isobaras de referencia (líneas horizontales) ─────────────────
    for p in isobaras_principales:
        y_p = p_to_y(p)
        fig.add_trace(go.Scatter(
            x=[x_left, x_right + 15], y=[y_p, y_p],
            mode="lines",
            line=dict(color="rgba(51,65,85,0.60)", width=0.75),
            hoverinfo="skip", showlegend=False, legendgroup="bg",
        ))

    # ─── 4. Sombreado Inversiones Térmicas ────────────────────────────────
    df_tc = df.dropna(subset=["temperatura_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
    inversiones = []
    if len(df_tc) >= 2:
        for i in range(len(df_tc) - 1):
            p_inf = float(df_tc.iloc[i]["presion_hpa"])
            p_sup = float(df_tc.iloc[i + 1]["presion_hpa"])
            t_inf = df_tc.iloc[i]["temperatura_c"]
            t_sup = df_tc.iloc[i + 1]["temperatura_c"]
            if t_sup > t_inf:
                delta_inv = t_sup - t_inf
                inversiones.append((int(p_inf), int(p_sup), delta_inv))
                y0_inv = p_to_y(p_sup)   # nivel superior (y más alto)
                y1_inv = p_to_y(p_inf)   # nivel inferior (y más bajo)
                # Rectángulo como área rellena entre dos líneas horizontales
                fig.add_trace(go.Scatter(
                    x=[x_left, x_right + 15, x_right + 15, x_left, x_left],
                    y=[y0_inv, y0_inv, y1_inv, y1_inv, y0_inv],
                    fill="toself",
                    fillcolor="rgba(251,191,36,0.18)",
                    line=dict(width=0),
                    mode="lines",
                    name=f"⚠ Inversión {int(p_sup)}-{int(p_inf)} hPa",
                    showlegend=True,
                    legendgroup="inv",
                    hoverinfo="skip",
                ))
                # Anotación de texto
                y_mid = (y0_inv + y1_inv) / 2
                fig.add_annotation(
                    x=x_left + 1.5, y=y_mid,
                    text=f"⚠ Inversión +{delta_inv:.1f}°C",
                    showarrow=False,
                    font=dict(color="#FDE047", size=9),
                    bgcolor="rgba(113,63,18,0.85)",
                    bordercolor="#CA8A04",
                    borderwidth=1,
                    xanchor="left",
                    yanchor="middle",
                )

    # ─── 5. Sombreado Sequedad (T - Td) ───────────────────────────────────
    df_both = df.dropna(subset=["temperatura_c", "punto_rocio_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
    if len(df_both) >= 2:
        x_t_f  = [skew_x(t, p) for t, p in zip(df_both["temperatura_c"], df_both["presion_hpa"])]
        x_td_f = [skew_x(td, p) for td, p in zip(df_both["punto_rocio_c"], df_both["presion_hpa"])]
        y_f    = [p_to_y(p) for p in df_both["presion_hpa"]]
        x_poly = x_t_f + x_td_f[::-1]
        y_poly = y_f   + y_f[::-1]
        fig.add_trace(go.Scatter(
            x=x_poly, y=y_poly,
            fill="toself",
            fillcolor="rgba(234,88,12,0.15)",
            line=dict(width=0),
            mode="lines",
            name="Sequedad (T − Td)",
            showlegend=True,
            legendgroup="seq",
            hoverinfo="skip",
        ))

    # ─── 6. Curva de Punto de Rocío (Td — Cyan) ───────────────────────────
    df_td = df.dropna(subset=["punto_rocio_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
    if not df_td.empty:
        x_td = [skew_x(td, p) for td, p in zip(df_td["punto_rocio_c"], df_td["presion_hpa"])]
        y_td = [p_to_y(p) for p in df_td["presion_hpa"]]
        rh_col = df_td.get("humedad_relativa", pd.Series([np.nan] * len(df_td), index=df_td.index))
        hover_td = []
        for td_v, p_v, hr_v in zip(df_td["punto_rocio_c"], df_td["presion_hpa"], rh_col):
            txt = f"<b>{int(p_v)} hPa</b><br>Td: <b>{td_v:.1f}°C</b>"
            if pd.notna(hr_v):
                txt += f"<br>HR: {hr_v:.0f}%"
            hover_td.append(txt)
        fig.add_trace(go.Scatter(
            x=x_td, y=y_td,
            mode="lines+markers",
            name="Punto de Rocío (Td)",
            line=dict(color="#06B6D4", width=3.0),
            marker=dict(color="#06B6D4", size=7, symbol="circle",
                        line=dict(color="#083344", width=1.5)),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_td,
            legendgroup="td",
        ))

    # ─── 7. Curva de Temperatura (T — Rojo) ───────────────────────────────
    df_t = df.dropna(subset=["temperatura_c", "presion_hpa"]).sort_values("presion_hpa", ascending=False)
    if not df_t.empty:
        x_t = [skew_x(t, p) for t, p in zip(df_t["temperatura_c"], df_t["presion_hpa"])]
        y_t = [p_to_y(p) for p in df_t["presion_hpa"]]
        hover_t = []
        for _, r in df_t.iterrows():
            p_v  = int(r["presion_hpa"])
            t_v  = r["temperatura_c"]
            td_v = r.get("punto_rocio_c", np.nan)
            hr_v = r.get("humedad_relativa", np.nan)
            ws_v = r.get("velocidad_viento_kmh", np.nan)
            wd_v = r.get("direccion_viento_deg", np.nan)
            txt  = f"<b>{p_v} hPa</b><br>T: <b>{t_v:.1f}°C</b>"
            if pd.notna(td_v): txt += f"  |  Td: {td_v:.1f}°C"
            if pd.notna(hr_v): txt += f"<br>HR: {hr_v:.0f}%"
            if pd.notna(ws_v): txt += f"<br>Viento: {ws_v:.1f} km/h  ({ws_v * 0.54:.0f} kt)"
            if pd.notna(wd_v): txt += f"  desde {deg_to_dir(wd_v)} ({wd_v:.0f}°)"
            hover_t.append(txt)
        fig.add_trace(go.Scatter(
            x=x_t, y=y_t,
            mode="lines+markers",
            name="Temperatura (T)",
            line=dict(color="#EF4444", width=3.5),
            marker=dict(color="#EF4444", size=8, symbol="circle",
                        line=dict(color="#450A0A", width=1.5)),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_t,
            legendgroup="t",
        ))

        # Anotaciones numéricas en niveles clave
        for _, r in df_t.iterrows():
            p_v = float(r["presion_hpa"])
            if p_v in [850, 700, 500, 300]:
                t_v  = r["temperatura_c"]
                td_v = r.get("punto_rocio_c", np.nan)
                xt   = skew_x(t_v, p_v)
                yt   = p_to_y(p_v)
                lbl  = f"{t_v:.0f}°" if pd.isna(td_v) else f"{t_v:.0f}° / {td_v:.0f}°"
                fig.add_annotation(
                    x=xt + 1.0, y=yt,
                    text=lbl,
                    showarrow=False,
                    font=dict(color="#F8FAFC", size=8.5),
                    xanchor="left", yanchor="middle",
                )

    # ─── 8. Velocidades de viento a la derecha ────────────────────────────
    df_v = df.dropna(subset=["velocidad_viento_kmh", "presion_hpa"])
    niveles_v = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200]
    x_v_col = x_right + 6.0

    vx, vy, vc, vh = [], [], [], []
    for nivel in niveles_v:
        row = df_v[df_v["presion_hpa"] == nivel]
        if row.empty:
            continue
        ws_kmh = float(row.iloc[0]["velocidad_viento_kmh"])
        ws_kt  = ws_kmh * 0.54
        wd_deg = row.iloc[0].get("direccion_viento_deg", np.nan)
        color  = "#22C55E" if ws_kt < 15 else "#F59E0B" if ws_kt < 30 else "#EF4444" if ws_kt < 50 else "#7C3AED"
        dir_txt = f" {deg_to_dir(wd_deg)} ({wd_deg:.0f}°)" if pd.notna(wd_deg) else ""
        vx.append(x_v_col)
        vy.append(p_to_y(nivel))
        vc.append(color)
        vh.append(f"<b>{nivel} hPa</b><br>Viento: <b>{ws_kmh:.1f} km/h ({ws_kt:.0f} kt)</b><br>Dirección:{dir_txt}")

        # Etiqueta kt
        fig.add_annotation(
            x=x_v_col + 1.5, y=p_to_y(nivel),
            text=f"{ws_kt:.0f} kt",
            showarrow=False,
            font=dict(color="#94A3B8", size=8),
            xanchor="left", yanchor="middle",
        )

    if vx:
        fig.add_trace(go.Scatter(
            x=vx, y=vy,
            mode="markers",
            name="Viento (kt)",
            marker=dict(color=vc, size=10, symbol="circle",
                        line=dict(color="white", width=1)),
            hovertemplate="%{customdata}<extra></extra>",
            customdata=vh,
            showlegend=True,
        ))

    # ─── 9. Tarjeta Índice de Haines ──────────────────────────────────────
    r850 = df[df["presion_hpa"] == 850]
    r700 = df[df["presion_hpa"] == 700]
    if not r850.empty and not r700.empty:
        t850 = r850.iloc[0]["temperatura_c"]
        t700 = r700.iloc[0]["temperatura_c"]
        td850 = r850.iloc[0].get("punto_rocio_c", np.nan)
        if pd.notna(t850) and pd.notna(t700) and pd.notna(td850):
            dt_val  = t850 - t700
            dpd_val = t850 - td850
            a_idx = 1 if dt_val <= 5.5  else 2 if dt_val <= 10.5 else 3
            b_idx = 1 if dpd_val <= 5.5 else 2 if dpd_val <= 12.5 else 3
            h_val = a_idx + b_idx
            h_color = {2: "#16A34A", 3: "#16A34A", 4: "#F59E0B", 5: "#EA580C", 6: "#DC2626"}.get(h_val, "#16A34A")
            h_cat   = {2: "2 — Muy Bajo", 3: "3 — Muy Bajo", 4: "4 — Moderado",
                       5: "5 — ALTO",     6: "6 — EXTREMO"}.get(h_val, str(h_val))
            fig.add_annotation(
                x=x_left + 1.5,
                y=p_to_y(280),
                text=f"<b>Índice de Haines: {h_cat}</b><br>A (Inestabilidad)={a_idx}   B (Sequedad)={b_idx}",
                showarrow=False,
                bgcolor=h_color,
                bordercolor="white",
                borderwidth=1.5,
                borderpad=6,
                font=dict(color="white", size=10.5),
                xanchor="left",
                yanchor="top",
            )

    # ─── Layout ───────────────────────────────────────────────────────────
    titulo_final = titulo
    if subtitulo:
        titulo_final += f"<br><sup>{subtitulo}</sup>"

    tick_y_vals = [p_to_y(p) for p in isobaras_principales]
    tick_y_text = [altitudes.get(p, f"{p} hPa") for p in isobaras_principales]
    tick_x_vals = [skew_x(t, p0) for t in np.arange(-40, 46, 10)]
    tick_x_text = [f"{t}°C" for t in np.arange(-40, 46, 10)]

    fig.update_layout(
        title=dict(
            text=titulo_final,
            font=dict(size=14, color="#F8FAFC", family="Inter, Arial, sans-serif"),
            x=0.5, xanchor="center",
        ),
        plot_bgcolor="#1E293B",
        paper_bgcolor="#0F172A",
        font=dict(color="#94A3B8", family="Inter, Arial, sans-serif"),
        xaxis=dict(
            title="Temperatura / Isotermas inclinadas (°C)",
            title_font=dict(size=11, color="#F8FAFC"),
            range=[x_left, x_right + 22],
            showgrid=False,
            zeroline=False,
            tickvals=tick_x_vals,
            ticktext=tick_x_text,
            tickfont=dict(color="#94A3B8", size=9),
            linecolor="#475569",
        ),
        yaxis=dict(
            title="Presión / Altitud",
            title_font=dict(size=11, color="#F8FAFC"),
            range=[y_bot - 0.01, y_top + 0.01],
            showgrid=False,
            zeroline=False,
            tickvals=tick_y_vals,
            ticktext=tick_y_text,
            tickfont=dict(color="#94A3B8", size=9),
            linecolor="#475569",
        ),
        legend=dict(
            orientation="v",
            x=1.01, y=1.0,
            xanchor="left", yanchor="top",
            bgcolor="rgba(15,23,42,0.85)",
            bordercolor="#334155",
            borderwidth=1,
            font=dict(color="#F8FAFC", size=9.5),
        ),
        hoverlabel=dict(
            bgcolor="#1E293B",
            bordercolor="#475569",
            font=dict(color="#F8FAFC", size=11, family="Inter, Arial, sans-serif"),
        ),
        hovermode="closest",
        height=700,
        margin=dict(l=20, r=150, t=85, b=55),
    )

    return fig




# ==============================================================================
# 3. SERIES TEMPORALES DE SUPERFICIE (PLOTLY CON FALLBACK MATPLOTLIB)
=======
# 2. SERIES TEMPORALES DE SUPERFICIE (PLOTLY CON FALLBACK MATPLOTLIB)
>>>>>>> incendios-magnitud-meteorologia/master
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
