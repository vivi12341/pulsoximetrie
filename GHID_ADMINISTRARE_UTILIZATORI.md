# 👥 Ghid Administrare Utilizatori - Platformă Pulsoximetrie

## 🎯 Prezentare Generală

Platforma suportă acum două modalități de creare conturi:
1. **Sign Up Public** - Oricine poate crea un cont de medic
2. **Administrare Conturi (Admin)** - Administratorii pot gestiona toți utilizatorii din setări

---

## 🚀 Setup Inițial

### Pasul 1: Creare Primul Administrator

Înainte de a porni aplicația pentru prima dată, creați primul utilizator admin:

```powershell
python create_admin.py
```

Veți fi întrebat:
- **Nume Complet**: Ex: "Dr. Popescu Ion"
- **Email**: Ex: "admin@clinica.ro"
- **Parolă**: Minimum 8 caractere (litere mari, mici, cifre, caractere speciale)

**Notă**: Scriptul va detecta automat dacă aveți PostgreSQL instalat sau va folosi SQLite.

### Pasul 2: Pornire Aplicație

```powershell
python run_medical.py
```

### Pasul 3: Autentificare

Accesați: `http://localhost:8050/login` și autentificați-vă cu credențialele de admin.

---

## 📝 Sign Up Public

### Acces

Oricine poate accesa: `http://localhost:8050/signup`

### Proces Înregistrare

1. Completați formularul:
   - **Nume Complet**
   - **Email** (unic în sistem)
   - **Parolă** (min. 8 caractere, cu cerințe de securitate)
   - **Confirmă Parola**

2. Click pe **"✨ Creează Cont"**

3. Veți fi redirecționat la pagina de login

**Notă**: Conturile create prin sign up **NU sunt administratori** by default.

### Dezactivare Sign Up Public

Pentru a dezactiva înregistrarea publică, setați variabila de mediu:

```powershell
$env:ALLOW_PUBLIC_SIGNUP="false"
```

Apoi reporniți aplicația. Utilizatorii vor vedea mesajul:
> "Înregistrarea publică este dezactivată. Contactați administratorul pentru a crea un cont."

---

## 👑 Administrare Utilizatori (Doar Admin)

### Acces

1. Autentificați-vă ca **Administrator**
2. Navigați la tab-ul **"⚙️ Setări"**
3. Veți vedea secțiunea **"👥 Administrare Utilizatori"** (doar pentru admini)

### Funcționalități Disponibile

#### 📊 Vizualizare Listă Utilizatori

Secțiunea afișează:
- **Statistici**: Total utilizatori | Activi | Administratori
- **Card pentru fiecare utilizator**:
  - Nume complet + Email
  - Badge **👑 ADMIN** (dacă este administrator)
  - Status: ✅ Activ / ❌ Dezactivat
  - Data creării contului
  - Ultimul login
  - Număr login-uri eșuate

#### ➕ Creare Utilizator Nou

1. Click pe **"➕ Creare Utilizator Nou"**
2. Completați formularul:
   - **Nume Complet**
   - **Email** (unic)
   - **Parolă** (min. 8 caractere)
   - **☑️ Cont Administrator** (opțional)
3. Click pe **"💾 Salvează Utilizator"**

**Avantaje față de Sign Up Public**:
- Adminul poate crea direct **conturi admin**
- Adminul poate seta parolele inițiale
- Control total asupra utilizatorilor

#### ✏️ Editare Utilizator

1. Click pe **"✏️ Editează"** la utilizatorul dorit
2. Modificați:
   - Nume complet
   - Email
   - Parolă (lasă gol pentru a păstra parola actuală)
   - Rol (Admin / Medic)
3. Click pe **"💾 Salvează Modificări"**

**Restricții**:
- **NU puteți edita propriul cont** (protecție împotriva auto-dezactivării)

#### 🔒 Activare / Dezactivare Utilizator

Click pe butonul:
- **"❌ Dezactivează"** - Utilizatorul NU se mai poate autentifica
- **"✅ Activează"** - Reactivează contul

**Cazuri de utilizare**:
- Medic plecat în concediu → Dezactivare temporară
- Suspendare cont din motive de securitate
- Reactivare după investigație

#### 🔓 Deblocare Cont

Dacă un utilizator are **5 încercări eșuate de autentificare**, contul se blochează automat pentru **15 minute**.

Adminul poate **debloca manual** contul:
- Click pe **"🔒 Deblocă"**
- Utilizatorul poate încerca imediat să se autentifice

#### 👑 Acordare / Retragere Rol Admin

Click pe butonul:
- **"👑 Admin"** - Promovează utilizatorul la administrator
- **"👤 Medic"** - Retrage rolul de administrator

**Atenție**: Administratorii au acces la:
- Gestionarea tuturor utilizatorilor
- Setări avansate ale platformei

**Restricții**:
- **NU vă puteți schimba singur rolul** (protecție)

---

## 🔐 Securitate și Cerințe Parolă

