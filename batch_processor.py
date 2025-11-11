# ==============================================================================
# batch_processor.py (VERSIUNEA 3.0 - Nume Intuitiv Folder și Imagini)
# ------------------------------------------------------------------------------
# ROL: Conține motorul pentru procesarea în lot. Scanează un folder, citește
#      fiecare fișier CSV, îl "feliază" în intervale de timp definite și
#      salvează un grafic pentru fiecare felie ca imagine JPG.
#
# MOD DE UTILIZARE:
#   from batch_processor import run_batch_job
#   # Această funcție va fi apelată dintr-un callback Dash,
#   # ideal într-un proces/thread separat pentru a nu bloca interfața.
#   run_batch_job("cale/folder_intrare", "cale/folder_iesire", 30)
#
# MODIFICĂRI CHEIE (v3.0):
#  - [FEATURE] Nume imagini intuitive: "Aparat1442_00h25m-00h55m.jpg"
#  - [FEATURE] Nume folder intuitiv: "02mai2025_00h25-06h37_Aparat1442"
#  - [SMART] Detectare automată dacă testul continuă peste miezul nopții
#  - [UX] Format ușor citibil de orice utilizator (folder + imagini)
# ==============================================================================

import os
import re
import pandas as pd
from datetime import timedelta

# Importăm modulele și configurațiile necesare
import config
from logger_setup import logger
from data_parser import parse_csv_data
from plot_generator import create_plot

# --- Mapare Luni în Română ---
MONTH_NAMES_RO = {
    1: 'ian', 2: 'feb', 3: 'mar', 4: 'apr', 5: 'mai', 6: 'iun',
    7: 'iul', 8: 'aug', 9: 'sep', 10: 'oct', 11: 'nov', 12: 'dec'
}

def extract_device_number(filename: str) -> str:
    """
    Extrage numărul aparatului din numele fișierului.
    
    Args:
        filename (str): Numele fișierului CSV
        
    Returns:
        str: Numărul aparatului (ex: "1442")
    """
    device_number = None
    
    # Încercăm pattern "O2 XXXX" sau "O2_XXXX"
    match = re.search(r'O2[\s_]+(\d{4})', filename, re.IGNORECASE)
    if match:
        device_number = match.group(1)
    else:
        # Încercăm ultimele 4 cifre consecutive înainte de extensie sau underscore
        match = re.search(r'(\d{4})(?:_|\.|$)', filename)
        if match:
            device_number = match.group(1)
    
    if not device_number:
        logger.warning(f"Nu s-a putut extrage numărul aparatului din '{filename}'. Se folosește 'XXXX'.")
        device_number = "XXXX"
    
    return device_number

