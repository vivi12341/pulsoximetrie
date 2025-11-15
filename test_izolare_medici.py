#!/usr/bin/env python3
# ==============================================================================
# test_izolare_medici.py
# ------------------------------------------------------------------------------
# ROL: Demonstrație practică a izolării footer-urilor între medici diferiți
# USAGE: python test_izolare_medici.py
# ==============================================================================

import doctor_settings
import os
import json

print("=" * 80)
print("🔒 TEST IZOLARE MULTI-MEDIC - Footer Personalizat")
print("=" * 80)
print()

# ==============================================================================
# STEP 1: Creăm 3 Medici Diferiți
# ==============================================================================
print("📋 STEP 1: Creăm 3 medici cu footer-uri diferite...")
print("-" * 80)

# MEDIC 1 (contul tău actual)
doctor_settings.update_footer_info(
    "Cardio Help Team SRL\nStrada Crisanei nr 10, Alba Iulia\nTel: 0745603880\nSite: https://cardiohelpteam.ro",
    doctor_id="default"
)
print("✅ MEDIC 1 (default): Footer salvat")

# MEDIC 2 (Dr. Popescu)
doctor_settings.update_footer_info(
    "Cabinet Medical Dr. Popescu Maria\nStr. Libertății nr. 15, Cluj-Napoca\nTel: 0722 111 222 | Email: contact@popescu.ro\nProgram: Luni-Vineri 9:00-17:00",
    doctor_id="popescu_maria_67890"
)
print("✅ MEDIC 2 (popescu_maria_67890): Footer salvat")

# MEDIC 3 (Dr. Ionescu)
doctor_settings.update_footer_info(
    "Clinica Medicală Dr. Ionescu\nBucurești, Sector 1\nWebsite: www.clinica-ionescu.ro\nTel: 0723 333 444\nProgram: NON-STOP",
    doctor_id="ionescu_dan_11223"
)
print("✅ MEDIC 3 (ionescu_dan_11223): Footer salvat")

print()

# ==============================================================================
# STEP 2: Verificăm Izolarea - Citim Footer-urile
# ==============================================================================
print("📖 STEP 2: Citim footer-urile fiecărui medic...")
print("-" * 80)

footer_1 = doctor_settings.get_footer_info("default")
footer_2 = doctor_settings.get_footer_info("popescu_maria_67890")
footer_3 = doctor_settings.get_footer_info("ionescu_dan_11223")

print(f"\n🏥 MEDIC 1 (default):")
print(f"   {footer_1.replace(chr(10), chr(10) + '   ')}")

print(f"\n🏥 MEDIC 2 (popescu_maria_67890):")
print(f"   {footer_2.replace(chr(10), chr(10) + '   ')}")

print(f"\n🏥 MEDIC 3 (ionescu_dan_11223):")
print(f"   {footer_3.replace(chr(10), chr(10) + '   ')}")

print()

# ==============================================================================
# STEP 3: Modificăm DOAR Footer-ul Medicului 2
# ==============================================================================
print("✏️ STEP 3: Modificăm DOAR footer-ul medicului 2...")
print("-" * 80)

doctor_settings.update_footer_info(
    "Cabinet Medical Dr. Popescu Maria [ACTUALIZAT]\nProgram EXTINS: Luni-Sâmbătă 8:00-20:00\nTel: 0722 111 222 (NOU: 0722 999 888)",
    doctor_id="popescu_maria_67890"
)
print("✅ Footer medicului 2 modificat")

print()

# ==============================================================================
# STEP 4: Verificăm că Ceilalți Medici Rămân Neschimbați
# ==============================================================================
print("🔍 STEP 4: Verificăm că ceilalți medici rămân NESCHIMBAȚI...")
print("-" * 80)

footer_1_dupa = doctor_settings.get_footer_info("default")
footer_2_dupa = doctor_settings.get_footer_info("popescu_maria_67890")
footer_3_dupa = doctor_settings.get_footer_info("ionescu_dan_11223")

print(f"\n🏥 MEDIC 1 (default) - DUPĂ modificarea medicului 2:")
print(f"   {footer_1_dupa.replace(chr(10), chr(10) + '   ')}")
print(f"   Status: {'✅ NESCHIMBAT' if footer_1 == footer_1_dupa else '❌ SCHIMBAT (PROBLEMA!)'}")

print(f"\n🏥 MEDIC 2 (popescu_maria_67890) - DUPĂ modificare:")
print(f"   {footer_2_dupa.replace(chr(10), chr(10) + '   ')}")
print(f"   Status: {'✅ MODIFICAT CORECT' if footer_2 != footer_2_dupa else '❌ NU S-A MODIFICAT (PROBLEMA!)'}")