### Cerințe Minime Parolă

Pentru toate conturile (sign up + admin create):
- **Minimum 8 caractere**
- **Cel puțin o literă mare** (A-Z)
- **Cel puțin o literă mică** (a-z)
- **Cel puțin o cifră** (0-9)
- **Cel puțin un caracter special** (!@#$%^&*...)

### Protecții Brute-Force

- **5 încercări eșuate** → Blocare cont **15 minute**
- **Rate limiting** pe email: max 5 încercări / 15 minute
- **Logging** complet (fără date sensibile)

### Hash-uri Parole

- **bcrypt** cu cost factor adaptiv
- **Rehashing automat** dacă parametrii vechi
- **Niciodată** nu se stochează parole în clar

---

## 📋 Workflow Recomandat

### Setup Inițial Clinică

1. **Admin principal** creează cont prin `python create_admin.py`
2. **Pornește aplicația**: `python run_medical.py`
3. **Se autentifică** ca admin
4. **Creează conturi** pentru ceilalți medici din **Tab Setări**
5. **Trimite credențialele** medicilor (ei pot schimba parola după primul login)

### Sign Up Public

**Dezactivați** sign up-ul public dacă:
- Vreți control total asupra utilizatorilor
- Mediul este production (recomandare de securitate)

**Activați** sign up-ul public dacă:
- Permiteți medicilor să se înregistreze singuri
- Aveți un proces de verificare ulterioară (ex: aprobare admin)

---

## ⚠️ Protecții Auto-Sabotaj

Sistemul previne scenarii periculoase:

### ❌ NU Poți:
- **Edita propriul cont** (risc de auto-dezactivare)
- **Dezactiva propriul cont** (risc de blocare totală)
- **Schimba propriul rol** (risc de pierdere acces admin)

### ✅ Soluții:
- Cereți unui **alt administrator** să vă modifice contul
- Dacă sunteți **singurul admin**, creați un al doilea admin temporar

---

## 🐛 Troubleshooting

### Problema: "Nu văd secțiunea Administrare Utilizatori"

**Cauză**: Nu sunteți autentificat ca administrator.

**Soluție**:
1. Verificați că sunteți autentificat (vedeți **👑 ADMIN** în header)
2. Dacă nu, contactați un administrator existent
3. Dacă nu există admini, folosiți `python create_admin.py`

### Problema: "Eroare la creare utilizator - Email există deja"

**Cauză**: Email-ul este deja folosit de alt utilizator.

**Soluție**:
1. Verificați lista de utilizatori
2. Dacă utilizatorul există dar este dezactivat → Reactivați-l
3. Folosiți alt email

### Problema: "Cont blocat după 5 încercări eșuate"

**Auto-deblocare**: După **15 minute** contul se deblochează automat.

**Deblocare manuală** (de către admin):
1. Mergem la **Tab Setări** → **Administrare Utilizatori**
2. Găsim utilizatorul (va avea butonul **🔒 Deblocă**)
3. Click pe **🔒 Deblocă**

---

## 📊 Statistici și Monitoring

### Informații Disponibile per Utilizator

- **Data creării**: Când a fost creat contul
- **Ultimul login**: Data + ora + IP
- **Login-uri eșuate**: Număr de încercări eșuate consecutive
- **Status blocare**: Dacă contul este blocat temporar

### Log-uri

Toate acțiunile sunt loggate în:
```
output/LOGS/app_activity.log
```

**Exemple**:
- `✅ Admin admin@clinica.ro a creat utilizatorul medic@clinica.ro`
- `✅ Admin admin@clinica.ro a dezactivat utilizatorul medic2@clinica.ro`
- `🔒 Cont blocat după 5 încercări eșuate: medic@clinica.ro`

**GDPR Compliant**: Log-urile **NU conțin** date personale sensibile (CNP, telefon, adresă).

---

## 🎓 Best Practices

### Pentru Administratori

1. **Creați un backup admin** - Aveți întotdeauna 2+ administratori
2. **Parolă puternică** - Minimum 12 caractere pentru conturi admin
3. **Monitorizați login-urile eșuate** - Semnal de încercare de acces neautorizat
4. **Dezactivați conturile neutilizate** - Reduceți suprafața de atac
5. **Nu distribuiți acreditările admin** - Fiecare admin propriul cont

### Pentru Medici

1. **Schimbați parola inițială** - După primul login (dacă a fost creată de admin)
2. **Parolă unică** - Nu folosiți aceeași parolă ca pe alte site-uri
3. **Verificați ultimul login** - Detectați accese neautorizate
4. **Contactați adminul** - Dacă observați activitate suspectă

---

## 📞 Contact & Suport

Pentru probleme tehnice:
- Verificați `output/LOGS/app_activity.log`
- Contactați administratorul platformei
- Consultați `.cursorrules` pentru arhitectură

---

**Versiune**: 1.0  
**Data**: Noiembrie 2025  
**Platformă**: Pulsoximetrie - Python + Dash + PostgreSQL

