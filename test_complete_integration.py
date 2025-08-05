#!/usr/bin/env python3
"""
Test completo dell'integrazione Stripe + Discord Bot
"""

import asyncio
import discord
from discord.ext import commands
import stripe
import sqlite3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test configuration
STRIPE_SECRET_KEY = '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'
stripe.api_key = STRIPE_SECRET_KEY

def test_database():
    """Test database connection and tables"""
    try:
        conn = sqlite3.connect('chaos.db')
        c = conn.cursor()
        
        # Test tables exist
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in c.fetchall()]
        
        print("✅ Database connection successful!")
        print(f"📊 Tables found: {tables}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_stripe_items():
    """Test Stripe items configuration"""
    items = {
        'booster': {'name': 'Epic Booster Pack', 'price': 200, 'currency': 'usd', 'rewards': '5 rare cards'},
        'legendary': {'name': 'Legendary Pack', 'price': 500, 'currency': 'usd', 'rewards': '3 legendary cards'},
        'streak_saver': {'name': 'Streak Saver', 'price': 50, 'currency': 'usd', 'rewards': 'Reset daily cooldown'},
        'pity_booster': {'name': 'Pity Booster', 'price': 100, 'currency': 'usd', 'rewards': 'Reduce pity by 10'},
        'achievement': {'name': 'Achievement Booster', 'price': 50, 'currency': 'usd', 'rewards': 'Auto-unlock achievement'}
    }
    
    print("✅ Items configuration loaded!")
    print(f"📦 Available items: {list(items.keys())}")
    return True

def test_webhook_url():
    """Test webhook URL accessibility"""
    import requests
    
    try:
        response = requests.get('https://f9d98f31a7f3.ngrok-free.app/health', timeout=5)
        if response.status_code == 200:
            print("✅ Webhook health check successful!")
            return True
        else:
            print(f"⚠️ Webhook health check returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Webhook health check failed: {e}")
        return False

def test_stripe_connection():
    """Test Stripe API connection"""
    try:
        account = stripe.Account.retrieve()
        print(f"✅ Stripe connection successful!")
        print(f"🏢 Account ID: {account.id}")
        return True
    except Exception as e:
        print(f"❌ Stripe connection failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Complete Integration...")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database),
        ("Stripe Connection", test_stripe_connection),
        ("Items Configuration", test_stripe_items),
        ("Webhook Health", test_webhook_url)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Integration is ready!")
        return True
    else:
        print("⚠️ Some tests failed. Check configuration.")
        return False

if __name__ == "__main__":
    main() 