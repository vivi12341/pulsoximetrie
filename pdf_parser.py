# ==============================================================================
# pdf_parser.py (Parser Rapoarte Checkme O2)
# ------------------------------------------------------------------------------
# ROL: Parsează rapoartele PDF generate de dispozitivul Checkme O2
#      și extrage statistici și evenimente (SpO2, puls, desaturări)
#
# RESPECTĂ: .cursorrules - Privacy by Design (ZERO date personale în PDF)
# ==============================================================================

import os
import re
from typing import Dict, Optional, List
from datetime import datetime

from logger_setup import logger

try:
    import pdfplumber
    PDF_SUPPORT = True
    logger.info("✅ pdfplumber disponibil pentru parsing PDF")
except ImportError:
    PDF_SUPPORT = False
    logger.warning("⚠️ pdfplumber nu este instalat. Instalați cu: pip install pdfplumber")


def extract_pdf_text(pdf_path: str) -> str:
    """
    Extrage textul complet din PDF folosind pdfplumber.
    
    Args:
        pdf_path (str): Calea către fișierul PDF
        
    Returns:
        str: Textul complet extras din PDF
    """
    if not PDF_SUPPORT:
        raise ImportError("pdfplumber nu este instalat. Rulați: pip install pdfplumber")
    
    try:
        text_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
        
        full_text = "\n".join(text_content)
        logger.debug(f"Extras text din PDF: {len(full_text)} caractere")
        return full_text
        
    except Exception as e:
        logger.error(f"Eroare la extragerea textului din PDF: {e}", exc_info=True)
        raise


