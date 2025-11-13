# ==============================================================================
# doctor_settings.py
# ------------------------------------------------------------------------------
# ROL: Gestionează setările personalizate ale medicilor:
#      - Logo personalizat (aplicat pe imagini, PDF, grafice)
#      - Informații footer (afișate în josul paginii)
#
# RESPECTĂ: .cursorrules - Privacy by Design, Logging comprehensiv
# ==============================================================================

import os
import json
import base64
from datetime import datetime
from typing import Dict, Optional
from logger_setup import logger
from PIL import Image
import io

# --- Configurare Căi ---
DOCTOR_SETTINGS_DIR = "doctor_settings"
DEFAULT_DOCTOR_ID = "default"  # ID implicit pentru medic (poate fi extins pentru multi-medic)

# Creăm directorul de bază la import
os.makedirs(DOCTOR_SETTINGS_DIR, exist_ok=True)


# ==============================================================================
# FUNCȚII CORE - GESTIONARE SETĂRI DOCTOR
# ==============================================================================

def get_doctor_folder(doctor_id: str = DEFAULT_DOCTOR_ID) -> str:
    """
    Returnează calea către folderul de setări al medicului.
    
    Args:
        doctor_id: ID-ul medicului (default: "default")
        
    Returns:
        str: Cale absolută către folderul medicului
    """
    folder_path = os.path.join(DOCTOR_SETTINGS_DIR, doctor_id)
    os.makedirs(folder_path, exist_ok=True)
    return folder_path


def get_settings_file(doctor_id: str = DEFAULT_DOCTOR_ID) -> str:
    """
    Returnează calea către fișierul de setări JSON al medicului.
    
    Args:
        doctor_id: ID-ul medicului
        
    Returns:
        str: Cale către settings.json
    """
    return os.path.join(get_doctor_folder(doctor_id), "settings.json")


def load_doctor_settings(doctor_id: str = DEFAULT_DOCTOR_ID) -> Dict:
    """
    Încarcă setările medicului din fișierul JSON.
    
    Args:
        doctor_id: ID-ul medicului
        
    Returns:
        Dict: Setările medicului sau dict gol dacă nu există
    """
    settings_file = get_settings_file(doctor_id)
    
    if not os.path.exists(settings_file):
        logger.debug(f"Fișierul de setări pentru medicul '{doctor_id}' nu există. Se returnează setări implicite.")
        return {
            "footer_info": "",
            "logo_filename": None,
            "logo_uploaded_at": None,
            "apply_logo_to_images": True,
            "apply_logo_to_pdf": True,
            "apply_logo_to_site": True,
            "logo_position": "top-right",  # top-right, top-left, bottom-right, bottom-left
            "logo_size": "medium",  # small, medium, large
            "created_at": datetime.now().isoformat(),
            "updated_at": None
        }
    
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            logger.debug(f"Setări încărcate pentru medicul '{doctor_id}'.")
            return settings
    except Exception as e:
        logger.error(f"Eroare la încărcarea setărilor pentru medicul '{doctor_id}': {e}", exc_info=True)
        return {}


def save_doctor_settings(settings: Dict, doctor_id: str = DEFAULT_DOCTOR_ID) -> bool:
    """
    Salvează setările medicului în fișierul JSON.
    
    Args:
        settings: Dicționar cu setări
        doctor_id: ID-ul medicului
        
    Returns:
        bool: True dacă salvarea a reușit
    """
    settings_file = get_settings_file(doctor_id)
    
    try:
        # Actualizăm timestamp-ul
        settings['updated_at'] = datetime.now().isoformat()
        
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✅ Setări salvate pentru medicul '{doctor_id}'.")
        return True
    except Exception as e:
        logger.error(f"Eroare la salvarea setărilor pentru medicul '{doctor_id}': {e}", exc_info=True)
        return False


# ==============================================================================
# FUNCȚII LOGO - GESTIONARE LOGO PERSONALIZAT
# ==============================================================================

