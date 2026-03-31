# Cum funcționează Workflows și Prompt-urile în Antigravity și alte AI-uri

## 1. Ce sunt Workflows în Antigravity?
În Google Antigravity, poți defini "Workflows" (Fluxuri de lucru). Acestea sunt rețete sau șabloane pe care AI-ul este forțat să le urmeze pas cu pas.
- **Unde se află?** Antigravity se uită automat după un folder ascuns numit `.agents/workflows/` (sau `.agent/workflows/`) în root-ul proiectului tău. 
- **Cum se folosesc?** Orice fișier `.md` din acel folder devine o comandă (slash command). De exemplu, fișierul `super_crew.md` îți permite să scrii în chat `/super_crew [cerința]` și AI-ul va citi direct acel mod de funcționare și îl va aplica.

## 2. Pot folosi aceste Prompt-uri în alte programe? (ChatGPT, Claude, Cursor, GitHub Copilot)
**DA!** Motivul pentru care am creat acest folder separat pentru tine este exact acesta.
Dacă folosești alte programe (ex: lucrezi într-un alt proiect unde Antigravity nu e disponibil, sau vorbești cu ChatGPT web), pur și simplu deschizi oricare dintre fișierele `.md` din acest folder, dai Copy la text și îi dai Paste în chat-ul celuilalt AI. 

Toate prompt-urile de aici sunt scrise la nivel nivel "Senior Prompt Engineer" și deblochează performanța maximă din orice model lingvistic de top.

## 3. Ce face fiecare fișier de aici?
- `Prompt_The_Architect.md` - Folosește-l la **începutul** unei noi funcționalități. Îi cere AI-ului să gândească variante structurale, NU să scrie direct cod dezordonat.
- `Prompt_Super_Crew.md` - Folosește-l pentru **implementarea completă** a unei munci complexe. Împarte munca AI-ului în Arhitect -> Coder -> Tester.
- `Prompt_Sniper_Debugger.md` - Cel mai bun mod de a repara bug-uri evazive. Împiedică AI-ul să ghicească greșit, forțându-l să genereze ipoteze logice prima oară.
- `Super_Crew_Workflow_Antigravity.md` - Copia exactă a workflow-ului instalat intern aici, ca să-l poți citi sau exporta în alte proiecte de-ale tale.
