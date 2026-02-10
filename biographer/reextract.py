"""
Re-extract insights from existing session transcripts using improved methodology.

This script:
1. Reads existing session JSON files
2. Extracts Bill's raw speech
3. Runs the new balanced extraction prompts
4. Stores new entries in the database
5. Logs what was extracted

Improvements for robustness:
- Multiple JSON parsing attempts
- Regex-based fallback extraction
- Better error handling
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Import local modules
from biographer.enricher import DatabaseEnricher

# Output paths
SESSIONS_DIR = Path(__file__).parent / "logs" / "sessions"
REEXTRACT_LOG = Path(__file__).parent / "logs" / "reextract_log.json"


def load_session(session_path: Path) -> Dict[str, Any]:
    """Load a session JSON file."""
    with open(session_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_bill_speech(session: Dict[str, Any]) -> List[str]:
    """Extract all of Bill's speech from a session."""
    speeches = []
    seen_texts = set()  # Avoid duplicates

    for event in session.get('events', []):
        if event.get('type') == 'BILL_SPEAKS':
            text = event.get('data', {}).get('text', '')
            # Skip very short utterances and duplicates
            if text and len(text) > 50 and text not in seen_texts:
                speeches.append(text)
                seen_texts.add(text)
    return speeches


def load_extraction_prompt() -> str:
    """Load extraction prompt optimized for maximum capture."""
    return """Extract ALL information from this transcript for Bill's biography database.

CRITICAL: Extract EVERYTHING. There is NO LIMIT on number of extractions.
A substantial transcript should yield 20-50+ entries.

IMPORTANT: Output ONLY valid JSON. No markdown, no explanations.

For each piece of information, create an entry with these fields:
- category: one of [life_events, relationships, stories, joys, sorrows, loves, fears, wounds, healings, growth, strengths, vulnerabilities, regrets, wisdom, decisions, questions, self_knowledge, preferences, reasoning_patterns, value_hierarchies]
- title: brief title (NO quotes inside)
- insight: the content with ALL details (escape quotes with backslash)
- time_period: when this happened if mentioned
- significance: 1-10

Output format - return ONLY this JSON structure:
{
  "extractions": [
    {"category": "life_events", "title": "First motorcycle ride", "insight": "Bill first rode...", "time_period": "1976", "significance": 7},
    {"category": "relationships", "title": "Dad", "insight": "Bills father was...", "time_period": "", "significance": 8}
  ]
}

EXTRACTION RULES - MAXIMIZE CAPTURE:
1. Create SEPARATE entries for EACH distinct event, person, insight, or detail
2. EVERY PERSON mentioned = 1 relationships entry (even people mentioned in passing)
3. EVERY EVENT described = 1 life_events entry
4. EVERY EMOTION expressed = appropriate emotional category entry
5. EVERY PREFERENCE or opinion = preferences or self_knowledge entry
6. EVERY TIME/PLACE mentioned = include in time_period/insight
7. Do NOT summarize multiple things into one entry
8. Keep insight text clean - escape quotes, no special characters
9. Output ONLY the JSON object, nothing else

There is NO penalty for extracting too much. There IS a penalty for missing things.
Extract EXHAUSTIVELY. Aim for 20-50+ entries per transcript."""


def try_parse_json(text: str) -> Optional[Dict]:
    """Try multiple approaches to parse JSON from Claude's response."""

    # Approach 1: Direct parse
    try:
        return json.loads(text)
    except:
        pass

    # Approach 2: Find JSON block in markdown
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(.*?)\s*```',
        r'\{[\s\S]*"extractions"[\s\S]*\}'
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                json_str = match.group(1) if '```' in pattern else match.group(0)
                return json.loads(json_str)
            except:
                continue

    # Approach 3: Try to fix common issues
    # Find the JSON object boundaries
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        json_str = text[start:end+1]

        # Fix common issues
        # Replace unescaped newlines in strings
        json_str = re.sub(r'(?<!\\)\n(?=[^"]*"[^"]*(?:"[^"]*"[^"]*)*$)', '\\n', json_str)

        try:
            return json.loads(json_str)
        except:
            pass

    # Approach 4: Extract entries using regex
    entries = []
    entry_pattern = r'\{\s*"category"\s*:\s*"([^"]+)"\s*,\s*"title"\s*:\s*"([^"]+)"\s*,\s*"insight"\s*:\s*"([^"]+)"\s*,\s*"time_period"\s*:\s*"([^"]*)"\s*,\s*"significance"\s*:\s*(\d+)\s*\}'

    for match in re.finditer(entry_pattern, text):
        entries.append({
            'category': match.group(1),
            'title': match.group(2),
            'insight': match.group(3),
            'time_period': match.group(4),
            'significance': int(match.group(5))
        })

    if entries:
        return {'extractions': entries}

    return None


