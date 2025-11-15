# 🔄 Migrare Stocare Locală → Cloudflare R2

## 📋 Ce Trebuie Modificat

Aplicația actuală folosește stocare **LOCALĂ** (`patient_data/`). Trebuie să migrăm la **Cloudflare R2** pentru persistență pe Railway.

---

## 🗂️ Fișiere Care Trebuie Modificate

### ✅ 1. `patient_links.py` - Salvare CSV-uri

**Funcție afectată:** `add_recording()`

**Înainte (local):**
```python
# Salvăm CSV-ul local
csv_folder = os.path.join(patient_folder, "csvs")
os.makedirs(csv_folder, exist_ok=True)
csv_path = os.path.join(csv_folder, csv_filename)

with open(csv_path, 'wb') as f:
    f.write(csv_content)
```

**După (R2):**
```python
from storage_service import upload_patient_csv

# Uploadăm CSV în R2
csv_url = upload_patient_csv(
    token=token,
    csv_content=csv_content,
    filename=csv_filename
)

if not csv_url:
    logger.error("Eroare la upload CSV în R2")
    return False
```

---

### ✅ 2. `pdf_parser.py` - Salvare PDF-uri

**Funcție afectată:** `save_pdf_locally()`

**Înainte (local):**
```python
def save_pdf_locally(pdf_file_content: bytes, filename: str, token: str, 
                     patient_data_dir: str = "patient_data") -> str:
    patient_folder = os.path.join(patient_data_dir, token)
    pdfs_folder = os.path.join(patient_folder, "pdfs")
    os.makedirs(pdfs_folder, exist_ok=True)
    
    pdf_path = os.path.join(pdfs_folder, safe_filename)
    
    with open(pdf_path, 'wb') as f:
        f.write(pdf_file_content)
    
    return pdf_path
```

**După (R2):**
```python
from storage_service import upload_patient_pdf

def save_pdf_to_storage(pdf_file_content: bytes, filename: str, token: str) -> str:
    """
    Salvează PDF în R2 (sau local ca fallback).
    
    Returns:
        str: URL sau calea către PDF
    """
    pdf_url = upload_patient_pdf(
        token=token,
        pdf_content=pdf_file_content,
        filename=filename
    )
    
    if not pdf_url:
        logger.error("Eroare la upload PDF în R2")
        raise Exception("Failed to upload PDF")
    
    return pdf_url
```

---

### ✅ 3. `callbacks_medical.py` - Salvare Grafice PNG

**Context:** După generarea graficului Plotly, salvăm ca PNG

**Înainte (local):**
```python
# Exportăm graficul ca PNG
plot_folder = os.path.join(patient_folder, "plots")
os.makedirs(plot_folder, exist_ok=True)
plot_filename = f"plot_{recording_date}.png"
plot_path = os.path.join(plot_folder, plot_filename)

fig.write_image(plot_path, format='png', width=1280, height=720)
```

**După (R2):**
```python
from storage_service import upload_patient_plot

# Exportăm graficul ca bytes (nu fișier)
plot_bytes = fig.to_image(format='png', width=1280, height=720)

# Uploadăm în R2
plot_url = upload_patient_plot(
    token=token,
    plot_content=plot_bytes,
    filename=f"plot_{recording_date}.png"
)

if not plot_url:
    logger.error("Eroare la upload grafic PNG în R2")
```

---

### ✅ 4. `app_instance.py` - Servire Fișiere pentru Pacient

**Funcție afectată:** `serve_patient_resource()`

**Înainte (local - Flask send_from_directory):**
```python
@app.server.route('/patient/<token>/<resource_type>/<filename>')
def serve_patient_resource(token, resource_type, filename):
    patient_folder = os.path.join(PATIENT_DATA_DIR, token, resource_type)
    return send_from_directory(patient_folder, filename)
```

**După (R2 - redirect sau stream):**
```python
from storage_service import download_patient_file

@app.server.route('/patient/<token>/<resource_type>/<filename>')
def serve_patient_resource(token, resource_type, filename):
    """
    Servește fișiere pacient din R2 (sau local fallback).
    """
    # Descarcă fișierul din R2
    file_content = download_patient_file(
        token=token,
        file_type=resource_type,  # 'csvs', 'pdfs', 'plots'
        filename=filename
    )
    
    if not file_content:
        return "Fișier inexistent", 404
    
    # Determină MIME type
    mime_types = {
        'csvs': 'text/csv',
        'pdfs': 'application/pdf',
        'plots': 'image/png'
    }
    mime_type = mime_types.get(resource_type, 'application/octet-stream')
    
    # Trimite fișierul ca răspuns
    from flask import Response
    return Response(
        file_content,
        mimetype=mime_type,
        headers={'Content-Disposition': f'inline; filename="{filename}"'}
    )
```

