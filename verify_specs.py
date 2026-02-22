
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

try:
    from core.system_control import SystemControl  # type: ignore[import-not-found]
    from core.command_handler import CommandHandler  # type: ignore[import-not-found]
except ImportError as e:
    print(f"FAILED: Import error: {e}", flush=True)
    sys.exit(1)

def verify_specs_feature():
    print("Verifying System Specs Feature...", flush=True)
    
    # 1. Test get_system_info
    print("\n[1] Testing SystemControl.get_system_info()...", flush=True)
    try:
        info = SystemControl.get_system_info()
        print(f"Info type: {type(info)}", flush=True)
        print(f"Keys: {list(info.keys())}", flush=True)
        
        # Check critical keys
        required = ["os", "ram_total", "cpu_cores_physical"]
        missing = [k for k in required if k not in info]
        
        if not missing:
            print("PASS: Got all required system info keys.", flush=True)
            print(f"Sample data: {json.dumps(info, indent=2)}", flush=True)
        else:
            print(f"FAIL: Missing keys: {missing}", flush=True)
            
    except Exception as e:
        print(f"FAIL: get_system_info crashed: {e}", flush=True)

    # 2. Test Command Handler detection
    print("\n[2] Testing CommandHandler detection...", flush=True)
    test_phrases = [
        "what are my specs",
        "give me system info",
        "how much ram do i have",
        "tell me about my processor",
    ]
    
    cmd = CommandHandler()
    passed = 0
    for phrase in test_phrases:
        res = cmd.parse(phrase)
        if res[0] == "specs":
            print(f"PASS: '{phrase}' -> {res}", flush=True)
            passed += 1  # type: ignore[operator]
        else:
            print(f"FAIL: '{phrase}' -> {res}", flush=True)
    
    if passed == len(test_phrases):
        print("PASS: All phrases detected correclty.", flush=True)
    else:
        print("FAIL: Some detection phrases failed.", flush=True)

if __name__ == "__main__":
    verify_specs_feature()
