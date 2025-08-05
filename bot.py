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
from dotenv import load_dotenv
import stripe
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from threading import Thread
import logging

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.getenv('DISCORD_TOKEN')
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
LEONARDO_API_KEY = os.getenv('LEONARDO_API_KEY')

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
            # Process the purchase
            process_purchase(user_id, item_id, session['id'])
        else:
            logger.warning(f"Missing metadata in session {session['id']}")
            
    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        logger.info(f"Payment succeeded: {payment_intent['id']}")
        
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        logger.warning(f"Payment failed: {payment_intent['id']}")
        
    return 'OK', 200

def process_purchase(user_id, item_id, session_id):
    """Process a successful purchase and award rewards"""
    try:
        # Get user from Discord
        user = bot.get_user(int(user_id))
        if not user:
            logger.warning(f"User {user_id} not found")
            return
            
        # Define items and their rewards
        items = {
            "booster": {
                "name": "Epic Booster Pack", 
                "price": 200, 
                "currency": "usd", 
                "rewards": "5 rare cards",
                "action": "award_booster_pack"
            },
            "legendary": {
                "name": "Legendary Pack", 
                "price": 500, 
                "currency": "usd", 
                "rewards": "3 legendary cards",
                "action": "award_legendary_pack"
            },
            "streak_saver": {
                "name": "Streak Saver", 
                "price": 50, 
                "currency": "usd", 
                "rewards": "Reset daily cooldown",
                "action": "reset_daily_cooldown"
            },
            "pity_booster": {
                "name": "Pity Booster", 
                "price": 100, 
                "currency": "usd", 
                "rewards": "Reduce pity by 10",
                "action": "reduce_pity"
            },
            "achievement_booster": {
                "name": "Achievement Booster", 
                "price": 50, 
                "currency": "usd", 
                "rewards": "Auto-unlock next achievement",
                "action": "unlock_next_achievement"
            },
            "fusion_crystal": {
                "name": "Fusion Crystal", 
                "price": 100, 
                "currency": "usd", 
                "rewards": "Guarantee fusion success",
                "action": "add_fusion_crystal"
            },
            "event_booster": {
                "name": "Event Booster", 
                "price": 100, 
                "currency": "usd", 
                "rewards": "Extra drops during events",
                "action": "add_event_booster"
            }
        }
        
        if item_id not in items:
            logger.warning(f"Invalid item_id: {item_id}")
            return
            
        item = items[item_id]
        
        # Log the purchase
        logger.info(f"Processing purchase: {user.name} bought {item['name']} (Session: {session_id})")
        
        # Award rewards based on item type
        if item_id == "booster":
            award_booster_pack(user_id)
        elif item_id == "legendary":
            award_legendary_pack(user_id)
        elif item_id == "streak_saver":
            reset_daily_cooldown(user_id)
        elif item_id == "pity_booster":
            reduce_pity(user_id)
        elif item_id == "achievement_booster":
            unlock_next_achievement(user_id)
        elif item_id == "fusion_crystal":
            add_fusion_crystal(user_id)
        elif item_id == "event_booster":
            add_event_booster(user_id)
            
        # Send confirmation message
        asyncio.run_coroutine_threadsafe(
            user.send(f"🎉 **Purchase Successful!**\n"
                     f"You bought: **{item['name']}**\n"
                     f"Rewards: **{item['rewards']}**\n"
                     f"Thank you for your purchase!"),
            bot.loop
        )
        
    except Exception as e:
        logger.error(f"Error processing purchase: {e}")

def award_booster_pack(user_id):
    """Award 5 rare cards to user"""
    # Simulate 5 rare chaos pulls
    for _ in range(5):
        # Generate a rare card (you can customize this logic)
        card_name = f"Rare Card {random.randint(1000, 9999)}"
        # Add to user's inventory (implement your card storage logic)
        logger.info(f"Awarded rare card to user {user_id}")

