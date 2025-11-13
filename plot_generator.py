# ==============================================================================
# plot_generator.py (VERSIUNEA 12.0 - METODA LINE.COLOR)
# ------------------------------------------------------------------------------
# ROL: Generează vizualizarea grafică a datelor de pulsoximetrie.
#
# MODIFICĂRI CHEIE (v12.0):
#  - IMPLEMENTAT: Metoda modernă `line.color` pentru crearea unei linii
#    cu gradient de culoare pentru SaO2, înlocuind tehnica anterioară
#    cu markeri.
#  - CURĂȚENIE: S-a eliminat funcția `generate_procedural_colorscale` și
#    referințele la `SPO2_COLOR_STOPS` care nu mai sunt necesare.
#  - CONFIGURABIL: Toate setările de stil sunt citite din `config.py`.
#  - PERFORMANȚĂ: Interpolarea de înaltă densitate pentru o linie fină.
# ==============================================================================
import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import numpy as np
from PIL import Image
import io

import config
from logger_setup import logger



def interpolate_data(df: pd.DataFrame, factor: int) -> pd.DataFrame:
    """
    Crește densitatea punctelor dintr-un DataFrame folosind interpolare temporală.
    Necesar pentru a crea o linie cu gradient fin.
    """
    # [WHY] Adăugăm un log de nivel DEBUG pentru a monitoriza cererile de interpolare.
    logger.debug(f"Request pentru interpolare date cu factorul {factor}. Puncte inițiale: {len(df)}")

    if df.empty or factor <= 1:
        # [WHY] Prevenim procesarea inutilă dacă nu e nevoie de interpolare.
        logger.debug("DataFrame gol sau factor de interpolare trivial. Se returnează datele originale.")
        return df
        
    # Creăm un nou index de timp cu de 'factor' ori mai multe puncte
    new_index = pd.date_range(start=df.index.min(), end=df.index.max(), periods=len(df) * factor)
    
    # Re-eșantionăm DataFrame-ul pe noul index și interpolăm valorile lipsă
    df_interpolated = df.reindex(df.index.union(new_index)).interpolate(method='time').loc[new_index]
    
    # [WHY] Logăm rezultatul pentru a confirma că interpolarea a funcționat.
    logger.info(f"Interpolare date finalizată. Puncte noi: {len(df_interpolated)}")
    
    return df_interpolated

