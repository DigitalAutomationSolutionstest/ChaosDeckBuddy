import os
import logging
from flask import Flask, request, jsonify
import stripe
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
logger.info("Stripe initialized successfully")

@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "Chaos Deck Buddy Webhook Server", "message": "Server is running!"})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "stripe_configured": bool(stripe.api_key),
        "webhook_secret": bool(os.getenv('STRIPE_WEBHOOK_SECRET'))
    })

@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    logger.info("Webhook received!")
    
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        logger.info(f"Webhook verified! Event: {event['type']}")
        
        # Handle the event
        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            logger.info(f"Payment succeeded: {payment_intent['id']}")
            
        elif event['type'] == 'payment_intent.payment_failed':
            payment_intent = event['data']['object']
            logger.info(f"Payment failed: {payment_intent['id']}")
            
        elif event['type'] == 'customer.subscription.created':
            subscription = event['data']['object']
            logger.info(f"Subscription created: {subscription['id']}")
            
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            logger.info(f"Subscription deleted: {subscription['id']}")
            
        elif event['type'] == 'invoice.payment_succeeded':
            invoice = event['data']['object']
            logger.info(f"Invoice payment succeeded: {invoice['id']}")
            
        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            logger.info(f"Invoice payment failed: {invoice['id']}")
            
        elif event['type'] == 'customer.created':
            customer = event['data']['object']
            logger.info(f"Customer created: {customer['id']}")
            
        elif event['type'] == 'charge.succeeded':
            charge = event['data']['object']
            logger.info(f"Charge succeeded: {charge['id']}")
            
        else:
            logger.info(f"Unhandled event type: {event['type']}")
            
        return jsonify({"status": "success"}), 200
        
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return jsonify({"error": "Invalid signature"}), 400
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    logger.info(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True) 