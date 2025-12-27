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
from typing import List, Dict

# Importăm modulele și configurațiile necesare
import config
from logger_setup import logger
from data_parser import parse_csv_data
from plot_generator import create_plot
from patient_links import generate_patient_link, add_recording
import batch_session_manager
from storage_service import upload_patient_csv

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

def process_associated_pdf(input_folder: str, csv_filename: str, device_number: str, token: str) -> bool:
    """
    Caută și procesează PDF-ul asociat unui CSV în același folder.
    
    Logica de matching:
    - Același device number (ex: "3539", "0331")
    - Format: "Checkme O2 {device}_*.pdf" sau similar
    
    Args:
        input_folder: Folder unde se caută PDF-ul
        csv_filename: Numele fișierului CSV (pentru referință)
        device_number: Numărul aparatului (ex: "3539")
        token: Token-ul pacientului pentru salvare
        
    Returns:
        bool: True dacă PDF găsit și procesat cu succes
    """
    try:
        # Listăm toate PDF-urile din folder
        pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
        
        if not pdf_files:
            logger.debug(f"Nu există PDF-uri în folderul {input_folder}")
            return False
        
        # Căutăm PDF cu același device number
        matching_pdf = None
        for pdf_file in pdf_files:
            # Verificăm dacă device_number apare în numele PDF-ului
            if device_number in pdf_file:
                matching_pdf = pdf_file
                break
        
        if not matching_pdf:
            logger.debug(f"Nu s-a găsit PDF asociat pentru device #{device_number}")
            return False
        
        # Avem PDF potrivit - procesăm
        pdf_path = os.path.join(input_folder, matching_pdf)
        logger.info(f"📄 Găsit PDF asociat: {matching_pdf} pentru device #{device_number}")
        
        # Citim PDF-ul
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        # Salvăm PDF-ul pentru pacient
        from patient_links import save_pdf_for_link, save_pdf_parsed_data
        saved_path = save_pdf_for_link(token, pdf_content, matching_pdf)
        
        if not saved_path:
            logger.error(f"Eroare la salvarea PDF-ului {matching_pdf}")
            return False
        
        # Parsăm PDF-ul
        try:
            from pdf_parser import parse_checkme_o2_report, PDF_SUPPORT
            
            if not PDF_SUPPORT:
                logger.warning("pdfplumber nu este instalat - skip parsing PDF")
                return True  # PDF salvat, dar nu parsat
            
            # Creăm fișier temporar pentru parsing
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(pdf_content)
                tmp_pdf_path = tmp_file.name
            
            try:
                # Parsăm PDF-ul
                parsed_data = parse_checkme_o2_report(tmp_pdf_path)
                
                # Salvăm datele parsate
                if save_pdf_parsed_data(token, saved_path, parsed_data):
                    logger.info(f"✅ PDF {matching_pdf} parsat și salvat pentru token {token[:8]}...")
                    return True
                else:
                    logger.warning(f"Eroare la salvarea datelor parsate pentru {matching_pdf}")
                    return False
                    
            finally:
                # Ștergem fișierul temporar
                if os.path.exists(tmp_pdf_path):
                    os.remove(tmp_pdf_path)
                    
        except Exception as parse_error:
            logger.error(f"Eroare la parsarea PDF {matching_pdf}: {parse_error}")
            return False  # Salvat dar nu parsat
        
    except Exception as e:
        logger.error(f"Eroare la procesarea PDF asociat: {e}", exc_info=True)
        return False


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

