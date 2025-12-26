
try:
    import data_service
    print("✅ data_service imported successfully")
except ImportError as e:
    print(f"❌ Failed to import data_service: {e}")
    exit(1)

if hasattr(data_service, 'get_patient_dataframe'):
    print("✅ get_patient_dataframe function exists")
else:
    print("❌ get_patient_dataframe function MISSING")
    exit(1)

print("Verification complete.")
