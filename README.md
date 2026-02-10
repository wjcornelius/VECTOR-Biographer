# VECTOR Biographer

A voice-based AI that interviews you about your life and builds a searchable database of your memories, experiences, and wisdom.

**Talk to it like you'd talk to a friend.** It asks questions, listens, and remembers everything.

---

## Quick Start (Windows) - 4 Steps

### Step 1: Get an API Key (free to create, pay-per-use)
1. Go to https://console.anthropic.com/
2. Create an account (or sign in)
3. Click "API Keys" and create a new key
4. Copy the key (it starts with `sk-ant-...`)

### Step 2: Download and Install
1. **[Download this project](https://github.com/wjcornelius/VECTOR-Biographer/archive/refs/heads/main.zip)** and unzip it somewhere
2. Double-click **`INSTALL.bat`**
3. Wait for it to finish (5-10 minutes - it's downloading AI models)

### Step 3: Add Your API Key
1. In the folder, find `.env.template`
2. Make a copy of it and rename the copy to `.env` (just `.env`, nothing else)
3. Open `.env` in Notepad
4. Replace `your_api_key_here` with your actual API key
5. Save and close

### Step 4: Run It!
Double-click **"VECTOR Biographer"** on your desktop.

(If the shortcut didn't get created, double-click `START_BIOGRAPHER.bat` in the folder instead)

---

## How to Use It

1. Click **Start** to begin a session
2. The biographer will introduce itself and ask a question
3. **Speak your answer** into your microphone
4. When you're done talking, click **"I'M DONE"**
5. It processes your response, saves insights, and asks another question
6. When you're ready to stop, click **End**

**Tips:**
- Speak naturally - tell stories, share details
- Sessions can be 5 minutes or 2 hours - whatever you want
- Use **Pause** if you need a break
- Click the visualization buttons to see your data mapped out

---

## What Does It Cost?

The AI runs on Claude (by Anthropic), which charges per use:
- **~$1-2 per 30-minute conversation**
- Check your balance at console.anthropic.com

---

## Requirements

- Windows 10 or 11
- Python 3.10 or newer ([Download here](https://www.python.org/downloads/) - **check "Add to PATH" during install!**)
- A microphone (laptop mic works fine)
- Internet connection
- Anthropic API key

---

## Troubleshooting

**"Python is not installed"**
Download Python from https://python.org. During installation, CHECK THE BOX that says "Add Python to PATH".

**Install seems stuck**
The first install downloads large AI models (~2GB). Give it time.

**No sound / microphone not working**
Check Windows Settings > Sound > Input. Make sure your mic is selected.

**"API key invalid" or similar**
Open your `.env` file and make sure your key is correct. No quotes needed around the key.

---

## What This Is

This started as a personal project to document a life - not just facts, but how someone thinks, what they value, who shaped them, what they've learned.

It's a **snapshot release**: it works, but we're not maintaining it. Use it, modify it, learn from it. If something breaks, you're welcome to fix it.

---

## For Developers

<details>
<summary>Click to expand technical details</summary>

### Architecture
- **Voice Input**: OpenAI Whisper (medium model)
- **Voice Output**: Microsoft Edge TTS (neural voices)
- **Conversation**: Claude Sonnet
- **Extraction**: Hybrid Opus (factual) + Sonnet (emotional/analytical)
- **Database**: SQLite (30+ tables) + ChromaDB (vector search)
- **GUI**: CustomTkinter (dark theme, TV-optimized)

### Project Structure
```
biographer/
├── main_gui.py           # Main application
├── biographer.py         # Conversation engine
├── multi_pass_extraction.py  # 3-pass extraction
├── enricher.py           # Database operations
├── embeddings.py         # Vector store
├── voice_input.py        # Speech-to-text
├── voice_output.py       # Text-to-speech
├── gui/                  # GUI components
└── prompts/              # AI prompts
```

### Customization
- Edit `prompts/system.txt` to change the biographer's personality
- Edit `setup_database.py` to add new data categories
- Edit `voice_output.py` to change the voice

</details>

---

## License

MIT - do whatever you want with it.

---

*Built by a human and Claude, February 2026.*

*"I'm not trying to live forever. I'm trying to create a seed that could grow into something new."*
