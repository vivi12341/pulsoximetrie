# 📧 Configurare Brevo API pentru Email (Railway)

## ⚠️ Status Curent

```
ERROR - [email_service] - ❌ Brevo API key invalid: 401
```

**Impact**: Reset parolă pentru medici **NU funcționează**.

---

## ✅ Soluție (2 minute)

### 1. Obține Brevo API Key

1. Mergi la [Brevo](https://app.brevo.com) (cont gratuit)
2. Login / Creare cont
3. Settings → **API Keys**
4. Click **Generate a new API key**
5. **Copiază key-ul** (începe cu `xkeysib-...`)

### 2. Adaugă în Railway

1. Railway Dashboard → Proiect `pulsoximetrie`
2. Tab **Variables**
3. Click **+ New Variable**
4. Adaugă:
   ```
   BREVO_API_KEY=xkeysib-your-key-here
   ```
5. Click **Add**

### 3. Verificare

După restart (automat), verifică **Deploy Logs**:
- ✅ **SUCCES**: NU mai vezi `❌ Brevo API key invalid`
- ✅ **FUNCȚIONAL**: Reset parolă trimite email-uri

---

## 🔧 Variabile Opționale (Railway)

Poți personaliza și alte setări:

```bash
# Email Settings
BREVO_API_KEY=xkeysib-...                    # OBLIGATORIU pentru reset parolă
SENDER_EMAIL=noreply@pulsoximetrie.ro        # Opțional (default: noreply@localhost)
SENDER_NAME=Platformă Pulsoximetrie          # Opțional

# Admin Implicit
ADMIN_EMAIL=viorelmada1@gmail.com            # Setat deja
ADMIN_PASSWORD=Admin123!Change               # Schimbă-l!
ADMIN_NAME=Administrator                     # Opțional

# Security
SECRET_KEY=your-random-32-char-string        # IMPORTANT: generează unul unic!
SESSION_COOKIE_SECURE=True                   # Doar HTTPS (Railway HTTPS by default)
PERMANENT_SESSION_LIFETIME=30                # Zile (default: 30)
```

---

## 🎯 Generare SECRET_KEY Securizat

```python
# Rulează în terminal local:
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Copiază output-ul și adaugă-l ca variabilă `SECRET_KEY` în Railway.

---

## 📋 Checklist Post-Configurare

- [ ] Brevo API key adăugat
- [ ] SECRET_KEY schimbat (NU folosi `dev-secret-key-change-in-production`!)
- [ ] ADMIN_PASSWORD schimbat (login cu email + parolă nouă)
- [ ] Test reset parolă (funcționează?)
- [ ] Verificat Deploy Logs (NU mai apar erori ❌)

---

**Notă**: Aplicația funcționează FĂRĂ Brevo API, dar **reset parolă NU va funcționa**.  
Alternativă temporară: Medicii folosesc parola inițială sau contactează admin pentru reset manual.

