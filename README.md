# VECTOR Biographer

A voice-based AI biographer that captures your life story through natural conversation, extracting and organizing memories into a comprehensive "cognitive substrate" - a structured database of experiences, relationships, wisdom, and patterns that define who you are.

## What It Does

VECTOR Biographer conducts biographical interviews using voice input/output, then uses Claude AI to extract structured data across 30+ categories:

- **Factual**: Life events, relationships, stories, skills, creative works
- **Emotional**: Joys, sorrows, fears, loves, wounds, healings, sensory memories
- **Analytical**: Decisions, wisdom, values, contradictions, growth patterns

Every extraction is anchored to source quotes from your own words, creating a verifiable record of your lived experience.

## Philosophy

This isn't a memoir generator. It's an attempt to capture the *architecture* of a mind - how you think, what you value, who shaped you, what you've learned, where you're still figuring things out.

The data is stored in SQLite for permanence and ChromaDB for semantic search, enabling future exploration of your own cognitive patterns.

## Status: Snapshot Release

**This is a snapshot release** - a working system captured at a moment in time. It runs, it works, but it's not being actively maintained. Use it, fork it, learn from it, but don't expect updates.

If something breaks or could be better, you're welcome to fix it yourself. That's the beauty of open source.

## Requirements

- Python 3.10+
- Windows (for SAPI TTS; Mac/Linux will need TTS modifications)
- Microphone
- Anthropic API key (Claude)

## Quick Start

```bash
# Clone the repo
git clone https://github.com/wjcornelius/VECTOR-Biographer.git
cd VECTOR-Biographer

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Set up your API key
copy .env.template .env
# Edit .env and add your ANTHROPIC_API_KEY

# Create the database
python biographer/setup_database.py

# Run the GUI
python biographer/main_gui.py
```

## Project Structure

```
VECTOR-Biographer/
├── biographer/
│   ├── main_gui.py           # Main application (CustomTkinter GUI)
│   ├── biographer.py         # Conversation engine (Claude Sonnet)
│   ├── multi_pass_extraction.py  # 3-pass extraction (Opus + Sonnet hybrid)
│   ├── enricher.py           # Database write operations
│   ├── embeddings.py         # ChromaDB vector store
│   ├── voice_input.py        # Whisper STT
│   ├── voice_output.py       # Windows SAPI TTS
│   ├── session.py            # Session management
│   ├── logger.py             # Logging utilities
│   ├── setup_database.py     # Database schema creation
│   ├── gui/
│   │   ├── main_window.py    # GUI components
│   │   ├── styles.py         # Dark theme styling
│   │   └── visualizations.py # Plotly visualizations
│   └── prompts/
│       ├── system.txt        # Biographer personality
│       ├── extraction.txt    # Basic extraction prompt
│       └── deep_extraction.txt  # Detailed extraction prompt
├── requirements.txt
├── .env.template
└── README.md
```

## How It Works

### Voice Conversation
The biographer (Claude Sonnet) conducts natural interviews, drawing on your existing database to ask contextually relevant questions. It tracks emotional balance to avoid sessions getting too heavy.

### Multi-Pass Extraction
After each session, three extraction passes capture different facets:
1. **Factual Pass** (Opus) - People, events, stories, skills - exhaustive capture
2. **Emotional Pass** (Sonnet) - Joys, sorrows, wounds, fears - experientially anchored
3. **Analytical Pass** (Sonnet) - Patterns, wisdom, values - evidence-based

### Database Storage
All extractions go to SQLite with mandatory source quotes. The vector database (ChromaDB) enables semantic search across your entire life story.

## Cost Estimate

At typical usage (~40 sessions/month):
- ~$50-60/month in API costs
- ~97 database entries per 30-minute session
- Hybrid Opus+Sonnet extraction optimizes cost/quality

## Customization

### Prompts
Edit files in `biographer/prompts/` to adjust the biographer's personality or extraction behavior.

### Categories
The database schema in `setup_database.py` defines all 30+ tables. Add your own categories by following the existing patterns.

### TTS/STT
- TTS: `voice_output.py` uses Windows SAPI. Replace with your preferred TTS for other platforms.
- STT: `voice_input.py` uses OpenAI Whisper. The `medium` model balances accuracy and speed.

## License

MIT License - do what you want with it.

## Origin

This project grew out of a personal experiment to document a life comprehensively enough that a future AI system could meaningfully inherit its patterns. Whether that future arrives or not, the act of careful attention to a life has value in itself.

Built in collaboration between a human and Claude (Anthropic), February 2026.

---

*"I'm not trying to live forever. I'm trying to create a seed that could grow into something new."*