def run_batch_job(input_folder: str, output_folder: str, window_minutes: int, session_id: str = None) -> List[Dict]:
    """
    Execută procesul de generare în lot a imaginilor cu grafice.
    
    [NEW v4.0] Generează automat link-uri persistente pentru fiecare CSV procesat.
    [NEW v6.0] Tracking progres cu batch_session_manager pentru reluare automată.

    Args:
        input_folder (str): Calea către folderul care conține fișierele CSV.
        output_folder (str): Calea către folderul rădăcină unde vor fi salvate
                             rezultatele.
        window_minutes (int): Durata în minute a fiecărei "felii" de grafic.
        session_id (str, optional): UUID sesiune pentru tracking progres.
                             
    Returns:
        List[Dict]: Listă cu link-urile generate (token, device, date, etc.)
    """
    logger.info("=" * 50)
    logger.warning(f"🚀 [BATCH_TRACE_START] JOB STARTED | Input: {input_folder}")
    logger.info(f"Folder intrare: {input_folder}")
    logger.info(f"Folder ieșire: {output_folder}")
    logger.info(f"Durată fereastră: {window_minutes} minute")
    logger.info("=" * 50)
    
    generated_links = []  # Lista de link-uri generate

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
            
            # [NEW v6.0] Actualizăm status la "processing" pentru tracking
            if session_id:
                batch_session_manager.update_file_status(
                    session_id, 
                    file_name, 
                    "processing"
                )

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

                    # [v7.0 DEFENSIVE] Salvăm imaginea cu fallback graceful pentru Kaleido/Chrome
                    try:
                        fig.write_image(
                            image_full_path,
                            width=config.IMAGE_RESOLUTION['width'],
                            height=config.IMAGE_RESOLUTION['height']
                        )
                        logger.info(f"Salvat imaginea: {image_file_name}")
                        
                        # Aplicăm logo-ul medicului pe imagine (dacă este configurat)
                        try:
                            from plot_generator import apply_logo_to_image
                            apply_logo_to_image(image_full_path)
                        except Exception as logo_error:
                            logger.warning(f"Nu s-a putut aplica logo pe {image_file_name}: {logo_error}")
                            
                    except RuntimeError as kaleido_error:
                        # FALLBACK GRACEFUL: Kaleido necesită Chrome (lipsește din container)
                        if "Kaleido requires" in str(kaleido_error) or "Chrome" in str(kaleido_error):
                            logger.warning(
                                f"⚠️ Kaleido/Chrome indisponibil pentru {image_file_name}. "
                                f"Export imagini dezactivat. SOLUȚIE: Adaugă 'chromium' în nixpacks.toml"
                            )
                            logger.warning(f"Eroare Kaleido: {kaleido_error}")
                            
                            # CONTINUĂM procesarea fără imagini (graceful degradation)
                            # Link-ul pacient va funcționa cu grafice interactive HTML
                        else:
                            # Altă eroare runtime - re-raise
                            raise
                            
                    except Exception as img_error:
                        # Orice altă eroare la salvare imagine
                        logger.error(
                            f"❌ Eroare neașteptată la salvarea imaginii {image_file_name}: {img_error}",
                            exc_info=True
                        )
                        # CONTINUĂM procesarea (resilience)
                    
                    # Trecem la următoarea felie
                    current_slice_start = current_slice_end

                logger.info(f"Procesare finalizată pentru '{file_name}'. S-au generat {slice_count-1} imagini.")
                
                # [NEW v4.0] Generăm automat link persistent pentru acest CSV
                try:
                    # Extragem metadata pentru link
                    recording_date = record_start_time.strftime('%Y-%m-%d')
                    start_time_str = record_start_time.strftime('%H:%M')
                    end_time_str = record_end_time.strftime('%H:%M')
                    device_display_name = f"Checkme O2 #{device_number}"
                    
                    # Generăm link-ul cu metadata despre folderul de output
                    token = generate_patient_link(
                        device_name=device_display_name,
                        notes=f"Procesare automată batch - {file_name}",
                        recording_date=recording_date,
                        start_time=start_time_str,
                        end_time=end_time_str
                    )
                    
                    if token:
                        # Salvăm și calea folderului de output în metadata link-ului
                        from patient_links import load_patient_links, save_patient_links
                        links = load_patient_links()
                        if token in links:
                            links[token]['output_folder'] = file_output_folder_name
                            links[token]['output_folder_path'] = file_output_path
                            links[token]['images_count'] = slice_count - 1
                            links[token]['output_folder'] = file_output_folder_name
                            links[token]['output_folder_path'] = file_output_path
                            links[token]['images_count'] = slice_count - 1
                            links[token]['original_filename'] = file_name
                            
                            # [FIX TEAM] Upload CSV to R2 & Update Metadata
                            try:
                                r2_filename = f"recording_batch_{token[:8]}_{file_name}"
                                r2_url = upload_patient_csv(token, file_content, r2_filename)
                                if r2_url:
                                    logger.warning(f"☁️ [BATCH_R2_FIX] Uploaded CSV to R2: {r2_url}")
                                    links[token]['r2_url'] = r2_url
                                    links[token]['storage_type'] = 'r2'
                                    links[token]['csv_path'] = f"r2://{token}/csvs/{r2_filename}"
                                else:
                                    logger.warning(f"⚠️ [BATCH_R2_FIX] R2 Upload failed/disabled. Using local fallback.")
                                    links[token]['storage_type'] = 'local'
                            except Exception as r2_e:
                                logger.error(f"❌ [BATCH_R2_FIX] R2 Error: {r2_e}")
                                links[token]['storage_type'] = 'local'

                            save_patient_links(links)
                        
                        # [NEW v5.0] Căutăm și procesăm PDF asociat (același folder, același device)
                        try:
                            pdf_processed = process_associated_pdf(input_folder, file_name, device_number, token)
                            if pdf_processed:
                                logger.info(f"📄 PDF asociat procesat pentru {device_display_name}")
                        except Exception as pdf_error:
                            logger.warning(f"Nu s-a putut procesa PDF asociat pentru '{file_name}': {pdf_error}")
                        
                        generated_links.append({
                            "token": token,
                            "device_name": device_display_name,
                            "device_number": device_number,
                            "recording_date": recording_date,
                            "start_time": start_time_str,
                            "end_time": end_time_str,
                            "original_filename": file_name,
                            "output_folder": file_output_folder_name,
                            "images_count": slice_count - 1
                        })
                        logger.warning(f"🔗 [BATCH_TRACE_LINK] Link Generated: {token} | Device: {device_display_name}")
                        logger.warning(f"   - Output Folder: {file_output_folder_name}")
                        logger.warning(f"   - PDF Asoc: {pdf_processed}")
                        
                        # [NEW v6.0] Actualizăm status la "completed" pentru tracking
                        if session_id:
                            pdf_name = f"Checkme O2 {device_number}*.pdf" if pdf_processed else None
                            batch_session_manager.update_file_status(
                                session_id, 
                                file_name, 
                                "completed",
                                token=token,
                                pdf_associated=pdf_name
                            )
                    else:
                        logger.warning(f"Nu s-a putut genera link pentru '{file_name}'")
                        
                except Exception as link_error:
                    logger.error(f"Eroare la generarea link-ului pentru '{file_name}': {link_error}", exc_info=True)

            except ValueError as e:
                # Prindem erorile de la data_parser (ex: CSV invalid)
                logger.error(f"EROARE la procesarea fișierului '{file_name}': {e}. Se trece la următorul fișier.")
                
                # [NEW v6.0] Actualizăm status la "failed" pentru tracking
                if session_id:
                    batch_session_manager.update_file_status(
                        session_id, 
                        file_name, 
                        "failed",
                        error=str(e)
                    )
                    
            except Exception as e:
                # Prindem orice altă eroare neașteptată
                logger.critical(f"EROARE CRITICĂ neașteptată la procesarea fișierului '{file_name}': {e}", exc_info=True)
                
                # [NEW v6.0] Actualizăm status la "failed" pentru tracking
                if session_id:
                    batch_session_manager.update_file_status(
                        session_id, 
                        file_name, 
                        "failed",
                        error=str(e)
                    )

    except Exception as e:
        logger.critical(f"O eroare critică a oprit procesul de batch: {e}", exc_info=True)
    finally:
        logger.info("=" * 50)
        logger.info("PROCESUL DE PROCESARE ÎN LOT (BATCH) S-A FINALIZAT.")
        logger.info(f"🔗 Link-uri generate: {len(generated_links)}")
        logger.info("=" * 50)
    
    return generated_links