def create_plot(df_slice: pd.DataFrame, file_name: str, line_width_scale: float = 1.0, marker_size_scale: float = 1.0) -> go.Figure:
    """
    Creează figura Plotly completă, folosind un heatmap pe post de legendă
    într-un subplot dedicat pentru aliniere perfectă.
    
    Args:
        df_slice: DataFrame cu datele de pulsoximetrie
        file_name: Numele fișierului pentru logging
        line_width_scale: Factor de scalare pentru grosimea liniei (0.3-1.0 pentru zoom dinamic)
        marker_size_scale: Factor de scalare pentru dimensiunea markerilor (0.3-1.0 pentru zoom dinamic)
    """
    # [WHY] Logăm începutul procesului pentru a urmări execuția.
    logger.info(f"Pornire generare grafic avansat (cu heatmap) pentru '{file_name}'. Scalare: linie={line_width_scale:.2f}, marker={marker_size_scale:.2f}")

    # --- Pas 1: Crearea grilei de subploturi ---
    # [WHY] Adăugăm shared_yaxes=True. Aceasta este cheia pentru a sincroniza
    # mișcarea verticală a legendei-heatmap cu cea a graficului principal.
    logger.debug("Creare figură cu 'shared_yaxes=True' pentru a sincroniza legenda cu graficul.")
    fig = make_subplots(
        rows=2, cols=2,
        column_widths=[0.05, 0.95],
        row_heights=[0.7, 0.3],
        shared_xaxes='columns',
        shared_yaxes=True, # <<< MODIFICAREA CHEIE AICI
        vertical_spacing=0.05,
        horizontal_spacing=0.01
    )

    if df_slice.empty or len(df_slice) < 2:
        logger.warning(f"DataFrame gol pentru '{file_name}'. Se returnează un grafic gol.")
        return fig

    # --- Pas 2: Preluarea stilurilor și pregătirea datelor ---
    spo2_style = config.GOLDEN_STYLE['traces']['spo2']
    pulse_style = config.GOLDEN_STYLE['traces']['pulse']
    layout_style = config.GOLDEN_STYLE['layout']
    
    # [WHY] Aplicăm factorii de scalare dinamici pentru zoom
    dynamic_line_width = spo2_style['line_width'] * line_width_scale
    dynamic_marker_size = spo2_style['marker_size'] * marker_size_scale
    
    # [WHY] Logăm intervalul de culoare folosit și valorile dinamice calculate
    logger.info(f"Se aplică gradientul de culoare pe intervalul SaO2: [{spo2_style['colorscale_min']}, {spo2_style['colorscale_max']}]")
    logger.debug(f"Valori dinamice calculate: line_width={dynamic_line_width:.2f}, marker_size={dynamic_marker_size:.2f}")
    
    # Interpolăm datele pentru o linie fină
    df_spo2_dense = interpolate_data(df_slice[['SpO2']], factor=spo2_style['interpolation_factor'])
    spo2_values = df_spo2_dense['SpO2'].values

    # --- Pas 3: Crearea legendei-heatmap (Coloana 1) ---
    # [WHY] Pregătim datele pentru heatmap. `z` trebuie să fie o coloană (multiple liste cu un element).
    y_axis_values = np.arange(config.GOLDEN_STYLE['axes']['yaxis_spo2']['range'][0], config.GOLDEN_STYLE['axes']['yaxis_spo2']['range'][1] + 1)
    heatmap_z = [[val] for val in y_axis_values] 

    heatmap_params = {
        'z': heatmap_z, # <-- CORECȚIE 1: Folosim datele remodelate
        'x': [''], # O singură coloană, fără etichetă
        'y': y_axis_values, # <-- CORECȚIE 2: Aliniem rândurile la valorile de pe axa Y
        'colorscale': spo2_style['colorscale'],
        'zmin': spo2_style['colorscale_min'],
        'zmax': spo2_style['colorscale_max'],
        'showscale': False,
        'hoverinfo': 'none'
    }
    # [WHY] Logăm forma (shape) datelor 'z'. O formă (N, 1) este corectă pentru o bară verticală.
    logger.debug(f"Adăugare Heatmap. Forma datelor 'z': {np.array(heatmap_z).shape}. Parametri: { {k: v for k, v in heatmap_params.items() if k != 'z'} }")
    fig.add_trace(go.Heatmap(heatmap_params), row=1, col=1)


    # --- Pas 4: Crearea graficului SaO2 (Tehnica Hibridă) ---
    # [WHY] Logăm stilurile aplicate pentru a depana ușor aspectul vizual.
    logger.debug(f"Aplicare stiluri DINAMICE: lățime linie={dynamic_line_width:.2f}, dimensiune marker={dynamic_marker_size:.2f}")

    # Urma 1: Linia de Bază (Robustețe la Zoom)
    line_params = {
        'x': df_slice.index,
        'y': df_slice['SpO2'],
        'mode': 'lines',
        'showlegend': False,
        'line': dict(width=dynamic_line_width), # <-- Folosește valoarea DINAMICĂ
        'marker': dict(
            color=df_slice['SpO2'].values,
            colorscale=spo2_style['colorscale'],
            cmin=spo2_style['colorscale_min'],
            cmax=spo2_style['colorscale_max']
        ),
        'hoverinfo': 'none'
    }
    # [WHY] Logăm adăugarea urmei de bază, esențială pentru stabilitatea la zoom.
    logger.debug(f"Adăugare urmă de BAZĂ SaO2 (linie) cu {len(df_slice)} puncte.")
    fig.add_trace(go.Scattergl(line_params), row=1, col=2)


    # Urma 2: Markerii de Detaliu (Finețe Vizuală)
    marker_params = {
        'color': spo2_values,
        'colorscale': spo2_style['colorscale'],
        'cmin': spo2_style['colorscale_min'],
        'cmax': spo2_style['colorscale_max'],
        'size': dynamic_marker_size, # <-- Folosește valoarea DINAMICĂ
        'showscale': False
    }
    scatter_params = {
        'x': df_spo2_dense.index,
        'y': spo2_values,
        'mode': 'markers',
        'name': spo2_style['name'],
        'marker': marker_params,
        'hovertemplate': '<b>SaO2</b>: %{y:.1f}%<br><b>Timp</b>: %{x|%H:%M:%S}<extra></extra>'
    }
    # [WHY] Logăm adăugarea urmei de detaliu, responsabilă pentru aspectul fin.
    logger.debug(f"Adăugare urmă de DETALIU SaO2 (markeri) cu {len(spo2_values)} puncte.")
    fig.add_trace(go.Scattergl(scatter_params), row=1, col=2)

    # --- Pas 5: Crearea graficului Puls (Coloana 2, Rândul 2) ---
    # [WHY] Logăm adăugarea urmei secundare, specificând poziția.
    logger.debug("Adăugare urmă Puls în row=2, col=2.")
    fig.add_trace(go.Scattergl(
        x=df_slice.index,
        y=df_slice['Pulse Rate'],
        name=pulse_style['name'],
        mode='lines',
        line=dict(color=pulse_style['color'], width=pulse_style['width']),
        hovertemplate='<b>Puls</b>: %{y} bpm<br><b>Timp</b>: %{x|%H:%M:%S}<extra></extra>'
    ), row=2, col=2)

    # --- Pas 6: Stilul final și configurarea axelor multiple (VERSIUNEA FINALĂ) ---
    # [WHY] Logăm explicit că intrăm în etapa finală de stilizare a figurii.
    logger.debug("Inițiere Pas 6: Stilul final și configurarea axelor multiple.")

    start_time = df_slice.index.min().strftime('%H:%M:%S')
    end_time = df_slice.index.max().strftime('%H:%M:%S')
    record_date = df_slice.index.min().strftime('%d/%m/%Y')
    dynamic_title = f"Analiză Puls-Oximetrie: {record_date} (Interval: {start_time} - {end_time})"

    fig.update_layout(
        title=dict(text=dynamic_title, x=0.5, font_size=layout_style['title_font_size']),
        height=700,
        plot_bgcolor=layout_style['plot_bgcolor'],
        paper_bgcolor=layout_style['paper_bgcolor'],
        font=layout_style['font'],
        showlegend=True,
        legend=config.GOLDEN_STYLE['legend']
    )

    # Preluăm stilurile pentru axe
    spo2_axis_style = config.GOLDEN_STYLE['axes']['yaxis_spo2']
    pulse_axis_style = config.GOLDEN_STYLE['axes']['yaxis_pulse']
    xaxis_style = config.GOLDEN_STYLE['axes']['xaxis']

    # [WHY] Adăugăm un log pentru a verifica valoarea `dtick` preluată din config.
    logger.debug(f"Setare riglă axa Y (dtick): {spo2_axis_style.get('dtick')}")

    # Axa Y a legendei (heatmap) - ascundem complet orice element al axei
    fig.update_yaxes(
        row=1, col=1, 
        showticklabels=False, title_text="", showgrid=False, zeroline=False
    )

    # Axa Y a graficului SaO2 - AICI ESTE CORECȚIA CRITICĂ
    fig.update_yaxes(
        row=1, col=2,
        title_text=spo2_axis_style['title'], 
        range=spo2_axis_style['range'], 
        gridcolor=spo2_axis_style['gridcolor'],
        dtick=spo2_axis_style.get('dtick'),    # Aplicăm noua riglă
        showticklabels=True                   # CORECȚIE: Forțăm afișarea etichetelor
    )
    # Axa Y a pulsului
    fig.update_yaxes(
        row=2, col=2,
        title_text=pulse_axis_style['title'], 
        range=pulse_axis_style.get('range')
    )

    # Ascundem axele X inutile și o configurăm pe cea principală
    fig.update_xaxes(row=1, col=1, showticklabels=False, title_text="", showgrid=False, zeroline=False)
    fig.update_xaxes(row=1, col=2, showticklabels=False)
    fig.update_xaxes(
        row=2, col=2,
        title_text=xaxis_style['title'], 
        gridcolor=xaxis_style['gridcolor']
    )

    # [WHY] Log final care confirmă că toate setările au fost aplicate cu succes.
    logger.info("Figura finală a fost creată și stilizată cu toate corecțiile de layout și stil.")
    return fig


