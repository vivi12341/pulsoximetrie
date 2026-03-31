# ⚙️ CONFIGURARE APP_URL pe Railway - URGENT

## 📋 Ce face APP_URL?

Link-urile generate pentru pacienți vor folosi `APP_URL` în loc de `http://127.0.0.1:8050`.

**Înainte:**
```
❌ http://127.0.0.1:8050/?token=abc123  (nu funcționează online!)
```

**După:**
```
✅ https://pulsoximetrie.cardiohelpteam.ro/?token=abc123  (funcționează perfect!)
```

---

## 🚀 Pași Configurare (2 minute)

### 1. Accesează Railway Dashboard

1. Mergi la **https://railway.app/**
2. Click pe proiectul **"pulsoximetrie"**
3. Click pe serviciul **aplicației** (nu PostgreSQL!)

### 2. Adaugă Variabila APP_URL

1. Click pe tab-ul **"Variables"** (stânga jos)
2. Click pe **"+ New Variable"** (buton albastru sus)
3. Adaugă:

```
Nume: APP_URL
Valoare: https://pulsoximetrie.cardiohelpteam.ro
```

**⚠️ ATENȚIE:** NU pune `/` la sfârșit! Doar domeniul!

### 3. (Opțional) Adaugă și Variabilele Admin

Dacă nu ai făcut deja, adaugă și:

```
ADMIN_EMAIL=admin@pulsoximetrie.ro
ADMIN_PASSWORD=ParolaTaSigura2024!
ADMIN_NAME=Administrator
```

### 4. Salvează și Redeploy

Railway va reporni **automat** aplicația după ce salvezi variabilele.

**SAU** forțează redeploy:
- Click pe **"Deployments"** (tab din stânga)
- Click pe **"..." (3 puncte)** pe ultimul deployment
- Click pe **"Redeploy"**

---

## ✅ Verificare După Deploy (~90 secunde)

După ce Railway termină deploy-ul:

1. **Refresh** aplicația: https://pulsoximetrie.cardiohelpteam.ro/
2. **Login** (dacă ai setat ADMIN_EMAIL/ADMIN_PASSWORD)
3. **Procesare Batch** → Upload CSV
4. **Link-urile generate** vor arăta:
   ```
   ✅ https://pulsoximetrie.cardiohelpteam.ro/?token=...
   ```
5. **Butoanele funcționale:**
   - 📋 **Copy** → Copiază link-ul în clipboard
   - 🌐 **Testează în browser** → Deschide în tab nou

---

## 🔍 Debugging (dacă ceva nu funcționează)

### Link-urile încă arată localhost?

**Cauză:** APP_URL nu e setat sau Railway nu a făcut rebuild.

**Soluție:**
```bash
# Verifică variabilele de mediu pe Railway:
# Dashboard → Service → Variables → Caută "APP_URL"

# Dacă nu există, adaugă-o!
```

### Butoanele Copy nu funcționează?

**Cauză:** Browser-ul blochează clipboard API pe HTTP (trebuie HTTPS).

**Soluție:** Railway folosește HTTPS by default, deci ar trebui să funcționeze. Dacă nu:
- Verifică că accesezi `https://` (nu `http://`)
- Încearcă alt browser (Chrome/Edge/Firefox)

---

## 📊 Rezultat Final

După configurare, medicul va vedea:

```
✅ Procesare Batch Finalizată Cu Succes!
🔗 2 link-uri generate automat:

┌─────────────────────────────────────────────────────────────────┐
│ 📅 Marți 14/10/2025 | 20:32 - 04:45                            │
│ 🔧 Checkme O2 #3539 | 🖼️ 15 imagini                            │
│                                                                   │
│ [https://pulsoximetrie.cardiohelpteam.ro/?token=abc123...]      │
│                                                                   │
│ [📋 Copy]  [🌐 Testează în browser]                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Testare Completă test1

După setare, testează:

1. ✅ **Pagină login** → https://pulsoximetrie.cardiohelpteam.ro/
2. ✅ **Autentificare** → admin@pulsoximetrie.ro
3. ✅ **Upload CSV** → Tab "Procesare Batch"
4. ✅ **Link-uri generate** → Verifică că sunt cu domeniul corect
5. ✅ **Copy buton** → Click și CTRL+V să testezi
6. ✅ **Testează buton** → Deschide în tab nou
7. ✅ **Link pacient** → Funcționează fără autentificare

---

**Ultima actualizare:** 15 Noiembrie 2025, 02:45
**Commit:** `7859f75` - Fix link-uri producție + butoane Copy/Testează

