# Chaos Deck AI - Discord Bot

Un bot Discord avanzato per un gioco di carte gacha con integrazione Stripe per pagamenti, generazione di immagini AI con Leonardo, e campagne PvE.

## 🚀 Production Ready Features

### ✅ Modifiche per Render Deployment
- **Ngrok rimosso completamente** - Non più necessario per deployment cloud
- **Flask production mode** - Configurato per Render con `debug=False`
- **Environment variables** - Tutte le chiavi caricate da variabili d'ambiente
- **Logging migliorato** - Log strutturati per debugging production
- **Health checks** - Routes `/` e `/health` per monitoraggio
- **Error handling** - Gestione errori robusta per production
- **Graceful shutdown** - Gestione corretta dei segnali SIGTERM/SIGINT
- **Always-On functionality** - Bot login alla fine del server startup
- **No local dependencies** - Rimossi tutti i riferimenti a localhost/ngrok

### 🔧 Configurazione Production

1. **Variabili d'ambiente su Render:**
   ```
   DISCORD_TOKEN=your_bot_token
   OPENAI_API_KEY=your_openai_key
   ELEVENLABS_API_KEY=your_elevenlabs_key
   LEONARDO_API_KEY=your_leonardo_key
   STRIPE_PUBLISHABLE_KEY=pk_live_...
   STRIPE_SECRET_KEY=sk_live_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   BASE_URL=https://your-app.onrender.com
   ```

2. **Webhook URL Production:**
   - URL: `https://your-app.onrender.com/webhook`
   - Health: `https://your-app.onrender.com/health`
   - Root: `https://your-app.onrender.com/`

### 🎮 Comandi Disponibili

- `!chaos [mode] [theme]` - Genera carte gacha
- `!daily` - Riscatta ricompense giornaliere
- `!fuse [card1] [card2]` - Fonde due carte
- `!inventory` - Mostra la tua collezione
- `!campaign [action] [theme]` - Campagne PvE
- `!shop [buy <item>]` - Negozio premium
- `!event` - Eventi attivi
- `!leaderboard` - Classifica punti

### 💳 Integrazione Stripe

Il bot gestisce pagamenti per:
- Epic Booster Pack ($2)
- Legendary Pack ($5)
- Streak Saver ($0.50)
- Pity Booster ($1)
- Achievement Booster ($0.50)
- Fusion Crystal ($1)
- Event Booster ($1)

### 🎨 Generazione Immagini

- **Leonardo AI** per carte personalizzate
- **ElevenLabs** per audio in voice chat
- **OpenAI** per descrizioni e narrazione

### 📊 Database SQLite

Tabelle incluse:
- `users` - Punti, livelli, streak
- `cards` - Collezione carte
- `campaigns` - Progresso campagne
- `badges` - Badge sbloccati
- `achievements` - Sistema achievement

## 🛠️ Setup Locale

1. **Clona il repository:**
   ```bash
   git clone <repository-url>
   cd DiscordBot
   ```

2. **Installa dipendenze:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configura variabili d'ambiente:**
   ```bash
   cp env.example .env
   # Modifica .env con le tue chiavi
   ```

4. **Avvia il bot:**
   ```bash
   python bot.py
   ```

## 🌐 Deploy su Render

### Metodo 1: Deploy Automatico (Raccomandato)
1. **Crea nuovo Web Service su Render**
2. **Connetti il repository GitHub**
3. **Configura le variabili d'ambiente**
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `python bot.py`

### Metodo 2: Usando render.yaml
Il file `render.yaml` è già configurato per deployment automatico:
```yaml
services:
  - type: web
    name: chaos-deck-buddy
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python bot.py
```

### ✅ Features Always-On
- **Graceful Shutdown**: Gestione corretta dei segnali di terminazione
- **Database Safety**: Chiusura sicura delle connessioni
- **Logging Completo**: Tutti gli eventi registrati
- **Health Monitoring**: Endpoints per monitoraggio

### 🔍 Monitoraggio

- **Health Check:** `GET /health`
- **Root:** `GET /` 
- **Webhook:** `POST /webhook` (Stripe)

### 📝 Logs

Il bot ora usa logging strutturato:
- `INFO` - Operazioni normali
- `WARNING` - Problemi non critici
- `ERROR` - Errori critici
- `DEBUG` - Debug dettagliato

## 🎯 Features Avanzate

### Sistema Pity
- Contatore pity per garantire Legendary
- Reset automatico su Legendary
- Booster per ridurre pity

### Eventi Speciali
- Bonus per temi specifici
- Eventi limitati nel tempo
- Drop rate aumentati

### Campagne PvE
- Sistema D&D-like
- Scelte interattive
- Ricompense speciali
- Immagini generate per turno

### Sistema Achievement
- Badge automatici
- Achievement progressivi
- Ricompense punti

## 🔒 Sicurezza

- Tutte le chiavi in variabili d'ambiente
- Validazione webhook Stripe
- Error handling robusto
- Logging sicuro (no dati sensibili)

## 📈 Performance

- Threading per Flask in background
- Database SQLite ottimizzato
- Caching per API calls
- Timeout gestiti

---

**Chaos Deck AI** - Un'esperienza gacha completa con pagamenti, AI e campagne! 🎮✨ 