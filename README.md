# Pulsoximetrie — platformă medicală (Dash)

**Pornire:** `python run_medical.py` sau `start_server.bat` / `start_server_medical.bat`  
**Producție (Gunicorn):** `wsgi:application` (vezi `railway.json`, `Procfile`, `nixpacks.toml`)

Documentație istorică și rapoarte: [docs/rapoarte/](docs/rapoarte/)  
Prompturi workflow: [docs/Prompts_si_Workflows/](docs/Prompts_si_Workflows/)

Arhitectură: pachete `shared/`, `ui/`, `callbacks/`, `repositories/`, `services/`, `auth/`.