def generate_intuitive_folder_name(df: pd.DataFrame, original_filename: str) -> str:
    """
    Generează un nume de folder intuitiv și ușor citibil pentru utilizatori.
    
    FORMAT GENERAT:
    - Test într-o zi: "02mai2025_00h25-06h37_Aparat1442"
    - Test peste miezul nopții: "02mai2025_23h30-03mai_01h15_Aparat1443"
    
    Args:
        df (pd.DataFrame): DataFrame cu date parsate, cu index DatetimeIndex
        original_filename (str): Numele original al fișierului CSV
        
    Returns:
        str: Nume folder generat în format intuitiv
        
    Raises:
        ValueError: Dacă nu se poate extrage informația necesară
    """
    try:
        # [STEP 1] Extragem data/ora început și sfârșit din date
        start_time = df.index.min()
        end_time = df.index.max()
        
        logger.debug(f"Generare nume folder: Start={start_time}, End={end_time}")
        
        # [STEP 2] Extragem numărul aparatului din numele fișierului
        device_number = extract_device_number(original_filename)
        logger.debug(f"Număr aparat detectat: {device_number}")
        
        # [STEP 3] Formatăm data și ora de început
        start_day = start_time.day
        start_month = MONTH_NAMES_RO[start_time.month]
        start_year = start_time.year
        start_hour = start_time.hour
        start_minute = start_time.minute
        
        start_str = f"{start_day:02d}{start_month}{start_year}_{start_hour:02d}h{start_minute:02d}"
        
        # [STEP 4] Formatăm data și ora de sfârșit (inteligent)
        # Dacă testul s-a terminat în ACEEAȘI ZI, punem doar ora
        # Dacă testul s-a terminat în ALTĂ ZI, punem data completă + ora
        if start_time.date() == end_time.date():
            # Aceeași zi - doar ora
            end_str = f"{end_time.hour:02d}h{end_time.minute:02d}"
            logger.debug(f"Test în aceeași zi. End format: {end_str}")
        else:
            # Zi diferită - data + ora
            end_day = end_time.day
            end_month = MONTH_NAMES_RO[end_time.month]
            end_str = f"{end_day:02d}{end_month}_{end_time.hour:02d}h{end_time.minute:02d}"
            logger.debug(f"Test peste miezul nopții. End format: {end_str}")
        
        # [STEP 5] Asamblăm numele final
        folder_name = f"{start_str}-{end_str}_Aparat{device_number}"
        
        logger.info(f"Nume folder generat: '{folder_name}' (din '{original_filename}')")
        return folder_name
        
    except Exception as e:
        logger.error(f"Eroare la generarea numelui intuitiv pentru '{original_filename}': {e}", exc_info=True)
        # [FALLBACK] Dacă ceva merge greșit, folosim numele original fără extensie
        fallback_name = os.path.splitext(original_filename)[0]
        logger.warning(f"Se folosește numele fallback: '{fallback_name}'")
        return fallback_name

def generate_intuitive_image_name(df_slice: pd.DataFrame, device_number: str) -> str:
    """
    Generează un nume intuitiv pentru fișierele imagine salvate în batch.
    
    FORMAT GENERAT:
    - Aceeași zi: "Aparat1442_00h25m-00h55m.jpg"
    - Zile diferite: "Aparat1442_02mai_23h30m-03mai_01h15m.jpg"
    
    Args:
        df_slice (pd.DataFrame): DataFrame cu datele pentru felia curentă
        device_number (str): Numărul aparatului (ex: "1442")
        
    Returns:
        str: Numele fișierului imagine în format intuitiv
    """
    try:
        start_time = df_slice.index.min()
        end_time = df_slice.index.max()
        
        # Formatăm ora de început
        start_hour = f"{start_time.hour:02d}h{start_time.minute:02d}m"
        
        # Formatăm ora de sfârșit (cu sau fără dată)
        if start_time.date() == end_time.date():
            # Aceeași zi - doar ora
            end_hour = f"{end_time.hour:02d}h{end_time.minute:02d}m"
            image_name = f"Aparat{device_number}_{start_hour}-{end_hour}.jpg"
        else:
            # Zile diferite - includem datele
            start_day = start_time.day
            start_month = MONTH_NAMES_RO[start_time.month]
            end_day = end_time.day
            end_month = MONTH_NAMES_RO[end_time.month]
            end_hour = f"{end_time.hour:02d}h{end_time.minute:02d}m"
            
            image_name = f"Aparat{device_number}_{start_day:02d}{start_month}_{start_hour}-{end_day:02d}{end_month}_{end_hour}.jpg"
        
        logger.debug(f"Nume imagine generat: {image_name}")
        return image_name
        
    except Exception as e:
        logger.error(f"Eroare la generarea numelui imaginii: {e}", exc_info=True)
        # Fallback la formatul vechi
        start_str = df_slice.index.min().strftime('%Y%m%d_%H%M%S')
        end_str = df_slice.index.max().strftime('%H%M%S')
        return f"grafic_{start_str}_pana_la_{end_str}.jpg"