def apply_logo_to_image(image_path: str, doctor_id: str = "default") -> bool:
    """
    Aplică logo-ul medicului pe o imagine generată.
    
    Args:
        image_path: Calea către imaginea pe care să se aplice logo-ul
        doctor_id: ID-ul medicului (default: "default")
        
    Returns:
        bool: True dacă logo-ul a fost aplicat cu succes
    """
    try:
        import doctor_settings
        
        # Verificăm dacă trebuie să aplicăm logo-ul
        if not doctor_settings.should_apply_logo_to_images(doctor_id):
            logger.debug(f"Logo nu este activat pentru imagini (doctor {doctor_id})")
            return False
        
        # Încărcăm logo-ul
        logo_path = doctor_settings.get_doctor_logo_path(doctor_id)
        if not logo_path:
            logger.debug(f"Nu există logo pentru medicul {doctor_id}")
            return False
        
        # Deschidem imaginea de bază
        base_img = Image.open(image_path)
        base_width, base_height = base_img.size
        
        # Deschidem logo-ul
        logo_img = Image.open(logo_path)
        
        # Încărcăm setările
        settings = doctor_settings.load_doctor_settings(doctor_id)
        logo_position = settings.get('logo_position', 'top-right')
        logo_size_setting = settings.get('logo_size', 'medium')
        
        # Calculăm dimensiunea logo-ului (proporțional cu imaginea de bază)
        size_factors = {
            'small': 0.08,   # 8% din lățimea imaginii
            'medium': 0.12,  # 12% din lățimea imaginii
            'large': 0.18    # 18% din lățimea imaginii
        }
        
        max_logo_width = int(base_width * size_factors.get(logo_size_setting, 0.12))
        
        # Redimensionăm logo-ul menținând aspect ratio-ul
        logo_aspect_ratio = logo_img.width / logo_img.height
        new_logo_width = max_logo_width
        new_logo_height = int(new_logo_width / logo_aspect_ratio)
        
        # Dacă logo-ul e prea înalt, ajustăm după înălțime
        max_logo_height = int(base_height * 0.15)  # Max 15% din înălțimea imaginii
        if new_logo_height > max_logo_height:
            new_logo_height = max_logo_height
            new_logo_width = int(new_logo_height * logo_aspect_ratio)
        
        logo_img = logo_img.resize((new_logo_width, new_logo_height), Image.Resampling.LANCZOS)
        
        # Calculăm poziția
        margin = 20  # Margine în pixeli
        positions = {
            'top-right': (base_width - new_logo_width - margin, margin),
            'top-left': (margin, margin),
            'bottom-right': (base_width - new_logo_width - margin, base_height - new_logo_height - margin),
            'bottom-left': (margin, base_height - new_logo_height - margin)
        }
        
        position = positions.get(logo_position, positions['top-right'])
        
        # Convertim imaginea de bază în RGBA dacă nu e deja
        if base_img.mode != 'RGBA':
            base_img = base_img.convert('RGBA')
        
        # Convertim logo-ul în RGBA pentru transparență
        if logo_img.mode != 'RGBA':
            logo_img = logo_img.convert('RGBA')
        
        # Aplicăm logo-ul cu transparență
        base_img.paste(logo_img, position, logo_img)
        
        # Salvăm imaginea (convertim înapoi în RGB pentru JPEG)
        if image_path.lower().endswith('.jpg') or image_path.lower().endswith('.jpeg'):
            base_img = base_img.convert('RGB')
        
        base_img.save(image_path, optimize=True, quality=95)
        
        logger.info(f"✅ Logo aplicat pe imaginea: {image_path} (poziție: {logo_position}, dimensiune: {new_logo_width}x{new_logo_height})")
        return True
        
    except Exception as e:
        logger.error(f"Eroare la aplicarea logo-ului pe {image_path}: {e}", exc_info=True)
        return False


