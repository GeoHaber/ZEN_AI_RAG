#!/usr/bin/env python3
"""Test TTS synthesis"""

import asyncio
from zena_mode.voice_manager import get_voice_manager

async def test_tts():
    vm = get_voice_manager()
    
    print("Testing TTS Synthesis...\n")
    
    # Test 1: Simple synthesis
    print("1️⃣ Testing basic synthesis...")
    result = vm.synthesize("Hello, this is a test.")
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Duration: {result['duration']} seconds")
        print(f"   Audio data: {len(result['audio_data'])} chars (base64)")
        print(f"   Has audio URL: {'audio_url' in result and bool(result['audio_url'])}")
    else:
        print(f"   Error: {result.get('error')}")
    
    # Test 2: Longer text
    print("\n2️⃣ Testing longer synthesis...")
    long_text = "Artificial Intelligence is transforming the world. From healthcare to education, AI is making systems smarter and more efficient."
    result = vm.synthesize(long_text)
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Duration: {result['duration']} seconds")
        print(f"   Audio data: {len(result['audio_data'])} chars")
    
    # Test 3: Cache test
    print("\n3️⃣ Testing cache...")
    result1 = vm.synthesize("Test cache", use_cache=True)
    result2 = vm.synthesize("Test cache", use_cache=True)
    print(f"   First call success: {result1['success']}")
    print(f"   Second call success: {result2['success']}")
    print(f"   Same audio: {result1['audio_data'] == result2['audio_data']}")
    
    print("\n✅ All TTS tests passed!")

if __name__ == '__main__':
    asyncio.run(test_tts())
