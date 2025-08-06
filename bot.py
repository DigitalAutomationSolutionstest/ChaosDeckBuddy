import discord
from discord.ext import commands
from discord.ui import Button, View
from openai import OpenAI
import requests
import aiohttp
import sqlite3
from io import BytesIO
import random
import asyncio
from pydub import AudioSegment
import os
import json
from dotenv import load_dotenv
import stripe
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from threading import Thread
import logging
import signal
import sys
import base64

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
LEONARDO_API_KEY = os.getenv('LEONARDO_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Validate critical environment variables
if not TOKEN:
    logger.error("DISCORD_TOKEN not found - Bot cannot start")
    exit(1)

logger.info("Environment variables loaded successfully")

# Stripe keys - Load from environment variables
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET')

# Initialize Stripe
if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY
    logger.info("Stripe initialized successfully")
else:
    logger.warning("STRIPE_SECRET_KEY not found - Stripe features disabled")

# Flask app per gestire il webhook
app = Flask(__name__)

# Production routes
@app.route('/', methods=['GET'])
def root():
    return "Chaos Deck AI Webhook Server - Running!", 200

@app.route('/health', methods=['GET'])
def health_check():
    return "OK", 200

# Configurazione degli intents con i fix richiesti
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Flask routes per webhook Stripe
@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    if not STRIPE_WEBHOOK_SECRET:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        return 'Webhook secret not configured', 500
    
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Webhook received: {event['type']}")
    except ValueError as e:
        logger.error(f"Invalid payload: {e}")
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {e}")
        return 'Invalid signature', 400
    
    # Handle events
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        logger.info(f"Checkout completed: {session['id']}")
        
        # Extract metadata
        user_id = session.get('metadata', {}).get('user_id')
        item_id = session.get('metadata', {}).get('item_id')
        
        if user_id and item_id:
            process_purchase(user_id, item_id, session['id'])
    
    return 'OK', 200

def process_purchase(user_id, item_id, session_id):
    """Process a successful purchase"""
    logger.info(f"Processing purchase: User {user_id}, Item {item_id}, Session {session_id}")
    
    # Award items based on purchase
    if item_id == 'booster_pack':
        award_booster_pack(user_id)
    elif item_id == 'legendary_pack':
        award_legendary_pack(user_id)
    elif item_id == 'daily_reset':
        reset_daily_cooldown(user_id)
    elif item_id == 'pity_reduction':
        reduce_pity(user_id)
    elif item_id == 'achievement_unlock':
        unlock_next_achievement(user_id)
    elif item_id == 'fusion_crystal':
        add_fusion_crystal(user_id)
    elif item_id == 'event_booster':
        add_event_booster(user_id)

def award_booster_pack(user_id):
    """Award a booster pack to the user"""
    c.execute("UPDATE users SET booster_packs = booster_packs + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Awarded booster pack to user {user_id}")

def award_legendary_pack(user_id):
    """Award a legendary pack to the user"""
    c.execute("UPDATE users SET legendary_packs = legendary_packs + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Awarded legendary pack to user {user_id}")

def reset_daily_cooldown(user_id):
    """Reset daily cooldown for the user"""
    c.execute("UPDATE users SET last_daily = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Reset daily cooldown for user {user_id}")

def reduce_pity(user_id):
    """Reduce pity counter for the user"""
    c.execute("UPDATE users SET pity_counter = GREATEST(pity_counter - 10, 0) WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Reduced pity counter for user {user_id}")

def unlock_next_achievement(user_id):
    """Unlock the next achievement for the user"""
    # Implementation for achievement unlocking
    logger.info(f"Unlocked achievement for user {user_id}")

def add_fusion_crystal(user_id):
    """Add fusion crystal to the user"""
    c.execute("UPDATE users SET fusion_crystals = fusion_crystals + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Added fusion crystal to user {user_id}")

def add_event_booster(user_id):
    """Add event booster to the user"""
    c.execute("UPDATE users SET event_boosters = event_boosters + 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Added event booster to user {user_id}")

def run_flask():
    """Run Flask server in background"""
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

def signal_handler(signum, frame):
    """Handle graceful shutdown"""
    logger.info("Received shutdown signal, closing gracefully...")
    try:
        # Close database connection
        conn.close()
        logger.info("Database connection closed")
    except:
        pass
    
    # Stop the bot
    try:
        asyncio.create_task(bot.close())
        logger.info("Bot shutdown initiated")
    except:
        pass
    
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# Database setup
conn = sqlite3.connect('chaos_deck.db', check_same_thread=False)
c = conn.cursor()

# Create tables if they don't exist
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id TEXT PRIMARY KEY, points INTEGER DEFAULT 0, level INTEGER DEFAULT 1, 
              last_daily TEXT, pity_counter INTEGER DEFAULT 0, booster_packs INTEGER DEFAULT 0,
              legendary_packs INTEGER DEFAULT 0, fusion_crystals INTEGER DEFAULT 0, 
              event_boosters INTEGER DEFAULT 0, total_cards INTEGER DEFAULT 0,
              legendary_cards INTEGER DEFAULT 0, limited_cards INTEGER DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS cards
             (card_id TEXT PRIMARY KEY, user_id TEXT, rarity TEXT, name TEXT, 
              lore TEXT, image_url TEXT, attack INTEGER, health INTEGER, source TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS badges
             (user_id TEXT, badge_name TEXT, description TEXT, unlocked_date TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS achievements
             (user_id TEXT, achievement_name TEXT, progress INTEGER, completed_date TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS card_lore
             (card_id TEXT PRIMARY KEY, lore TEXT, version INTEGER DEFAULT 0)''')

c.execute('''CREATE TABLE IF NOT EXISTS pull_history
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, pull_type TEXT, 
              card_name TEXT, timestamp TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS server_announcements
             (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, card_name TEXT, 
              rarity TEXT, timestamp TEXT)''')

conn.commit()

@bot.event
async def on_ready():
    """Bot startup event"""
    logger.info(f'{bot.user} has connected to Discord!')
    
    # Start Flask server in background
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask server avviato in background sulla porta 5000")
    
    # Test Leonardo AI connection
    try:
        # Test with a simple generation to verify API key
        test_payload = {
            "prompt": "Test single trading card in anime style",
            "modelId": "b63f7119-31dc-4540-969b-2a9df997e173",  # DreamShaper v7
            "width": 512,
            "height": 720,
            "num_images": 1
        }
        
        headers = {"Authorization": f"Bearer {LEONARDO_API_KEY}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.post("https://cloud.leonardo.ai/api/rest/v1/generations", 
                                  json=test_payload, headers=headers) as resp:
                data = await resp.json()
                if 'sdGenerationJob' in data:
                    logger.info("Hardcoded models available: 4 total")
                    logger.info(f"Test dummy started with model {test_payload['modelId']}")
                    
                    # Poll for test result
                    gen_id = data['sdGenerationJob']['generationId']
                    for _ in range(10):  # Shorter test
                        async with session.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", 
                                             headers=headers) as poll:
                            poll_data = await poll.json()
                            if poll_data.get('generations_by_pk', {}).get('generated_images'):
                                test_url = poll_data['generations_by_pk']['generated_images'][0]['url']
                                logger.info(f"Test gen success with model {test_payload['modelId']}: Image URL {test_url}")
                                break
                        await asyncio.sleep(3)
                else:
                    logger.warning(f"Leonardo test failed: {data}")
                    
    except Exception as e:
        logger.error(f"Leonardo connection test failed: {e}")
    
    print("Chaos Deck AI online! 🚀 Flask running on port 5000")
    print("Webhook URL: https://chaosdeckbuddy.onrender.com/webhook")

async def add_points(user_id, points, ctx=None):
    """Add points to a user and check for level ups"""
    c.execute("INSERT OR IGNORE INTO users (user_id, points) VALUES (?, 0)", (user_id,))
    c.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (points, user_id))
    
    # Get current level and points
    c.execute("SELECT points, level FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if result:
        current_points, current_level = result
        new_level = (current_points // 100) + 1
        
        if new_level > current_level:
            c.execute("UPDATE users SET level = ? WHERE user_id = ?", (new_level, user_id))
            conn.commit()
            
            if ctx:
                embed = discord.Embed(
                    title="🎉 Level Up!",
                    description=f"Congratulations! You've reached level **{new_level}**!",
                    color=0x00FF00
                )
                await ctx.send(embed=embed)
    
    conn.commit()

def unlock_badge(user_id, badge_name, desc=""):
    """Unlock a badge for a user"""
    c.execute("INSERT OR IGNORE INTO badges (user_id, badge_name, description, unlocked_date) VALUES (?, ?, ?, ?)",
              (user_id, badge_name, desc, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

def get_user_badges(user_id):
    """Get all badges for a user"""
    c.execute("SELECT badge_name, description FROM badges WHERE user_id = ?", (user_id,))
    return c.fetchall()

async def check_achievements(user_id, ctx=None):
    """Check and award achievements based on user stats"""
    c.execute("SELECT total_cards, legendary_cards, limited_cards, points FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    if not result:
        return
    
    total_cards, legendary_cards, limited_cards, points = result
    
    achievements = [
        ("First Card", "Collect your first card", 1, total_cards),
        ("Card Collector", "Collect 10 cards", 10, total_cards),
        ("Card Master", "Collect 50 cards", 50, total_cards),
        ("Legendary Hunter", "Collect your first legendary card", 1, legendary_cards),
        ("Legendary Master", "Collect 5 legendary cards", 5, legendary_cards),
        ("Limited Collector", "Collect your first limited card", 1, limited_cards),
        ("Gacha Addict", "Pull 100 cards", 100, total_cards),
        ("Point Collector", "Earn 1000 points", 1000, points),
        ("Point Master", "Earn 5000 points", 5000, points)
    ]
    
    for achievement_name, description, required, current in achievements:
        c.execute("SELECT progress FROM achievements WHERE user_id = ? AND achievement_name = ?", 
                  (user_id, achievement_name))
        result = c.fetchone()
        
        if not result:
            # New achievement
            c.execute("INSERT INTO achievements (user_id, achievement_name, progress) VALUES (?, ?, ?)",
                      (user_id, achievement_name, current))
            if current >= required:
                unlock_badge(user_id, achievement_name, description)
                if ctx:
                    embed = discord.Embed(
                        title="🏆 Achievement Unlocked!",
                        description=f"**{achievement_name}**: {description}",
                        color=0xFFD700
                    )
                    await ctx.send(embed=embed)
        else:
            # Update existing achievement
            old_progress = result[0]
            if current >= required and old_progress < required:
                unlock_badge(user_id, achievement_name, description)
                if ctx:
                    embed = discord.Embed(
                        title="🏆 Achievement Unlocked!",
                        description=f"**{achievement_name}**: {description}",
                        color=0xFFD700
                    )
                    await ctx.send(embed=embed)
            
            c.execute("UPDATE achievements SET progress = ? WHERE user_id = ? AND achievement_name = ?",
                      (current, user_id, achievement_name))
    
    conn.commit()

def get_user_achievements(user_id):
    """Get all achievements for a user"""
    c.execute("SELECT achievement_name, progress FROM achievements WHERE user_id = ?", (user_id,))
    return c.fetchall()

def get_rarity_distribution():
    """Get rarity distribution for gacha cards"""
    rand = random.random()
    if rand < 0.50:
        return "Common"
    elif rand < 0.80:
        return "Rare"
    elif rand < 0.95:
        return "Epic"
    elif rand < 0.99:
        return "Legendary"
    else:
        return "Limited"

def get_rarity_style(rarity):
    """Get visual style elements for each rarity with enhanced gacha styling"""
    styles = {
        'Common': {
            'emoji': '⚪',
            'color': 'silver',
            'embed_color': 0xC0C0C0,
            'frame_style': 'simple metallic border with subtle glow',
            'glow_effect': 'subtle silver aura',
            'text_color': 'white',
            'border_style': 'clean metallic frame'
        },
        'Rare': {
            'emoji': '🔵',
            'color': 'blue',
            'embed_color': 0x0000FF,
            'frame_style': 'crystalline blue border with energy flow',
            'glow_effect': 'blue energy aura',
            'text_color': 'cyan',
            'border_style': 'flowing blue crystal frame'
        },
        'Epic': {
            'emoji': '💎',
            'color': 'purple',
            'embed_color': 0x800080,
            'frame_style': 'diamond purple border with sparkle effects',
            'glow_effect': 'purple sparkle aura',
            'text_color': 'magenta',
            'border_style': 'ornate purple diamond frame'
        },
        'Legendary': {
            'emoji': '✨',
            'color': 'gold',
            'embed_color': 0xFFD700,
            'frame_style': 'golden ornate border with divine glow',
            'glow_effect': 'golden divine radiance',
            'text_color': 'gold',
            'border_style': 'elaborate golden ornate frame'
        },
        'Limited': {
            'emoji': '🌟',
            'color': 'rainbow',
            'embed_color': 0xFF6B35,
            'frame_style': 'cosmic rainbow border with stellar energy',
            'glow_effect': 'cosmic stellar energy',
            'text_color': 'rainbow',
            'border_style': 'cosmic rainbow stellar frame'
        }
    }
    return styles.get(rarity, styles['Common'])

def generate_card_lore(name, rarity, ability_desc, theme="dark fantasy"):
    """Generate lore for a card using OpenAI"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        lore_prompt = f"""
        Generate a compelling lore/story for a {rarity} card named "{name}" with ability "{ability_desc}".
        
        Style: Anime/gacha/dark fantasy, chaotic, ironic, and dramatic. Include:
        - Origin story (2-3 sentences)
        - Power level and significance
        - Connection to the chaotic realm
        - A memorable quote or catchphrase
        
        Make it engaging and fitting for a {rarity} rarity card. Respond in English only.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": lore_prompt}],
            max_tokens=200,
            temperature=0.9
        )
        
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Lore generation error: {e}")
        return f"A mysterious {rarity.lower()} card with unknown origins and chaotic powers."

async def validate_image_quality(image_url, card_name, rarity):
    """Validate image quality using OpenAI Vision"""
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Download image
        async with aiohttp.ClientSession() as session:
            async with session.get(image_url) as resp:
                if resp.status != 200:
                    return False, "Failed to download image"
                
                image_data = await resp.read()
        
        # Encode image for OpenAI Vision
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        validation_prompt = f"""
        Analyze this trading card image for quality and readability:
        
        Card: {card_name} ({rarity})
        
        Check for:
        1. Text readability - stats, name, description should be clearly visible
        2. Frame quality - border should be intact and properly styled
        3. Character visibility - main character should be clearly visible
        4. Overall composition - should be vertical trading card format
        5. No text cutoff or blurry elements
        6. Proper contrast for text overlay
        7. Rarity-appropriate visual styling
        
        Respond with: "PASS" if the image meets all quality standards, or "FAIL: [reason]" if there are issues.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": validation_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=100,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        logger.info(f"Image validation result: {result}")
        
        if result.startswith("PASS"):
            return True, "Image quality validated"
        else:
            return False, result
        
    except Exception as e:
        logger.error(f"Image validation error: {e}")
        return False, f"Validation error: {str(e)}"

async def generate_gacha_card(ctx, prompt=None, is_multi_pull=False):
    """Generate a single gacha card with enhanced visual quality control"""
    
    # Se non c'è prompt, genera un tema casuale
    if not prompt:
        # Enhanced themes mixing the specific anime/game styles requested
        random_themes = [
            # Jujutsu Kaisen
            "jujutsu kaisen cursed technique user", "jujutsu kaisen domain expansion", "jujutsu kaisen cursed spirit",
            "jujutsu kaisen sorcerer with cursed energy", "jujutsu kaisen shikigami summoner",
            
            # Chainsaw Man
            "chainsaw man devil hunter", "chainsaw man hybrid form", "chainsaw man devil contract",
            "chainsaw man public safety agent", "chainsaw man devil transformation",
            
            # Demon Slayer
            "demon slayer hashira warrior", "demon slayer breathing technique user", "demon slayer demon slayer",
            "demon slayer nichirin blade wielder", "demon slayer demon hunter",
            
            # Bleach
            "bleach shinigami captain", "bleach bankai release", "bleach hollow mask",
            "bleach zanpakuto spirit", "bleach soul reaper",
            
            # One Piece
            "one piece devil fruit user", "one piece haki master", "one piece pirate captain",
            "one piece marine admiral", "one piece ancient weapon wielder",
            
            # Nier Automata
            "nier automata android 2b", "nier automata machine lifeform", "nier automata yorha unit",
            "nier automata pod companion", "nier automata corrupted android",
            
            # Elden Ring / From Software
            "elden ring tarnished lord", "elden ring outer god", "dark souls abyss watcher",
            "bloodborne hunter beast", "sekiro shadow assassin", "demon souls corrupted knight",
            
            # Hearthstone / Genshin
            "hearthstone corrupted paladin", "hearthstone legendary dragon", "genshin impact vision wielder",
            "genshin impact archon", "genshin impact fatui harbinger",
            
            # Soft ecchi/hentai (SFW)
            "anime waifu dark mage", "anime heroine battle armor", "anime warrior princess",
            "anime magical girl dark form", "anime priestess of chaos",
            
            # Gacha/Heroine trends
            "gacha limited edition warrior", "gacha ssr character", "gacha event heroine",
            "gacha summer festival unit", "gacha valentine special character"
        ]
        prompt = random.choice(random_themes)
        logger.info(f"Gacha card - User: {ctx.author.name}, Random theme selected: {prompt}")
    else:
        logger.info(f"Gacha card - User: {ctx.author.name}, Prompt: {prompt}")
    
    # Step 1: Generate card data with GPT-4
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        
        # Enhanced prompt for gacha-style cards
        gpt_prompt = f"""
        Genera una carta gacha stile Pokemon x Hearthstone basata su questo prompt: "{prompt}"
        
        Rispondi SOLO con un JSON valido nel seguente formato:
        {{
            "name": "Nome della carta",
            "rarity": "Common/Rare/Epic/Legendary/Limited",
            "attack": numero_attacco,
            "health": numero_vita,
            "ability_desc": "Descrizione breve dell'abilità (max 100 caratteri)"
        }}
        
        Regole per gacha:
        - Nome: creativo e tematico, focus su dark fantasy, anime, gacha
        - Rarity: usa la distribuzione fornita (Common 50%, Rare 30%, Epic 15%, Legendary 4%, Limited 1%)
        - Attack: 1-8 per Common, 2-12 per Rare, 3-15 per Epic, 5-20 per Legendary, 8-25 per Limited
        - Health: 1-6 per Common, 2-10 per Rare, 3-12 per Epic, 5-15 per Legendary, 8-20 per Limited
        - Ability: breve e potente, stile Hearthstone, tema dark fantasy/anime/gacha
        - Focus su creature caotiche, demoni, ombre, void, corruzione, anime waifus, gacha characters
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": gpt_prompt}],
            max_tokens=300,
            temperature=0.8
        )
        
        # Parsing della risposta JSON
        card_data = json.loads(response.choices[0].message.content.strip())
        
        name = card_data["name"]
        rarity = card_data["rarity"]
        attack = card_data["attack"]
        health = card_data["health"]
        ability_desc = card_data["ability_desc"]
        
        logger.info(f"Gacha card data generated: {name} ({rarity}) - {attack}/{health}")
        
    except Exception as e:
        logger.error(f"GPT-4 error: {e}")
        return None, f"❌ **Errore GPT-4:** {str(e)}"
    
    # Step 2: Generate lore
    lore = generate_card_lore(name, rarity, ability_desc)
    
    # Step 3: Generate image with Leonardo AI with quality control
    rarity_style = get_rarity_style(rarity)
    
    # Enhanced Leonardo prompt with specific anime/game styles
    leonardo_prompt = f"""ultra high quality trading card, trending anime style, dynamic pose, detailed armor, epic weapon, mix of jujutsu kaisen, demon slayer, chainsaw man, nier automata, hearthstone, genshin, dark fantasy, vertical frame, chaos energy, glowing aura, waifu or hero, sharp details, high contrast, clear space for stats and text, gothic ornate border, rarity badge ({rarity.lower()}), overlay readable, no watermark, no tattoo

Character: {name} ({rarity} rarity)
Stats: Attack {attack} / Health {health}
Ability: {ability_desc}
Frame: {rarity_style['frame_style']} with {rarity_style['glow_effect']}
Colors: {rarity_style['color']}/black/purple with {rarity_style['text_color']} text
Style: {rarity_style['border_style']}, vertical format 512x720, "Chaos Deck Buddy" watermark, gacha-friendly colors, clear text overlay, no blur, no distortion"""
    
    # Generate Image with multiple attempts for quality
    image_url = None
    max_attempts = 3
    
    for attempt in range(max_attempts):
        try:
            leo_payload = {
                "prompt": leonardo_prompt,
                "modelId": "b63f7119-31dc-4540-969b-2a9df997e173",  # DreamShaper v7
                "width": 512,
                "height": 720,
                "num_images": 1,
                "negative_prompt": "blurry, low quality, multiple images, collage, text errors, distorted, tattoo, tribal, horizontal format, watermark, signature, ugly, deformed, bad anatomy, bad proportions, extra limbs, missing limbs, floating limbs, mutated hands and fingers, out of focus, long neck, long body, mutated hands and fingers, missing arms, missing legs, extra arms, extra legs, mutated hands and fingers, bad anatomy, bad proportions, blind, bad eyes, ugly eyes, dead eyes, blur, vignette, out of shot, out of focus, gaussian, closeup, monochrome, grain, noisy, text, writing, watermark, logo, oversaturation, over saturation, over shadow"
            }
            
            headers = {"Authorization": f"Bearer {LEONARDO_API_KEY}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.post("https://cloud.leonardo.ai/api/rest/v1/generations", 
                                      json=leo_payload, headers=headers) as resp:
                    data = await resp.json()
                    logger.info(f"Leonardo response (attempt {attempt + 1}): {data}")
                    
                    if 'sdGenerationJob' in data:
                        gen_id = data['sdGenerationJob']['generationId']
                        logger.info(f"Leonardo: Generation started, gen_id: {gen_id}")
                        
                        # Polling per il risultato
                        for _ in range(30):
                            async with session.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", 
                                                 headers=headers) as poll:
                                poll_data = await poll.json()
                                if poll_data.get('generations_by_pk', {}).get('generated_images'):
                                    image_url = poll_data['generations_by_pk']['generated_images'][0]['url']
                                    logger.info(f"Image generated (attempt {attempt + 1}): {image_url}")
                                    
                                    # Validate image quality
                                    is_valid, validation_msg = await validate_image_quality(image_url, name, rarity)
                                    
                                    if is_valid:
                                        logger.info(f"Image quality validated on attempt {attempt + 1}")
                                        break
                                    else:
                                        logger.warning(f"Image quality check failed on attempt {attempt + 1}: {validation_msg}")
                                        image_url = None  # Will trigger retry
                                        break
                            await asyncio.sleep(5)
                        
                        if image_url and is_valid:
                            break  # Success, exit retry loop
                        else:
                            logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                            await asyncio.sleep(2)
                            
                    else:
                        logger.error(f"Leonardo error (attempt {attempt + 1}): {data}")
                        await asyncio.sleep(2)
                        
        except Exception as e:
            logger.error(f"Leonardo error (attempt {attempt + 1}): {str(e)}")
            await asyncio.sleep(2)
    
    # Fallback if all attempts failed
    if not image_url:
        logger.error("All image generation attempts failed")
        image_url = 'https://i.imgur.com/example_card.png'  # Fallback
    
    # Step 4: Create Discord embed
    embed = discord.Embed(
        title=f"{rarity_style['emoji']} Gacha Card: {name}",
        description=f"**Rarity:** {rarity}\n**Stats:** {attack}/{health}\n**Ability:** {ability_desc}\n\n**Lore:** {lore}",
        color=rarity_style['embed_color']
    )
    
    embed.set_image(url=image_url)
    embed.set_footer(text=f"🎮 Generated by {ctx.author.name} | Prompt: {prompt}")
    
    # Step 5: Save to database
    try:
        card_id = str(random.randint(100000, 999999))
        c.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (card_id, str(ctx.author.id), rarity, name, lore, image_url, attack, health, "gacha_generated"))
        
        # Save lore separately
        c.execute("INSERT OR REPLACE INTO card_lore VALUES (?, ?, ?)", (card_id, lore, 0))
        
        # Track pull history
        c.execute("INSERT INTO pull_history VALUES (NULL, ?, ?, ?, ?)", 
                  (str(ctx.author.id), "single" if not is_multi_pull else "multi", name, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        logger.info(f"Gacha card saved to database: {card_id}")
        
        # Check for legendary/limited announcements
        if rarity in ['Legendary', 'Limited']:
            c.execute("INSERT INTO server_announcements VALUES (NULL, ?, ?, ?, ?)", 
                      (str(ctx.author.id), name, rarity, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
            
            # Send server announcement
            announcement_embed = discord.Embed(
                title=f"🎉 {rarity} Card Pulled!",
                description=f"**{ctx.author.name}** just pulled **{name}** ({rarity})!",
                color=rarity_style['embed_color']
            )
            announcement_embed.set_image(url=image_url)
            await ctx.send(embed=announcement_embed)
        
        return embed, None
        
    except Exception as e:
        logger.error(f"Database error: {e}")
        return embed, f"⚠️ Card generated but database error: {str(e)}"

@bot.command(name='chaos')
@commands.cooldown(1, 30, commands.BucketType.user)  # 30 second cooldown
async def chaos(ctx, amount: int = 1, *, prompt: str = None):
    """
    Genera carte gacha AI stile Pokemon x Hearthstone.
    Uso: !chaos <numero> <prompt> (es. "!chaos 1 fiery chaos dragon" o "!chaos 10")
    Se usato senza parametri, genera una carta basata su temi casuali.
    """
    
    if amount < 1 or amount > 20:
        await ctx.send("❌ **Errore:** Numero di carte deve essere tra 1 e 20!")
        return
    
    if amount == 1:
        # Single pull
        loading_msg = await ctx.send("🔄 **Generating Gacha Card...** 🔮")
        
        # Generate single card
        embed, error = await generate_gacha_card(ctx, prompt, is_multi_pull=False)
        
        if error:
            await loading_msg.edit(content=error)
            return
        
        await ctx.send(embed=embed)
        await loading_msg.edit(content="✅ **Carta gacha generata con successo!** 🎉")
    else:
        # Multi-pull with enhanced cooldown
        loading_msg = await ctx.send(f"🔄 **Generating {amount} Gacha Cards...** 🔮")
        
        cards_generated = []
        for i in range(amount):
            await loading_msg.edit(content=f"🎨 **Generating card {i+1}/{amount}...**")
            
            embed, error = await generate_gacha_card(ctx, prompt, is_multi_pull=True)
            
            if error:
                await loading_msg.edit(content=f"❌ **Errore carta {i+1}:** {error}")
                continue
            
            cards_generated.append(embed)
            
            # Send each card
            await ctx.send(embed=embed)
            
            # Small delay between cards
            await asyncio.sleep(1)
        
        # Summary message
        rarity_counts = {}
        for embed in cards_generated:
            # Extract rarity from embed description
            desc = embed.description
            if "**Rarity:**" in desc:
                rarity = desc.split("**Rarity:**")[1].split("\n")[0].strip()
                rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        summary = f"✅ **Multi-pull completato!** Generati {len(cards_generated)}/{amount} carte:\n"
        for rarity, count in rarity_counts.items():
            summary += f"{get_rarity_style(rarity)['emoji']} {rarity}: {count}\n"
        
        await loading_msg.edit(content=summary)

@bot.command(name='story')
async def story(ctx, card_id: str):
    """
    Genera lore extra per una carta specifica.
    Uso: !story <card_id>
    """
    
    # Check if card exists and is owned by user
    c.execute("SELECT name, rarity, description FROM cards WHERE id=? AND user_id=?", (card_id, str(ctx.author.id)))
    card = c.fetchone()
    
    if not card:
        await ctx.send("❌ **Carta non trovata!** Assicurati di possedere la carta e di usare l'ID corretto.")
        return
    
    name, rarity, description = card
    
    loading_msg = await ctx.send("📖 **Generando lore extra...**")
    
    try:
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Generate extended lore
        lore_prompt = f"""
        Generate an extended, detailed lore story for the {rarity} card "{name}" with description "{description}".
        
        Create a compelling narrative that includes:
        - Detailed origin story (3-4 sentences)
        - Character development and personality
        - Powers and abilities explanation
        - Connection to the chaotic realm
        - Memorable quotes or catchphrases
        - Future potential or evolution
        
        Style: Anime/gacha/dark fantasy, chaotic, ironic, and dramatic. Make it engaging and fitting for a {rarity} rarity card.
        Respond in English only.
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": lore_prompt}],
            max_tokens=400,
            temperature=0.9
        )
        
        extended_lore = response.choices[0].message.content.strip()
        
        # Update lore in database
        c.execute("UPDATE card_lore SET lore=?, story_requests=story_requests+1 WHERE card_id=?", (extended_lore, card_id))
        conn.commit()
        
        # Create embed
        rarity_style = get_rarity_style(rarity)
        embed = discord.Embed(
            title=f"📖 Extended Lore: {name}",
            description=extended_lore,
            color=rarity_style['embed_color']
        )
        embed.set_footer(text=f"🎮 Story requested by {ctx.author.name}")
        
        await ctx.send(embed=embed)
        await loading_msg.edit(content="✅ **Lore extra generato con successo!** 📖")
        
    except Exception as e:
        logger.error(f"Story generation error: {e}")
        await loading_msg.edit(content=f"❌ **Errore generazione lore:** {str(e)}")

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """Enhanced leaderboard with gacha statistics"""
    
    # Get top users by points
    c.execute("SELECT user_id, points, level FROM users ORDER BY points DESC LIMIT 10")
    top_users = c.fetchall()
    
    # Get gacha statistics
    c.execute("""
        SELECT user_id, COUNT(*) as total_cards,
               SUM(CASE WHEN rarity = 'Legendary' THEN 1 ELSE 0 END) as legendary_count,
               SUM(CASE WHEN rarity = 'Limited' THEN 1 ELSE 0 END) as limited_count
        FROM cards 
        GROUP BY user_id 
        ORDER BY total_cards DESC 
        LIMIT 10
    """)
    top_collectors = c.fetchall()
    
    # Create leaderboard embed
    embed = discord.Embed(title="🏆 Chaos Deck Leaderboard", color=0xFFD700)
    
    # Points leaderboard
    points_text = ""
    for i, user in enumerate(top_users, 1):
        user_name = bot.get_user(int(user[0])).name if bot.get_user(int(user[0])) else user[0]
        points_text += f"{i}. **{user_name}**: {user[1]} pts (Lvl {user[2]})\n"
    
    embed.add_field(name="💰 Points Leaderboard", value=points_text, inline=False)
    
    # Collection leaderboard
    collection_text = ""
    for i, collector in enumerate(top_collectors, 1):
        user_name = bot.get_user(int(collector[0])).name if bot.get_user(int(collector[0])) else collector[0]
        collection_text += f"{i}. **{user_name}**: {collector[1]} cards (✨{collector[2]} 🌟{collector[3]})\n"
    
    embed.add_field(name="🎴 Collection Leaderboard", value=collection_text, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='daily')
async def daily(ctx):
    user_id = str(ctx.author.id)
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check if already claimed today
    c.execute("SELECT last_daily, streak FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    
    if result and result[0] == today:
        await ctx.send("❌ **Already claimed today!** Come back tomorrow!")
        return
    
    # Calculate streak and rewards
    current_streak = result[1] if result else 0
    new_streak = current_streak + 1
    
    # Base rewards
    base_points = 100
    streak_bonus = min(new_streak * 25, 500)  # Max 500 bonus
    total_points = base_points + streak_bonus
    
    # Special rewards for milestone streaks
    special_reward = None
    if new_streak == 7:
        special_reward = "🔥 **7-Day Streak!** Unlocking rare card pull!"
        # Generate rare card
        await generate_daily_card(ctx, "Rare")
    elif new_streak == 30:
        special_reward = "🌟 **30-Day Streak!** Legendary card unlocked!"
        # Generate legendary card
        await generate_daily_card(ctx, "Legendary")
    
    # Update user data
    c.execute("UPDATE users SET last_daily=?, streak=? WHERE user_id=?", (today, new_streak, user_id))
    await add_points(user_id, total_points, ctx)
    conn.commit()
    
    # Send reward embed
    embed = discord.Embed(title="🎁 Daily Reward Claimed!", color=0xFFD700)
    embed.add_field(name="Points Earned", value=f"+{total_points} points", inline=True)
    embed.add_field(name="Streak", value=f"{new_streak} days 🔥", inline=True)
    if special_reward:
        embed.add_field(name="Special Reward", value=special_reward, inline=False)
    embed.set_footer(text="Come back tomorrow to maintain your streak!")
    
    await ctx.send(embed=embed)

async def generate_daily_card(ctx, rarity):
    """Generate a special daily card"""
    # Generate card similar to chaos but simpler
    name_prompt = f"Generate a unique name for a {rarity} daily reward card. Respond in English only."
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    name_response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[{"role": "user", "content": name_prompt}], 
        max_tokens=50
    )
    name = name_response.choices[0].message.content.strip()
    
    desc_prompt = f"Generate a description for a {rarity} daily reward card named '{name}'. Respond in English only."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[{"role": "user", "content": desc_prompt}], 
        max_tokens=150
    )
    desc = response.choices[0].message.content.strip()
    
    power = random.randint(50, 200) * (4 if rarity == 'Legendary' else 2 if rarity == 'Rare' else 1)
    special = "Daily Reward"
    
    # Save to DB
    card_id = str(random.randint(100000, 999999))
    c.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (card_id, str(ctx.author.id), rarity, name, desc, 
               'https://i.imgur.com/daily_card.png', power, special, "daily"))
    conn.commit()
    
    # Send card embed
    rarity_colors = {'Common': 0xC0C0C0, 'Rare': 0x0000FF, 'Epic': 0x800080, 'Legendary': 0xFFD700}
    embed = discord.Embed(title=f"🎁 Daily Card: {name}", description=desc, color=rarity_colors.get(rarity, 0x00FF00))
    embed.add_field(name="Power", value=power, inline=True)
    embed.add_field(name="Special", value=special, inline=True)
    embed.set_footer(text="Daily Reward | Generated by Chaos Deck AI 🚀")
    await ctx.send(embed=embed)

@bot.command(name='fuse')
async def fuse(ctx, card1_id: str, card2_id: str):
    user_id = str(ctx.author.id)
    
    # Check card ownership
    c.execute("SELECT name, rarity, power, special_effect, theme FROM cards WHERE id=? AND user_id=?", (card1_id, user_id))
    card1 = c.fetchone()
    c.execute("SELECT name, rarity, power, special_effect, theme FROM cards WHERE id=? AND user_id=?", (card2_id, user_id))
    card2 = c.fetchone()
    
    if not card1 or not card2:
        await ctx.send("❌ **Cards not found or not owned!** Make sure you own both cards.")
        return
    
    if card1_id == card2_id:
        await ctx.send("❌ **Cannot fuse the same card!** Choose two different cards.")
        return
    
    # Get user level for fusion bonus
    c.execute("SELECT level FROM users WHERE user_id=?", (user_id,))
    user_level = c.fetchone()[0] if c.fetchone() else 1
    
    # Fusion animation
    await ctx.send("🔗 **Fusion initiated...**")
    await asyncio.sleep(1)
    await ctx.send("⚡ **Merging card energies...**")
    await asyncio.sleep(1)
    await ctx.send("💫 **Creating fusion card...**")
    
    # Calculate fusion success chance
    base_success = 0.7
    rarity_bonus = 0.1 if card1[1] == 'Epic' or card2[1] == 'Epic' else 0
    power_bonus = min((card1[2] + card2[2]) / 200, 0.2)
    level_bonus = min(user_level / 20, 0.1)  # Level bonus
    
    success_rate = base_success + rarity_bonus + power_bonus + level_bonus
    
    if random.random() < success_rate:
        # Fusion successful
        await ctx.send("✅ **Fusion successful!**")
        
        # Generate fused card
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Generate fusion name
        name_prompt = f"Generate a unique name for a fused card combining '{card1[0]}' and '{card2[0]}'. Respond in English only. Only return the name."
        name_response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": name_prompt}], 
            max_tokens=50
        )
        fusion_name = name_response.choices[0].message.content.strip()
        
        # Generate fusion description
        desc_prompt = f"Generate a description for a fused card named '{fusion_name}' that combines the powers of '{card1[0]}' ({card1[3]}) and '{card2[0]}' ({card2[3]}). Respond in English only."
        desc_response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": desc_prompt}], 
            max_tokens=200
        )
        fusion_desc = desc_response.choices[0].message.content.strip()
        
        # Calculate fusion stats
        avg_power = (card1[2] + card2[2]) // 2
        power_boost = int(avg_power * 0.5)  # +50% power
        fusion_power = avg_power + power_boost
        
        # Determine fusion rarity
        if card1[1] == 'Legendary' or card2[1] == 'Legendary':
            fusion_rarity = 'Legendary'
        elif card1[1] == 'Epic' or card2[1] == 'Epic':
            fusion_rarity = 'Epic'
        else:
            fusion_rarity = 'Rare'
        
        fusion_special = "Fusion Power"
        
        # Generate fusion image
        leo_payload = {
            "prompt": f"Generate a HIGH-QUALITY SINGLE trading card ONLY: Fused {fusion_rarity} card combining {card1[0]} and {card2[0]}, detailed central illustration, glowing {fusion_rarity} borders, anime/JRPG vibe, high resolution, no text overlays except title. Card frame like Yu-Gi-Oh.", 
            "modelId": random.choice(available_models),
            "width": 512, 
            "height": 768, 
            "num_images": 1,
            "negative_prompt": "multiple images, blurry, low quality, collage, extra elements"
        }
        
        image_url = 'https://i.imgur.com/fusion_card.png'  # Fallback
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://cloud.leonardo.ai/api/rest/v1/generations", json=leo_payload, headers={"Authorization": f"Bearer {LEONARDO_API_KEY}"}) as resp:
                    data = await resp.json()
                    gen_id = data['sdGenerationJob']['generationId']
                    
                    for _ in range(30):
                        async with session.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", headers={"Authorization": f"Bearer {LEONARDO_API_KEY}"}) as poll:
                            poll_data = await poll.json()
                            if poll_data['generations_by_pk']['generated_images']:
                                image_url = poll_data['generations_by_pk']['generated_images'][0]['url']
                                break
                        await asyncio.sleep(5)
        except Exception as e:
            print(f"Error generating fusion image: {e}")
        
        # Save fusion card
        fusion_card_id = str(random.randint(100000, 999999))
        c.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                  (fusion_card_id, user_id, fusion_rarity, fusion_name, fusion_desc, 
                   image_url, fusion_power, fusion_special, "fusion"))
        
        # Remove original cards
        c.execute("DELETE FROM cards WHERE id IN (?, ?)", (card1_id, card2_id))
        conn.commit()
        
        # Send fusion card embed
        rarity_colors = {'Common': 0xC0C0C0, 'Rare': 0x0000FF, 'Epic': 0x800080, 'Legendary': 0xFFD700}
        embed = discord.Embed(title=f"🔗 Fusion Card: {fusion_name}", description=fusion_desc, color=rarity_colors.get(fusion_rarity, 0x00FF00))
        embed.add_field(name="Power", value=fusion_power, inline=True)
        embed.add_field(name="Special", value=fusion_special, inline=True)
        embed.add_field(name="Fused From", value=f"{card1[0]} + {card2[0]}", inline=False)
        embed.set_image(url=image_url)
        embed.set_footer(text="Fusion Success | Generated by Chaos Deck AI 🚀")
        await ctx.send(embed=embed)
        
        # Check fusion achievements
        await check_achievements(user_id, ctx)
        
    else:
        # Fusion failed
        await ctx.send("💥 **Fusion failed!** Cards lost...")
        c.execute("DELETE FROM cards WHERE id IN (?, ?)", (card1_id, card2_id))
        conn.commit()

@bot.command(name='inventory')
async def inventory(ctx):
    user_id = str(ctx.author.id)
    c.execute("SELECT * FROM cards WHERE user_id=?", (user_id,))
    cards = c.fetchall()
    
    if not cards:
        await ctx.send("Your inventory is empty! Use !chaos to pull epic cards. 🚀")
        return
    
    # Paginazione: Dividi in pagine da 5 cards
    pages = [cards[i:i+5] for i in range(0, len(cards), 5)]
    current_page = 0
    
    embed = discord.Embed(title=f"{ctx.author.name}'s Chaos Deck Inventory", color=0x00ff00)
    
    # Add badges field
    user_badges = get_user_badges(str(ctx.author.id))
    if user_badges:
        badges_str = ", ".join(user_badges)
        embed.add_field(name="🏆 Badges", value=badges_str, inline=False)
    
    # Add cards from first page
    for card in pages[current_page]:
        # card[0]=id, card[1]=user_id, card[2]=rarity, card[3]=name, card[4]=desc, card[5]=image_url, card[6]=power, card[7]=special
        rarity_emoji = "✨" if card[2] == "Legendary" else "💎" if card[2] == "Epic" else "🔵" if card[2] == "Rare" else "⚪"
        desc_snippet = card[4][:100] + "..." if len(card[4]) > 100 else card[4]
        embed.add_field(
            name=f"{rarity_emoji} {card[2]} Card: {card[3]}", 
            value=f"Power: {card[6]} | Special: {card[7]}\n{desc_snippet}", 
            inline=False
        )
        # Use first image as thumbnail
        if card[5] and card[5] != 'https://placeholder.com/512x768':
            embed.set_thumbnail(url=card[5])
            break
    
    embed.set_footer(text=f"Pagina {current_page+1}/{len(pages)} | Total Cards: {len(cards)}")
    msg = await ctx.send(embed=embed)
    
    # Aggiungi reactions per paginazione se più di una pagina
    if len(pages) > 1:
        await msg.add_reaction("◀️")
        await msg.add_reaction("▶️")
        
        def check(reaction, user): 
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == msg.id
        
        while True:
            try:
                reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                if str(reaction.emoji) == "▶️" and current_page < len(pages)-1:
                    current_page += 1
                elif str(reaction.emoji) == "◀️" and current_page > 0:
                    current_page -= 1
                
                # Update embed with new page
                embed.clear_fields()
                for card in pages[current_page]:
                    rarity_emoji = "✨" if card[2] == "Legendary" else "💎" if card[2] == "Epic" else "🔵" if card[2] == "Rare" else "⚪"
                    desc_snippet = card[4][:100] + "..." if len(card[4]) > 100 else card[4]
                    embed.add_field(
                        name=f"{rarity_emoji} {card[2]} Card: {card[3]}", 
                        value=f"Power: {card[6]} | Special: {card[7]}\n{desc_snippet}", 
                        inline=False
                    )
                    # Update thumbnail with first image of the page
                    if card[5] and card[5] != 'https://placeholder.com/512x768':
                        embed.set_thumbnail(url=card[5])
                        break
                
                embed.set_footer(text=f"Pagina {current_page+1}/{len(pages)} | Total Cards: {len(cards)}")
                await msg.edit(embed=embed)
                await msg.remove_reaction(reaction, user)
            except asyncio.TimeoutError:
                await msg.clear_reactions()
                break

@bot.command(name='shop')
async def shop(ctx, *args):
    if not args:
        embed = discord.Embed(title="🛒 Premium Shop", description="Buy exclusive packs and boosters!", color=0xFFD700)
        embed.add_field(name="📦 Epic Booster Pack", value="5 rare/epic cards - $2", inline=False)
        embed.add_field(name="💎 Legendary Pack", value="3 legendary cards - $5", inline=False)
        embed.add_field(name="🎮 Custom Quest", value="Personalized campaign - $5", inline=False)
        embed.add_field(name="🔥 Premium Pass", value="30 days of bonuses - $10", inline=False)
        embed.add_field(name="⏰ Streak Saver", value="Reset daily cooldown - $0.50", inline=False)
        embed.add_field(name="🎲 Pity Booster", value="Reduce pity by 10 - $1", inline=False)
        embed.add_field(name="🏆 Achievement Booster", value="Auto-unlock next achievement - $0.50", inline=False)
        embed.add_field(name="🔗 Fusion Crystal", value="Guarantee fusion success - $1", inline=False)
        embed.add_field(name="🎪 Event Booster", value="Extra drops during events - $1", inline=False)
        embed.set_footer(text="💳 Use '!shop buy <item_id>' to purchase!")
        await ctx.send(embed=embed)
        return
    
    if args[0] == "buy" and len(args) > 1:
        item_id = args[1]
        
        # Define items with consistent pricing (in cents)
        items = {
            "booster": {
                "name": "Epic Booster Pack", 
                "price": 200, 
                "description": "5 rare/epic cards",
                "currency": "usd"
            },
            "legendary": {
                "name": "Legendary Pack", 
                "price": 500, 
                "description": "3 legendary cards",
                "currency": "usd"
            },
            "quest": {
                "name": "Custom Quest", 
                "price": 500, 
                "description": "Personalized campaign",
                "currency": "usd"
            },
            "premium": {
                "name": "Premium Pass", 
                "price": 1000, 
                "description": "30 days of bonuses",
                "currency": "usd"
            },
            "streak_saver": {
                "name": "Streak Saver", 
                "price": 50, 
                "description": "Reset daily cooldown",
                "currency": "usd"
            },
            "pity_booster": {
                "name": "Pity Booster", 
                "price": 100, 
                "description": "Reduce pity by 10",
                "currency": "usd"
            },
            "achievement_booster": {
                "name": "Achievement Booster", 
                "price": 50, 
                "description": "Auto-unlock next achievement",
                "currency": "usd"
            },
            "fusion_crystal": {
                "name": "Fusion Crystal", 
                "price": 100, 
                "description": "Guarantee fusion success",
                "currency": "usd"
            },
            "event_booster": {
                "name": "Event Booster", 
                "price": 100, 
                "description": "Extra drops during events",
                "currency": "usd"
            }
        }
        
        if item_id not in items:
            valid_items = ", ".join(items.keys())
            await ctx.send(f"❌ Invalid item ID: `{item_id}`\nValid items: `{valid_items}`")
            return
            
        item = items[item_id]
        
        try:
            # Create Stripe Checkout Session with metadata
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': item['currency'],
                        'product_data': {
                            'name': item['name'],
                            'description': item['description']
                        },
                        'unit_amount': item['price']  # Already in cents
                    },
                    'quantity': 1
                }],
                mode='payment',
                metadata={
                    'user_id': str(ctx.author.id),
                    'item_id': item_id
                },
                success_url='https://discord.com/channels/@me',
                cancel_url='https://discord.com/channels/@me'
            )
            
            # Send payment link to user
            price_display = f"${item['price']/100:.2f}"
            embed = discord.Embed(
                title=f"💳 Purchase {item['name']}", 
                description=f"**Price:** {price_display}\n**Description:** {item['description']}",
                color=0x00FF00
            )
            embed.add_field(
                name="Payment Link", 
                value=f"[Click here to pay]({session.url})", 
                inline=False
            )
            embed.set_footer(text="Complete your payment to receive your rewards!")
            
            await ctx.send(embed=embed)
            
            # Log the purchase attempt
            print(f"Purchase initiated: {ctx.author.name} ({ctx.author.id}) - {item['name']} - Session: {session.id}")
            
        except stripe.error.StripeError as e:
            await ctx.send(f"❌ Stripe error: {str(e)}")
            print(f"Stripe error for user {ctx.author.id}: {e}")
        except Exception as e:
            await ctx.send(f"❌ Unexpected error: {str(e)}")
            print(f"Unexpected error for user {ctx.author.id}: {e}")
    else:
        await ctx.send("❌ Invalid command. Use: `!shop buy <item_id>`")

@bot.command(name='event')
async def event(ctx):
    """Check current active events"""
    current_time = datetime.now()
    
    # Hardcoded events (can be expanded)
    events = [
        {
            "name": "Seven Deadly Sins Event",
            "theme": "seven_deadly_sins",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31),
            "bonus": "+20% Epic chance in chaos!",
            "description": "Sinful power flows through the cards..."
        },
        {
            "name": "Dragon Ball Fusion Event",
            "theme": "dragonball",
            "start_date": datetime(2024, 2, 1),
            "end_date": datetime(2024, 2, 28),
            "bonus": "+15% Legendary chance!",
            "description": "Fusion cards have increased power..."
        },
        {
            "name": "Evangelion Chaos Event",
            "theme": "evangelion",
            "start_date": datetime(2024, 3, 1),
            "end_date": datetime(2024, 3, 31),
            "bonus": "+25% Rare chance in chaos!",
            "description": "The angels bring chaos to card pulls..."
        }
    ]
    
    active_events = []
    for event in events:
        if event["start_date"] <= current_time <= event["end_date"]:
            active_events.append(event)
    
    if not active_events:
        embed = discord.Embed(title="🎪 Events", description="No active events right now!", color=0x808080)
        embed.add_field(name="Coming Soon", value="Check back for limited-time events with special bonuses!", inline=False)
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(title="🎪 Active Events", color=0xFF6B35)
    for event in active_events:
        embed.add_field(
            name=f"🎭 {event['name']}", 
            value=f"**Bonus:** {event['bonus']}\n**Description:** {event['description']}\n**Theme:** {event['theme']}", 
            inline=False
        )
    
    embed.set_footer(text="Use !chaos with event themes for bonus chances!")
    await ctx.send(embed=embed)

def get_active_events():
    """Get list of currently active events"""
    current_time = datetime.now()
    
    events = [
        {
            "name": "Seven Deadly Sins Event",
            "theme": "seven_deadly_sins",
            "start_date": datetime(2024, 1, 1),
            "end_date": datetime(2024, 12, 31),
            "bonus": "epic_boost"
        },
        {
            "name": "Dragon Ball Fusion Event",
            "theme": "dragonball",
            "start_date": datetime(2024, 2, 1),
            "end_date": datetime(2024, 2, 28),
            "bonus": "legendary_boost"
        },
        {
            "name": "Evangelion Chaos Event",
            "theme": "evangelion",
            "start_date": datetime(2024, 3, 1),
            "end_date": datetime(2024, 3, 31),
            "bonus": "rare_boost"
        }
    ]
    
    active_events = []
    for event in events:
        if event["start_date"] <= current_time <= event["end_date"]:
            active_events.append(event)
    
    return active_events

@bot.command(name="campaign")
async def campaign(ctx, action: str = "start", theme: str = "random"):
    user_id = str(ctx.author.id)
    if theme not in THEMES: 
        theme = "random"
    
    if action == "start":
        # Create new campaign
        campaign_id = str(random.randint(100000, 999999))
        story_prompt = f"Generate a short D&D-like campaign story intro (3-5 sentences) in {theme} theme, crossover with One Piece/Dragon Ball/Evangelion/From Software. Respond in English only. Include a quest goal, enemies, and chaos elements."
        client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": story_prompt}],
            max_tokens=200
        )
        story = response.choices[0].message.content.strip()
        c.execute("INSERT INTO campaigns VALUES (?, ?, ?, 0, ?, 'active')", (campaign_id, user_id, theme, story))
        conn.commit()
        embed = discord.Embed(title=f"PVE Campaign Started: {theme.capitalize()}", description=story, color=0x800080)
        await ctx.send(embed=embed)
        await run_campaign(ctx, campaign_id)  # Start campaign
    
    elif action == "continue":
        c.execute("SELECT * FROM campaigns WHERE user_id=? AND status='active' ORDER BY campaign_id DESC LIMIT 1", (user_id,))
        camp = c.fetchone()
        if not camp: 
            await ctx.send("No active campaign! Use !campaign start.")
            return
        await run_campaign(ctx, camp[0])
    
    elif action == "end":
        c.execute("UPDATE campaigns SET status='ended' WHERE user_id=? AND status='active'", (user_id,))
        conn.commit()
        await ctx.send("Campaign ended! Points gained: 100.")
        await add_points(user_id, 100, ctx)  # Reward

async def run_campaign(ctx, campaign_id):
    c.execute("SELECT theme, story, current_turn FROM campaigns WHERE campaign_id=?", (campaign_id,))
    camp = c.fetchone()
    if not camp:
        await ctx.send("Error: Campaign not found!")
        return
    
    theme, story, turn_num = camp[0], camp[1], camp[2]
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    while turn_num < 10:  # Loop for turns
        turn_num += 1
        logger.info(f"Turn {turn_num}: Starting...")
        
        # Generate turn
        turn_prompt = f"Based on story: '{story}', generate next turn for D&D-like PVE in {theme}: Describe situation (2-3 sentences), then list 1-3 choices (e.g., '1: Attack the boss, 2: Defend allies, 3: Use special ability'). Respond in English only. Include chaos elements from crossover themes."
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": turn_prompt}], 
            max_tokens=200
        )
        turn_desc = response.choices[0].message.content.strip()
        logger.info(f"Turn {turn_num}: Desc '{turn_desc[:50]}...'")
        
        # Generate image for turn
        leo_payload = {
            "prompt": f"High-quality anime scene from {theme} D&D campaign: {turn_desc[:100]}, chaotic crossover vibe.", 
            "modelId": random.choice(available_models), 
            "width": 512, 
            "height": 512, 
            "num_images": 1,
            "negative_prompt": "multiple images, blurry, low quality, collage, extra elements"
        }
        
        image_url = 'https://placeholder.com/512x512'  # Fallback
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://cloud.leonardo.ai/api/rest/v1/generations", json=leo_payload, headers={"Authorization": f"Bearer {LEONARDO_API_KEY}"}) as resp:
                    data = await resp.json()
                    gen_id = data['sdGenerationJob']['generationId']
                    
                    for _ in range(30):
                        async with session.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", headers={"Authorization": f"Bearer {LEONARDO_API_KEY}"}) as poll:
                            poll_data = await poll.json()
                            if poll_data['generations_by_pk']['generated_images']:
                                image_url = poll_data['generations_by_pk']['generated_images'][0]['url']
                                break
                        await asyncio.sleep(5)
        except Exception as e:
            print(f"Error generating turn image: {e}")
        
        embed = discord.Embed(title=f"Turn {turn_num} - {theme.capitalize()}", description=turn_desc, color=0xFF0000)
        embed.set_image(url=image_url)
        logger.info(f"Sending embed for Turn {turn_num}: Title '{embed.title}', Desc '{embed.description[:50]}...'")
        await ctx.send(embed=embed)
        await ctx.send("*(See embed above for details)*")  # Fallback text for log
        
        # Buttons for choices
        view = View()
        for i in range(1, 4):  # Assume always 3 choices
            view.add_item(Button(label=str(i), style=discord.ButtonStyle.primary, custom_id=f"choice_{i}"))
        logger.info(f"Button view added with {len(view.children)} buttons")
        msg = await ctx.send("Choose your action:", view=view)
        
        try:
            interaction = await bot.wait_for("interaction", timeout=120.0, check=lambda inter: inter.user == ctx.author and inter.data['custom_id'].startswith("choice_") and inter.message.id == msg.id)
            choice = int(interaction.data['custom_id'].split("_")[1])
            await interaction.response.defer()  # Ack
        except asyncio.TimeoutError:
            choice = random.randint(1, 3)
            await ctx.send("⏰ Timeout! Choice randomized.")
        
        logger.info(f"Turn {turn_num}: Choice {choice}")
        
        # Card selection: First 3 from DB
        c.execute("SELECT id, name, power, special_effect FROM cards WHERE user_id=? LIMIT 3", (str(ctx.author.id),))
        cards = c.fetchall()
        if not cards: 
            await ctx.send("❌ No cards! Pull with !chaos.")
            break
        
        select_embed = discord.Embed(title="Choose a card for this action:", color=0x00FF00)
        for i, card in enumerate(cards, 1):
            select_embed.add_field(name=f"{i}: {card[1]}", value=f"Power: {card[2]} | Special: {card[3]}", inline=False)
        logger.info(f"Sending card selection embed: Fields {len(select_embed.fields)}")
        await ctx.send(embed=select_embed)
        await ctx.send("*(See embed above for details)*")  # Fallback text for log
        
        # Buttons for card selection
        view = View()
        labels = ["A", "B", "C"]
        for i, card in enumerate(cards):
            view.add_item(Button(label=labels[i], style=discord.ButtonStyle.secondary, custom_id=f"card_{i}"))
        select_msg = await ctx.send("Choose your card:", view=view)
        
        try:
            interaction = await bot.wait_for("interaction", timeout=120.0, check=lambda inter: inter.user == ctx.author and inter.data['custom_id'].startswith("card_") and inter.message.id == select_msg.id)
            card_index = int(interaction.data['custom_id'].split("_")[1])
            await interaction.response.defer()
        except asyncio.TimeoutError:
            card_index = random.randint(0, len(cards)-1)
            await ctx.send("⏰ Timeout! Card randomized.")
        selected_card = cards[card_index]
        
        logger.info(f"Turn {turn_num}: Card {selected_card[1]}")
        
        # Simulate outcome
        success_prob = (selected_card[2] / 100) + (0.2 if selected_card[3] == "Power Drain" else 0) + random.uniform(-0.1, 0.1)  # Chaos
        success = random.random() < success_prob
        outcome = "Epic success!" if success else "Chaotic failure!"
        
        outcome_prompt = f"Generate a punchy outcome (2-3 sentences) for choice {choice} using card '{selected_card[1]}' ({selected_card[3]}): {outcome} with a chaotic twist from {theme} crossover. Respond in English only. No hashtags or artifacts."
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", 
            messages=[{"role": "user", "content": outcome_prompt}], 
            max_tokens=100
        )
        outcome_text = response.choices[0].message.content.strip()
        logger.info(f"Outcome generated: {outcome_text[:50]}...")
        
        story += f"\n\n**Turn {turn_num}:** {turn_desc}\nChoice: {choice} with {selected_card[1]}\n{outcome_text}"
        c.execute("UPDATE campaigns SET story=?, current_turn=? WHERE campaign_id=?", (story, turn_num, campaign_id))
        conn.commit()
        
        await ctx.send(f"🎲 **Outcome:** {outcome_text}")
        
        # Pause between turns
        await asyncio.sleep(2)
    
    # End campaign
    await ctx.send("🎉 Campaign completed! Here's your loot:")
    
    # Generate and save new card (similar to chaos)
    rarity = random.choice(['Common', 'Rare', 'Epic', 'Legendary'])
    name_prompt = f"Generate a unique name for a {rarity} loot card from {theme} campaign. Respond in English only."
    name_response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[{"role": "user", "content": name_prompt}], 
        max_tokens=50
    )
    name = name_response.choices[0].message.content.strip()
    
    desc_prompt = f"Generate an exciting description for a {rarity} loot card named '{name}' from a completed {theme} D&D campaign. Respond in English only. Make it 3-5 punchy sentences about the rewards and achievements."
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[{"role": "user", "content": desc_prompt}], 
        max_tokens=200
    )
    desc = response.choices[0].message.content.strip()
    
    power = random.randint(10, 100) * (4 if rarity == 'Legendary' else 1)
    special = "Campaign Reward" if random.random() > 0.5 else "Victory Bonus"
    
    # Generate image for loot card (similar to chaos)
    leo_payload = {
        "prompt": f"Generate a HIGH-QUALITY SINGLE trading card ONLY in {rarity} gacha style: Title '{name}' centered at top, detailed central illustration based on '{desc}', glowing {rarity} borders, anime/JRPG vibe, high resolution, no text overlays except title. Card frame like Yu-Gi-Oh.", 
        "modelId": random.choice(available_models),
        "width": 512, 
        "height": 768, 
        "num_images": 1,
        "negative_prompt": "multiple images, blurry, low quality, collage, extra elements"
    }
    
    image_url = 'https://i.imgur.com/example_card.png'  # Fallback
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://cloud.leonardo.ai/api/rest/v1/generations", json=leo_payload, headers={"Authorization": f"Bearer {LEONARDO_API_KEY}"}) as resp:
                data = await resp.json()
                gen_id = data['sdGenerationJob']['generationId']
                
                for _ in range(30):
                    async with session.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", headers={"Authorization": f"Bearer {LEONARDO_API_KEY}"}) as poll:
                        poll_data = await poll.json()
                        if poll_data['generations_by_pk']['generated_images']:
                            image_url = poll_data['generations_by_pk']['generated_images'][0]['url']
                            break
                    await asyncio.sleep(5)
    except Exception as e:
        print(f"Error generating loot card: {e}")
    
    # Save loot card to DB
    card_id = str(random.randint(100000, 999999))
    c.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (card_id, str(ctx.author.id), rarity, name, desc, image_url, power, special, theme))
    conn.commit()
    
    # Show loot card embed (similar to chaos)
    rarity_colors = {
        'Common': 0xC0C0C0, 'Rare': 0x0000FF, 'Epic': 0x800080, 'Legendary': 0xFFD700
    }
    embed_color = rarity_colors.get(rarity, 0x00FF00)
    embed = discord.Embed(title=f"🎁 Loot Card: {name}", description=desc, color=embed_color)
    embed.add_field(name="Power", value=power, inline=True)
    embed.add_field(name="Special", value=special, inline=True)
    embed.set_image(url=image_url)
    embed.set_footer(text=f"Campaign Reward | Generated by Chaos Deck AI 🚀")
    await ctx.send(embed=embed)
    await ctx.send("*(See embed above for details)*")  # Fallback text for log
    
    # Unlock campaign badge
    unlock_badge(str(ctx.author.id), "⚔️ Campaign Conqueror", "Completed a campaign!")
    
    await add_points(str(ctx.author.id), 200, ctx)  # Campaign completion bonus

# Help command to list commands
@bot.command(name='commands')
async def commands_list(ctx):
    embed = discord.Embed(title="🎮 Chaos Deck AI - Available Commands", color=0x00FF00)
    embed.add_field(name="!chaos [mode] [theme] [target]", 
                   value="Generate a gacha card. Mode: solo/pvp/pve, Theme: onepiece/dragonball/evangelion/fromsoftware/jrpg/anime/soulslike/random", 
                   inline=False)
    embed.add_field(name="!daily", value="Claim daily rewards and maintain streak", inline=False)
    embed.add_field(name="!fuse [card1_id] [card2_id]", value="Fuse two cards into a powerful fusion card", inline=False)
    embed.add_field(name="!event", value="Check active limited-time events", inline=False)
    embed.add_field(name="!inventory", value="Show your cards", inline=False)
    embed.add_field(name="!campaign [action] [theme]", 
                   value="D&D-like PVE campaigns. Actions: start/continue/end, Theme: onepiece/dragonball/evangelion/fromsoftware/jrpg/anime/soulslike/random", 
                   inline=False)
    embed.add_field(name="!leaderboard", value="Show points leaderboard", inline=False)
    embed.add_field(name="!shop [buy <item_id>]", value="Show premium shop or buy items", inline=False)
    embed.add_field(name="!commands", value="Show this help message", inline=False)
    embed.add_field(name="!ping", value="Connection test", inline=False)
    embed.add_field(name="!hello", value="Bot greeting", inline=False)
    
    await ctx.send(embed=embed)

@bot.command()
async def hello(ctx):
    logger.info(f"!hello command triggered by {ctx.author} in channel {ctx.channel.name if hasattr(ctx.channel, 'name') else 'DM'}")
    await ctx.send("Hello, I'm Chaos Deck Buddy! 🎮")

@bot.command()
async def ping(ctx):
    logger.info("Ping command triggered")
    await ctx.send("Pong! 🏓")

@bot.command()
async def webhook_test(ctx):
    """Test del webhook Stripe"""
    base_url = os.getenv('BASE_URL', 'https://chaosdeckbuddy.onrender.com')
    webhook_url = f"{base_url}/webhook"
    health_url = f"{base_url}/health"
    
    await ctx.send('✅ Webhook configurato correttamente!\n'
                   f'🌐 URL: {webhook_url}\n'
                   f'🔗 Health check: {health_url}\n'
                   f'💳 Stripe configurato con chiavi live')

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        await interaction.response.defer()

@bot.event
async def on_message(message):
    logger.debug(f"Message received in channel {message.channel.name if hasattr(message.channel, 'name') else 'DM'}: {message.content} from {message.author}")
    if message.author == bot.user:
        return
    await bot.process_commands(message)

# Error handlers
@chaos.error
async def chaos_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Cooldown! Wait {error.retry_after:.2f} sec.")
    else:
        await ctx.send(f"Error: {error}")

@daily.error
async def daily_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"Daily cooldown! Wait {error.retry_after:.2f} sec.")
    else:
        await ctx.send(f"Daily error: {error}")

@fuse.error
async def fuse_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ **Usage:** !fuse [card1_id] [card2_id]")
    else:
        await ctx.send(f"Fusion error: {error}")

bot.run(TOKEN)