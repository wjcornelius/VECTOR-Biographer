"""Batch extractor for cognitive architecture analysis.

Processes existing source materials through Opus deep extraction.
Tracks costs and provides stop/resume capability.

Usage:
    python batch_extractor.py --preprocess    # Phase 1: Extract Bill's content only
    python batch_extractor.py --classify      # Phase 2: Haiku classification (optional)
    python batch_extractor.py --extract       # Phase 3: Opus deep extraction
    python batch_extractor.py --status        # Show progress and costs
    python batch_extractor.py --all           # Run all phases
"""

import os
import sys
import json
import re
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add parent for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# Cost tracking
COSTS = {
    "opus_input": 15.0 / 1_000_000,      # $15 per million tokens
    "opus_output": 75.0 / 1_000_000,     # $75 per million tokens
    "haiku_input": 0.25 / 1_000_000,     # $0.25 per million tokens
    "haiku_output": 1.25 / 1_000_000,    # $1.25 per million tokens
}

BUDGET_LIMIT = 50.0  # Maximum spend


@dataclass
class SourceDocument:
    """A document to be processed."""
    path: str
    source_type: str  # poe, text, letter, document
    raw_content: str
    bill_content: str  # Just Bill's parts
    token_estimate: int
    priority: int  # 1-10, higher = more important
    processed: bool = False
    extraction_result: Optional[Dict] = None


@dataclass
class CostTracker:
    """Tracks API costs."""
    opus_input_tokens: int = 0
    opus_output_tokens: int = 0
    haiku_input_tokens: int = 0
    haiku_output_tokens: int = 0

    @property
    def total_cost(self) -> float:
        return (
            self.opus_input_tokens * COSTS["opus_input"] +
            self.opus_output_tokens * COSTS["opus_output"] +
            self.haiku_input_tokens * COSTS["haiku_input"] +
            self.haiku_output_tokens * COSTS["haiku_output"]
        )

    @property
    def remaining_budget(self) -> float:
        return BUDGET_LIMIT - self.total_cost

    def can_afford_opus(self, input_tokens: int, est_output_tokens: int = None) -> bool:
        """Check if we can afford an Opus call."""
        if est_output_tokens is None:
            est_output_tokens = input_tokens  # Assume 1:1 ratio
        estimated_cost = (
            input_tokens * COSTS["opus_input"] +
            est_output_tokens * COSTS["opus_output"]
        )
        return estimated_cost <= self.remaining_budget