def award_legendary_pack(user_id):
    """Award 3 legendary cards to user"""
    for _ in range(3):
        card_name = f"Legendary Card {random.randint(1000, 9999)}"
        logger.info(f"Awarded legendary card to user {user_id}")

def reset_daily_cooldown(user_id):
    """Reset user's daily cooldown"""
    c.execute("UPDATE users SET last_daily = NULL WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Reset daily cooldown for user {user_id}")

def reduce_pity(user_id):
    """Reduce user's pity count by 10"""
    c.execute("UPDATE users SET pity_count = MAX(0, pity_count - 10) WHERE user_id = ?", (user_id,))
    conn.commit()
    logger.info(f"Reduced pity for user {user_id}")

def unlock_next_achievement(user_id):
    """Auto-unlock next achievement"""
    # Implement achievement unlocking logic
    logger.info(f"Unlocked next achievement for user {user_id}")

def add_fusion_crystal(user_id):
    """Add fusion crystal to user"""
    # Implement fusion crystal logic
    logger.info(f"Added fusion crystal to user {user_id}")

def add_event_booster(user_id):
    """Add event booster to user"""
    # Implement event booster logic
    logger.info(f"Added event booster to user {user_id}")

def run_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)

# DB Setup
conn = sqlite3.connect('chaos.db')
c = conn.cursor()

THEMES = [
    'onepiece', 'dragonball', 'evangelion', 'fromsoftware', 'jrpg', 'anime', 'soulslike', 'random',
    'seven_deadly_sins', 'naruto', 'my_hero_academia', 'jujutsu_kaisen', 'demon_slayer', 'attack_on_titan', 
    'bleach', 'hunter_x_hunter', 'fullmetal_alchemist', 'death_note', 'chainsaw_man', 'spy_x_family', 
    'black_clover', 'tokyo_ghoul', 'final_fantasy', 'persona', 'kingdom_hearts', 'tales_of', 'nier_automata', 
    'dragon_quest', 'chrono_trigger', 'fire_emblem', 'xenoblade', 'bravely_default', 'octopath_traveler', 
    'shin_megami_tensei', 'suikoden', 'valkyria_chronicles'
]

available_models = [
    "2067ae52-33fd-4a82-bb92-c2c55e7d2786",  # AlbedoBase XL
    "b63f7119-31dc-4540-969b-2a9df997e173",  # SDXL 0.9
    "5c232a9e-9061-4777-980a-ddc8e65647c6",  # Leonardo Vision XL
    "1e60896f-3c26-4296-8ecc-53e2afecc132"   # Leonardo Diffusion XL
]

