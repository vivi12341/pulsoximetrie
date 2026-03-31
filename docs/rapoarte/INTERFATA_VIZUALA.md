# Interfața Vizuală a Aplicației (Harta Elementelor)

Acest document prezintă structura interfeței ("cu linii și puncte"), detaliind ecranele principale și elementele (butoane, texte, câmpuri) pentru referință rapidă.

## 1. Ecranul de Autentificare (Login)

Acesta este primul ecran pe care îl vede un medic neautentificat.

```text
+-------------------------------------------------------------+
|  📊 Platformă Pulsoximetrie                                 |
|                                                             |
|           +-------------------------------------+           |
|           |  🔒 Autentificare Necesară          |           |
|           |                                     |           |
|           |  Trebuie să te autentifici pentru   |           |
|           |  a accesa această funcționalitate.  |           |
|           |                                     |           |
|           |  [ 🔐 Autentifică-te Acum ] <------- (Buton)    |
|           |                                     |           |
|           +-------------------------------------+           |
|                                                             |
+-------------------------------------------------------------+
```

## 2. Dashboard Medic (Admin) - Layout Principal

Vizibil doar după autentificare. Include Header, Titlu și Tab-uri de navigare.

```text
+-----------------------------------------------------------------------------------------+
| [Header]                                                                                |
| 👨‍⚕️ Dr. Nume Prenume | email@doctor.com | 👑 ADMIN                                      |
|                                    [ ⚙️ Setări ]  [ 👋 Deconectare ]                      |
+-----------------------------------------------------------------------------------------+
|                                                                                         |
|                        📊 Platformă Pulsoximetrie  (Titlu H1)                           |
|                                                                                         |
|  [ TAB: 📁 Procesare Batch ]  [ TAB: ⚙️ Setări ]  [ TAB: 📊 Vizualizare Date ]           |
|                                                                                         |
|  (Conținutul se schimbă în funcție de tab-ul selectat mai jos)                          |
|                                                                                         |
+-----------------------------------------------------------------------------------------+
| [Footer]                                                                                |
| _______________________________________________________________________________________ |
| (Text Footer Personalizabil - ex: Dr. Popescu Ion...)                                   |
| 🔒 Platformă securizată conform GDPR - Date anonimizate by design                       |
+-----------------------------------------------------------------------------------------+
```

### 2.1. Tab: 📁 Procesare Batch (Default)

Aici se face upload și procesare fișiere.

```text
+---------------------------------------------------------------------------------------+
|  📁 Procesare Batch CSV + Generare Link-uri                                           |
|  Încărcați mai multe fișiere CSV + PDF simultan...                                    |
|                                                                                       |
|  +-- [Info Box] -------------------------------------------------------------------+  |
|  | 💡 Cum funcționează:                                                            |  |
|  | • Puneți CSV-uri + PDF-uri în același folder...                                 |  |
|  | • Sistemul procesează tot și generează link-uri persistente                     |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  🔧 Selectați modul de lucru:                                                         |
|  ( ) 📁 Mod Local (Folder pe disk)   (●) ☁️ Mod Online (Streaming Upload)             |
|                                                                                       |
|  +-- [Mod Online - Activ] ---------------------------------------------------------+  |
|  | 📤 Selectați fișiere CSV + PDF (Streaming):                                     |  |
|  | +-----------------------------------------------------------------------------+ |  |
|  | | [ Click sau Drop aici (CSV + PDF) - Suportă fișiere mari ] (Upload Component)| |  |
|  | +-----------------------------------------------------------------------------+ |  |
|  |                                                                                 |  |
|  | Note: Fișierele sunt salvate temporar pe server.                                |  |
|  | 📭 Așteptare fișiere... (Lista fișiere uploadate)                               |  |
|  |                                                                                 |  |
|  | [ 🗑️ Șterge toate fișierele ] (Buton Stergere - Ascuns initial)                 |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  📂 Folder ieșire imagini: [ .__Output_Default____ ] (Input)                          |
|                                                                                       |
|  ⏱️ Durată fereastră (minute): [ 60 ] (Input Numeric)                                 |
|                                                                                       |
|  [ 🚀 Pornește Procesare Batch + Generare Link-uri ] (BUTON PRINCIPAL ACȚIUNE)        |
|                                                                                       |
|  +-- [Progress Bar Container - Ascuns initial] ------------------------------------+  |
|  | 📊 Progres procesare: 0 / 0 fișiere                                             |  |
|  | [====================================] (Bară Progres)                           |  |
|  | (Status detaliat procesare...)                                                  |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  📜 Istoric Sesiuni Batch                                                             |
|  Ultimele sesiuni de procesare...                                                     |
|  (Listă sesiuni anterioare sau mesaj "Nu există sesiuni batch încă.")                 |
+---------------------------------------------------------------------------------------+
```