def parse_checkme_o2_report(pdf_path: str) -> Dict:
    """
    Parsează un raport PDF de la Checkme O2 și extrage datele structurate.
    
    FORMAT AȘTEPTAT (exemplu raport Checkme O2):
    ═══════════════════════════════════════
      RAPORT PULSOXIMETRIE - Checkme O2
    ═══════════════════════════════════════
    Aparat: Checkme O2 #3539
    Data: 7 octombrie 2025
    Ora start: 23:04:37
    Durată: 8h 23min
    
    STATISTICI:
    - SpO2 mediu: 94.2%
    - SpO2 minim: 87%
    - SpO2 maxim: 99%
    - Puls mediu: 72 bpm
    - Puls minim: 58 bpm
    - Puls maxim: 95 bpm
    
    EVENIMENTE DETECTATE:
    - Desaturări (SpO2 < 90%): 23 evenimente
    - Durată totală desaturări: 45 minute
    - Cea mai lungă desaturare: 3min 15s
    
    Args:
        pdf_path (str): Calea către fișierul PDF
        
    Returns:
        Dict: Date structurate extrase din PDF
        {
            "device_info": {"device_name": "...", "device_number": "..."},
            "recording_info": {"date": "...", "start_time": "...", "duration": "..."},
            "statistics": {"avg_spo2": 94.2, "min_spo2": 87, ...},
            "events": {"desaturations_count": 23, "total_duration": "45 minute", ...},
            "raw_text": "...",
            "interpretation": "..."
        }
    """
    logger.info(f"🔍 Parsare raport PDF: {os.path.basename(pdf_path)}")
    
    try:
        # Extragem textul complet
        text = extract_pdf_text(pdf_path)
        
        # Inițializăm structura de date
        report_data = {
            "device_info": {},
            "recording_info": {},
            "statistics": {},
            "events": {},
            "raw_text": text,
            "interpretation": "",
            "parsed_at": datetime.now().isoformat()
        }
        
        # === PARSING DEVICE INFO ===
        # Pattern: "Aparat: Checkme O2 #3539" sau "Device: Checkme O2 3539"
        device_match = re.search(r'(?:Aparat|Device)[:\s]+(?:Checkme\s*O2\s*)?[#\s]*(\d{4})', text, re.IGNORECASE)
        if device_match:
            device_number = device_match.group(1)
            report_data["device_info"]["device_number"] = device_number
            report_data["device_info"]["device_name"] = f"Checkme O2 #{device_number}"
            logger.debug(f"Device detectat: {device_number}")
        
        # === PARSING RECORDING INFO ===
        # Data
        date_patterns = [
            r'Data[:\s]+(\d{1,2}\s+\w+\s+\d{4})',  # "7 octombrie 2025"
            r'Date[:\s]+(\d{1,2}[\/-]\d{1,2}[\/-]\d{4})',  # "07/10/2025" sau "07-10-2025"
            r'Recording Date[:\s]+(\d{4}-\d{2}-\d{2})'  # "2025-10-07"
        ]
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                report_data["recording_info"]["date"] = date_match.group(1)
                logger.debug(f"Dată detectată: {date_match.group(1)}")
                break
        
        # Ora start
        time_patterns = [
            r'Ora\s+start[:\s]+(\d{1,2}:\d{2}(?::\d{2})?)',
            r'Start\s+time[:\s]+(\d{1,2}:\d{2}(?::\d{2})?)',
            r'Recording\s+start[:\s]+(\d{1,2}:\d{2}(?::\d{2})?)'
        ]
        for pattern in time_patterns:
            time_match = re.search(pattern, text, re.IGNORECASE)
            if time_match:
                report_data["recording_info"]["start_time"] = time_match.group(1)
                logger.debug(f"Ora start detectată: {time_match.group(1)}")
                break
        
        # Durată
        duration_match = re.search(r'Durat[ăa][:\s]+([\d\s]+h[\s]*[\d]*\s*min)', text, re.IGNORECASE)
        if duration_match:
            report_data["recording_info"]["duration"] = duration_match.group(1).strip()
            logger.debug(f"Durată detectată: {duration_match.group(1)}")
        
        # === PARSING STATISTICI SPO2 ===
        # SpO2 mediu
        spo2_avg_match = re.search(r'SpO2\s+medi[ue][:\s]+([\d.]+)\s*%?', text, re.IGNORECASE)
        if spo2_avg_match:
            report_data["statistics"]["avg_spo2"] = float(spo2_avg_match.group(1))
        
        # SpO2 minim
        spo2_min_match = re.search(r'SpO2\s+minim[:\s]+([\d.]+)\s*%?', text, re.IGNORECASE)
        if spo2_min_match:
            report_data["statistics"]["min_spo2"] = float(spo2_min_match.group(1))
        
        # SpO2 maxim
        spo2_max_match = re.search(r'SpO2\s+maxim[:\s]+([\d.]+)\s*%?', text, re.IGNORECASE)
        if spo2_max_match:
            report_data["statistics"]["max_spo2"] = float(spo2_max_match.group(1))
        
        # === PARSING STATISTICI PULS ===
        # Puls mediu
        pulse_avg_match = re.search(r'Puls\s+medi[ue][:\s]+([\d.]+)\s*(?:bpm)?', text, re.IGNORECASE)
        if pulse_avg_match:
            report_data["statistics"]["avg_pulse"] = float(pulse_avg_match.group(1))
        
        # Puls minim
        pulse_min_match = re.search(r'Puls\s+minim[:\s]+([\d.]+)\s*(?:bpm)?', text, re.IGNORECASE)
        if pulse_min_match:
            report_data["statistics"]["min_pulse"] = float(pulse_min_match.group(1))
        
        # Puls maxim
        pulse_max_match = re.search(r'Puls\s+maxim[:\s]+([\d.]+)\s*(?:bpm)?', text, re.IGNORECASE)
        if pulse_max_match:
            report_data["statistics"]["max_pulse"] = float(pulse_max_match.group(1))
        
        # === PARSING EVENIMENTE ===
        # Desaturări
        desat_count_match = re.search(r'Desatur[ăa]ri[^:]*:\s*(\d+)\s*evenimente', text, re.IGNORECASE)
        if desat_count_match:
            report_data["events"]["desaturations_count"] = int(desat_count_match.group(1))
        
        # Durată totală desaturări
        desat_duration_match = re.search(r'Durat[ăa]\s+total[ăa]\s+desatur[ăa]ri[:\s]+([\d\s]+(?:minute|min))', text, re.IGNORECASE)
        if desat_duration_match:
            report_data["events"]["total_desaturation_duration"] = desat_duration_match.group(1).strip()
        
        # Cea mai lungă desaturare
        longest_desat_match = re.search(r'Cea\s+mai\s+lung[ăa]\s+desaturare[:\s]+([\d\s]+min[\d\s]*s?)', text, re.IGNORECASE)
        if longest_desat_match:
            report_data["events"]["longest_desaturation"] = longest_desat_match.group(1).strip()
        
        # === PARSING INTERPRETARE AUTOMATĂ ===
        interp_match = re.search(r'INTERPRETARE\s+AUTOMAT[ĂA][:\s]+(.*?)(?:\n\n|═|$)', text, re.IGNORECASE | re.DOTALL)
        if interp_match:
            report_data["interpretation"] = interp_match.group(1).strip()
        
        # Log rezumat
        stats_count = len([v for v in report_data["statistics"].values() if v])
        events_count = len([v for v in report_data["events"].values() if v])
        logger.info(f"✅ PDF parsat cu succes: {stats_count} statistici, {events_count} evenimente")
        
        return report_data
        
    except Exception as e:
        logger.error(f"Eroare la parsarea raportului PDF: {e}", exc_info=True)
        # Returnăm structură goală cu eroarea
        return {
            "device_info": {},
            "recording_info": {},
            "statistics": {},
            "events": {},
            "raw_text": "",
            "interpretation": "",
            "error": str(e),
            "parsed_at": datetime.now().isoformat()
        }


