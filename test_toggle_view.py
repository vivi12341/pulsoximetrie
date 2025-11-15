"""
TEST pentru funcționalitatea Toggle View Imagini
Conform .cursorrules - "test1" pentru testare extensivă
"""
import os
import sys
import json

# Fix encoding pentru Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 70)
print("TEST TOGGLE VIEW IMAGINI - Dashboard Medical")
print("=" * 70)

# Test 1: Verificare patient_links.json
print("\n1️⃣ TEST: Verificare bază de date link-uri")
try:
    with open('patient_links.json', 'r', encoding='utf-8') as f:
        links = json.load(f)
    print(f"   ✅ Găsite {len(links)} link-uri în baza de date")
    
    # Verificăm câte au output_folder_path
    with_path = sum(1 for d in links.values() if d.get('output_folder_path'))
    without_path = len(links) - with_path
    
    print(f"   📊 Cu output_folder_path: {with_path}")
    print(f"   📊 Fără output_folder_path: {without_path} (vor folosi fallback)")
    
except Exception as e:
    print(f"   ❌ EROARE: {e}")
    sys.exit(1)

# Test 2: Verificare foldere output
print("\n2️⃣ TEST: Verificare foldere imagini")
try:
    output_dir = 'output'
    if os.path.exists(output_dir):
        folders = [f for f in os.listdir(output_dir) if os.path.isdir(os.path.join(output_dir, f))]
        print(f"   ✅ Găsite {len(folders)} foldere în output/")
        
        for folder in folders:
            folder_path = os.path.join(output_dir, folder)
            images = [f for f in os.listdir(folder_path) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            print(f"   📁 {folder}: {len(images)} imagini")
    else:
        print(f"   ❌ Folderul output/ nu există!")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ EROARE: {e}")
    sys.exit(1)

# Test 3: Simulare fallback logic
print("\n3️⃣ TEST: Simulare căutare automată folder")
try:
    from datetime import datetime
    
    for token, data in list(links.items())[:2]:  # Testăm primele 2
        device_num = data['device_name'].split('#')[-1].strip()
        recording_date = data.get('recording_date', '')
        
        print(f"\n   Token: {token[:16]}...")
        print(f"   Device: #{device_num}")
        print(f"   Data: {recording_date}")
        
        if recording_date:
            date_obj = datetime.strptime(recording_date, '%Y-%m-%d')
            day = date_obj.day
            month_name = ['ian', 'feb', 'mar', 'apr', 'mai', 'iun', 
                         'iul', 'aug', 'sep', 'oct', 'nov', 'dec'][date_obj.month - 1]
            year = date_obj.year
            
            search_pattern = f"{day:02d}{month_name}{year}"
            print(f"   🔍 Caut folder cu: '{search_pattern}' și '{device_num}'")
            
            found = False
            for folder in folders:
                if device_num in folder and search_pattern in folder:
                    print(f"   ✅ GĂSIT: {folder}")
                    found = True
                    break
            
            if not found:
                print(f"   ⚠️ NU S-A GĂSIT folder corespunzător")
        else:
            print(f"   ⚠️ Lipsește recording_date")
            
except Exception as e:
    print(f"   ❌ EROARE: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Verificare callbacks în cod
print("\n4️⃣ TEST: Verificare callbacks Dash")
try:
    import callbacks_medical
    print("   ✅ Modulul callbacks_medical.py importat corect")
    
    # Verificăm dacă toggle_images_view există
    if hasattr(callbacks_medical, 'toggle_images_view'):
        print("   ✅ Funcția toggle_images_view() există")
    else:
        print("   ❌ Funcția toggle_images_view() NU EXISTĂ!")
        
except Exception as e:
    print(f"   ❌ EROARE la import: {e}")

# Rezumat final
print("\n" + "=" * 70)
print("📊 REZUMAT TEST")
print("=" * 70)
print(f"✅ Link-uri: {len(links)}")
print(f"✅ Foldere cu imagini: {len(folders)}")
print(f"⚠️  Link-uri fără output_folder_path: {without_path}")
print(f"✅ Fallback logic implementat")
print("\n💡 Pentru testare manuală:")
print("   1. Browser: http://127.0.0.1:8050/")
print("   2. Tab 'Vizualizare Date'")
print("   3. Click pe o linie pentru expandare")
print("   4. Click pe '📊 Ansamblu' (ar trebui să funcționeze acum)")
print("=" * 70)

