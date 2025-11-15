"""
Test rapid pentru a verifica detectarea numerelor de telefon
"""
import re
import sys

# Setăm encoding pentru Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Pattern pentru numere de telefon (același ca în doctor_settings.py)
phone_pattern = r'(\+?\d{1,3}[\s.-]?\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}|\b0\d{9}\b)'

# Texte de test
test_cases = [
    "Tel: 0745603880",
    "Tel: 0745 603 880",
    "Tel: 0745-603-880",
    "Tel: +40745603880",
    "Telefon: 0721234567",
    "Mobil: 07XX XXX XXX",
    "Contact: 0264123456 sau 0745603880"
]

print("=" * 60)
print("TEST DETECTARE NUMERE DE TELEFON")
print("=" * 60)

for test_text in test_cases:
    matches = list(re.finditer(phone_pattern, test_text))
    print(f"\nText: {test_text}")
    if matches:
        print(f"OK - Gasite {len(matches)} numar(e):")
        for match in matches:
            phone = match.group(0)
            clean_phone = re.sub(r'[\s.-]', '', phone)
            print(f"   - '{phone}' -> tel:{clean_phone}")
    else:
        print("FAIL - Niciun numar de telefon detectat")

print("\n" + "=" * 60)
print("TEST COMPLETAT")
print("=" * 60)

