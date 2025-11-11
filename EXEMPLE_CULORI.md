# 📋 Exemple Rapide de Configurații Culori

Copiați și lipiți aceste exemple în fișierul `colors_config.json` pentru a schimba rapid culorile.

## 1. Profilul "simple" - Doar 2 Culori (Roșu → Verde)

**Recomandat pentru: Vizualizare clară, fără distrageri**

```json
"active_profile": "simple"
```

Rezultat:
- **75-90% SaO2**: Roșu
- **90-99% SaO2**: Verde

---

## 2. Profilul "gradient" - Gradient Complex (11 Culori)

**Recomandat pentru: Analiză detaliată, diferențiere fină**

```json
"active_profile": "gradient"
```

Rezultat:
- **75%**: Violet Intens
- **80%**: Violet-Roșu
- **85%**: Roșu
- **89%**: Portocaliu
- **90%**: Auriu
- **92%**: Galben
- **94%**: Verde-Galben
- **95%**: Verde
- **96%**: Verde Intens
- **98%**: Verde Pădure
- **99%**: Verde Închis

---

## 3. Doar Roșu și Albastru

**Pentru o perspectiv diferită**

Schimbați în `colors_config.json`:
```json
"active_profile": "blue_red"
```

---

## 4. Configurație Personalizată: 3 Zone Clare

**Pericol (Roșu) | Atenție (Portocaliu) | Sigur (Verde)**

Adăugați acest profil în secțiunea `"profiles"`:

```json
"three_zones": {
  "description": "3 zone distincte: Roșu (75-85%), Portocaliu (85-92%), Verde (92-99%)",
  "colorscale_min": 75,
  "colorscale_max": 99,
  "colorscale": [
    [0.0,  "#DC143C"],
    [0.41, "#DC143C"],
    [0.42, "#FF8C00"],
    [0.70, "#FF8C00"],
    [0.71, "#32CD32"],
    [1.0,  "#32CD32"]
  ]
}
```

Apoi setați: `"active_profile": "three_zones"`

---

## 5. Configurație Personalizată: Semaforizare Medicală

**Standard medical: <90% = Pericol | 90-95% = Atenție | >95% = Bine**

```json
"medical_standard": {
  "description": "Semaforizare medicală: <90% roșu, 90-95% galben, >95% verde",
  "colorscale_min": 75,
  "colorscale_max": 99,
  "colorscale": [
    [0.0,  "#FF0000"],
    [0.62, "#FF0000"],
    [0.63, "#FFD700"],
    [0.83, "#FFD700"],
    [0.84, "#00C853"],
    [1.0,  "#00C853"]
  ]
}
```

---

## 6. Configurație Personalizată: Gradient Termic

**Albastru (rece/pericol) → Roșu (cald/bine)**

```json
"thermal": {
  "description": "Gradient termic invers: albastru (jos) la roșu (sus)",
  "colorscale_min": 75,
  "colorscale_max": 99,
  "colorscale": [
    [0.0,  "#0000FF"],
    [0.25, "#00FFFF"],
    [0.50, "#00FF00"],
    [0.75, "#FFFF00"],
    [1.0,  "#FF0000"]
  ]
}
```

---

## 7. Configurație Personalizată: Monocrom (Gri)

**Pentru printare sau rapoarte alb-negru**

```json
"grayscale": {
  "description": "Gradient monocrom pentru printare",
  "colorscale_min": 75,
  "colorscale_max": 99,
  "colorscale": [
    [0.0, "#000000"],
    [0.5, "#808080"],
    [1.0, "#E0E0E0"]
  ]
}
```

---

## 8. Configurație Personalizată: Doar Verde (Intensitate Variabilă)

**Toate valorile în nuanțe de verde**

```json
"green_only": {
  "description": "Doar nuanțe de verde, de la închis la deschis",
  "colorscale_min": 75,
  "colorscale_max": 99,
  "colorscale": [
    [0.0, "#004D00"],
    [0.5, "#00AA00"],
    [1.0, "#90EE90"]
  ]
}
```

---

## Cum Să Aplicați Aceste Exemple

### Metoda 1: Folosiți Profile Existente
Doar schimbați valoarea `"active_profile"`:
```json
{
  "active_profile": "simple",
  "profiles": { ... }
}
```

### Metoda 2: Adăugați Profil Nou
1. Copiați exemplul dorit
2. Lipiți-l în secțiunea `"profiles"` din `colors_config.json`
3. Setați `"active_profile"` cu numele noului profil

**Exemplu complet:**
```json
{
  "active_profile": "medical_standard",
  
  "profiles": {
    "gradient": { ... },
    "simple": { ... },
    
    "medical_standard": {
      "description": "Semaforizare medicală",
      "colorscale_min": 75,
      "colorscale_max": 99,
      "colorscale": [
        [0.0, "#FF0000"],
        [0.62, "#FF0000"],
        [0.63, "#FFD700"],
        [0.83, "#FFD700"],
        [0.84, "#00C853"],
        [1.0, "#00C853"]
      ]
    }
  }
}
```

---

## Calculator Rapid de Poziții

Pentru intervalul standard [75, 99%]:

| SaO2 (%) | Poziție în colorscale |
|----------|----------------------|
| 75 | 0.00 |
| 80 | 0.21 |
| 85 | 0.42 |
| 90 | 0.625 |
| 92 | 0.71 |
| 95 | 0.83 |
| 98 | 0.96 |
| 99 | 1.00 |

**Formula**: `poziție = (valoare - 75) / (99 - 75)`

---

## Recomandări

### Pentru Prezentări
✅ Folosiți `"simple"` sau `"three_zones"` - clar și profesional

### Pentru Analiză Clinică Detaliată
✅ Folosiți `"gradient"` sau `"medical_standard"` - diferențiere fină

### Pentru Rapoarte Printate
✅ Folosiți `"grayscale"` - economie de cerneală

### Pentru Demonstrații
✅ Folosiți `"thermal"` sau `"gradient"` - atrăgător vizual

---

**Nu uitați**: După orice modificare, restartați aplicația și reîncărcați pagina!