def save_doctor_logo(logo_content: bytes, logo_filename: str, doctor_id: str = DEFAULT_DOCTOR_ID) -> Optional[str]:
    """
    Salvează logo-ul medicului și actualizează setările.
    
    Args:
        logo_content: Conținutul binar al imaginii logo
        logo_filename: Numele original al fișierului
        doctor_id: ID-ul medicului
        
    Returns:
        str: Calea către logo salvat sau None dacă eroare
    """
    try:
        doctor_folder = get_doctor_folder(doctor_id)
        
        # Determinăm extensia fișierului
        _, ext = os.path.splitext(logo_filename)
        if not ext:
            ext = '.png'  # Extensie implicită
        
        # Salvăm cu nume standardizat
        logo_path = os.path.join(doctor_folder, f"logo{ext}")
        
        # Validăm că este o imagine validă
        try:
            img = Image.open(io.BytesIO(logo_content))
            # Opțional: redimensionăm pentru a optimiza spațiul
            max_size = (800, 800)  # Dimensiune maximă rezonabilă
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Salvăm imaginea optimizată
            img.save(logo_path, optimize=True, quality=95)
            
            logger.info(f"✅ Logo salvat pentru medicul '{doctor_id}': {logo_path} ({img.size[0]}x{img.size[1]}px)")
            
        except Exception as img_error:
            logger.error(f"Imaginea nu este validă: {img_error}", exc_info=True)
            return None
        
        # Actualizăm setările
        settings = load_doctor_settings(doctor_id)
        settings['logo_filename'] = f"logo{ext}"
        settings['logo_uploaded_at'] = datetime.now().isoformat()
        
        if save_doctor_settings(settings, doctor_id):
            return logo_path
        else:
            return None
            
    except Exception as e:
        logger.error(f"Eroare la salvarea logo-ului pentru medicul '{doctor_id}': {e}", exc_info=True)
        return None


def get_doctor_logo_path(doctor_id: str = DEFAULT_DOCTOR_ID) -> Optional[str]:
    """
    Returnează calea către logo-ul medicului.
    
    Args:
        doctor_id: ID-ul medicului
        
    Returns:
        str: Cale absolută către logo sau None dacă nu există
    """
    settings = load_doctor_settings(doctor_id)
    logo_filename = settings.get('logo_filename')
    
    if not logo_filename:
        return None
    
    logo_path = os.path.join(get_doctor_folder(doctor_id), logo_filename)
    
    if os.path.exists(logo_path):
        return logo_path
    else:
        logger.warning(f"Logo specificat în setări nu există pe disk: {logo_path}")
        return None


def get_doctor_logo_base64(doctor_id: str = DEFAULT_DOCTOR_ID) -> Optional[str]:
    """
    Returnează logo-ul medicului în format base64 (pentru afișare în HTML).
    
    Args:
        doctor_id: ID-ul medicului
        
    Returns:
        str: String base64 cu prefixul data:image/... sau None
    """
    logo_path = get_doctor_logo_path(doctor_id)
    
    if not logo_path:
        return None
    
    try:
        with open(logo_path, 'rb') as f:
            logo_bytes = f.read()
        
        # Determinăm tipul MIME
        ext = os.path.splitext(logo_path)[1].lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.svg': 'image/svg+xml'
        }
        mime_type = mime_types.get(ext, 'image/png')
        
        # Encodăm în base64
        logo_base64 = base64.b64encode(logo_bytes).decode('utf-8')
        
        return f"data:{mime_type};base64,{logo_base64}"
        
    except Exception as e:
        logger.error(f"Eroare la citirea logo-ului pentru medicul '{doctor_id}': {e}", exc_info=True)
        return None


def delete_doctor_logo(doctor_id: str = DEFAULT_DOCTOR_ID) -> bool:
    """
    Șterge logo-ul medicului.
    
    Args:
        doctor_id: ID-ul medicului
        
    Returns:
        bool: True dacă ștergerea a reușit
    """
    try:
        logo_path = get_doctor_logo_path(doctor_id)
        
        if logo_path and os.path.exists(logo_path):
            os.remove(logo_path)
            logger.info(f"🗑️ Logo șters pentru medicul '{doctor_id}'.")
        
        # Actualizăm setările
        settings = load_doctor_settings(doctor_id)
        settings['logo_filename'] = None
        settings['logo_uploaded_at'] = None
        
        return save_doctor_settings(settings, doctor_id)
        
    except Exception as e:
        logger.error(f"Eroare la ștergerea logo-ului pentru medicul '{doctor_id}': {e}", exc_info=True)
        return False


# ==============================================================================
# FUNCȚII FOOTER - GESTIONARE INFORMAȚII FOOTER
# ==============================================================================

