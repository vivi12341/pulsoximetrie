# 🎨 Ghid de Configurare Culori pentru Graficul de Pulsoximetrie

## Prezentare Generală

Acest sistem permite schimbarea rapidă a culorilor graficului de pulsoximetrie prin editarea unui fișier JSON simplu, fără a modifica codul sursă.

## Fișierul de Configurare

Fișierul **`colors_config.json`** conține toate setările de culori disponibile.

### Structura Fișierului

```json
{
  "active_profile": "simple",
  "profiles": {
    "gradient": { ... },
    "simple": { ... },
    "blue_red": { ... },
    "red_green": { ... }
  }
}
```

## Cum Să Schimbi Culorile

### 1. Schimbarea între Profile Existente

Pentru a schimba profilul de culori, editează valoarea `"active_profile"` în `colors_config.json`:

```json
"active_profile": "simple"
```

Profilele disponibile:

| Profil | Descriere |
|--------|-----------|
| `gradient` | Gradient complex cu 11 culori (violet → roșu → portocaliu → galben → verde) |
| `simple` | Doar 2 culori: roșu pentru valori joase (≤90%) și verde pentru valori normale (>90%) |
| `blue_red` | Gradient simplu de la roșu la albastru |
| `red_green` | Tranziție directă de la roșu la verde |

### 2. Crearea unui Profil Personalizat

Poți adăuga propriul tău profil de culori în secțiunea `"profiles"`:

```json
"profiles": {
  "my_custom_colors": {
    "description": "Descrierea mea personalizată",
    "colorscale_min": 75,
    "colorscale_max": 99,
    "colorscale": [
      [0.0, "#FF0000"],
      [0.5, "#FFFF00"],
      [1.0, "#00FF00"]
    ]
  }
}
```

Apoi setează: `"active_profile": "my_custom_colors"`

### 3. Înțelegerea Scalei de Culori

Scala de culori este o listă de perechi `[poziție, culoare]`:

- **Poziție**: Valoare între 0.0 și 1.0
  - `0.0` = valoarea minimă (de ex. 75% SaO2)
  - `1.0` = valoarea maximă (de ex. 99% SaO2)
  - `0.5` = mijlocul intervalului (87% pentru range 75-99)

- **Culoare**: Cod HEX (de ex. `"#FF0000"` pentru roșu)

#### Exemplu: Doar 2 Culori (Simple)

Pentru un gradient simplu între 2 culori:

```json
"colorscale": [
  [0.0, "#D62728"],  // Roșu la 75%
  [1.0, "#2CA02C"]   // Verde la 99%
]
```

#### Exemplu: 3 Culori cu Prag

Pentru a avea 2 culori distincte cu o tranziție bruscă la 90%:

```json
"colorscale": [
  [0.0,  "#FF0000"],  // Roșu la 75%
  [0.62, "#FF0000"],  // Tot roșu până la 90% (calculat: (90-75)/(99-75) = 0.625)
  [0.63, "#00FF00"],  // Verde de la 90%
  [1.0,  "#00FF00"]   // Tot verde până la 99%
]
```

## Calcul Poziție pentru Valori Specifice

Formula pentru a calcula poziția unei valori în interval:

```
poziție = (valoare - colorscale_min) / (colorscale_max - colorscale_min)
```

Exemple pentru intervalul [75, 99]:
- 75% → (75-75)/(99-75) = 0.0
- 80% → (80-75)/(99-75) = 0.21
- 85% → (85-75)/(99-75) = 0.42
- 90% → (90-75)/(99-75) = 0.625
- 95% → (95-75)/(99-75) = 0.83
- 99% → (99-75)/(99-75) = 1.0

## Coduri Culori Comune (HEX)

| Culoare | Cod HEX |
|---------|---------|
| Roșu | `#FF0000` |
| Verde | `#00FF00` |
| Albastru | `#0000FF` |
| Galben | `#FFFF00` |
| Portocaliu | `#FFA500` |
| Violet | `#800080` |
| Roz | `#FF1493` |
| Cyan | `#00FFFF` |
| Alb | `#FFFFFF` |
| Negru | `#000000` |
| Gri | `#808080` |

## Aplicarea Modificărilor

După editarea fișierului `colors_config.json`:

1. **Salvează fișierul**
2. **Restart aplicația** (oprește și repornește serverul)
3. **Reîncarcă pagina** în browser (F5 sau Ctrl+R)
4. **Generează un nou grafic** pentru a vedea culorile actualizate

## Depanare

### Culorile nu se schimbă?

1. Verifică că ai salvat fișierul `colors_config.json`
2. Verifică că sintaxa JSON este corectă (folosește un validator JSON online)
3. Verifică că numele profilului din `active_profile` există în secțiunea `profiles`
4. Restart aplicația
5. Verifică consola pentru mesaje de eroare

### Erori de sintaxă JSON

- Asigură-te că toate șirurile sunt între ghilimele duble (`"`)
- Verifică că toate parantezele și acoladele sunt închise corect
- Nu lăsa virgule după ultimul element dintr-o listă
- Valorile numerice nu au ghilimele (de ex. `0.5` nu `"0.5"`)

## Exemple Rapide

### Exemplu 1: Doar Roșu și Verde (Simplu)

```json
"active_profile": "simple"
```
Sau manual:
```json
"colorscale": [
  [0.0, "#D62728"],
  [1.0, "#2CA02C"]
]
```

### Exemplu 2: Tranziție Bruscă la 92%

```json
"colorscale": [
  [0.0, "#FF0000"],
  [0.70, "#FF0000"],
  [0.71, "#00FF00"],
  [1.0, "#00FF00"]
]
```

### Exemplu 3: 3 Zone Distincte

```json
"colorscale": [
  [0.0,  "#FF0000"],   // Roșu: 75-85%
  [0.41, "#FF0000"],
  [0.42, "#FFA500"],   // Portocaliu: 85-92%
  [0.70, "#FFA500"],
  [0.71, "#00FF00"],   // Verde: 92-99%
  [1.0,  "#00FF00"]
]
```

## Suport

Pentru mai multe informații despre culorile Plotly, vizitează:
https://plotly.com/python/colorscales/

---

**Notă:** Modificările din `colors_config.json` sunt încărcate doar la pornirea aplicației. Pentru a vedea schimbările, trebuie să restartezi serverul.

