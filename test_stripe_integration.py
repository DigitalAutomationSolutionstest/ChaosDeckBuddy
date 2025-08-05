#!/usr/bin/env python3
"""
Test script per verificare l'integrazione Stripe
"""

import stripe
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test Stripe configuration
STRIPE_SECRET_KEY = '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'
stripe.api_key = STRIPE_SECRET_KEY

def test_stripe_connection():
    """Test basic Stripe connection"""
    try:
        # Try to retrieve account information
        account = stripe.Account.retrieve()
        print(f"✅ Stripe connection successful!")
        print(f"Account ID: {account.id}")
        print(f"Account name: {account.business_profile.name}")
        return True
    except Exception as e:
        print(f"❌ Stripe connection failed: {e}")
        return False

def test_create_checkout_session():
    """Test creating a checkout session"""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': 'Test Item',
                        'description': 'Test description'
                    },
                    'unit_amount': 200  # $2.00
                },
                'quantity': 1
            }],
            mode='payment',
            metadata={
                'user_id': '123456789',
                'item_id': 'test_item'
            },
            success_url='https://discord.com/channels/@me',
            cancel_url='https://discord.com/channels/@me'
        )
        print(f"✅ Checkout session created successfully!")
        print(f"Session ID: {session.id}")
        print(f"Payment URL: {session.url}")
        return True
    except Exception as e:
        print(f"❌ Failed to create checkout session: {e}")
        return False

def test_webhook_verification():
    """Test webhook signature verification"""
    try:
        # This is a test payload - in real usage, this would come from Stripe
        test_payload = b'{"test": "data"}'
        test_signature = 'test_signature'
        
        # This should fail with invalid signature, which is expected
        try:
            event = stripe.Webhook.construct_event(
                test_payload, 
                test_signature, 
                'whsec_4PevJRK51VhKFYFFwjTG3SnhB02jkzSL'
            )
            print("❌ Webhook verification should have failed")
            return False
        except stripe.error.SignatureVerificationError:
            print("✅ Webhook signature verification working correctly")
            return True
    except Exception as e:
        print(f"❌ Webhook verification test failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Stripe Integration...")
    print("=" * 50)
    
    # Test 1: Basic connection
    print("\n1. Testing Stripe connection...")
    connection_ok = test_stripe_connection()
    
    # Test 2: Create checkout session
    print("\n2. Testing checkout session creation...")
    session_ok = test_create_checkout_session()
    
    # Test 3: Webhook verification
    print("\n3. Testing webhook verification...")
    webhook_ok = test_webhook_verification()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"Connection: {'✅ PASS' if connection_ok else '❌ FAIL'}")
    print(f"Checkout Session: {'✅ PASS' if session_ok else '❌ FAIL'}")
    print(f"Webhook Verification: {'✅ PASS' if webhook_ok else '❌ FAIL'}")
    
    if all([connection_ok, session_ok, webhook_ok]):
        print("\n🎉 All tests passed! Stripe integration is ready.")
    else:
        print("\n⚠️ Some tests failed. Please check the configuration.") 