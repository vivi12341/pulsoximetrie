╔══════════════════════════════════════════════════════════════════════════════╗
║                    SISTEM DE CONFIGURARE CULORI                              ║
║                     Pulsoximetrie - Versiunea 1.0                            ║
╚══════════════════════════════════════════════════════════════════════════════╝

📌 FIȘIERE IMPORTANTE:
   ├─ colors_config.json      → Configurația principală (EDITEAZĂ AICI!)
   ├─ GHID_CULORI.md          → Documentație completă
   └─ EXEMPLE_CULORI.md       → Exemple gata de folosit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎨 SCHIMBAREA RAPIDĂ A CULORILOR:

1. Deschide fișierul: colors_config.json

2. Schimbă profilul activ:
   
   Pentru GRADIENT COMPLEX (multe culori):
   "active_profile": "gradient"
   
   Pentru DOAR 2 CULORI (simplu):
   "active_profile": "simple"

3. Salvează fișierul

4. Restart aplicația (stop_server.bat apoi start_server.bat)

5. Reîncarcă pagina în browser (F5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ PROFILE DISPONIBILE INSTANT:

┌─────────────┬──────────────────────────────────────────────────────────────┐
│ gradient    │ 11 culori: violet → roșu → portocaliu → galben → verde      │
│ simple      │ 2 culori: roșu (≤90%) → verde (>90%)                         │
│ blue_red    │ 2 culori: roșu → albastru                                    │
│ red_green   │ 2 culori: roșu → verde (gradient lin)                        │
└─────────────┴──────────────────────────────────────────────────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 COMPARAȚIE GRADIENT vs SIMPLE:

GRADIENT (11 culori):
   75% ████ Violet Intens
   80% ████ Violet-Roșu
   85% ████ Roșu
   89% ████ Portocaliu
   90% ████ Auriu
   92% ████ Galben
   94% ████ Verde-Galben (Lime)
   95% ████ Verde Standard
   96% ████ Verde Intens
   98% ████ Verde Pădure
   99% ████ Verde Închis

SIMPLE (2 culori):
   75-90% ████████████████████████ Roșu
   90-99% ████████████████████████ Verde

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔧 PENTRU CULORI PERSONALIZATE:

→ Vezi EXEMPLE_CULORI.md pentru configurații gata făcute
→ Vezi GHID_CULORI.md pentru explicații detaliate
→ Copiază și adaptează un profil existent în colors_config.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 EXEMPLU RAPID - Doar 2 Culori:

Deschide colors_config.json și modifică:

   {
     "active_profile": "simple",     ← SCHIMBĂ DOAR ACEASTĂ LINIE!
     "profiles": {
       ...
     }
   }

Restartează aplicația → GATA! 🎉

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❓ PROBLEME?

1. Verifică sintaxa JSON (ghilimele duble, virgule)
2. Verifică că profilul există în secțiunea "profiles"
3. Restart aplicația complet
4. Vezi GHID_CULORI.md secțiunea "Depanare"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✨ SUCCES!

