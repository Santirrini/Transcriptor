import os
import sys
import json
import time
from pathlib import Path

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.audit_logger import audit_logger, AuditEventType

def test_audit_logging():
    print("Testing Audit Logger...")
    
    # 1. Log a simple event
    print("Logging APP_START...")
    audit_logger.log_event(AuditEventType.APP_START, "Test Script Started")
    
    # 2. Log file open
    print("Logging FILE_OPEN...")
    audit_logger.log_file_open("C:/Users/Test/audio.mp3", 1024*1024)
    
    # 3. Log security event
    print("Logging SECURITY_EVENT...")
    audit_logger.log_security_event(
        AuditEventType.SECURITY_VALIDATION_FAIL, 
        "Test security alert", 
        {"ip": "127.0.0.1"}
    )
    
    # 4. Check log file
    log_file = audit_logger.current_audit_file
    print(f"Checking log file: {log_file}")
    
    if not log_file.exists():
        print("FAIL: Log file does not exist!")
        return
        
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        print(f"Found {len(lines)} lines in log file.")
        
        last_line = lines[-1]
        try:
            data = json.loads(last_line)
            print("Last log entry parsed successfully:")
            print(json.dumps(data, indent=2))
            
            if data["event_type"] == AuditEventType.SECURITY_VALIDATION_FAIL.value:
                print("SUCCESS: Last event matches expected type.")
            else:
                print(f"FAIL: Expected SECURITY_VALIDATION_FAIL, got {data['event_type']}")
                
        except json.JSONDecodeError:
            print("FAIL: Could not parse last line as JSON")

if __name__ == "__main__":
    test_audit_logging()