def run_batch_job(input_folder: str, output_folder: str, window_minutes: int):
    """
    Execută procesul de generare în lot a imaginilor cu grafice.

    Args:
        input_folder (str): Calea către folderul care conține fișierele CSV.
        output_folder (str): Calea către folderul rădăcină unde vor fi salvate
                             rezultatele.
        window_minutes (int): Durata în minute a fiecărei "felii" de grafic.
    """
    logger.info("=" * 50)
    logger.info("A ÎNCEPUT PROCESUL DE PROCESARE ÎN LOT (BATCH).")
    logger.info(f"Folder intrare: {input_folder}")
    logger.info(f"Folder ieșire: {output_folder}")
    logger.info(f"Durată fereastră: {window_minutes} minute")
    logger.info("=" * 50)

    try:
        # Validăm existența folderului de intrare
        if not os.path.isdir(input_folder):
            logger.error(f"Folderul de intrare '{input_folder}' nu există sau nu este un director.")
            return

        # Listăm doar fișierele CSV
        try:
            csv_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.csv')]
            if not csv_files:
                logger.warning(f"Niciun fișier .csv găsit în folderul de intrare '{input_folder}'.")
                return
        except OSError as e:
            logger.error(f"Nu s-a putut accesa conținutul folderului de intrare '{input_folder}'. Motiv: {e}")
            return

        logger.info(f"S-au găsit {len(csv_files)} fișiere CSV pentru procesare.")

        # Iterăm prin fiecare fișier CSV găsit
        for file_name in csv_files:
            file_path = os.path.join(input_folder, file_name)
            logger.info(f"--- Procesare fișier: {file_name} ---")

            try:
                # Citim conținutul fișierului
                with open(file_path, 'rb') as f:
                    file_content = f.read()

                # Parsăm și validăm datele folosind modulul dedicat
                df = parse_csv_data(file_content, file_name)

                # [v2.0] Creăm un sub-folder dedicat cu nume intuitiv bazat pe date și aparat
                file_output_folder_name = generate_intuitive_folder_name(df, file_name)
                file_output_path = os.path.join(output_folder, file_output_folder_name)
                os.makedirs(file_output_path, exist_ok=True)
                logger.info(f"Folderul de ieșire pentru acest fișier a fost creat la: '{file_output_path}'")
                
                # Extragem numărul aparatului pentru numele imaginilor
                device_number = extract_device_number(file_name)

                # Logica de "feliere"
                record_start_time = df.index.min()
                record_end_time = df.index.max()
                time_window = timedelta(minutes=window_minutes)
                
                current_slice_start = record_start_time
                slice_count = 0

                while current_slice_start < record_end_time:
                    slice_count += 1
                    current_slice_end = current_slice_start + time_window
                    
                    # Selectăm datele pentru felia curentă
                    df_slice = df[(df.index >= current_slice_start) & (df.index < current_slice_end)]

                    if df_slice.empty:
                        logger.warning(f"Felia {slice_count} ({current_slice_start.time()} - {current_slice_end.time()}) nu conține date. Se omite.")
                        current_slice_start = current_slice_end
                        continue
                    
                    # Generăm graficul pentru felie
                    fig = create_plot(df_slice, file_name)

                    # [v3.0] Creăm un nume de fișier intuitiv și ușor citibil
                    image_file_name = generate_intuitive_image_name(df_slice, device_number)
                    image_full_path = os.path.join(file_output_path, image_file_name)

                    # Salvăm imaginea
                    fig.write_image(
                        image_full_path,
                        width=config.IMAGE_RESOLUTION['width'],
                        height=config.IMAGE_RESOLUTION['height']
                    )
                    logger.info(f"Salvat imaginea: {image_file_name}")
                    
                    # Trecem la următoarea felie
                    current_slice_start = current_slice_end

                logger.info(f"Procesare finalizată pentru '{file_name}'. S-au generat {slice_count-1} imagini.")

            except ValueError as e:
                # Prindem erorile de la data_parser (ex: CSV invalid)
                logger.error(f"EROARE la procesarea fișierului '{file_name}': {e}. Se trece la următorul fișier.")
            except Exception as e:
                # Prindem orice altă eroare neașteptată
                logger.critical(f"EROARE CRITICĂ neașteptată la procesarea fișierului '{file_name}': {e}", exc_info=True)

    except Exception as e:
        logger.critical(f"O eroare critică a oprit procesul de batch: {e}", exc_info=True)
    finally:
        logger.info("=" * 50)
        logger.info("PROCESUL DE PROCESARE ÎN LOT (BATCH) S-A FINALIZAT.")
        logger.info("=" * 50)