def update_footer_info(footer_text: str, doctor_id: str = DEFAULT_DOCTOR_ID) -> bool:
    """
    Actualizează informațiile de footer pentru medic.
    
    Args:
        footer_text: Textul pentru footer (poate include HTML)
        doctor_id: ID-ul medicului
        
    Returns:
        bool: True dacă actualizarea a reușit
    """
    try:
        settings = load_doctor_settings(doctor_id)
        settings['footer_info'] = footer_text
        settings['footer_updated_at'] = datetime.now().isoformat()
        
        if save_doctor_settings(settings, doctor_id):
            logger.info(f"📝 Footer actualizat pentru medicul '{doctor_id}' ({len(footer_text)} caractere).")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Eroare la actualizarea footer-ului pentru medicul '{doctor_id}': {e}", exc_info=True)
        return False


def get_footer_info(doctor_id: str = DEFAULT_DOCTOR_ID) -> str:
    """
    Preia informațiile de footer pentru medic.
    
    Args:
        doctor_id: ID-ul medicului
        
    Returns:
        str: Textul footer-ului sau string gol
    """
    settings = load_doctor_settings(doctor_id)
    return settings.get('footer_info', '')


def process_footer_links(footer_text: str):
    """
    Procesează footer-ul pentru a converti URL-urile și HTML în componente Dash.
    Suportă atât HTML explicit (<a href="...">) cât și auto-detectare URL-uri.
    
    Args:
        footer_text: Textul brut al footer-ului
        
    Returns:
        list: Lista de componente Dash (html.Span, html.A, html.Br)
    """
    import re
    from dash import html
    
    if not footer_text:
        return []
    
    components = []
    
    # Împărțim textul în linii (pentru a procesa \n ca <br>)
    lines = footer_text.split('\n')
    
    for line_idx, line in enumerate(lines):
        if not line.strip():
            # Linie goală - adăugăm un break
            if line_idx > 0:
                components.append(html.Br())
            continue
        
        # Pattern pentru detectarea link-urilor HTML existente
        html_link_pattern = r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>'
        
        # Pattern pentru URL-uri simple (fără tag <a>)
        url_pattern = r'(https?://[^\s<>"]+|www\.[^\s<>"]+)'
        
        # Pattern pentru numere de telefon (suportă format românesc și internațional)
        # Exemple: 0745603880, 0745 603 880, 0745-603-880, +40745603880, 07XX XXX XXX
        phone_pattern = r'(\+?\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}|\b0\d{9}\b)'
        
        # Găsim toate link-urile HTML din linie
        html_matches = list(re.finditer(html_link_pattern, line, re.IGNORECASE))
        
        if html_matches:
            # Procesăm linia cu link-uri HTML
            last_end = 0
            for match in html_matches:
                # Text înainte de link
                if match.start() > last_end:
                    text_before = line[last_end:match.start()]
                    if text_before:
                        components.append(html.Span(text_before))
                
                # Creăm link-ul
                url = match.group(1)
                text = match.group(2)
                components.append(
                    html.A(
                        text,
                        href=url,
                        target='_blank',
                        rel='noopener noreferrer',
                        style={
                            'color': '#3498db',
                            'textDecoration': 'underline',
                            'cursor': 'pointer'
                        }
                    )
                )
                last_end = match.end()
            
            # Text după ultimul link
            if last_end < len(line):
                text_after = line[last_end:]
                if text_after:
                    components.append(html.Span(text_after))
        else:
            # Nu există link-uri HTML - căutăm URL-uri și numere de telefon
            url_matches = list(re.finditer(url_pattern, line))
            phone_matches = list(re.finditer(phone_pattern, line))
            
            # Combinăm toate match-urile și le sortăm după poziție
            all_matches = []
            for match in url_matches:
                all_matches.append(('url', match))
            for match in phone_matches:
                all_matches.append(('phone', match))
            
            # Sortăm după poziția de start
            all_matches.sort(key=lambda x: x[1].start())
            
            if all_matches:
                last_end = 0
                for match_type, match in all_matches:
                    # Text înainte de match
                    if match.start() > last_end:
                        text_before = line[last_end:match.start()]
                        if text_before:
                            components.append(html.Span(text_before))
                    
                    if match_type == 'url':
                        # Creăm link pentru URL
                        url = match.group(0)
                        if url.startswith('www.'):
                            full_url = 'https://' + url
                        else:
                            full_url = url
                        
                        components.append(
                            html.A(
                                url,
                                href=full_url,
                                target='_blank',
                                rel='noopener noreferrer',
                                style={
                                    'color': '#3498db',
                                    'textDecoration': 'underline',
                                    'cursor': 'pointer'
                                }
                            )
                        )
                    elif match_type == 'phone':
                        # Creăm link pentru telefon
                        phone_number = match.group(0)
                        # Curățăm numărul de spații și caractere speciale pentru href
                        clean_phone = re.sub(r'[\s.-]', '', phone_number)
                        
                        components.append(
                            html.A(
                                phone_number,
                                href=f'tel:{clean_phone}',
                                style={
                                    'color': '#27ae60',
                                    'textDecoration': 'underline',
                                    'cursor': 'pointer',
                                    'fontWeight': 'bold'
                                }
                            )
                        )
                    
                    last_end = match.end()
                
                # Text după ultimul match
                if last_end < len(line):
                    text_after = line[last_end:]
                    if text_after:
                        components.append(html.Span(text_after))
            else:
                # Niciun link sau telefon - doar text simplu
                components.append(html.Span(line))
        
        # Adăugăm break după fiecare linie (exceptând ultima)
        if line_idx < len(lines) - 1:
            components.append(html.Br())
    
    return components