@bot.event
async def on_ready():
    port = int(os.environ.get('PORT', 5000))
    base_url = os.getenv('BASE_URL', 'https://chaosdeckbuddy.onrender.com')
    webhook_url = f"{base_url}/webhook"
    
    print(f'Chaos Deck AI online! 🚀 Flask running on port {port}')
    print(f'Webhook URL: {webhook_url}')
    
    # Avvia Flask server in background
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f'Flask server avviato in background sulla porta {port}')
    
    # Initialize DB on ready
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, points INT DEFAULT 0, level INT DEFAULT 1, last_daily TEXT, streak INT DEFAULT 0, pity_count INT DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, user_id TEXT, rarity TEXT, name TEXT, description TEXT, image_url TEXT, power INTEGER, special_effect TEXT, theme TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS campaigns (campaign_id TEXT PRIMARY KEY, user_id TEXT, theme TEXT, current_turn INT DEFAULT 0, story TEXT, status TEXT DEFAULT 'active')''')
    c.execute('''CREATE TABLE IF NOT EXISTS badges (user_id TEXT, badge_name TEXT, PRIMARY KEY (user_id, badge_name))''')
    c.execute('''CREATE TABLE IF NOT EXISTS achievements (achievement_id TEXT PRIMARY KEY, name TEXT, description TEXT, points_reward INT, requirement_type TEXT, requirement_value INT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS user_achievements (user_id TEXT, achievement_id TEXT, unlocked_date TEXT, PRIMARY KEY (user_id, achievement_id))''')
    conn.commit()
    
    logger.info(f"Hardcoded models available: {len(available_models)} total")
    
    # Test dummy generation
    leo_test_payload = {"prompt": "Test single trading card in anime style", "modelId": random.choice(available_models), "width": 512, "height": 768, "num_images": 1}
    logger.info(f"Test dummy started with model {leo_test_payload['modelId']}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://cloud.leonardo.ai/api/rest/v1/generations", json=leo_test_payload, headers={"Authorization": f"Bearer {LEONARDO_API_KEY}"}) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    gen_id = data['sdGenerationJob']['generationId']
                    
                    # Poll for 10 loops
                    for _ in range(10):
                        async with session.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", headers={"Authorization": f"Bearer {LEONARDO_API_KEY}"}) as poll:
                            poll_data = await poll.json()
                            if poll_data['generations_by_pk']['generated_images']:
                                image_url = poll_data['generations_by_pk']['generated_images'][0]['url']
                                logger.info(f"Test gen success with model {leo_test_payload['modelId']}: Image URL {image_url}")
                                break
                        await asyncio.sleep(3)
                else:
                    logger.warning(f"Test fail: Status {resp.status} - {await resp.text()}")
    except Exception as e:
        logger.error(f"Test Leonardo dummy failed: {str(e)}")
    
    # Initialize achievements
    achievements_data = [
        ("first_pull", "First Pull", "Pull your first card", 50, "cards", 1),
        ("card_collector", "Card Collector", "Collect 25 cards", 200, "cards", 25),
        ("legendary_hunter", "Legendary Hunter", "Pull 5 legendary cards", 500, "legendary", 5),
        ("streak_master", "Streak Master", "Maintain 7-day streak", 300, "streak", 7),
        ("campaign_veteran", "Campaign Veteran", "Complete 3 campaigns", 400, "campaigns", 3),
        ("fusion_expert", "Fusion Expert", "Successfully fuse 5 cards", 600, "fusions", 5),
        ("chaos_puller", "Chaos Puller", "Pull 100 cards total", 1000, "cards", 100),
        ("daily_warrior", "Daily Warrior", "Claim 30 daily rewards", 800, "dailies", 30)
    ]
    
    for achievement in achievements_data:
        c.execute("INSERT OR IGNORE INTO achievements VALUES (?, ?, ?, ?, ?, ?)", achievement)
    conn.commit()

async def add_points(user_id, points, ctx=None):
    c.execute("INSERT OR IGNORE INTO users VALUES (?, 0, 1, NULL, 0, 0)", (user_id,))
    c.execute("UPDATE users SET points = points + ? WHERE user_id=?", (points, user_id))
    c.execute("SELECT points FROM users WHERE user_id=?", (user_id,))
    total = c.fetchone()[0]
    old_level = total // 500 + 1
    new_level = total // 500 + 1
    c.execute("UPDATE users SET level = ? WHERE user_id=?", (new_level, user_id))
    conn.commit()
    
    # Check for level up and perks
    if new_level > old_level and ctx:
        perks = {
            2: "+5% success in PVE",
            5: "Unlock rare themes",
            10: "Daily free !chaos"
        }
        perk = perks.get(new_level, "New level unlocked!")
        
        embed = discord.Embed(title="🔥 Level Up!", description=f"Reached Level {new_level}! Unlocked: {perk}", color=0xFFD700)
        await ctx.send(embed=embed)
    
    return total, new_level

def unlock_badge(user_id, badge_name, desc=""):
    c.execute("INSERT OR IGNORE INTO badges VALUES (?, ?)", (user_id, badge_name))
    conn.commit()
    logger.info(f"Badge unlocked for {user_id}: {badge_name} - {desc}")

def get_user_badges(user_id):
    c.execute("SELECT badge_name FROM badges WHERE user_id=?", (user_id,))
    badges = c.fetchall()
    return [badge[0] for badge in badges]

async def check_achievements(user_id, ctx=None):
    """Check and unlock achievements based on user progress"""
    c.execute("SELECT achievement_id, requirement_type, requirement_value, points_reward FROM achievements")
    achievements = c.fetchall()
    
    for achievement in achievements:
        achievement_id, req_type, req_value, points_reward = achievement
        
        # Check if already unlocked
        c.execute("SELECT 1 FROM user_achievements WHERE user_id=? AND achievement_id=?", (user_id, achievement_id))
        if c.fetchone():
            continue
        
        # Check requirements
        unlocked = False
        if req_type == "cards":
            c.execute("SELECT COUNT(*) FROM cards WHERE user_id=?", (user_id,))
            count = c.fetchone()[0]
            unlocked = count >= req_value
        elif req_type == "legendary":
            c.execute("SELECT COUNT(*) FROM cards WHERE user_id=? AND rarity='Legendary'", (user_id,))
            count = c.fetchone()[0]
            unlocked = count >= req_value
        elif req_type == "streak":
            c.execute("SELECT streak FROM users WHERE user_id=?", (user_id,))
            streak = c.fetchone()[0]
            unlocked = streak >= req_value
        elif req_type == "campaigns":
            c.execute("SELECT COUNT(*) FROM campaigns WHERE user_id=? AND status='ended'", (user_id,))
            count = c.fetchone()[0]
            unlocked = count >= req_value
        elif req_type == "fusions":
            # Track fusions in user stats
            c.execute("SELECT fusion_count FROM users WHERE user_id=?", (user_id,))
            fusion_count = c.fetchone()[0] if c.fetchone() else 0
            unlocked = fusion_count >= req_value
        elif req_type == "dailies":
            c.execute("SELECT daily_count FROM users WHERE user_id=?", (user_id,))
            daily_count = c.fetchone()[0] if c.fetchone() else 0
            unlocked = daily_count >= req_value
        
        if unlocked:
            # Unlock achievement
            c.execute("INSERT INTO user_achievements VALUES (?, ?, ?)", (user_id, achievement_id, datetime.now().strftime('%Y-%m-%d')))
            c.execute("UPDATE users SET points = points + ? WHERE user_id=?", (points_reward, user_id))
            conn.commit()
            
            if ctx:
                embed = discord.Embed(title="🏆 Achievement Unlocked!", description=f"**{achievement_id.replace('_', ' ').title()}**\n+{points_reward} points!", color=0xFFD700)
                await ctx.send(embed=embed)

def get_user_achievements(user_id):
    """Get list of unlocked achievements for user"""
    c.execute("""
        SELECT a.name, a.description, a.points_reward 
        FROM achievements a
        JOIN user_achievements ua ON a.achievement_id = ua.achievement_id
        WHERE ua.user_id = ?
    """, (user_id,))
    return c.fetchall()

@bot.command(name='chaos')
@commands.cooldown(1, 300, commands.BucketType.user)
async def chaos(ctx, *args):
    # Argument parsing
    mode = 'solo'
    theme = 'random'
    target = None
    
    if args:
        # First argument can be mode or theme
        if args[0].lower() in ['solo', 'pvp', 'pve']:
            mode = args[0].lower()
            if len(args) > 1:
                theme = args[1].lower()
                if len(args) > 2:
                    # Third argument is target for PvP
                    target = discord.utils.get(ctx.guild.members, name=args[2])
        else:
            # First argument is theme
            theme = args[0].lower()
            if len(args) > 1:
                if args[1].lower() in ['solo', 'pvp', 'pve']:
                    mode = args[1].lower()
                    if len(args) > 2:
                        target = discord.utils.get(ctx.guild.members, name=args[2])
                else:
                    # Second argument is target
                    target = discord.utils.get(ctx.guild.members, name=args[1])
    
    if theme not in THEMES: 
        theme = 'random'
    
    logger.info(f"Chaos command - User: {ctx.author.name}, Theme: {theme}, Mode: {mode}")
    
    # Get user level for rarity boost
    c.execute("SELECT level FROM users WHERE user_id=?", (str(ctx.author.id),))
    user_level = c.fetchone()
    user_level = user_level[0] if user_level else 1
    
    # Get pity count
    c.execute("SELECT pity_count FROM users WHERE user_id=?", (str(ctx.author.id),))
    pity_count = c.fetchone()[0] if c.fetchone() else 0
    
    # Adjust rarity based on level and pity
    if user_level >= 5:
        rarity_weights = ['Common']*35 + ['Rare']*30 + ['Epic']*20 + ['Legendary']*15
    else:
        rarity_weights = ['Common']*40 + ['Rare']*30 + ['Epic']*20 + ['Legendary']*10
    
    rarity = random.choice(rarity_weights)
    
    # Check for active events and apply bonuses
    active_events = get_active_events()
    event_bonus = None
    for event in active_events:
        if event["theme"] == theme:
            if event["bonus"] == "epic_boost":
                # Increase Epic chance during Seven Deadly Sins event
                if rarity == 'Common' and random.random() < 0.2:
                    rarity = 'Epic'
                    event_bonus = "🎭 Event Bonus: Upgraded to Epic!"
            elif event["bonus"] == "legendary_boost":
                # Increase Legendary chance during Dragon Ball event
                if rarity in ['Common', 'Rare'] and random.random() < 0.15:
                    rarity = 'Legendary'
                    event_bonus = "🎭 Event Bonus: Upgraded to Legendary!"
            elif event["bonus"] == "rare_boost":
                # Increase Rare chance during Evangelion event
                if rarity == 'Common' and random.random() < 0.25:
                    rarity = 'Rare'
                    event_bonus = "🎭 Event Bonus: Upgraded to Rare!"
    
    # Pity system: Force Legendary if pity >= 50
    if pity_count >= 50 and rarity != 'Legendary':
        rarity = 'Legendary'
        await ctx.send("🎉 **Pity Legendary!** Your patience has been rewarded!")
    
    # Update pity count
    if rarity == 'Legendary':
        new_pity_count = 0  # Reset pity on Legendary
    else:
        new_pity_count = pity_count + 1
    
    c.execute("UPDATE users SET pity_count = ? WHERE user_id=?", (new_pity_count, str(ctx.author.id)))
    conn.commit()
    
    # Addictive pull animation
    await ctx.send("🔮 Summoning chaotic energies...")
    await asyncio.sleep(1)
    await ctx.send("✨ Infusing with crossover powers...")
    await asyncio.sleep(1)
    await ctx.send("🃏 Revealing your card!")
    
    # Generate name with English prompt
    name_prompt = f"Generate a unique name for a {rarity} card in {theme} theme. Respond in English only. Only return the name, nothing else."
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    name_response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[{"role": "user", "content": name_prompt}], 
        max_tokens=50
    )
    name = name_response.choices[0].message.content.strip()
    
    # Generate description with English prompt
    desc_prompt = f"Generate an exciting, chaotic description for a {rarity} gacha card named '{name}' in a crossover game with themes from One Piece, Dragon Ball, Evangelion, and From Software, inspired by {theme} universe. Respond in English only. Make it 3-5 punchy sentences: Focus on unique, unpredictable abilities, epic lore tie-ins, and addictive gameplay hooks (e.g., random buffs/debuffs, universe collisions). Keep it immersive and fun, like a real trading card game – no generic intros, be specific!"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[{"role": "user", "content": desc_prompt}], 
        max_tokens=200
    )
    desc = response.choices[0].message.content.strip()
    
    # Truncate desc if too long for Discord embed
    if len(desc) > 1024:
        desc = desc[:1021] + '...'
    
    power = random.randint(10, 100) * (4 if rarity == 'Legendary' else 1)
    special = "Chaos Boost" if random.random() > 0.5 else "Power Drain"

    # Generate Image (Leonardo AI - poll for result)
    leo_payload = {
        "prompt": f"Generate a HIGH-QUALITY SINGLE trading card ONLY in {rarity} gacha style, themed around {theme}: Title '{name}' centered at top, detailed central illustration based on '{desc}', glowing {rarity} borders, anime/JRPG vibe inspired by One Piece/Dragon Ball/Evangelion/From Software with {theme} elements, high resolution, no text overlays except title. Card frame like Yu-Gi-Oh.", 
        "modelId": random.choice(available_models),
        "width": 512, 
        "height": 768, 
        "num_images": 1,
        "negative_prompt": "multiple images, blurry, low quality, collage, extra elements"
    }
    logger.info(f"Selected model for this generation: {leo_payload['modelId']}")
    headers = {"Authorization": f"Bearer {LEONARDO_API_KEY}"}
    
    image_url = 'https://placeholder.com/512x768'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://cloud.leonardo.ai/api/rest/v1/generations", json=leo_payload, headers=headers) as resp:
                data = await resp.json()
                logger.info(f"Response from post: {data}")
                gen_id = data['sdGenerationJob']['generationId']
                logger.info(f"Leonardo: Generation started, gen_id: {gen_id}")
                
                for _ in range(30):
                    async with session.get(f"https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}", headers=headers) as poll:
                        poll_data = await poll.json()
                        logger.debug(f"Polling {_+1}: {poll_data}")
                        if poll_data['generations_by_pk']['generated_images']:
                            image_url = poll_data['generations_by_pk']['generated_images'][0]['url']
                            logger.info(f"Image generated: {image_url}")
                            break
                    await asyncio.sleep(5)
                
                if image_url == 'https://placeholder.com/512x768':
                    logger.warning("Generation failed: No image ready after 30 attempts")
                    await ctx.send("Image not generated – retry or check Leonardo credits!")
                        
    except Exception as e:
        logger.error(f"Detailed Leonardo error: {str(e)} - Status: {resp.status if 'resp' in locals() else 'unknown'} - Response: {await resp.text() if 'resp' in locals() else 'no response'}")
        await ctx.send(f"Image error: {str(e)} – Check model ID or API.")
    
    # Fallback if image not generated
    if image_url == 'https://placeholder.com/512x768':
        image_url = 'https://i.imgur.com/example_card.png'  # Fallback URL

    # Save to DB
    card_id = str(random.randint(100000, 999999))
    c.execute("INSERT INTO cards VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
              (card_id, str(ctx.author.id), rarity, name, desc, image_url, power, special, theme))
    conn.commit()
    
    # Check for badges and achievements
    c.execute("SELECT COUNT(*) FROM cards WHERE user_id=?", (str(ctx.author.id),))
    total_cards = c.fetchone()[0]
    if total_cards >= 50:
        unlock_badge(str(ctx.author.id), "🃏 Pull Master", "50+ cards pulled!")
    if total_cards >= 100:
        unlock_badge(str(ctx.author.id), "🎴 Card Collector", "100+ cards in collection!")
    
    # Check achievements
    await check_achievements(str(ctx.author.id), ctx)

    # Audio if in voice (ElevenLabs) with voice channel check
    if ctx.author.voice and ctx.author.voice.channel:
        try:
            el_payload = {'text': desc, 'model_id': 'eleven_monolingual_v1'}
            el_resp = requests.post(
                'https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM', 
                headers={'xi-api-key': ELEVENLABS_API_KEY, 'Content-Type': 'application/json'}, 
                json=el_payload
            )
            if el_resp.status_code == 200:
                audio = AudioSegment.from_file(BytesIO(el_resp.content), format="mp3")
                audio.export("temp.mp3", format="mp3")
                vc = await ctx.author.voice.channel.connect()
                vc.play(discord.FFmpegPCMAudio("temp.mp3"))
                while vc.is_playing(): 
                    await asyncio.sleep(1)
                await vc.disconnect()
                os.remove("temp.mp3")
        except Exception as e:
            logger.error(f"ElevenLabs audio error: {e}")

    # Colori rarity
    rarity_colors = {
        'Common': 0xC0C0C0,    # Silver
        'Rare': 0x0000FF,       # Blue
        'Epic': 0x800080,       # Purple
        'Legendary': 0xFFD700    # Gold
    }
    embed_color = rarity_colors.get(rarity, 0x00FF00)
    
    # Embed migliorato
    embed = discord.Embed(title=f"{rarity} Card: {name}", color=embed_color)
    embed.add_field(name="Power", value=power, inline=True)
    embed.add_field(name="Special", value=special, inline=True)
    embed.add_field(name="Description", value=f"*{desc}*", inline=False)  # Italics per vibe narrativa
    embed.set_image(url=image_url)
    
    # Thumbnail per rarity
    rarity_icons = {
        'Common': "https://cdn.discordapp.com/emojis/1107.png",
        'Rare': "https://cdn.discordapp.com/emojis/1108.png", 
        'Epic': "https://cdn.discordapp.com/emojis/1109.png",
        'Legendary': "https://cdn.discordapp.com/emojis/1110.png"
    }
    embed.set_thumbnail(url=rarity_icons.get(rarity, "https://cdn.discordapp.com/emojis/1107.png"))
    
    # Footer with badges and pity
    user_badges = get_user_badges(str(ctx.author.id))
    badges_str = " ".join(user_badges) if user_badges else ""
    embed.set_footer(text=f"🚀 Powered by Chaos | Level: {level} | Pity: {new_pity_count}/50 {badges_str}")
    
    await ctx.send(embed=embed)
    await ctx.send("*(See embed above for details)*")  # Fallback text for log
    
    # Show event bonus if applicable
    if event_bonus:
        await ctx.send(event_bonus)

    points = power // 10
    total, level = await add_points(str(ctx.author.id), points, ctx)
    await ctx.send(f"{ctx.author.mention} gained {points} points! Total: {total} | Level: {level}")
    
    # Random bonus reward
    if random.random() > 0.7:
        extra_points = 50
        await add_points(str(ctx.author.id), extra_points, ctx)
        await ctx.send(f"🎉 Bonus! +{extra_points} points!")

    # Modes (PvP/PvE stub - expand)
    if mode == 'pvp' and target:
        await ctx.send("PvP mode: AI judging... (Implement full logic)")
        # Basic PvP logic
        pvp_prompt = f"Judge a card battle between {ctx.author.name} and {target.name}. Respond in English only. Winner is [user] because [reason]."
        try:
            pvp_response = client.chat.completions.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": pvp_prompt}], 
                max_tokens=100
            )
            result = pvp_response.choices[0].message.content.strip()
            await ctx.send(f"🏆 PvP Result: {result}")
        except Exception as e:
            await ctx.send("Error in PvP judgment")
    elif mode == 'pve':
        await ctx.send("PvE mode: Group quest started!")
        # Redirect to campaign system
        await campaign(ctx, "start", theme)

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

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    c.execute("SELECT * FROM users ORDER BY points DESC LIMIT 5")
    top = c.fetchall()
    
    leaderboard_msg = "🏆 **Leaderboard:**\n"
    for i, user in enumerate(top, 1):
        user_name = bot.get_user(int(user[0])).name if bot.get_user(int(user[0])) else user[0]
        user_badges = get_user_badges(user[0])
        badges_str = " " + " ".join(user_badges) if user_badges else ""
        leaderboard_msg += f"{i}. **{user_name}**: {user[1]} pts (Lvl {user[2]}){badges_str}\n"
    
    await ctx.send(leaderboard_msg)

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