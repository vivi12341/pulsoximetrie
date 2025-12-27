
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
    
    # Test Truncation
    long_msg = "A" * 1500
    memory_handler.emit(logging.LogRecord("test_long", logging.INFO, "test", 1, long_msg, None, None))
    
    logs = memory_handler.get_logs_text()
    
    # Check if truncated
    if "TRUNCATED" in logs:
            print("✅ Log truncation working (Long message handled)")
    else:
            print("❌ Log truncation FAILED")

except Exception as e:
    print(f"❌ Error testing Memory Handler: {e}")

print("Verification complete.")
