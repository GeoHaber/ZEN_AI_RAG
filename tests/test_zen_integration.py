#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
test_zen_integration.py - Verify Phase 5 Integration
Tests that LocalLLMManager is properly integrated into ZenBrain
"""
import sys
from pathlib import Path

# Add paths
# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_zen_brain_imports():
    """Test that ZenBrain and LocalLLMManager import correctly"""
    print("✓ Testing imports...")
    try:
        from zena_mode.heart_and_brain import ZenBrain, zen_brain
        from local_llm import LocalLLMManager
        print("  ✓ ZenBrain imported successfully")
        print("  ✓ LocalLLMManager imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_zen_brain_initialization():
    """Test that ZenBrain initializes correctly"""
    print("✓ Testing ZenBrain initialization...")
    try:
        from zena_mode.heart_and_brain import ZenBrain
        from config_system import config
        ZenBrain(Path(config.MODEL_DIR))
        print("  ✓ ZenBrain instance created")
        return True
    except Exception as e:
        print(f"  ✗ Initialization failed: {e}")
        return False

def test_zen_brain_wake_up():
    """Test that ZenBrain can wake up and discover models"""
    print("✓ Testing ZenBrain.wake_up()...")
    try:
        from zena_mode.heart_and_brain import ZenBrain
        from config_system import config
        brain = ZenBrain(Path(config.MODEL_DIR))
        status = brain.wake_up()
        
        print(f"  ✓ Wake up successful")
        print(f"  ✓ llama.cpp ready: {status.llama_cpp_ready}")
        print(f"  ✓ Models discovered: {status.models_discovered}")
        
        if status.models:
            print(f"  ✓ Available models: {len(status.models)}")
            print(f"    - {status.models[0].name}")
        
        return True
    except Exception as e:
        print(f"  ✗ Wake up failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_zen_brain_recommendation():
    """Test that ZenBrain can recommend models"""
    print("✓ Testing model recommendation...")
    try:
        from zena_mode.heart_and_brain import ZenBrain
        from config_system import config
        brain = ZenBrain(Path(config.MODEL_DIR))
        brain.wake_up()
        
        recommended = brain.recommend_model()
        if recommended:
            print(f"  ✓ Recommended model: {recommended}")
        else:
            print(f"  ⚠ No models available to recommend")
        
        return True
    except Exception as e:
        print(f"  ✗ Recommendation failed: {e}")
        return False

def test_no_dead_code():
    """Verify that dead code files have been deleted"""
    print("✓ Checking for dead code...")
    try:
        voice_engine_path = Path(__file__).parent / "zena_mode" / "voice_engine.py"
        exp_voice_path = Path(__file__).parent / "experimental_voice_lab"
        
        if voice_engine_path.exists():
            print(f"  ✗ voice_engine.py still exists: {voice_engine_path}")
            return False
        else:
            print(f"  ✓ voice_engine.py deleted")
        
        if exp_voice_path.exists():
            print(f"  ✗ experimental_voice_lab still exists: {exp_voice_path}")
            return False
        else:
            print(f"  ✓ experimental_voice_lab deleted")
        
        return True
    except Exception as e:
        print(f"  ✗ Dead code check failed: {e}")
        return False

def main():
    """Main."""
    print("\n" + "="*60)
    print("PHASE 5 INTEGRATION TEST")
    print("="*60 + "\n")
    
    tests = [
        ("Imports", test_zen_brain_imports),
        ("Initialization", test_zen_brain_initialization),
        ("Wake Up", test_zen_brain_wake_up),
        ("Recommendation", test_zen_brain_recommendation),
        ("Dead Code Cleanup", test_no_dead_code),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ Test {name} crashed: {e}")
            results.append((name, False))
        print()
    
    # Summary
    print("="*60)
    print("RESULTS")
    print("="*60)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{'✓ ALL TESTS PASSED' if passed == total else f'✗ {total - passed} TESTS FAILED'}")
    print(f"Score: {passed}/{total}\n")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