# ==============================================================================
# FUNCȚII APLICARE SETĂRI - VERIFICARE UNDE SE APLICĂ LOGO
# ==============================================================================

def update_logo_preferences(apply_to_images: bool = True, apply_to_pdf: bool = True, 
                           apply_to_site: bool = True, doctor_id: str = DEFAULT_DOCTOR_ID) -> bool:
    """
    Actualizează preferințele de aplicare a logo-ului.
    
    Args:
        apply_to_images: Aplică logo pe imaginile generate
        apply_to_pdf: Aplică logo pe documentele PDF
        apply_to_site: Afișează logo pe site (deasupra titlului)
        doctor_id: ID-ul medicului
        
    Returns:
        bool: True dacă actualizarea a reușit
    """
    try:
        settings = load_doctor_settings(doctor_id)
        settings['apply_logo_to_images'] = apply_to_images
        settings['apply_logo_to_pdf'] = apply_to_pdf
        settings['apply_logo_to_site'] = apply_to_site
        
        return save_doctor_settings(settings, doctor_id)
        
    except Exception as e:
        logger.error(f"Eroare la actualizarea preferințelor logo pentru medicul '{doctor_id}': {e}", exc_info=True)
        return False


def should_apply_logo_to_images(doctor_id: str = DEFAULT_DOCTOR_ID) -> bool:
    """Verifică dacă logo-ul trebuie aplicat pe imagini."""
    settings = load_doctor_settings(doctor_id)
    return settings.get('apply_logo_to_images', True) and get_doctor_logo_path(doctor_id) is not None


def should_apply_logo_to_pdf(doctor_id: str = DEFAULT_DOCTOR_ID) -> bool:
    """Verifică dacă logo-ul trebuie aplicat pe PDF."""
    settings = load_doctor_settings(doctor_id)
    return settings.get('apply_logo_to_pdf', True) and get_doctor_logo_path(doctor_id) is not None


def should_apply_logo_to_site(doctor_id: str = DEFAULT_DOCTOR_ID) -> bool:
    """Verifică dacă logo-ul trebuie afișat pe site."""
    settings = load_doctor_settings(doctor_id)
    return settings.get('apply_logo_to_site', True) and get_doctor_logo_path(doctor_id) is not None


# ==============================================================================
# INIȚIALIZARE
# ==============================================================================

# Creăm folderul de setări dacă nu există
os.makedirs(DOCTOR_SETTINGS_DIR, exist_ok=True)

# Creăm setările implicite pentru medicul default dacă nu există
if not os.path.exists(get_settings_file(DEFAULT_DOCTOR_ID)):
    default_settings = load_doctor_settings(DEFAULT_DOCTOR_ID)
    save_doctor_settings(default_settings, DEFAULT_DOCTOR_ID)
    logger.info(f"✅ Setări implicite create pentru medicul '{DEFAULT_DOCTOR_ID}'.")

logger.info("✅ Modulul doctor_settings.py inițializat cu succes.")