def save_pdf_locally(pdf_file_content: bytes, filename: str, token: str, patient_data_dir: str = "patient_data") -> str:
    """
    Salvează PDF-ul local în folderul pacientului.
    
    Args:
        pdf_file_content (bytes): Conținutul binar al fișierului PDF
        filename (str): Numele original al fișierului
        token (str): Token-ul pacientului (pentru folder)
        patient_data_dir (str): Directorul rădăcină pentru datele pacienților
        
    Returns:
        str: Calea completă unde a fost salvat PDF-ul
    """
    try:
        # Creăm structura de directoare: patient_data/{token}/pdfs/
        patient_folder = os.path.join(patient_data_dir, token)
        pdfs_folder = os.path.join(patient_folder, "pdfs")
        os.makedirs(pdfs_folder, exist_ok=True)
        
        # Sanitizăm numele fișierului (eliminăm caractere periculoase)
        safe_filename = re.sub(r'[^\w\s\-\.]', '_', filename)
        
        # Calea completă
        pdf_path = os.path.join(pdfs_folder, safe_filename)
        
        # Salvăm fișierul
        with open(pdf_path, 'wb') as f:
            f.write(pdf_file_content)
        
        logger.info(f"📄 PDF salvat local: {pdf_path} ({len(pdf_file_content)} bytes)")
        return pdf_path
        
    except Exception as e:
        logger.error(f"Eroare la salvarea PDF-ului local: {e}", exc_info=True)
        raise


