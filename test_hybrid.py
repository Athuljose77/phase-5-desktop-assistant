"""
Phase-5 — Hybrid AI Verification Script
Tests that all components of the hybrid system work correctly.
"""

import sys
import os

sys.path.append(os.getcwd())

def test_connectivity():
    """Test 1: Internet connectivity check returns a bool."""
    print("\n[1] Testing connectivity.check_internet()...", flush=True)
    from core.connectivity import check_internet  # type: ignore[import-not-found]
    result = check_internet()
    assert isinstance(result, bool), f"Expected bool, got {type(result)}"
    print(f"    Result: {'ONLINE' if result else 'OFFLINE'}", flush=True)
    print("    PASS", flush=True)
    return result

def test_config():
    """Test 2: Config loads correctly."""
    print("\n[2] Testing config loading...", flush=True)
    from config import (  # type: ignore[import-not-found]
        ONLINE_API_KEY, ONLINE_MODEL, ONLINE_BASE_URL,
        OFFLINE_MODEL, OLLAMA_URL, is_online_configured,
    )
    print(f"    Online model:  {ONLINE_MODEL}", flush=True)
    print(f"    Online URL:    {ONLINE_BASE_URL}", flush=True)
    print(f"    Offline model: {OFFLINE_MODEL}", flush=True)
    print(f"    Ollama URL:    {OLLAMA_URL}", flush=True)
    print(f"    API key set:   {is_online_configured()}", flush=True)
    print("    PASS", flush=True)

def test_offline_handler():
    """Test 3: OfflineHandler can be instantiated."""
    print("\n[3] Testing OfflineHandler instantiation...", flush=True)
    from core.offline_handler import OfflineHandler  # type: ignore[import-not-found]
    handler = OfflineHandler()
    assert handler.model == "qwen2.5:1.5b"
    print(f"    Model: {handler.model}", flush=True)
    print("    PASS", flush=True)

def test_online_handler():
    """Test 4: OnlineHandler can be instantiated."""
    print("\n[4] Testing OnlineHandler instantiation...", flush=True)
    from core.online_handler import OnlineHandler  # type: ignore[import-not-found]
    handler = OnlineHandler(api_key="test-key")
    assert handler.model == "llama-3.3-70b-versatile"
    print(f"    Model: {handler.model}", flush=True)
    print("    PASS", flush=True)

def test_hybrid_handler():
    """Test 5: HybridAIHandler routes correctly."""
    print("\n[5] Testing HybridAIHandler...", flush=True)
    from core.hybrid_handler import HybridAIHandler  # type: ignore[import-not-found]

    # Without API key → should default to offline
    handler = HybridAIHandler()
    assert handler.current_mode == "offline"
    print(f"    Default mode (no key): {handler.current_mode}", flush=True)

    # With a dummy API key → should still have online handler ready
    handler2 = HybridAIHandler(api_key="real-key-here")
    assert handler2._online is not None
    print(f"    With key: online handler created = {handler2._online is not None}", flush=True)
    print("    PASS", flush=True)

def test_backward_compat():
    """Test 6: AIHandler backward-compatible import still works."""
    print("\n[6] Testing backward compatibility (AIHandler import)...", flush=True)
    from core.ai_handler import AIHandler  # type: ignore[import-not-found]
    handler = AIHandler()
    assert handler.model == "qwen2.5:1.5b"
    print(f"    AIHandler model: {handler.model}", flush=True)
    print("    PASS", flush=True)


if __name__ == "__main__":
    print("=" * 50)
    print("Phase-5 Hybrid AI — Verification")
    print("=" * 50)
    
    tests = [
        test_connectivity,
        test_config,
        test_offline_handler,
        test_online_handler,
        test_hybrid_handler,
        test_backward_compat,
    ]
    
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1  # type: ignore[operator]
        except Exception as e:
            print(f"    FAIL: {e}", flush=True)
            failed += 1  # type: ignore[operator]
    
    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)