def apply_logo_to_figure(fig: go.Figure, doctor_id: str = "default") -> go.Figure:
    """
    Adaugă logo-ul medicului direct în figura Plotly (pentru grafice interactive).
    
    Args:
        fig: Figura Plotly
        doctor_id: ID-ul medicului (default: "default")
        
    Returns:
        go.Figure: Figura cu logo aplicat
    """
    try:
        import doctor_settings
        
        # Verificăm dacă trebuie să aplicăm logo-ul
        if not doctor_settings.should_apply_logo_to_images(doctor_id):
            return fig
        
        # Obținem logo-ul în format base64
        logo_base64 = doctor_settings.get_doctor_logo_base64(doctor_id)
        if not logo_base64:
            return fig
        
        # Încărcăm setările
        settings = doctor_settings.load_doctor_settings(doctor_id)
        logo_position = settings.get('logo_position', 'top-right')
        logo_size_setting = settings.get('logo_size', 'medium')
        
        # Configurăm dimensiunea logo-ului (ca proporție din grafic)
        size_configs = {
            'small': {'sizex': 0.08, 'sizey': 0.08},
            'medium': {'sizex': 0.12, 'sizey': 0.12},
            'large': {'sizex': 0.18, 'sizey': 0.18}
        }
        
        size_config = size_configs.get(logo_size_setting, size_configs['medium'])
        
        # Configurăm poziția (în coordonate relative 0-1)
        position_configs = {
            'top-right': {'xanchor': 'right', 'yanchor': 'top', 'x': 0.98, 'y': 0.98},
            'top-left': {'xanchor': 'left', 'yanchor': 'top', 'x': 0.02, 'y': 0.98},
            'bottom-right': {'xanchor': 'right', 'yanchor': 'bottom', 'x': 0.98, 'y': 0.02},
            'bottom-left': {'xanchor': 'left', 'yanchor': 'bottom', 'x': 0.02, 'y': 0.02}
        }
        
        position_config = position_configs.get(logo_position, position_configs['top-right'])
        
        # Adăugăm logo-ul ca imagine în layout
        fig.add_layout_image(
            dict(
                source=logo_base64,
                xref="paper",
                yref="paper",
                x=position_config['x'],
                y=position_config['y'],
                sizex=size_config['sizex'],
                sizey=size_config['sizey'],
                xanchor=position_config['xanchor'],
                yanchor=position_config['yanchor'],
                opacity=0.95,
                layer="above"
            )
        )
        
        logger.info(f"✅ Logo adăugat în figura Plotly (poziție: {logo_position})")
        return fig
        
    except Exception as e:
        logger.error(f"Eroare la adăugarea logo-ului în figura Plotly: {e}", exc_info=True)
        return fig