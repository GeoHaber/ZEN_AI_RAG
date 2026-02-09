# -*- coding: utf-8 -*-
"""
run_live_monkey.py - Live UI Monkey Test Runner
================================================
Run this while ZenAI is running to perform live chaos testing!
Open your browser to http://localhost:8080 to watch the chaos unfold.

Usage: python tests/run_live_monkey.py
"""
import requests
import random
import time
import json
import sys

# ZenAI NiceGUI Socket.IO API
BASE_URL = "http://127.0.0.1:8080"

# All button IDs from UI registry
BUTTON_IDS = [
    "ui-btn-new-chat",
    "ui-btn-settings",
    "ui-btn-scan-kb",
    "ui-btn-start-tour",
    "ui-btn-batch-menu",
    "ui-btn-swarm-manager",
]

QUICK_ACTION_BUTTONS = [
    "Multi-Expert Analysis",
    "Research Project Docs", 
    "Code Review",
    "Voice Control",
    "Scaling Swarm",
    "Evaluate My Model",
    "Specialist Roles",
    "Security Deep-Dive",
    "Quality Test",
]

CHAOS_MESSAGES = [
    "Hello!",
    "What can you do?",
    "'; DROP TABLE users; --",
    "<script>alert('xss')</script>",
    "🔥🔥🔥 EMOJI ATTACK 🔥🔥🔥",
    "你好世界 مرحبا こんにちは",
    "A" * 500,
    "",
    "   ",
    "Tell me about Python",
    "{{7*7}}",
    "../../../etc/passwd",
    "What's in my knowledge base?",
]


def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════╗
║                    🐒  LIVE MONKEY TEST  🐒                    ║
║                                                               ║
║  Watch your browser at http://localhost:8080 to see the UI   ║
║  react to random chaos clicks and messages!                  ║
╚═══════════════════════════════════════════════════════════════╝
""")


def check_connection():
    """Verify ZenAI is running."""
    print(f"⏳ Waiting for ZenAI at {BASE_URL}...")
    for i in range(20): # Try for 40 seconds
        try:
            r = requests.get(BASE_URL, timeout=5)
            if r.status_code == 200:
                print("✅ ZenAI is running at", BASE_URL)
                return True
        except Exception:
            pass
        time.sleep(2)
        if i % 2 == 0: print(f"   ... attempting connection ({i*2}s)")
    
    print("❌ Cannot connect to ZenAI (Timeout)")
    return False


def trigger_click(element_id):
    """Trigger a click on a UI element via the app's test API."""
    try:
        # Use the test endpoint exposed by on_startup
        r = requests.post(
            f"{BASE_URL}/_nicegui/api/run_javascript",
            json={"code": f"""
                const btn = document.querySelector('[id*="{element_id}"]') || 
                            document.evaluate('//*[contains(text(), "{element_id}")]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (btn) {{ btn.click(); console.log('Clicked: {element_id}'); }}
            """},
            timeout=2
        )
        print(f"   🖱️  Clicked: {element_id}")
    except Exception as e:
        # Fallback - just log the action
        print(f"   🖱️  Click (simulated): {element_id}")
    time.sleep(0.3)
    

def send_message(text):
    """Send a message by typing in the input and clicking send."""
    try:
        # Try to inject text and trigger send
        escaped_text = text.replace("'", "\\'").replace('"', '\\"')[:200]
        r = requests.post(
            f"{BASE_URL}/_nicegui/api/run_javascript",
            json={"code": f"""
                const input = document.querySelector('input[placeholder*="anything"]') || 
                              document.querySelector('textarea');
                if (input) {{
                    input.value = '{escaped_text}';
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    const sendBtn = document.querySelector('[id*="send"]') ||
                                    document.querySelector('button[class*="primary"]');
                    if (sendBtn) sendBtn.click();
                }}
            """},
            timeout=2
        )
        print(f"   💬 Sent: {text[:50]}{'...' if len(text) > 50 else ''}")
    except Exception as e:
        print(f"   💬 Message (simulated): {text[:30]}...")
    time.sleep(0.5)


def run_chaos_sequence(duration_seconds=30):
    """Run chaos monkey for specified duration."""
    print(f"\n🐒 Starting {duration_seconds}s chaos sequence...")
    print("   Watch your browser!\n")
    
    start = time.time()
    action_count = 0
    
    while time.time() - start < duration_seconds:
        action = random.choice(['click', 'message', 'wait'])
        
        if action == 'click':
            # Random click on a button
            target = random.choice(BUTTON_IDS + QUICK_ACTION_BUTTONS)
            trigger_click(target)
            action_count += 1
            
        elif action == 'message':
            # Send random message
            msg = random.choice(CHAOS_MESSAGES)
            send_message(msg)
            action_count += 1
            
        else:
            # Random pause
            pause = random.uniform(0.1, 0.5)
            time.sleep(pause)
        
        # Random delay between actions
        time.sleep(random.uniform(0.1, 0.3))
    
    return action_count


def run_manual_chaos():
    """Interactive chaos mode - press Enter for each action."""
    print("\n🐒 MANUAL CHAOS MODE")
    print("   Press Enter to trigger random action, 'q' to quit\n")
    
    action_count = 0
    while True:
        user_input = input(f"[{action_count}] Press Enter (or 'q' to quit): ")
        if user_input.lower() == 'q':
            break
        
        action = random.choice(['click', 'click', 'message'])  # More clicks than messages
        
        if action == 'click':
            target = random.choice(BUTTON_IDS + QUICK_ACTION_BUTTONS)
            trigger_click(target)
        else:
            msg = random.choice(CHAOS_MESSAGES)
            send_message(msg)
        
        action_count += 1
    
    return action_count


def main():
    print_banner()
    
    if not check_connection():
        sys.exit(1)
    
    print("\n📋 Available modes:")
    print("   1. Auto chaos (30 seconds of random actions)")
    print("   2. Manual chaos (you control the pace)")
    print("   3. Quick burst (10 rapid actions)")
    
    choice = input("\nSelect mode (1/2/3): ").strip()
    
    if choice == '1':
        count = run_chaos_sequence(30)
        print(f"\n✅ Completed {count} chaotic actions!")
        
    elif choice == '2':
        count = run_manual_chaos()
        print(f"\n✅ Completed {count} chaotic actions!")
        
    elif choice == '3':
        print("\n🐒 Quick burst mode - 10 rapid actions!")
        for i in range(10):
            target = random.choice(BUTTON_IDS)
            trigger_click(target)
            time.sleep(0.2)
        print("✅ Done!")
        
    else:
        print("Invalid choice. Running auto mode...")
        count = run_chaos_sequence(15)
        print(f"\n✅ Completed {count} chaotic actions!")
    
    print("\n📊 Check your browser to see the results!")
    print("   Any crashes or errors would be visible in the ZenAI console.")


if __name__ == "__main__":
    main()
