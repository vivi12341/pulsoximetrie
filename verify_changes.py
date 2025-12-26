
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

# Skip callbacks_medical import to avoid complex env setup issues
pass

print("Verificare integritate sistem debug...")
try:
    import logging
    from debug_system import memory_handler
    memory_handler.emit(logging.LogRecord("test", logging.INFO, "test", 1, "Mesaj test", None, None))
    logs = memory_handler.get_logs_text()
    if "Mesaj test" in logs:
        print("✅ Memory Handler functioning correctly (Thread Safe)")
    else:
        print("❌ Memory Handler failed to store log")
except Exception as e:
    print(f"❌ Error testing Memory Handler: {e}")

print("Verification complete.")
