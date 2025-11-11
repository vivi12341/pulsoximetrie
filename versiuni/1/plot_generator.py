# ==============================================================================
# plot_generator.py (VERSIUNEA 5.0 FINALĂ - GRADIENT PERFECTAT)
# ------------------------------------------------------------------------------
# ROL: Generează vizualizarea finală, de înaltă fidelitate.
#
# MODIFICĂRI CHEIE:
#   1. Interpolare de Înaltă Densitate: Datele SaO2 sunt interpolate pentru
#      a crea o linie vizual solidă și continuă, chiar și la zoom maxim.
#      Linia gri de bază a fost eliminată.
#   2. Aliniere Perfectă a Barei de Culoare: Bara de culoare pentru SaO2
#      este acum poziționată și dimensionată pentru a se alinia perfect
#      cu subplotul superior.
# ==============================================================================

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

import config
from logger_setup import logger

# Definim gradientul de culoare (Plotly Colorscale)
SPO2_COLORSACLE = [
    [0.0,  '#D62728'],  # Roșu Intens (la 88% sau sub)
    [0.3,  '#FF7F0E'],  # Portocaliu
    [0.6,  '#FFD700'],  # Auriu/Galben (la ~94%)
    [1.0,  '#2CA02C']   # Verde (la 98% sau peste)
]

def interpolate_data(df, column, factor=10):
    """
    Crește densitatea punctelor dintr-un DataFrame folosind interpolare.
    Acesta este secretul pentru o linie în gradient care pare continuă.
    """
    if df.empty:
        return df
        
    # Creăm un nou index de timp cu de 'factor' ori mai multe puncte
    new_index = pd.date_range(start=df.index.min(), end=df.index.max(), periods=len(df) * factor)
    
    # Re-eșantionăm DataFrame-ul pe noul index și interpolăm valorile lipsă
    df_interpolated = df.reindex(df.index.union(new_index)).interpolate(method='time').loc[new_index]
    
    return df_interpolated

def create_plot(df_slice: pd.DataFrame, file_name: str) -> go.Figure:
    logger.info(f"Se generează vizualizarea finală de înaltă fidelitate pentru '{file_name}'.")
    
    # --- Inițializarea figurii cu subploturi ---
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        row_heights=[0.7, 0.3]
    )

    if df_slice.empty:
        logger.warning(f"DataFrame gol pentru '{file_name}'.")
        return fig

    # --- Interpolare de înaltă densitate pentru SaO2 ---
    df_spo2_dense = interpolate_data(df_slice[['SpO2']], 'SpO2', factor=10)
    logger.info(f"Interpolare date SaO2: {len(df_slice)} puncte -> {len(df_spo2_dense)} puncte.")

    # --- SUBPLOT 1: Saturația de Oxigen (SaO2) - Acum o singură urmă densă ---
    fig.add_trace(go.Scattergl(
        x=df_spo2_dense.index,
        y=df_spo2_dense['SpO2'],
        mode='markers', # Desenăm doar puncte, dar foarte, foarte dese
        marker=dict(
            color=df_spo2_dense['SpO2'],
            colorscale=SPO2_COLORSACLE,
            cmin=88,
            cmax=98,
            colorbar=dict(
                title="SaO2",
                thickness=15,
                len=0.65, # Lungimea barei = 65% din înălțimea totală a figurii
                y=0.675,  # Poziția verticală a centrului barei (0.5 = centru)
                yanchor='middle'
            ),
            size=5 # Dimensiunea punctelor
        ),
        name='SaO2',
        hoverinfo='y+x',
    ), row=1, col=1)

    # --- SUBPLOT 2: Pulsul Cardiac ---
    fig.add_trace(go.Scattergl(
        x=df_slice.index,
        y=df_slice['Pulse Rate'],
        name=config.GOLDEN_STYLE['traces']['pulse']['name'],
        mode='lines',
        line=dict(
            color=config.GOLDEN_STYLE['traces']['pulse']['color'],
            width=config.GOLDEN_STYLE['traces']['pulse']['width']
        ),
        hoverinfo='y+x',
    ), row=2, col=1)

    # --- Aplicarea stilului general și configurarea axelor ---
    start_time = df_slice.index.min().strftime('%H:%M:%S')
    end_time = df_slice.index.max().strftime('%H:%M:%S')
    record_date = df_slice.index.min().strftime('%d/%m/%Y')
    dynamic_title = f"Analiză Oximetrie: {record_date} (Interval: {start_time} - {end_time})"

    fig.update_layout(
        title=dict(text=dynamic_title, x=0.5),
        height=700,
        plot_bgcolor=config.GOLDEN_STYLE['layout']['plot_bgcolor'],
        paper_bgcolor=config.GOLDEN_STYLE['layout']['paper_bgcolor'],
        font=config.GOLDEN_STYLE['layout']['font'],
        showlegend=True,
        legend=config.GOLDEN_STYLE['legend']
    )

    # Configurări specifice pentru fiecare axă
    fig.update_yaxes(title_text="SaO2 (%)", range=[70, 100], row=1, col=1)
    fig.update_yaxes(title_text="Puls (bpm)", row=2, col=1)
    fig.update_xaxes(showticklabels=False, row=1, col=1)
    fig.update_xaxes(title_text="Timp", row=2, col=1)

    logger.info("Vizualizarea finală a fost creată cu succes.")
    return fig