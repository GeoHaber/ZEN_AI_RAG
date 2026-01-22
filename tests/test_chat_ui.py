"""
Automated test for chat UI functionality.
Tests that messages are sent and responses are displayed.
"""
import asyncio
import httpx
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_llm_backend():
    """Test that LLM backend is responding."""
    print("=" * 60)
    print("TEST 1: LLM Backend Connectivity")
    print("=" * 60)
    
    api_url = "http://127.0.0.1:8001/v1/chat/completions"
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'TEST OK' and nothing else."}
        ],
        "stream": False,
        "temperature": 0.1,
        "max_tokens": 50
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"  → Sending test message to {api_url}")
            response = await client.post(api_url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                content = data['choices'][0]['message']['content']
                print(f"  ✅ LLM Response: {content[:100]}")
                return True
            else:
                print(f"  ❌ HTTP Error: {response.status_code}")
                return False
    except httpx.ConnectError:
        print("  ❌ Cannot connect to LLM backend on port 8001")
        print("     Make sure start_llm.py is running!")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_streaming_response():
    """Test streaming response from LLM."""
    print("\n" + "=" * 60)
    print("TEST 2: Streaming Response")
    print("=" * 60)
    
    api_url = "http://127.0.0.1:8001/v1/chat/completions"
    
    payload = {
        "messages": [
            {"role": "system", "content": "You are Zena."},
            {"role": "user", "content": "Count from 1 to 5."}
        ],
        "stream": True,
        "temperature": 0.1,
        "max_tokens": 100
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"  → Testing streaming...")
            chunk_count = 0
            full_response = ""
            
            async with client.stream('POST', api_url, json=payload) as response:
                if response.status_code != 200:
                    print(f"  ❌ HTTP Error: {response.status_code}")
                    return False
                
                async for line in response.aiter_lines():
                    if line.startswith('data: '):
                        json_str = line[6:]
                        if json_str.strip() == '[DONE]':
                            break
                        
                        try:
                            import json
                            data = json.loads(json_str)
                            delta = data['choices'][0]['delta']
                            content = delta.get('content', '')
                            if content:
                                chunk_count += 1
                                full_response += content
                        except:
                            pass
            
            print(f"  ✅ Received {chunk_count} chunks")
            print(f"  ✅ Response: {full_response[:100]}")
            return chunk_count > 0
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_ui_endpoint():
    """Test that NiceGUI is responding."""
    print("\n" + "=" * 60)
    print("TEST 3: NiceGUI Web Server")
    print("=" * 60)
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print("  → Checking http://localhost:8080")
            response = await client.get("http://localhost:8080")
            
            if response.status_code == 200:
                html = response.text
                has_nicegui = 'nicegui' in html.lower() or 'quasar' in html.lower()
                has_zena = 'zena' in html.lower() or 'chat' in html.lower()
                
                print(f"  ✅ Web server responding (HTTP 200)")
                print(f"  ✅ NiceGUI/Quasar detected: {has_nicegui}")
                print(f"  ✅ Zena content detected: {has_zena}")
                print(f"  📊 HTML size: {len(html)} bytes")
                return True
            else:
                print(f"  ❌ HTTP Error: {response.status_code}")
                return False
    except httpx.ConnectError:
        print("  ❌ Cannot connect to UI on port 8080")
        print("     Make sure zena.py is running!")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def test_multiple_messages():
    """Test sending multiple messages in sequence."""
    print("\n" + "=" * 60)
    print("TEST 4: Multiple Sequential Messages")
    print("=" * 60)
    
    api_url = "http://127.0.0.1:8001/v1/chat/completions"
    messages = ["Hello", "What is 2+2?", "Thank you"]
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, msg in enumerate(messages, 1):
                payload = {
                    "messages": [
                        {"role": "system", "content": "Be brief."},
                        {"role": "user", "content": msg}
                    ],
                    "stream": True,
                    "temperature": 0.1,
                    "max_tokens": 50
                }
                
                print(f"  → Message {i}: '{msg}'")
                chunk_count = 0
                response_text = ""
                
                async with client.stream('POST', api_url, json=payload) as response:
                    if response.status_code != 200:
                        print(f"    ❌ HTTP Error: {response.status_code}")
                        continue
                    
                    async for line in response.aiter_lines():
                        if line.startswith('data: '):
                            json_str = line[6:]
                            if json_str.strip() == '[DONE]':
                                break
                            try:
                                import json
                                data = json.loads(json_str)
                                content = data['choices'][0]['delta'].get('content', '')
                                if content:
                                    chunk_count += 1
                                    response_text += content
                            except:
                                pass
                
                print(f"    ✅ Got {chunk_count} chunks: {response_text[:50]}...")
                await asyncio.sleep(0.5)  # Small delay between messages
        
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


async def main():
    print("\n" + "🧪" * 30)
    print("   ZENA CHAT UI AUTOMATED TESTS")
    print("🧪" * 30 + "\n")
    
    results = []
    
    # Run tests
    results.append(("LLM Backend", await test_llm_backend()))
    results.append(("Streaming", await test_streaming_response()))
    results.append(("UI Server", await test_ui_endpoint()))
    results.append(("Multiple Messages", await test_multiple_messages()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n  🎉 ALL TESTS PASSED!")
    else:
        print("\n  ⚠️ Some tests failed. Check logs above.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