### 2.2. Tab: ⚙️ Setări

Configurare aspect și utilizatori.

```text
+---------------------------------------------------------------------------------------+
|  ⚙️ Setări Personalizare                                                              |
|                                                                                       |
|  +-- [ 🖼️ Sigla Cabinetului ] -----------------------------------------------------+  |
|  | Încărcați sigla cabinetului dumneavoastră.                                      |  |
|  | [ 📁 Click sau drag & drop logo aici ] (Upload Logo)                            |  |
|  |                                                                                 |  |
|  | 🎯 Unde să se aplice logo-ul:                                                   |  |
|  | [x] 🖼️ Pe imaginile generate                                                    |  |
|  | [x] 📄 Pe documentele PDF                                                       |  |
|  | [x] 🌐 Pe site (deasupra titlului)                                              |  |
|  |                                                                                 |  |
|  | [ 🗑️ Șterge Logo ] (Buton)                                                      |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +-- [ 📝 Informații Footer ] -----------------------------------------------------+  |
|  | 📄 Text footer:                                                                 |  |
|  | [ Textarea pentru footer (ex: Dr. Popescu...) ]                                 |  |
|  |                                                                                 |  |
|  | 👁️ Preview:                                                                    |  |
|  | (Footer-ul va apărea aici...)                                                   |  |
|  |                                                                                 |  |
|  | [ 💾 Salvează Footer ] (Buton)                                                  |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +-- [ 👥 Administrare Utilizatori ] ----------------------------------------------+  |
|  | [ ➕ Creare Utilizator Nou ]  [ 🔄 Reîmprospătează Lista ]                       |  |
|  |                                                                                 |  |
|  | (Lista Utilizatori se încarcă aici...)                                          |  |
|  +---------------------------------------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
```

### 2.3. Tab: 📊 Vizualizare Date

Vizualizare avansată a datelor pacienților.

```text
+---------------------------------------------------------------------------------------+
|  📊 Înregistrări Pacienți - Vizualizare Detaliată   [ 🔄 Reîmprospătează ]            |
|                                                                                       |
|  +-- [ 📅 Filtrare Cronologică ] --------------------------------------------------+  |
|  | ⚡ Acces Rapid:                                                                 |  |
|  | [📅 Azi] [⏮️ Ieri] [📆 1 Săptămână] [📅 1 Lună] [🗓️ 1 An]                     |  |
|  |                                                                                 |  |
|  | 🗓️ Interval Personalizat:                                                       |  |
|  | De la: [ Select Data ]  Până la: [ Select Data ]                                |  |
|  | [ 🔍 Filtrează ]   [ ❌ Resetare ]                                              |  |
|  | -----------------------------------------------------------------------------   |  |
|  | 📊 Grupare: ( ) 📅 Pe Zile  ( ) 📆 Pe Săptămâni  ( ) 🗓️ Pe Luni                 |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  (Aici apare Tabelul cu datele pacienților...)                                        |
|  (Click pe linie -> Detalii complete)                                                 |
|                                                                                       |
+---------------------------------------------------------------------------------------+
```

## 3. Ecranul Pacientului (Simplificat)

Acesta este ecranul pe care îl vede pacientul când accesează un link unic. Nu necesită login.

```text
+-------------------------------------------------------------+
|  (Logo Cabinet - Opțional)                                  |
|                                                             |
|  📊 Rezultate Pulsoximetrie  (Titlu)                        |
|  Vizualizați datele dumneavoastră rapid și simplu           |
|                                                             |
|  [ Date Pacient - Nume, Dată, Link-uri Descărcare ]         |
|                                                             |
|  +-- [Medical Card] -------------------------------------+  |
|  | 📈 Grafic Interactiv                                  |  |
|  | Folosiți mouse-ul pentru zoom și navigare.            |  |
|  |                                                       |  |
|  | [ ................................................. ] |  |
|  | [ ............ ZONA GRAFIC PLOTLY ................. ] |  |
|  | [ ................................................. ] |  |
|  +-------------------------------------------------------+  |
|                                                             |
|  __________________________________________________________ |
|  [Footer Personalizat Medic]                                |
|  🔒 Datele dumneavoastră sunt confidențiale...              |
+-------------------------------------------------------------+
```

## 4. Legenda ID-urilor Cheie

Pentru referință rapidă în cod:

*   **Tabs:** `app-tabs` (Main), `tab-batch-medical`, `tab-settings`, `tab-data-view`.
*   **Batch:** `admin-batch-file-upload` (Upload), `admin-start-batch-button` (Start), `admin-batch-progress-bar`.
*   **Settings:** `settings-logo-upload`, `settings-footer-textarea`, `admin-create-user-button`.
*   **Data View:** `admin-refresh-data-view`, `date-picker-start`, `date-picker-end`.
*   **Patient:** `patient-main-graph`, `patient-data-view`.