def run_extraction(client: Anthropic, transcript: str, extraction_prompt: str) -> Dict[str, Any]:
    """Run extraction on a transcript using Claude.

    Note: We NEVER truncate transcripts. Bill's words are precious.
    Uses streaming for Opus with high max_tokens (required for long operations).
    """

    full_prompt = f"""{extraction_prompt}

=== TRANSCRIPT ===
{transcript}"""

    # Use streaming for Opus with high max_tokens (required for operations > 10 min)
    response_text = ""
    with client.messages.stream(
        model="claude-opus-4-20250514",   # Use Opus for thorough extraction
        max_tokens=16000,                  # Large response for comprehensive extraction
        messages=[{"role": "user", "content": full_prompt}]
    ) as stream:
        for text in stream.text_stream:
            response_text += text

    # Try to parse JSON
    result = try_parse_json(response_text)

    if result:
        return result
    else:
        return {"error": "Could not parse JSON", "raw_response": response_text[:1000]}


def flatten_extractions(extraction_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten extraction result into a list of entries."""
    entries = []

    # Handle different extraction formats
    for key in ['factual_extractions', 'emotional_extractions', 'character_extractions',
                'cognitive_extractions', 'extractions']:
        if key in extraction_result:
            for ext in extraction_result[key]:
                # Normalize the extraction format
                normalized = {
                    'category': ext.get('category', 'self_knowledge'),
                    'sub_category': ext.get('sub_category', ''),
                    'title': ext.get('title', ''),
                    'insight': ext.get('insight', ext.get('observation', ext.get('content', ''))),
                    'evidence': ext.get('evidence', ''),
                    'time_period': ext.get('time_period', ext.get('date', '')),
                    'analysis': ext.get('analysis', ''),
                    'significance': ext.get('significance', 5),
                    'action': 'insert'
                }
                entries.append(normalized)

    return entries


def main():
    print("=" * 60)
    print("RE-EXTRACTION WITH IMPROVED METHODOLOGY")
    print("=" * 60)
    print()

    # Initialize
    client = Anthropic()
    enricher = DatabaseEnricher()
    extraction_prompt = load_extraction_prompt()

    # Track results
    results = {
        'started_at': datetime.now().isoformat(),
        'sessions_processed': 0,
        'transcripts_processed': 0,
        'entries_added': 0,
        'entries_by_category': {},
        'sessions': [],
        'errors': []
    }

    # Find session files
    session_files = sorted(SESSIONS_DIR.glob("session_*.json"))
    print(f"Found {len(session_files)} session files")
    print()

    for session_path in session_files:
        session_id = session_path.stem
        print(f"Processing: {session_id}")

        session = load_session(session_path)
        speeches = extract_bill_speech(session)

        if not speeches:
            print(f"  No speech found, skipping")
            continue

        session_result = {
            'session_id': session_id,
            'speeches_found': len(speeches),
            'entries_added': 0,
            'categories': {}
        }

        # Process each speech segment
        for i, speech in enumerate(speeches):
            print(f"  Speech {i+1}/{len(speeches)} ({len(speech)} chars)...")

            # Run extraction
            extraction = run_extraction(client, speech, extraction_prompt)

            if 'error' in extraction:
                error_msg = f"{session_id} speech {i+1}: {extraction['error']}"
                print(f"    Error: {extraction['error']}")
                results['errors'].append(error_msg)
                continue

            # Flatten and process entries
            entries = flatten_extractions(extraction)
            print(f"    Extracted {len(entries)} entries")

            if not entries:
                print(f"    No entries extracted")
                continue

            # Add to database
            for entry in entries:
                category = entry.get('category', 'self_knowledge')
                results['entries_by_category'][category] = results['entries_by_category'].get(category, 0) + 1
                session_result['categories'][category] = session_result['categories'].get(category, 0) + 1

            # Use enricher to process
            process_result = enricher.process_extractions(entries, require_confirmation=False)
            added = process_result.get('added', 0)
            session_result['entries_added'] += added
            results['entries_added'] += added
            results['transcripts_processed'] += 1

            print(f"    Added to database: {added}")

        results['sessions_processed'] += 1
        results['sessions'].append(session_result)
        print(f"  Session complete: {session_result['entries_added']} entries added")
        print()

    # Save log
    results['completed_at'] = datetime.now().isoformat()

    with open(REEXTRACT_LOG, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

    print("=" * 60)
    print("RE-EXTRACTION COMPLETE")
    print("=" * 60)
    print(f"Sessions processed: {results['sessions_processed']}")
    print(f"Transcripts processed: {results['transcripts_processed']}")
    print(f"Total entries added: {results['entries_added']}")
    print()
    print("Entries by category:")
    for cat, count in sorted(results['entries_by_category'].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    if results['errors']:
        print()
        print(f"Errors encountered: {len(results['errors'])}")
        for err in results['errors'][:5]:
            print(f"  - {err}")

    print()
    print(f"Log saved to: {REEXTRACT_LOG}")


if __name__ == '__main__':
    main()
