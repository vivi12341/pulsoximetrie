# Arhitectura Actuală a Platformei de Pulsoximetrie

Acest document vizualizează structura, relațiile și fluxul de date din cadrul aplicației, așa cum sunt definite în codul sursă curent.

## 1. Diagrama de Ansamblu (High-Level Architecture)

Această diagramă arată cum componentele majore interacționează între ele.

```mermaid
graph TD
    %% Stiluri pentru noduri
    classDef entry fill:#f9f,stroke:#333,stroke-width:2px;
    classDef core fill:#bbf,stroke:#333,stroke-width:2px;
    classDef layout fill:#bfb,stroke:#333,stroke-width:2px;
    classDef logic fill:#fbb,stroke:#333,stroke-width:2px;
    classDef data fill:#ff9,stroke:#333,stroke-width:2px;
    classDef infra fill:#ddd,stroke:#333,stroke-width:2px;

    %% Clienti
    User[Utilizator (Browser)] -->|HTTP Request| Entry
    Admin[Medic (Browser)] -->|HTTP Request| Entry

    %% Entry Points
    subgraph "Application Core"
        Entry[run_medical.py]:::entry
        AppInstance[app_instance.py]:::core
    end

    %% Relatii Core
    Entry -->|Initializează| AppInstance
    Entry -->|Folosește| Auth[Modul Autentificare]:::logic
    Entry -->|Folosește| Layouts[Layout-uri Dash]:::layout
    Entry -->|Înregistrează| Callbacks[Callbacks & Logic]:::logic

    %% Layouts
    subgraph "Frontend Layer (Dash Layouts)"
        Layouts --> MainLayout[app_layout_new.py]
        MainLayout --> DocLayout[layout_partials/medical_layout.py]
        MainLayout --> PatLayout[layout_partials/patient_layout.py]
    end

    %% Logic Layer
    subgraph "Logic & Processing Layer"
        Callbacks --> MedCB[callbacks_medical.py]
        Callbacks --> AdminCB[admin_callbacks.py]
        MedCB --> BatchProc[batch_processor.py]:::logic
        BatchProc --> PlotGen[plot_generator.py]:::logic
        BatchProc --> PDFParse[pdf_parser.py]:::logic
    end

    %% Data Layer
    subgraph "Data & Services Layer"
        Auth --> Models[auth/models.py]:::data
        BatchProc --> Storage[storage_service.py]:::data
        MedCB --> Storage
        Models --> DB[(PostgreSQL / SQLite)]:::infra
        Storage --> LocalFS[("Local FS (patient_data)")]:::infra
        Storage -.->|Opțional| R2[("Cloudflare R2")]:::infra
    end
```

## 2. Diagrama Detaliată a Fișierelor și Interfețelor

Această diagramă detaliază exact conexiunile dintre fișierele Python ("ce zic fisierele ca fac").

```mermaid
classDiagram
    %% Core Files
    class RunMedical {
        +main()
        +init_db()
        +init_auth()
    }
    class AppInstance {
        +app: Dash
        +server: Flask
    }
    
    %% Relationships Core
    RunMedical ..> AppInstance : Imports app
    RunMedical ..> AuthManager : Initializes
    RunMedical ..> LayoutNew : Sets layout

    %% Layouts
    class LayoutNew {
        +layout: html.Div
    }
    class MedicalLayout {
        +get_medical_layout()
        +tab_batch
        +tab_settings
        +tab_view
    }
    class PatientLayout {
        +get_patient_layout()
    }

    LayoutNew ..> MedicalLayout : Imports
    LayoutNew ..> PatientLayout : Imports

    %% Logic / Callbacks
    class CallbacksMedical {
        +handle_navigation()
        +handle_batch_processing()
        +handle_file_upload()
    }
    class BatchProcessor {
        +process_batch_folder()
        +process_single_patient()
    }
    class AdminCallbacks {
        +manage_users()
        +generate_invite_links()
    }

    RunMedical ..> CallbacksMedical : Imports
    RunMedical ..> AdminCallbacks : Imports
    
    CallbacksMedical ..> BatchProcessor : Uses
    CallbacksMedical ..> StorageService : Uses
    CallbacksMedical ..> AppInstance : Uses app

    %% Services
    class StorageService {
        +upload_file()
        +download_file()
        +R2_Client
        +Local_Fallback
    }
    class PlotGenerator {
        +create_interactive_plot()
        +create_static_image()
    }
    
    BatchProcessor ..> StorageService : Saves files
    BatchProcessor ..> PlotGenerator : Generates charts
    BatchProcessor ..> PDFParser : Extracts data

    %% Data Models
    class AuthModels {
        +User
        +Doctor
        +PatientLink
    }
    
    AdminCallbacks ..> AuthModels : CRUD Ops
    CallbacksMedical ..> AuthModels : Queries
```

## 3. Legenda Structurii

*   **`run_medical.py`**: "Creierul" operațiunii. Leagă totul împreună: serverul web, baza de date, paginile (layout) și logica (callbacks).
*   **`app_instance.py`**: "Inima". Ține obiectul aplicației în viață pentru a fi accesat de oriunde fără a crea confuzie (circular imports).
*   **`layout_partials/`**: "Fața". Definește cum arată paginile (butoane, grafice, tab-uri).
    *   `medical_layout.py`: Interfața pentru doctori (complexă).
    *   `patient_layout.py`: Interfața pentru pacienți (simplă, vizualizare).
*   **`callbacks_medical.py`**: "Sistemul Nervos". Aici se întâmplă acțiunea când cineva dă click. Decide ce se procesează și ce se afișează.
*   **`storage_service.py`**: "Magazia". Se ocupă de păstrarea fișierelor. Dacă e setat, le trimite în Cloud (R2), dacă nu, le ține pe Disk (Local).