def pdf_to_base64(pdf_path: str) -> str:
    """
    Convertește un PDF în format base64 pentru afișare în iframe.
    
    Args:
        pdf_path (str): Calea către fișierul PDF
        
    Returns:
        str: PDF encodat în base64 (data URI)
    """
    try:
        import base64
        with open(pdf_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()
            base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
            return f"data:application/pdf;base64,{base64_pdf}"
    except Exception as e:
        logger.error(f"Eroare la convertirea PDF în base64: {e}", exc_info=True)
        return ""


def pdf_first_page_to_image(pdf_path: str, output_path: Optional[str] = None, dpi: int = 150) -> Optional[str]:
    """
    Convertește prima pagină a unui PDF în imagine PNG.
    
    Args:
        pdf_path (str): Calea către fișierul PDF
        output_path (str): Calea unde să salveze imaginea (opțional)
        dpi (int): Rezoluția imaginii (default: 150 dpi)
        
    Returns:
        str: Calea către imaginea generată sau None în caz de eroare
    """
    if not PDF_SUPPORT:
        logger.warning("pdfplumber nu este disponibil pentru conversie imagine")
        return None
    
    try:
        from PIL import Image
        import io
        
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) == 0:
                logger.warning(f"PDF-ul {pdf_path} nu conține pagini")
                return None
            
            # Extragem prima pagină
            first_page = pdf.pages[0]
            
            # Convertim în imagine (pdfplumber returnează PIL Image)
            img = first_page.to_image(resolution=dpi)
            
            # Salvăm imaginea
            if output_path is None:
                # Generăm un nume automat
                output_path = pdf_path.replace('.pdf', '_preview.png')
            
            img.save(output_path, format='PNG')
            logger.info(f"✅ Prima pagină PDF convertită în imagine: {output_path}")
            return output_path
            
    except Exception as e:
        logger.error(f"Eroare la convertirea PDF în imagine: {e}", exc_info=True)
        return None


def format_report_for_display(report_data: Dict) -> str:
    """
    Formatează datele parsate din PDF pentru afișare în UI (HTML-friendly).
    
    Args:
        report_data (Dict): Date parsate din PDF
        
    Returns:
        str: Text formatat pentru afișare
    """
    lines = []
    
    # Device info
    if report_data.get("device_info", {}).get("device_name"):
        lines.append(f"🔧 **{report_data['device_info']['device_name']}**")
        lines.append("")
    
    # Recording info
    if report_data.get("recording_info"):
        rec_info = report_data["recording_info"]
        if rec_info.get("date"):
            lines.append(f"📅 Data: {rec_info['date']}")
        if rec_info.get("start_time"):
            lines.append(f"🕐 Ora start: {rec_info['start_time']}")
        if rec_info.get("duration"):
            lines.append(f"⏱️ Durată: {rec_info['duration']}")
        lines.append("")
    
    # Statistics
    if report_data.get("statistics"):
        stats = report_data["statistics"]
        lines.append("📊 **STATISTICI:**")
        if stats.get("avg_spo2"):
            lines.append(f"- SpO2 mediu: {stats['avg_spo2']:.1f}%")
        if stats.get("min_spo2"):
            lines.append(f"- SpO2 minim: {stats['min_spo2']:.1f}%")
        if stats.get("max_spo2"):
            lines.append(f"- SpO2 maxim: {stats['max_spo2']:.1f}%")
        if stats.get("avg_pulse"):
            lines.append(f"- Puls mediu: {stats['avg_pulse']:.0f} bpm")
        if stats.get("min_pulse"):
            lines.append(f"- Puls minim: {stats['min_pulse']:.0f} bpm")
        if stats.get("max_pulse"):
            lines.append(f"- Puls maxim: {stats['max_pulse']:.0f} bpm")
        lines.append("")
    
    # Events
    if report_data.get("events"):
        events = report_data["events"]
        lines.append("⚠️ **EVENIMENTE DETECTATE:**")
        if events.get("desaturations_count"):
            lines.append(f"- Desaturări (SpO2 < 90%): {events['desaturations_count']} evenimente")
        if events.get("total_desaturation_duration"):
            lines.append(f"- Durată totală desaturări: {events['total_desaturation_duration']}")
        if events.get("longest_desaturation"):
            lines.append(f"- Cea mai lungă desaturare: {events['longest_desaturation']}")
        lines.append("")
    
    # Interpretation
    if report_data.get("interpretation"):
        lines.append("📝 **INTERPRETARE AUTOMATĂ:**")
        lines.append(report_data["interpretation"])
    
    return "\n".join(lines)


logger.info("✅ Modulul pdf_parser.py încărcat cu succes.")