**ALTERNATIV (mai eficient - redirect către R2 signed URL):**
```python
from storage_service import r2_client

@app.server.route('/patient/<token>/<resource_type>/<filename>')
def serve_patient_resource(token, resource_type, filename):
    """
    Redirect către URL signed R2 (mai eficient - fără trafic prin Railway).
    """
    key = f"{token}/{resource_type}/{filename}"
    
    # Generăm URL signed (expiră în 1 oră)
    signed_url = r2_client.generate_presigned_url(key, expiration=3600)
    
    if not signed_url:
        return "Fișier inexistent", 404
    
    # Redirect către R2
    from flask import redirect
    return redirect(signed_url)
```

---

### ✅ 5. `callbacks_medical.py` - Încărcare CSV pentru Grafic

**Context:** Când pacientul accesează link-ul, încărcăm CSV pentru grafic

**Înainte (local):**
```python
csv_folder = os.path.join(patient_folder, "csvs")
if os.path.exists(csv_folder):
    csv_files = [f for f in os.listdir(csv_folder) if f.endswith('.csv')]
    if csv_files:
        csv_path = os.path.join(csv_folder, csv_files[0])
        df = data_parser.parse_csv_from_path(csv_path)
```

**După (R2):**
```python
from storage_service import list_patient_files, download_patient_file

# Listăm CSV-urile pacientului
csv_files = list_patient_files(token, file_type='csvs')

if csv_files:
    # Descarcăm primul CSV
    csv_key = csv_files[0]
    csv_filename = csv_key.split('/')[-1]  # Extragem numele din key
    
    csv_content = download_patient_file(token, 'csvs', csv_filename)
    
    if csv_content:
        # Parsăm CSV din bytes
        import io
        df = data_parser.parse_csv(io.BytesIO(csv_content))
```

---

## 🔄 Plan de Migrare Completă

### Faza 1: Pregătire (5 minute)
- [x] Creați cont Cloudflare
- [x] Activați R2 și creați bucket `pulsoximetrie-files`
- [x] Generați API token și salvați credențialele
- [x] Adăugați variabile R2 în Railway

### Faza 2: Instalare Dependințe (auto)
- [x] Adăugat `boto3==1.34.144` în `requirements.txt`
- [x] Creat modul `storage_service.py`
- [ ] Railway redeploy automat (după commit)

### Faza 3: Modificări Cod (30 minute)
- [ ] Modifică `patient_links.py` - funcția `add_recording()`
- [ ] Modifică `pdf_parser.py` - funcția `save_pdf_locally()` → `save_pdf_to_storage()`
- [ ] Modifică `callbacks_medical.py` - salvare grafice PNG
- [ ] Modifică `app_instance.py` - servire fișiere pacient
- [ ] Modifică `callbacks_medical.py` - încărcare CSV pentru grafic

### Faza 4: Testing (10 minute)
- [ ] Test upload CSV → verifică în R2 Dashboard
- [ ] Test generare link pacient → verifică că graficul se încarcă
- [ ] Test download PDF → verifică că se descarcă corect
- [ ] Test ștergere înregistrare (opțional)

### Faza 5: Cleanup (opțional)
- [ ] Șterge folderul local `patient_data/` (dacă nu mai e folosit)
- [ ] Actualizează `.gitignore` dacă e necesar

---

## 🎯 Avantaje După Migrare

✅ **Persistență:** Fișierele NU dispar la redeploy Railway  
✅ **Scalabilitate:** 10GB → nelimitat (upgrade ușor)  
✅ **Performance:** Cloudflare CDN global (download rapid)  
✅ **Backup:** Replicate automate pe multiple locații  
✅ **Costuri:** €0 primele 6-12 luni  
✅ **GDPR:** Compatibil cu legislația medicală EU  

---

## 🐛 Troubleshooting Post-Migrare

### Fișierele vechi (din perioada locală) nu se încarcă
**Soluție:** Migrează manual fișierele locale → R2:

```python
# Script migrare patient_data/ → R2
from storage_service import r2_client
import os

local_dir = "patient_data"

for token_folder in os.listdir(local_dir):
    token_path = os.path.join(local_dir, token_folder)
    
    if not os.path.isdir(token_path):
        continue
    
    # Migrează CSV-uri
    csv_folder = os.path.join(token_path, "csvs")
    if os.path.exists(csv_folder):
        for csv_file in os.listdir(csv_folder):
            csv_path = os.path.join(csv_folder, csv_file)
            with open(csv_path, 'rb') as f:
                content = f.read()
            
            key = f"{token_folder}/csvs/{csv_file}"
            r2_client.upload_file(content, key, 'text/csv')
            print(f"✅ Migrat: {key}")
    
    # Repetă pentru PDFs și plots...
```

### Aplicația încearcă să acceseze fișiere local
**Cauză:** Cod vechi care nu folosește `storage_service.py`

**Soluție:** Verifică că toate funcțiile folosesc modulul `storage_service` în loc de `os.path` + `open()`

---

**Data ultimei actualizări:** 15 Noiembrie 2025  
**Status:** ✅ Ghid complet de migrare pregătit


