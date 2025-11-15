#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
==============================================================================
test_system_complete.py - TEST EXTENSIV SISTEM PULSOXIMETRIE
==============================================================================
ROL: Testează automat toate funcționalitățile sistemului:
     - Parsing CSV (date corecte, invalide, encoding)
     - Parsing PDF (date corecte, format nestandard)
     - Link-uri persistente (creare, tracking, metadata)
     - Privacy audit (zero date personale)
     - Validare medicală (SpO2, Puls în range corect)

ACTIVARE: Rulați "python test_system_complete.py" sau tastați "test1" în chat
==============================================================================
"""

import os
import json
import sys
from datetime import datetime
from typing import Dict, List, Tuple

# Colorare output pentru Windows
try:
    import colorama
    colorama.init()
    GREEN = colorama.Fore.GREEN
    RED = colorama.Fore.RED
    YELLOW = colorama.Fore.YELLOW
    BLUE = colorama.Fore.BLUE
    RESET = colorama.Style.RESET_ALL
except ImportError:
    GREEN = RED = YELLOW = BLUE = RESET = ""

# ==============================================================================
# UTILITIES
# ==============================================================================

class TestResult:
    """Rezultat test individual"""
    def __init__(self, name: str, passed: bool, message: str = "", details: str = ""):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details

class TestSuite:
    """Suite de teste cu raportare"""
    def __init__(self, name: str):
        self.name = name
        self.tests: List[TestResult] = []
        self.start_time = None
        self.end_time = None
    
    def add_test(self, result: TestResult):
        self.tests.append(result)
        status = f"{GREEN}[PASS]{RESET}" if result.passed else f"{RED}[FAIL]{RESET}"
        print(f"  {status} | {result.name}")
        if result.message:
            print(f"        → {result.message}")
        if result.details and not result.passed:
            print(f"        Details: {result.details}")
    
    def summary(self) -> Tuple[int, int]:
        """Returnează (passed_count, total_count)"""
        passed = sum(1 for t in self.tests if t.passed)
        total = len(self.tests)
        return passed, total
    
    def print_summary(self):
        passed, total = self.summary()
        duration = (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
        
        if passed == total:
            status_icon = f"{GREEN}[OK]"
            status_text = "TOATE TESTELE AU TRECUT"
        else:
            status_icon = f"{RED}[!!]"
            status_text = f"{passed}/{total} TESTE AU TRECUT"
        
        print(f"\n{status_icon} {self.name}: {status_text} ({duration:.2f}s){RESET}\n")

# ==============================================================================
# TEST 1: PARSING CSV
# ==============================================================================

def test_csv_parsing():
    """Testează parsing CSV cu diverse scenarii"""
    suite = TestSuite("TEST 1: PARSING CSV")
    suite.start_time = datetime.now()
    
    print(f"\n{BLUE}{'='*70}")
    print(f">>> {suite.name}")
    print(f"{'='*70}{RESET}\n")
    
    try:
        from data_parser import parse_csv_data
        import pandas as pd
        
        # Test 1.1: CSV Valid (encoding UTF-8)
        test_csv_path = "bach data/Checkme O2 3539_20251007230437.csv"
        if os.path.exists(test_csv_path):
            with open(test_csv_path, 'rb') as f:
                content = f.read()
            
            try:
                df = parse_csv_data(content, os.path.basename(test_csv_path))
                
                # Verificări
                has_data = len(df) > 0
                has_spo2 = 'SpO2' in df.columns
                has_pulse = 'Pulse' in df.columns
                has_datetime_index = isinstance(df.index, pd.DatetimeIndex)
                
                if has_data and has_spo2 and has_pulse and has_datetime_index:
                    suite.add_test(TestResult(
                        "CSV Valid - Parsing Standard",
                        True,
                        f"{len(df)} rânduri, coloane: {list(df.columns)}"
                    ))
                else:
                    suite.add_test(TestResult(
                        "CSV Valid - Parsing Standard",
                        False,
                        "Date incomplete sau structură greșită"
                    ))
            except Exception as e:
                suite.add_test(TestResult(
                    "CSV Valid - Parsing Standard",
                    False,
                    f"Eroare parsing: {str(e)}"
                ))
        else:
            suite.add_test(TestResult(
                "CSV Valid - Parsing Standard",
                False,
                f"Fișier test nu există: {test_csv_path}"
            ))
        
        # Test 1.2: CSV cu encoding românesc
        test_csv_ro = "de modificat reguli/Checkme O2 0331_20251015203510.csv"
        if os.path.exists(test_csv_ro):
            with open(test_csv_ro, 'rb') as f:
                content_ro = f.read()
            
            try:
                df_ro = parse_csv_data(content_ro, os.path.basename(test_csv_ro))
                suite.add_test(TestResult(
                    "CSV Românesc - Encoding UTF-8",
                    len(df_ro) > 0,
                    f"{len(df_ro)} rânduri parsate corect"
                ))
            except Exception as e:
                suite.add_test(TestResult(
                    "CSV Românesc - Encoding UTF-8",
                    False,
                    f"Eroare: {str(e)}"
                ))
        
        # Test 1.3: Validare date medicale (SpO2, Puls în range)
        if 'df' in locals() and len(df) > 0:
            spo2_valid = df['SpO2'].between(0, 100).all()
            pulse_valid = df['Pulse'].between(30, 200).all()
            
            suite.add_test(TestResult(
                "Validare SpO2 (0-100%)",
                spo2_valid,
                f"Min: {df['SpO2'].min():.1f}%, Max: {df['SpO2'].max():.1f}%"
            ))
            
            suite.add_test(TestResult(
                "Validare Puls (30-200 bpm)",
                pulse_valid,
                f"Min: {df['Pulse'].min():.0f} bpm, Max: {df['Pulse'].max():.0f} bpm"
            ))
    
    except Exception as e:
        suite.add_test(TestResult(
            "Import module parsing",
            False,
            f"Eroare critică: {str(e)}"
        ))
    
    suite.end_time = datetime.now()
    suite.print_summary()
    return suite

# ==============================================================================
# TEST 2: PARSING PDF
# ==============================================================================

def test_pdf_parsing():
    """Testează parsing PDF cu diverse scenarii"""
    suite = TestSuite("TEST 2: PARSING PDF")
    suite.start_time = datetime.now()
    
    print(f"\n{BLUE}{'='*70}")
    print(f"📄 {suite.name}")
    print(f"{'='*70}{RESET}\n")
    
    try:
        from pdf_parser import parse_checkme_o2_report, PDF_SUPPORT
        
        # Test 2.1: Verificare pdfplumber instalat
        suite.add_test(TestResult(
            "Biblioteca pdfplumber disponibilă",
            PDF_SUPPORT,
            "pdfplumber instalat cu succes" if PDF_SUPPORT else "INSTALAȚI: pip install pdfplumber"
        ))
        
        if PDF_SUPPORT:
            # Test 2.2: Parsing PDF standard
            test_pdf_path = "de modificat reguli/Checkme O2 0331_70_100_20251015203510.pdf"
            if os.path.exists(test_pdf_path):
                try:
                    parsed_data = parse_checkme_o2_report(test_pdf_path)
                    
                    has_device = bool(parsed_data.get('device_info', {}).get('device_number'))
                    has_stats = bool(parsed_data.get('statistics', {}))
                    has_raw_text = bool(parsed_data.get('raw_text', ''))
                    
                    suite.add_test(TestResult(
                        "Parsing PDF Standard Checkme O2",
                        has_device or has_stats or has_raw_text,
                        f"Device: {parsed_data.get('device_info', {}).get('device_number', 'N/A')}, "
                        f"Stats: {len(parsed_data.get('statistics', {}))} câmpuri"
                    ))
                    
                    # Test 2.3: Extragere statistici SpO2
                    stats = parsed_data.get('statistics', {})
                    has_spo2_avg = stats.get('avg_spo2') is not None
                    has_spo2_min = stats.get('min_spo2') is not None
                    has_spo2_max = stats.get('max_spo2') is not None
                    
                    suite.add_test(TestResult(
                        "Extragere statistici SpO2",
                        has_spo2_avg or has_spo2_min or has_spo2_max,
                        f"Avg: {stats.get('avg_spo2', 'N/A')}, "
                        f"Min: {stats.get('min_spo2', 'N/A')}, "
                        f"Max: {stats.get('max_spo2', 'N/A')}"
                    ))
                    
                    # Test 2.4: Extragere evenimente
                    events = parsed_data.get('events', {})
                    has_events = len(events) > 0
                    
                    suite.add_test(TestResult(
                        "Extragere evenimente detectate",
                        has_events,
                        f"{len(events)} tipuri de evenimente găsite"
                    ))
                    
                except Exception as e:
                    suite.add_test(TestResult(
                        "Parsing PDF Standard Checkme O2",
                        False,
                        f"Eroare: {str(e)}"
                    ))
            else:
                suite.add_test(TestResult(
                    "Parsing PDF Standard Checkme O2",
                    False,
                    f"Fișier test nu există: {test_pdf_path}"
                ))
        
    except Exception as e:
        suite.add_test(TestResult(
            "Import module PDF",
            False,
            f"Eroare critică: {str(e)}"
        ))
    
    suite.end_time = datetime.now()
    suite.print_summary()
    return suite

# ==============================================================================
# TEST 3: LINK-URI PERSISTENTE
# ==============================================================================

def test_patient_links():
    """Testează funcționalitatea link-uri pacienți"""
    suite = TestSuite("TEST 3: LINK-URI PERSISTENTE")
    suite.start_time = datetime.now()
    
    print(f"\n{BLUE}{'='*70}")
    print(f"🔗 {suite.name}")
    print(f"{'='*70}{RESET}\n")
    
    try:
        import patient_links
        
        # Test 3.1: Încărcare link-uri existente
        links = patient_links.load_patient_links()
        suite.add_test(TestResult(
            "Încărcare link-uri din JSON",
            isinstance(links, dict),
            f"{len(links)} link-uri găsite"
        ))
        
        # Test 3.2: Validare structură metadata
        if len(links) > 0:
            sample_token = list(links.keys())[0]
            sample_data = links[sample_token]
            
            required_fields = ['device_name', 'created_at', 'is_active', 'recording_date']
            has_required = all(field in sample_data for field in required_fields)
            
            suite.add_test(TestResult(
                "Validare structură metadata",
                has_required,
                f"Token exemplu: {sample_token[:8]}..."
            ))
            
            # Test 3.3: Verificare tracking vizualizări
            has_tracking = 'view_count' in sample_data and 'first_viewed_at' in sample_data
            suite.add_test(TestResult(
                "Tracking vizualizări implementat",
                has_tracking,
                f"Views: {sample_data.get('view_count', 0)}"
            ))
            
            # Test 3.4: Verificare notițe medicale
            has_medical_notes = 'medical_notes' in sample_data
            suite.add_test(TestResult(
                "Câmp notițe medicale disponibil",
                has_medical_notes,
                "Câmp medical_notes prezent în metadata"
            ))
        
        # Test 3.5: Validare token UUID format
        if len(links) > 0:
            sample_token = list(links.keys())[0]
            import uuid
            try:
                uuid_obj = uuid.UUID(sample_token)
                is_uuid4 = uuid_obj.version == 4
                suite.add_test(TestResult(
                    "Token-uri UUID v4 (criptografic sigur)",
                    is_uuid4,
                    f"Token {sample_token[:8]}... este UUID v4"
                ))
            except ValueError:
                suite.add_test(TestResult(
                    "Token-uri UUID v4 (criptografic sigur)",
                    False,
                    "Token nu este UUID valid"
                ))
        
    except Exception as e:
        suite.add_test(TestResult(
            "Import module patient_links",
            False,
            f"Eroare critică: {str(e)}"
        ))
    
    suite.end_time = datetime.now()
    suite.print_summary()
    return suite

# ==============================================================================
# TEST 4: PRIVACY AUDIT
# ==============================================================================

def test_privacy_audit():
    """Auditează aplicația pentru date personale (GDPR compliance)"""
    suite = TestSuite("TEST 4: PRIVACY AUDIT (GDPR)")
    suite.start_time = datetime.now()
    
    print(f"\n{BLUE}{'='*70}")
    print(f"🔒 {suite.name}")
    print(f"{'='*70}{RESET}\n")
    
    # Lista cu date personale interzise (excludem campuri valide)
    FORBIDDEN_TERMS = [
        'nume', 'prenume', 'cnp', 'telefon', 'email', 'adresa', 'adresă',
        'surname', 'phone', 'address', 'ssn', 'social security'
    ]
    # EXCLUDEM: 'name' (device_name, filename sunt OK)
    
    try:
        # Test 4.1: Audit patient_links.json
        if os.path.exists('patient_links.json'):
            with open('patient_links.json', 'r', encoding='utf-8') as f:
                content = f.read().lower()
            
            found_terms = [term for term in FORBIDDEN_TERMS if term in content]
            
            suite.add_test(TestResult(
                "patient_links.json - Zero date personale",
                len(found_terms) == 0,
                "Niciun termen suspect găsit" if len(found_terms) == 0 else f"ATENȚIE: {found_terms}"
            ))
        
        # Test 4.2: Audit CSV-uri de test
        test_csv = "bach data/Checkme O2 3539_20251007230437.csv"
        if os.path.exists(test_csv):
            with open(test_csv, 'r', encoding='utf-8', errors='ignore') as f:
                csv_content = f.read().lower()
            
            found_in_csv = [term for term in FORBIDDEN_TERMS if term in csv_content and term not in ['time', 'date']]
            
            suite.add_test(TestResult(
                "CSV de test - Zero date personale",
                len(found_in_csv) == 0,
                "CSV conține doar date medicale" if len(found_in_csv) == 0 else f"ATENȚIE: {found_in_csv}"
            ))
        
        # Test 4.3: Verificare structură stocare (folderele patient_data)
        if os.path.exists('patient_data'):
            patient_folders = [f for f in os.listdir('patient_data') if os.path.isdir(os.path.join('patient_data', f))]
            
            # Verificăm că toate folderele sunt UUID-uri
            import uuid
            all_uuids = all(
                len(folder) == 36 and '-' in folder  # Format UUID
                for folder in patient_folders
            )
            
            suite.add_test(TestResult(
                "Folderele pacienți - Nume UUID (anonime)",
                all_uuids,
                f"{len(patient_folders)} foldere, toate UUID"
            ))
        
        # Test 4.4: Verificare log-uri (nu trebuie să conțină date personale)
        log_file = "output/LOGS/app_activity.log"
        if os.path.exists(log_file):
            # Citim ultimele 100 linii
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                log_lines = f.readlines()[-100:]
                log_content = ' '.join(log_lines).lower()
            
            found_in_logs = [term for term in FORBIDDEN_TERMS if term in log_content]
            
            suite.add_test(TestResult(
                "Log-uri aplicație - Zero date personale",
                len(found_in_logs) == 0,
                "Log-uri curate" if len(found_in_logs) == 0 else f"ATENȚIE: {found_in_logs}"
            ))
        
    except Exception as e:
        suite.add_test(TestResult(
            "Privacy audit",
            False,
            f"Eroare: {str(e)}"
        ))
    
    suite.end_time = datetime.now()
    suite.print_summary()
    return suite

# ==============================================================================
# TEST 5: PERFORMANȚĂ
# ==============================================================================

def test_performance():
    """Testează performanța sistemului (parsing < 2s, grafice < 3s)"""
    suite = TestSuite("TEST 5: PERFORMANȚĂ")
    suite.start_time = datetime.now()
    
    print(f"\n{BLUE}{'='*70}")
    print(f"⚡ {suite.name}")
    print(f"{'='*70}{RESET}\n")
    
    try:
        import time
        from data_parser import parse_csv_data
        from plot_generator import create_plot
        
        # Test 5.1: Parsing CSV < 2s (10,000 rânduri target)
        test_csv = "bach data/Checkme O2 3539_20251007230437.csv"
        if os.path.exists(test_csv):
            with open(test_csv, 'rb') as f:
                content = f.read()
            
            start = time.time()
            df = parse_csv_data(content, os.path.basename(test_csv))
            parsing_time = time.time() - start
            
            suite.add_test(TestResult(
                "CSV Parsing < 2s",
                parsing_time < 2.0,
                f"{parsing_time:.3f}s pentru {len(df)} rânduri ({len(df)/parsing_time:.0f} rânduri/s)"
            ))
            
            # Test 5.2: Generare grafic < 3s
            if len(df) > 0:
                start = time.time()
                fig = create_plot(df, os.path.basename(test_csv))
                plot_time = time.time() - start
                
                suite.add_test(TestResult(
                    "Generare grafic < 3s",
                    plot_time < 3.0,
                    f"{plot_time:.3f}s pentru grafic cu {len(df)} puncte"
                ))
        
    except Exception as e:
        suite.add_test(TestResult(
            "Test performanță",
            False,
            f"Eroare: {str(e)}"
        ))
    
    suite.end_time = datetime.now()
    suite.print_summary()
    return suite

# ==============================================================================
# MAIN - EXECUȚIE TESTE
# ==============================================================================

def main():
    """Rulează toate testele și generează raport final"""
    # Nu mai schimbăm stdout - probleme cu Windows
    
    print(f"\n{BLUE}{'='*70}")
    print(f"TEST EXTENSIV SISTEM PULSOXIMETRIE - test1")
    print(f"{'='*70}{RESET}")
    print(f"\n{YELLOW}Data: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Working Directory: {os.getcwd()}{RESET}\n")
    
    # Rulăm toate suite-urile de teste
    suites = [
        test_csv_parsing(),
        test_pdf_parsing(),
        test_patient_links(),
        test_privacy_audit(),
        test_performance()
    ]
    
    # Raport final
    print(f"\n{BLUE}{'='*70}")
    print(f">>> RAPORT FINAL")
    print(f"{'='*70}{RESET}\n")
    
    total_passed = 0
    total_tests = 0
    
    for suite in suites:
        passed, total = suite.summary()
        total_passed += passed
        total_tests += total
        
        status = GREEN if passed == total else RED
        print(f"{status}{suite.name:.<50} {passed}/{total}{RESET}")
    
    print(f"\n{'─'*70}")
    
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    if success_rate == 100:
        final_status = f"{GREEN}[SUCCESS] SUCCES COMPLET"
    elif success_rate >= 80:
        final_status = f"{YELLOW}[WARNING] PARTIAL REUSIT"
    else:
        final_status = f"{RED}[ERROR] ERORI CRITICE"
    
    print(f"\n{final_status}")
    print(f"{'='*70}")
    print(f"TOTAL: {total_passed}/{total_tests} teste trecute ({success_rate:.1f}%)")
    print(f"{'='*70}{RESET}\n")
    
    # Recomandari
    if success_rate < 100:
        print(f"\n{YELLOW}RECOMANDARI:")
        print(f"  1. Verificati log-urile in output/LOGS/app_activity.log")
        print(f"  2. Consultati GHID_TESTARE_PDF.md pentru detalii")
        print(f"  3. Raportati erorile gasite{RESET}\n")
    else:
        print(f"\n{GREEN}Toate testele au trecut cu succes!")
        print(f"   Sistemul este gata de utilizare!{RESET}\n")
    
    return 0 if success_rate == 100 else 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[!] Testare intrerupta de utilizator.{RESET}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{RED}[ERROR] EROARE CRITICA: {str(e)}{RESET}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

