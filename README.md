# Chaos Deck AI Bot

Un bot Discord per generare carte gacha con AI, integrato con OpenAI, ElevenLabs e Leonardo AI.

## 🚀 Installazione

1. **Installa le dipendenze:**
```bash
pip install -r requirements.txt
```

2. **Installa FFmpeg** (necessario per l'audio):
   - Windows: Scarica da https://ffmpeg.org/download.html
   - Linux: `sudo apt install ffmpeg`
   - macOS: `brew install ffmpeg`

3. **Crea un file `.env`** con le tue API keys:
```env
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
LEONARDO_API_KEY=your_leonardo_api_key
STRIPE_SECRET_KEY=your_stripe_secret_key
```

## 🎮 Comandi

- `!chaos [mode] [theme] [target]` - Genera una carta gacha
- `!inventory` - Mostra le tue carte
- `!leaderboard` - Mostra la classifica
- `!shop` - Mostra il negozio premium
- `!help` - Mostra tutti i comandi
- `!ping` - Test di connessione
- `!hello` - Saluto del bot

## 🎯 Funzionalità

- ✅ Intents configurati correttamente
- ✅ Estrazione nome migliorata con prompt separato
- ✅ Cooldown error handling
- ✅ Logica base PvP con AI judging
- ✅ Check voice channel per ElevenLabs
- ✅ Sistema punti e livelli funzionante
- ✅ Comando help completo
- ✅ Inizializzazione DB all'on_ready

## 🔧 Configurazione

Assicurati di avere tutte le API keys necessarie:
- **Discord Bot Token**: Crea un'applicazione su https://discord.com/developers/applications
- **OpenAI API Key**: Ottieni da https://platform.openai.com/api-keys
- **ElevenLabs API Key**: Ottieni da https://elevenlabs.io/
- **Leonardo AI API Key**: Ottieni da https://leonardo.ai/

## 🎵 Audio

Il bot supporta la sintesi vocale tramite ElevenLabs. Quando un utente è in un canale vocale, la descrizione della carta verrà letta ad alta voce.

## 🖼️ Immagini

Le immagini delle carte vengono generate tramite Leonardo AI con stile anime/JRPG.

## 🏆 Sistema Punti

- Ogni carta dà punti basati sul potere
- Ogni 500 punti = 1 livello
- I livelli sbloccano moltiplicatori

## 🚨 Note

- Il comando `!chaos` ha un cooldown di 5 minuti per utente
- Le carte vengono salvate nel database SQLite locale
- Il bot richiede permessi per leggere messaggi e connettersi ai canali vocali 