class BatchExtractor:
    """Batch extraction system for cognitive architecture analysis."""

    SOUL_DIR = Path(r"c:\Users\wjcor\OneDrive\Desktop\My_Songs\_soul")
    STATE_FILE = SOUL_DIR / "biographer" / "batch_state.json"

    def __init__(self):
        self.client = Anthropic()
        self.costs = CostTracker()
        self.documents: List[SourceDocument] = []
        self.load_state()

        # Load deep extraction prompt
        prompt_path = self.SOUL_DIR / "biographer" / "prompts" / "deep_extraction.txt"
        if prompt_path.exists():
            self.deep_extraction_prompt = prompt_path.read_text(encoding='utf-8')
        else:
            raise FileNotFoundError(f"Deep extraction prompt not found: {prompt_path}")

    def load_state(self):
        """Load previous state if exists."""
        if self.STATE_FILE.exists():
            try:
                state = json.loads(self.STATE_FILE.read_text(encoding='utf-8'))
                self.costs = CostTracker(**state.get('costs', {}))
                self.documents = [SourceDocument(**d) for d in state.get('documents', [])]
                print(f"Loaded state: {len(self.documents)} documents, ${self.costs.total_cost:.2f} spent")
            except Exception as e:
                print(f"Could not load state: {e}")

    def save_state(self):
        """Save current state for resume."""
        state = {
            'costs': asdict(self.costs),
            'documents': [asdict(d) for d in self.documents],
            'last_updated': datetime.now().isoformat()
        }
        self.STATE_FILE.write_text(json.dumps(state, indent=2, default=str), encoding='utf-8')

    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        return len(text) // 4

    # ==================== PHASE 1: PRE-PROCESSING ====================

    def extract_bill_from_poe(self, content: str) -> str:
        """Extract only Bill's messages from a POE conversation.

        POE format analysis:
        - Lines starting with @ followed by AI name = Bill's prompts
        - Lines that are timestamps (0:00, 1:23) = video transcripts (NOT Bill)
        - Large blocks of text without @ = AI responses (NOT Bill)

        We ONLY want Bill's prompts to the AI, as these reveal his thinking.
        """
        lines = content.split('\n')
        bill_messages = []
        current_prompt = []
        in_bill_prompt = False

        for i, line in enumerate(lines):
            stripped = line.strip()

            # Check if this is Bill prompting an AI (starts with @ModelName)
            if stripped.startswith('@') and any(m in stripped.lower() for m in
                ['claude', 'gemini', 'gpt', 'opus', 'sonnet', 'chatgpt', 'pro', 'flash']):
                # Save previous prompt if exists
                if current_prompt:
                    bill_messages.append('\n'.join(current_prompt))
                current_prompt = []
                in_bill_prompt = True

                # Extract the actual prompt content after @ModelName
                # Format: "@Model-Name prompt text here"
                parts = stripped.split(' ', 1)
                if len(parts) > 1:
                    current_prompt.append(parts[1])
                continue

            # Check if we've hit a timestamp (video transcript starting)
            if re.match(r'^\d{1,2}:\d{2}$', stripped):
                # End of Bill's prompt, video transcript starting
                if current_prompt:
                    bill_messages.append('\n'.join(current_prompt))
                current_prompt = []
                in_bill_prompt = False
                continue

            # Check if we've hit an AI response header
            ai_response_markers = [
                'Claude-Opus', 'Claude-Sonnet', 'Gemini', 'GPT-4', 'ChatGPT',
                'The Purpose Crisis', 'My Assessment', '## ', '### ',
                'Three Competing Frameworks', 'What I find most valuable'
            ]
            if any(marker in stripped for marker in ai_response_markers):
                if current_prompt:
                    bill_messages.append('\n'.join(current_prompt))
                current_prompt = []
                in_bill_prompt = False
                continue

            # If we're in Bill's prompt, collect the line
            if in_bill_prompt and stripped:
                # But skip if it looks like structured AI output
                if not stripped.startswith('-') and not stripped.startswith('*'):
                    current_prompt.append(line)

        # Save last prompt
        if current_prompt:
            bill_messages.append('\n'.join(current_prompt))

        # Clean up and join - only keep substantial prompts
        result = '\n\n---\n\n'.join(m.strip() for m in bill_messages if m.strip() and len(m.strip()) > 20)
        return result

    def extract_bill_from_texts(self, content: str, contact_name: str) -> str:
        """Extract Bill's messages from text conversations."""
        lines = content.split('\n')
        bill_messages = []
        current_message = []
        in_bill_message = False

        # Text format seems to be timestamp lines followed by messages
        # Bill's messages likely don't have the contact's name pattern

        for line in lines:
            stripped = line.strip()

            # Timestamp line pattern
            if re.match(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)', stripped):
                if current_message and in_bill_message:
                    bill_messages.append('\n'.join(current_message))
                current_message = []
                in_bill_message = True  # Next messages are Bill's until we see contact's pattern
                continue

            # If line contains media file references, it's from the contact
            if '.mp4' in stripped.lower() or '.jpg' in stripped.lower() or 'MB' in stripped:
                in_bill_message = False
                continue

            # Heuristic: longer messages with certain patterns are Bill's
            # (He writes longer, more reflective messages)
            if in_bill_message and stripped:
                current_message.append(line)

        if current_message and in_bill_message:
            bill_messages.append('\n'.join(current_message))

        return '\n\n---\n\n'.join(m.strip() for m in bill_messages if m.strip() and len(m.strip()) > 20)

    def extract_bill_from_claude_chat(self, content: str) -> str:
        """Extract Bill's parts from Claude chat transcripts.

        Format: BILLCOR: ... CLAUDE: ...
        We want only Bill's parts.
        """
        lines = content.split('\n')
        bill_messages = []
        current_message = []
        in_bill_section = False

        for line in lines:
            stripped = line.strip()

            # Check for Bill's message start
            if stripped.startswith('BILLCOR:') or stripped.startswith('BILLCOR '):
                if current_message:
                    bill_messages.append('\n'.join(current_message))
                current_message = [stripped.replace('BILLCOR:', '').replace('BILLCOR ', '').strip()]
                in_bill_section = True
                continue

            # Check for Claude's response start (end of Bill's message)
            if stripped.startswith('CLAUDE:') or stripped.startswith('CLAUDE '):
                if current_message:
                    bill_messages.append('\n'.join(current_message))
                current_message = []
                in_bill_section = False
                continue

            # Collect Bill's content
            if in_bill_section and stripped:
                current_message.append(line)

        # Save last message
        if current_message:
            bill_messages.append('\n'.join(current_message))

        return '\n\n---\n\n'.join(m.strip() for m in bill_messages if m.strip() and len(m.strip()) > 20)

    def preprocess(self) -> List[SourceDocument]:
        """Phase 1: Pre-process all source materials."""
        print("\n" + "=" * 60)
        print("PHASE 1: PRE-PROCESSING")
        print("=" * 60)

        documents = []

        # 1. Psychiatrist letter (highest priority - pure Bill)
        letter_path = self.SOUL_DIR / "psychiatrist_letter.txt"
        if letter_path.exists():
            content = letter_path.read_text(encoding='utf-8')
            doc = SourceDocument(
                path=str(letter_path),
                source_type="letter",
                raw_content=content,
                bill_content=content,  # All Bill
                token_estimate=self.estimate_tokens(content),
                priority=10
            )
            documents.append(doc)
            print(f"  + Psychiatrist letter: {doc.token_estimate} tokens (priority 10)")

        # 2. POE exports
        poe_dir = self.SOUL_DIR / "poe_exports"
        if poe_dir.exists():
            poe_files = sorted(poe_dir.glob("poe_*_Purpose_Crisis*.txt"))
            total_bill_tokens = 0
            for pf in poe_files:
                content = pf.read_text(encoding='utf-8')
                bill_content = self.extract_bill_from_poe(content)
                if bill_content:
                    doc = SourceDocument(
                        path=str(pf),
                        source_type="poe",
                        raw_content=content,
                        bill_content=bill_content,
                        token_estimate=self.estimate_tokens(bill_content),
                        priority=8
                    )
                    documents.append(doc)
                    total_bill_tokens += doc.token_estimate
            print(f"  + POE exports: {len(poe_files)} files, ~{total_bill_tokens} Bill tokens (priority 8)")

        # 3. Text conversations
        texts_dir = self.SOUL_DIR / "Texts"
        if texts_dir.exists():
            for tf in texts_dir.glob("*.txt"):
                content = tf.read_text(encoding='utf-8')
                contact = tf.stem
                bill_content = self.extract_bill_from_texts(content, contact)
                if bill_content and len(bill_content) > 100:
                    doc = SourceDocument(
                        path=str(tf),
                        source_type="text",
                        raw_content=content,
                        bill_content=bill_content,
                        token_estimate=self.estimate_tokens(bill_content),
                        priority=7 if contact == "Tracey" else 5
                    )
                    documents.append(doc)
                    print(f"  + Text ({contact}): {doc.token_estimate} tokens (priority {doc.priority})")

        # 4. Existing transcription in database
        try:
            import sqlite3
            db_path = self.SOUL_DIR / "bill_knowledge_base.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, raw_transcription FROM transcriptions")
            for row in cursor.fetchall():
                tid, content = row
                if content:
                    doc = SourceDocument(
                        path=f"db:transcriptions:{tid}",
                        source_type="transcription",
                        raw_content=content,
                        bill_content=content,  # Already Bill's words
                        token_estimate=self.estimate_tokens(content),
                        priority=9
                    )
                    documents.append(doc)
                    print(f"  + DB Transcription #{tid}: {doc.token_estimate} tokens (priority 9)")
            conn.close()
        except Exception as e:
            print(f"  ! Could not load transcriptions: {e}")

        # 5. Personal files from OneDrive Documents
        docs_dir = Path(r"C:\Users\wjcor\OneDrive\Documents")
        personal_files = [
            # High-value personal letters and reflections
            ("my story.txt", "letter", 10),
            ("my Story - Allen.txt", "letter", 10),  # Same letter with context
            ("Mum.txt", "letter", 10),
            ("Visiting Mum - CLAUDE an AI's Advice.txt", "letter", 10),
            ("String Dream.txt", "personal", 9),
            ("Dear CLAUDE.txt", "personal", 9),
            ("Project Intention Statement.txt", "personal", 8),
            ("Breakthroughs.txt", "personal", 8),
            ("Optimism.txt", "personal", 7),
            # Claude conversations with Bill's input (extract BILLCOR: parts)
            ("limitations of AI.txt", "claude_chat", 6),
            ("cognitive biases.txt", "claude_chat", 6),
        ]

        docs_count = 0
        for filename, doc_type, priority in personal_files:
            file_path = docs_dir / filename
            if file_path.exists():
                try:
                    content = file_path.read_text(encoding='utf-8')

                    # For Claude chats, extract just Bill's parts
                    if doc_type == "claude_chat":
                        bill_content = self.extract_bill_from_claude_chat(content)
                    else:
                        bill_content = content

                    if bill_content and len(bill_content) > 50:
                        doc = SourceDocument(
                            path=str(file_path),
                            source_type=doc_type,
                            raw_content=content,
                            bill_content=bill_content,
                            token_estimate=self.estimate_tokens(bill_content),
                            priority=priority
                        )
                        documents.append(doc)
                        docs_count += 1
                        print(f"  + {filename}: {doc.token_estimate} tokens (priority {priority})")
                except Exception as e:
                    print(f"  ! Could not read {filename}: {e}")

        if docs_count > 0:
            print(f"  Total personal documents: {docs_count}")

        # Sort by priority (highest first)
        documents.sort(key=lambda d: (-d.priority, d.token_estimate))

        self.documents = documents
        self.save_state()

        # Summary
        total_tokens = sum(d.token_estimate for d in documents)
        print(f"\nPre-processing complete:")
        print(f"  Documents: {len(documents)}")
        print(f"  Total Bill tokens: {total_tokens:,}")
        print(f"  Estimated Opus cost: ${total_tokens * COSTS['opus_input'] + total_tokens * COSTS['opus_output']:.2f}")

        return documents

    # ==================== PHASE 3: OPUS EXTRACTION ====================

    def extract_document(self, doc: SourceDocument) -> Dict[str, Any]:
        """Run Opus deep extraction on a single document."""
        prompt = f"""{self.deep_extraction_prompt}

=== SOURCE DOCUMENT ===
Source: {doc.path}
Type: {doc.source_type}

{doc.bill_content}
"""

        response = self.client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=8000,
            messages=[{"role": "user", "content": prompt}]
        )

        # Track costs
        self.costs.opus_input_tokens += response.usage.input_tokens
        self.costs.opus_output_tokens += response.usage.output_tokens

        # Parse response
        text = response.content[0].text
        try:
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                json_str = json_match.group()
                # Fix common JSON issues
                json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                result = json.loads(json_str)
                return result
        except Exception as e:
            print(f"    JSON parse error: {e}")

        return {"raw_response": text, "extractions": []}

    def run_extraction(self, max_docs: int = None):
        """Phase 3: Run Opus extraction on pre-processed documents."""
        print("\n" + "=" * 60)
        print("PHASE 3: OPUS DEEP EXTRACTION")
        print("=" * 60)
        print(f"Budget: ${BUDGET_LIMIT:.2f}")
        print(f"Spent: ${self.costs.total_cost:.2f}")
        print(f"Remaining: ${self.costs.remaining_budget:.2f}")
        print()

        # Filter to unprocessed documents
        to_process = [d for d in self.documents if not d.processed]
        if max_docs:
            to_process = to_process[:max_docs]

        print(f"Documents to process: {len(to_process)}")

        from biographer.enricher import DatabaseEnricher
        enricher = DatabaseEnricher()

        total_extractions = 0

        for i, doc in enumerate(to_process):
            # Check budget
            est_output = doc.token_estimate  # Assume 1:1
            if not self.costs.can_afford_opus(doc.token_estimate, est_output):
                print(f"\n*** BUDGET LIMIT REACHED ***")
                print(f"Stopping at document {i+1}/{len(to_process)}")
                break

            print(f"\n[{i+1}/{len(to_process)}] Processing: {Path(doc.path).name}")
            print(f"  Type: {doc.source_type}, Priority: {doc.priority}")
            print(f"  Tokens: ~{doc.token_estimate}")

            try:
                result = self.extract_document(doc)
                doc.extraction_result = result
                doc.processed = True

                # Process extractions
                all_extractions = []
                for ext in result.get('factual_extractions', []):
                    ext['extraction_type'] = 'factual'
                    if 'content' in ext and 'insight' not in ext:
                        ext['insight'] = ext['content']
                    all_extractions.append(ext)

                for ext in result.get('inferential_extractions', []):
                    ext['extraction_type'] = 'inferential'
                    if 'observation' in ext and 'insight' not in ext:
                        ext['insight'] = ext['observation']
                    all_extractions.append(ext)

                for ext in result.get('extractions', []):
                    if ext not in all_extractions:
                        all_extractions.append(ext)

                if all_extractions:
                    results = enricher.process_extractions(all_extractions)
                    print(f"  Extracted: {len(all_extractions)} items, saved: {results['added']}")
                    total_extractions += results['added']
                else:
                    print(f"  No extractions found")

                # Save state after each document
                self.save_state()

                # Cost update
                print(f"  Cost so far: ${self.costs.total_cost:.2f} / ${BUDGET_LIMIT:.2f}")

            except Exception as e:
                print(f"  ERROR: {e}")
                doc.processed = False

        print("\n" + "=" * 60)
        print("EXTRACTION COMPLETE")
        print("=" * 60)
        print(f"Documents processed: {sum(1 for d in self.documents if d.processed)}/{len(self.documents)}")
        print(f"Total extractions saved: {total_extractions}")
        print(f"Total cost: ${self.costs.total_cost:.2f}")
        print(f"Remaining budget: ${self.costs.remaining_budget:.2f}")

        self.save_state()

    def show_status(self):
        """Show current status."""
        print("\n" + "=" * 60)
        print("BATCH EXTRACTION STATUS")
        print("=" * 60)

        processed = [d for d in self.documents if d.processed]
        pending = [d for d in self.documents if not d.processed]

        print(f"\nDocuments:")
        print(f"  Total: {len(self.documents)}")
        print(f"  Processed: {len(processed)}")
        print(f"  Pending: {len(pending)}")

        print(f"\nCosts:")
        print(f"  Opus input tokens: {self.costs.opus_input_tokens:,}")
        print(f"  Opus output tokens: {self.costs.opus_output_tokens:,}")
        print(f"  Total spent: ${self.costs.total_cost:.2f}")
        print(f"  Budget remaining: ${self.costs.remaining_budget:.2f}")

        if pending:
            print(f"\nPending documents by priority:")
            for p in sorted(set(d.priority for d in pending), reverse=True):
                docs_at_priority = [d for d in pending if d.priority == p]
                tokens = sum(d.token_estimate for d in docs_at_priority)
                print(f"  Priority {p}: {len(docs_at_priority)} docs, ~{tokens:,} tokens")

        if processed:
            print(f"\nProcessed documents:")
            for d in processed[:10]:
                name = Path(d.path).name if not d.path.startswith('db:') else d.path
                exts = len(d.extraction_result.get('extractions', [])) if d.extraction_result else 0
                exts += len(d.extraction_result.get('factual_extractions', [])) if d.extraction_result else 0
                exts += len(d.extraction_result.get('inferential_extractions', [])) if d.extraction_result else 0
                print(f"  [{d.source_type}] {name[:40]}: {exts} extractions")


def main():
    parser = argparse.ArgumentParser(description="Batch cognitive architecture extraction")
    parser.add_argument('--preprocess', action='store_true', help='Run pre-processing phase')
    parser.add_argument('--extract', action='store_true', help='Run Opus extraction phase')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--all', action='store_true', help='Run all phases')
    parser.add_argument('--max-docs', type=int, help='Maximum documents to process')
    parser.add_argument('--reset', action='store_true', help='Reset state and start fresh')

    args = parser.parse_args()

    extractor = BatchExtractor()

    if args.reset:
        if extractor.STATE_FILE.exists():
            extractor.STATE_FILE.unlink()
            print("State reset.")
        extractor = BatchExtractor()

    if args.status:
        extractor.show_status()
        return

    if args.preprocess or args.all:
        extractor.preprocess()

    if args.extract or args.all:
        extractor.run_extraction(max_docs=args.max_docs)

    if not any([args.preprocess, args.extract, args.status, args.all, args.reset]):
        parser.print_help()


if __name__ == "__main__":
    main()
