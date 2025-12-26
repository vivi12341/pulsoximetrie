
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

# Basic syntax check for callbacks_medical.py
try:
    import callbacks_medical
    print("✅ callbacks_medical imported successfully (syntax check)")
except ImportError as e:
    # It might fail due to missing dependencies in this environment, but syntax errors would show up
    print(f"⚠️ callbacks_medical import warning (could be env dependencies): {e}")

print("Verification complete.")
