"""
Verification Script: Patient Data Integrity Check
Usage: python verify_patient_data.py <token>

Tests the complete data flow for a patient token:
1. Token validation
2. Metadata retrieval
3. Recordings check
4. DataFrame loading via data_service
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import patient_links
import data_service
from logger_setup import logger

def verify_patient(token):
    """Comprehensive verification of patient data availability."""
    print(f"\n{'='*80}")
    print(f"🔍 VERIFYING PATIENT DATA FOR TOKEN: {token[:8]}...")
    print(f"{'='*80}\n")
    
    # Step 1: Token Validation
    print("📋 Step 1: Token Validation")
    print("-" * 80)
    is_valid = patient_links.validate_token(token)
    print(f"  → Valid: {'✅ YES' if is_valid else '❌ NO'}\n")
    
    if not is_valid:
        print("❌ VERIFICATION FAILED: Token invalid or inactive!")
        return False
    
    # Step 2: Patient Metadata
    print("📋 Step 2: Patient Metadata")
    print("-" * 80)
    metadata = patient_links.get_patient_link(token, track_view=False)
    if metadata:
        print(f"  → Device: {metadata.get('device_name', 'N/A')}")
        print(f"  → Created: {metadata.get('created_at', 'N/A')}")
        print(f"  → Recording Date: {metadata.get('recording_date', 'N/A')}")
        print(f"  → Start Time: {metadata.get('start_time', 'N/A')}")
        print(f"  → End Time: {metadata.get('end_time', 'N/A')}")
        print(f"  → Active: {metadata.get('is_active', 'N/A')}\n")
    else:
        print("❌ VERIFICATION FAILED: No metadata found!\n")
        return False
    
    # Step 3: Recordings Check
    print("📋 Step 3: Recordings Check")
    print("-" * 80)
    recordings = patient_links.get_patient_recordings(token)
    print(f"  → Found: {len(recordings)} recording(s)\n")
    
    if recordings:
        for idx, rec in enumerate(recordings):
            print(f"  Recording #{idx+1}:")
            print(f"    - Filename: {rec.get('original_filename', 'N/A')}")
            print(f"    - Storage Type: {rec.get('storage_type', 'unknown')}")
            print(f"    - CSV Path: {rec.get('csv_path', 'N/A')}")
            print(f"    - R2 URL: {rec.get('r2_url', 'N/A')}")
            print(f"    - Uploaded: {rec.get('uploaded_at', 'N/A')}\n")
    else:
        print("⚠️  WARNING: No recordings found (data may not be uploaded yet)\n")
    
    # Step 4: Data Service Test (Critical)
    print("📋 Step 4: Data Service DataFrame Loading")
    print("-" * 80)
    try:
        df, filename, status = data_service.get_patient_dataframe(token)
        
        if df is not None:
            print(f"  ✅ SUCCESS! DataFrame loaded:")
            print(f"    - Rows: {len(df)}")
            print(f"    - Columns: {list(df.columns)}")
            print(f"    - Index Type: {type(df.index)}")
            print(f"    - First Timestamp: {df.index[0] if len(df) > 0 else 'N/A'}")
            print(f"    - Last Timestamp: {df.index[-1] if len(df) > 0 else 'N/A'}")
            print(f"    - Status: {status}")
            print(f"    - Filename: {filename}\n")
            
            print("="*80)
            print("✅ VERIFICATION PASSED: Patient data is complete and accessible!")
            print("="*80)
            return True
        else:
            print(f"  ❌ FAILED! DataFrame is None")
            print(f"    - Status: {status}")
            print(f"    - Filename: {filename}\n")
            
            print("="*80)
            print("❌ VERIFICATION FAILED: Data loading failed!")
            print(f"   Reason: {status}")
            print("="*80)
            return False
            
    except Exception as e:
        print(f"  💥 EXCEPTION: {e}\n")
        
        print("="*80)
        print("❌ VERIFICATION FAILED: Critical exception during data loading!")
        print(f"   Error: {str(e)}")
        print("="*80)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Use example token from user's issue
        token = "c9bace29-05d0-4d8d-a62e-7b256e716294"
        print(f"⚠️  No token provided, using example: {token}\n")
    else:
        token = sys.argv[1]
    
    try:
        success = verify_patient(token)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Verification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n💥 FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