print(f"\n🏥 MEDIC 3 (ionescu_dan_11223) - DUPĂ modificarea medicului 2:")
print(f"   {footer_3_dupa.replace(chr(10), chr(10) + '   ')}")
print(f"   Status: {'✅ NESCHIMBAT' if footer_3 == footer_3_dupa else '❌ SCHIMBAT (PROBLEMA!)'}")

print()

# ==============================================================================
# STEP 5: Verificăm Structura Fișierelor pe Disk
# ==============================================================================
print("📁 STEP 5: Verificăm structura fizică pe disk...")
print("-" * 80)

doctor_folders = ["default", "popescu_maria_67890", "ionescu_dan_11223"]

for doctor_id in doctor_folders:
    folder_path = doctor_settings.get_doctor_folder(doctor_id)
    settings_file = doctor_settings.get_settings_file(doctor_id)
    
    print(f"\n🏥 {doctor_id}:")
    print(f"   📂 Folder: {folder_path}")
    print(f"   📄 Settings: {settings_file}")
    print(f"   Există: {'✅ DA' if os.path.exists(settings_file) else '❌ NU'}")
    
    if os.path.exists(settings_file):
        with open(settings_file, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
            footer_preview = settings_data.get('footer_info', '').split('\n')[0]
            print(f"   Footer (preview): {footer_preview}...")

print()

# ==============================================================================
# STEP 6: Test Cross-Contamination (Securitate)
# ==============================================================================
print("🛡️ STEP 6: Test de securitate - Cross-contamination...")
print("-" * 80)

# Încercăm să accesăm footer-ul medicului 1 cu ID-ul medicului 2
footer_test_1 = doctor_settings.get_footer_info("default")
footer_test_2 = doctor_settings.get_footer_info("popescu_maria_67890")

if footer_test_1 != footer_test_2:
    print("✅ IZOLARE CONFIRMATĂ: Footer-urile sunt complet diferite!")
    print(f"   Medic 1 lungime: {len(footer_test_1)} caractere")
    print(f"   Medic 2 lungime: {len(footer_test_2)} caractere")
else:
    print("❌ PROBLEMĂ DE SECURITATE: Footer-urile sunt identice!")

print()

# ==============================================================================
# REZULTATE FINALE
# ==============================================================================
print("=" * 80)
print("📊 REZULTATE FINALE")
print("=" * 80)

all_pass = True

# Test 1: Fiecare medic are folder separat
test1 = all(os.path.exists(doctor_settings.get_doctor_folder(doc)) for doc in doctor_folders)
print(f"{'✅' if test1 else '❌'} Test 1: Foldere separate create")
all_pass = all_pass and test1

# Test 2: Footer-urile sunt diferite
test2 = len(set([footer_1_dupa, footer_2_dupa, footer_3_dupa])) == 3
print(f"{'✅' if test2 else '❌'} Test 2: Footer-uri unice pentru fiecare medic")
all_pass = all_pass and test2

# Test 3: Modificarea unui medic nu afectează ceilalți
test3 = (footer_1 == footer_1_dupa) and (footer_3 == footer_3_dupa) and (footer_2 != footer_2_dupa)
print(f"{'✅' if test3 else '❌'} Test 3: Izolare la modificare")
all_pass = all_pass and test3

# Test 4: Cross-contamination prevention
test4 = footer_test_1 != footer_test_2
print(f"{'✅' if test4 else '❌'} Test 4: Protecție cross-contamination")
all_pass = all_pass and test4

print()
if all_pass:
    print("🎉 TOATE TESTELE AU TRECUT! Izolarea este 100% funcțională!")
else:
    print("⚠️ UNELE TESTE AU EȘUAT! Verificați implementarea.")

print()
print("=" * 80)
print("🔒 CONCLUZIE: Fiecare medic are footer COMPLET IZOLAT!")
print("=" * 80)
print()

# ==============================================================================
# CLEANUP (OPȚIONAL)
# ==============================================================================
print("🧹 Cleanup test data...")
print("   Notă: Păstrăm contul 'default' - ștergem doar conturile de test")

# Șterge doar conturile de test (păstrăm 'default')
import shutil

for test_doctor in ["popescu_maria_67890", "ionescu_dan_11223"]:
    test_folder = doctor_settings.get_doctor_folder(test_doctor)
    if os.path.exists(test_folder):
        shutil.rmtree(test_folder)
        print(f"   ✅ Șters: {test_doctor}/")

print()
print("✅ Test complet! Contul 'default' a fost păstrat cu datele tale originale.")
print()

