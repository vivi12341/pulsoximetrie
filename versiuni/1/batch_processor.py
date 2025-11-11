# ==============================================================================
# batch_processor.py
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
# ==============================================================================

import os
import pandas as pd
from datetime import timedelta

# Importăm modulele și configurațiile necesare
import config
from logger_setup import logger
from data_parser import parse_csv_data
from plot_generator import create_plot

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

                # Creăm un sub-folder dedicat pentru imaginile acestui fișier
                file_output_folder_name = os.path.splitext(file_name)[0]
                file_output_path = os.path.join(output_folder, file_output_folder_name)
                os.makedirs(file_output_path, exist_ok=True)
                logger.info(f"Folderul de ieșire pentru acest fișier a fost creat la: '{file_output_path}'")

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

                    # Creăm un nume de fișier descriptiv pentru imagine
                    start_str = df_slice.index.min().strftime('%Y%m%d_%H%M%S')
                    end_str = df_slice.index.max().strftime('%H%M%S')
                    image_file_name = f"grafic_{start_str}_pana_la_{end_str}.jpg"
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