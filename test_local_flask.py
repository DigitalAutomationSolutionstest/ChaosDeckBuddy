#!/usr/bin/env python3
"""
Test locale per verificare Flask
"""

import requests
import time

def test_local_flask():
    """Test Flask locale"""
    try:
        # Test locale
        response = requests.get('http://localhost:5000/health', timeout=5)
        print(f"✅ Local Flask health check: {response.status_code}")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"❌ Local Flask test failed: {e}")
        return False

def test_ngrok_status():
    """Test ngrok status"""
    try:
        # Get ngrok status
        response = requests.get('http://localhost:4040/api/tunnels', timeout=5)
        if response.status_code == 200:
            tunnels = response.json()['tunnels']
            for tunnel in tunnels:
                if tunnel['config']['addr'] == 'localhost:5000':
                    print(f"✅ Ngrok tunnel found: {tunnel['public_url']}")
                    return tunnel['public_url']
        print("❌ No ngrok tunnel found")
        return None
    except Exception as e:
        print(f"❌ Ngrok status check failed: {e}")
        return None

def main():
    print("🔍 Testing Flask and Ngrok...")
    print("=" * 40)
    
    # Test Flask locale
    flask_ok = test_local_flask()
    
    # Test ngrok
    ngrok_url = test_ngrok_status()
    
    if flask_ok and ngrok_url:
        print(f"\n🎉 Everything is working!")
        print(f"🌐 Ngrok URL: {ngrok_url}")
        print(f"🔗 Health check: {ngrok_url}/health")
        print(f"🔗 Webhook: {ngrok_url}/webhook")
    else:
        print("\n⚠️ Some issues detected")
        if not flask_ok:
            print("- Flask server not responding")
        if not ngrok_url:
            print("- Ngrok tunnel not found")

if __name__ == "__main__":
    main() 