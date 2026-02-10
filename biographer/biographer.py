"""Biographer brain - Claude-powered interviewer for Bill's life story."""

import os
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from anthropic import Anthropic
from dotenv import load_dotenv

# Optional imports for GUI integration
try:
    from .embeddings import VectorStore
    VECTOR_AVAILABLE = True
except ImportError:
    VECTOR_AVAILABLE = False

try:
    from .logger import SessionLogger, system_log
    LOGGING_AVAILABLE = True
except ImportError:
    LOGGING_AVAILABLE = False


class Biographer:
    """The AI interviewer that conducts biographical conversations with Bill."""

    # Models for different tasks
    CONVERSATION_MODEL = "claude-sonnet-4-20250514"  # Fast, good for dialogue
    EXTRACTION_MODEL = "claude-opus-4-20250514"      # Opus for thorough extraction - capture EVERYTHING

    def __init__(
        self,
        db_path: Optional[Path] = None,
        model: str = None,
        prompts_dir: Optional[Path] = None,
        use_vector_store: bool = True,
        session_logger: Optional['SessionLogger'] = None,
    ):
        # Load environment
        load_dotenv()

        # Initialize Anthropic client
        self.client = Anthropic()
        self.model = model or self.CONVERSATION_MODEL

        # Database path
        if db_path is None:
            db_path = Path(__file__).parent.parent / "bill_knowledge_base.db"
        self.db_path = db_path

        # Prompts directory
        if prompts_dir is None:
            prompts_dir = Path(__file__).parent / "prompts"
        self.prompts_dir = prompts_dir

        # Load prompts
        self.system_prompt = self._load_prompt("system.txt")
        self.analysis_prompt = self._load_prompt("analysis.txt")
        self.extraction_prompt = self._load_prompt("extraction.txt")
        self.deep_extraction_prompt = self._load_prompt("deep_extraction.txt")

        # Conversation state
        self.messages: List[Dict[str, str]] = []
        self.current_topics: List[str] = []

        # Vector store for semantic memory retrieval
        self.vector_store: Optional[VectorStore] = None
        if use_vector_store and VECTOR_AVAILABLE:
            try:
                self.vector_store = VectorStore()
                print(f"  Vector store: {self.vector_store.get_entry_count()} entries")
            except Exception as e:
                print(f"  Vector store unavailable: {e}")

        # Session logger
        self.session_logger = session_logger

        # GUI callbacks (set by main_gui.py)
        self.on_memories_retrieved: Optional[Callable[[List[Dict]], None]] = None
        self.on_topic_change: Optional[Callable[[str], None]] = None
        self.on_insights_update: Optional[Callable[[str], None]] = None
        self.on_exploration_update: Optional[Callable[[str], None]] = None

        # Retrieved memories cache (for display)
        self.last_retrieved_memories: List[Dict[str, Any]] = []

        # Category coverage tracking for gap awareness
        self.category_coverage: Dict[str, int] = {}
        self.underrepresented_categories: List[str] = []
        self._analyze_gaps()

        # Session valence tracking for emotional balance (bipolar consideration)
        # Valence: -1.0 (very light/joyful) to +1.0 (very heavy/dark)
        # Target: keep near 0 (neutral) over the session
        self.session_valence_history: List[float] = []
        self.session_valence_avg: float = 0.0

        print(f"Biographer initialized:")
        print(f"  Conversation model: {self.model}")
        print(f"  Extraction model: {self.EXTRACTION_MODEL}")
        if self.underrepresented_categories:
            print(f"  Underrepresented areas: {', '.join(self.underrepresented_categories[:3])}")

    def _analyze_gaps(self):
        """Analyze the database to identify underrepresented categories."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Categories we care about and their friendly names
            category_info = {
                # Core factual categories
                'relationships': ('relationships', 'key people in Bill\'s life'),
                'life_events': ('life_events', 'specific events and experiences'),
                'stories': ('stories', 'full narratives from Bill\'s life'),

                # Positive/light categories
                'joys': ('joys', 'what brings Bill fulfillment and happiness'),
                'loves': ('loves', 'people and things Bill deeply loves'),
                'strengths': ('strengths', 'Bill\'s virtues and capacities'),
                'growth': ('growth', 'how Bill has grown through challenges'),
                'healings': ('healings', 'recoveries and how Bill has mended'),

                # Shadow/heavy categories (balanced with above)
                'sorrows': ('sorrows', 'grief and sadness Bill has experienced'),
                'wounds': ('wounds', 'psychological injuries and traumas'),
                'fears': ('fears', 'what threatens Bill'),
                'losses': ('losses', 'deaths and endings Bill has experienced'),
                'regrets': ('regrets', 'what Bill would do differently'),
                'vulnerabilities': ('vulnerabilities', 'Bill\'s tender spots'),

                # Cognitive/reflective categories
                'decisions': ('decisions', 'major life choices and their reasoning'),
                'wisdom': ('wisdom', 'hard-won insights'),
                'questions': ('questions', 'what Bill is still figuring out'),
                'longings': ('longings', 'Bill\'s unmet needs and yearnings'),

                # v2.0 new categories
                'sensory_memories': ('sensory_memories', 'vivid sensory experiences that stayed with Bill'),
                'creative_works': ('creative_works', 'things Bill has made, built, or created'),
                'skills_competencies': ('skills_competencies', 'skills and abilities Bill has developed'),
                'aspirations': ('aspirations', 'what Bill still wants to do or become'),
            }

            self.category_coverage = {}
            for table, (name, desc) in category_info.items():
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    self.category_coverage[table] = count
                except sqlite3.Error:
                    self.category_coverage[table] = 0

            conn.close()

            # Find underrepresented categories (less than 5 entries)
            # Prioritize the most important ones, balancing light and shadow
            priority_order = [
                # Core factual (highest priority)
                'relationships', 'life_events', 'stories',
                # Light categories (balanced exploration)
                'joys', 'loves', 'strengths', 'growth', 'healings',
                # Shadow categories (balanced with light)
                'sorrows', 'wounds', 'fears', 'losses', 'regrets', 'vulnerabilities',
                # Cognitive/reflective
                'decisions', 'wisdom', 'questions', 'longings',
                # v2.0 new categories
                'sensory_memories', 'creative_works', 'skills_competencies', 'aspirations'
            ]

            self.underrepresented_categories = [
                cat for cat in priority_order
                if self.category_coverage.get(cat, 0) < 5
            ]

        except Exception as e:
            print(f"Error analyzing gaps: {e}")
            self.category_coverage = {}
            self.underrepresented_categories = []

    def get_gap_context(self) -> str:
        """Get a brief description of what's underrepresented for Claude."""
        if not self.underrepresented_categories:
            return ""

        gap_descriptions = {
            # Core factual
            'relationships': 'the key people in your life',
            'life_events': 'specific events and experiences',
            'stories': 'complete stories from your life',
            # Light categories
            'joys': 'what brings you joy and fulfillment',
            'loves': 'people and things you deeply love',
            'strengths': 'your skills and virtues',
            'growth': 'how challenges helped you grow',
            'healings': 'how you\'ve recovered from hard times',
            # Shadow categories
            'sorrows': 'losses or sadness you\'ve experienced',
            'wounds': 'difficult experiences that shaped you',
            'fears': 'what concerns or worries you',
            'losses': 'endings or deaths that affected you',
            'regrets': 'things you\'d do differently',
            'vulnerabilities': 'areas where you struggle',
            # Cognitive/reflective
            'decisions': 'major life choices you\'ve made',
            'wisdom': 'hard-won insights from your experiences',
            'questions': 'things you\'re still figuring out',
            'longings': 'things you wish for',
            # v2.0 new categories
            'sensory_memories': 'vivid sensory experiences - smells, sounds, textures that stayed with you',
            'creative_works': 'things you\'ve made, built, or created',
            'skills_competencies': 'skills and abilities you\'ve developed',
            'aspirations': 'what you still want to do or become',
        }

        gaps = [gap_descriptions.get(cat, cat) for cat in self.underrepresented_categories[:3]]
        return "Areas we haven't explored much yet: " + ", ".join(gaps) + "."

    def assess_valence(self, text: str) -> float:
        """
        Assess the emotional valence of text.
        Returns: -1.0 (very light/joyful) to +1.0 (very heavy/dark)
        Uses keyword-based heuristics for speed (no API call).
        """
        text_lower = text.lower()

        # Heavy/dark indicators (positive valence = heavy)
        heavy_words = [
            'death', 'died', 'dying', 'funeral', 'grief', 'loss', 'lost',
            'trauma', 'abuse', 'pain', 'suffering', 'hurt', 'wound',
            'fear', 'afraid', 'scared', 'anxiety', 'depressed', 'depression',
            'suicide', 'cancer', 'illness', 'disease', 'hospital',
            'divorce', 'separation', 'abandoned', 'betrayed', 'regret',
            'mistake', 'failure', 'failed', 'guilt', 'shame', 'angry',
            'rage', 'violence', 'assault', 'war', 'tragedy', 'heartbreak'
        ]

        # Light/joyful indicators (negative valence = light)
        light_words = [
            'joy', 'happy', 'happiness', 'love', 'loved', 'fun', 'funny',
            'laugh', 'laughed', 'smile', 'exciting', 'excited', 'adventure',
            'wonderful', 'amazing', 'beautiful', 'peace', 'peaceful',
            'grateful', 'thankful', 'blessing', 'lucky', 'fortunate',
            'success', 'accomplished', 'proud', 'celebrate', 'celebration',
            'hobby', 'vacation', 'travel', 'music', 'art', 'creative',
            'friend', 'friendship', 'play', 'game', 'enjoy', 'pleasure'
        ]

        heavy_count = sum(1 for word in heavy_words if word in text_lower)
        light_count = sum(1 for word in light_words if word in text_lower)

        # Calculate valence: positive = heavy, negative = light
        total = heavy_count + light_count
        if total == 0:
            return 0.0  # Neutral

        valence = (heavy_count - light_count) / max(total, 1)
        return max(-1.0, min(1.0, valence))  # Clamp to [-1, 1]

    def update_session_valence(self, bill_text: str, biographer_text: str):
        """Update session valence based on the latest exchange."""
        # Weight Bill's words more heavily than biographer's
        bill_valence = self.assess_valence(bill_text)
        bio_valence = self.assess_valence(biographer_text)
        exchange_valence = (bill_valence * 0.7) + (bio_valence * 0.3)

        self.session_valence_history.append(exchange_valence)

        # Calculate running average (weighted toward recent)
        if len(self.session_valence_history) <= 3:
            self.session_valence_avg = sum(self.session_valence_history) / len(self.session_valence_history)
        else:
            # Exponential moving average for recent bias
            recent = self.session_valence_history[-5:]
            weights = [0.1, 0.15, 0.2, 0.25, 0.3][:len(recent)]
            self.session_valence_avg = sum(v * w for v, w in zip(recent, weights)) / sum(weights)

    def get_balance_guidance(self) -> str:
        """Get guidance for Claude based on current session valence."""
        if len(self.session_valence_history) < 2:
            return ""  # Not enough data yet

        avg = self.session_valence_avg

        if avg > 0.4:
            return """
SESSION BALANCE NOTE: The conversation has been exploring some heavy emotional territory.
Consider gently steering toward lighter memories or taking a brief pause.
You might say something like: "That's a lot to sit with. Want to shift gears for a moment?"
"""
        elif avg > 0.25:
            return """
SESSION BALANCE NOTE: We've touched on some deeper topics.
After this question, consider balancing with something lighter.
"""
        elif avg < -0.4:
            return """
SESSION BALANCE NOTE: The conversation has been quite light.
If appropriate, you might gently explore something with more depth.
"""
        else:
            return ""  # Balanced, no guidance needed

    def reset_session_valence(self):
        """Reset valence tracking for a new session."""
        self.session_valence_history = []
        self.session_valence_avg = 0.0

    def _load_prompt(self, filename: str) -> str:
        """Load a prompt from file."""
        prompt_path = self.prompts_dir / filename
        if prompt_path.exists():
            return prompt_path.read_text(encoding='utf-8')
        else:
            print(f"Warning: Prompt file not found: {prompt_path}")
            return ""

    def retrieve_relevant_memories(
        self,
        query: str,
        top_k: int = 15,
        tables: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve semantically relevant memories from the vector store.

        Args:
            query: The topic or question to find relevant memories for
            top_k: Number of memories to retrieve
            tables: Optional list of tables to filter by

        Returns:
            List of relevant memories with scores
        """
        if not self.vector_store:
            return []

        try:
            memories = self.vector_store.query(query, top_k=top_k, tables=tables)
            self.last_retrieved_memories = memories

            # Log the retrieval
            if self.session_logger:
                self.session_logger.log_vector_query(query, memories)

            # Notify GUI
            if self.on_memories_retrieved:
                self.on_memories_retrieved(memories)

            return memories
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            if self.session_logger:
                self.session_logger.log_error('VECTOR_QUERY', str(e))
            return []

    def _memories_to_context(self, memories: List[Dict[str, Any]]) -> str:
        """Convert retrieved memories to context string for Claude."""
        if not memories:
            return ""

        context_parts = ["=== RELEVANT MEMORIES (by semantic similarity) ==="]
        for i, mem in enumerate(memories[:15], 1):
            score = mem.get('score', 0)
            table = mem.get('table', 'unknown')
            text = mem.get('text', '')[:300]  # Truncate long entries
            context_parts.append(f"\n[{i}] ({table}, relevance: {score:.2f})")
            context_parts.append(text)

        return "\n".join(context_parts)

    def _get_db_context(self) -> str:
        """Get relevant context from the database for Claude."""
        context_parts = []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get self_knowledge entries
            cursor.execute("""
                SELECT category, insight, evidence
                FROM self_knowledge
                ORDER BY date_realized DESC
                LIMIT 50
            """)
            knowledge = cursor.fetchall()
            if knowledge:
                context_parts.append("=== BILL'S SELF-KNOWLEDGE ===")
                for cat, insight, evidence in knowledge:
                    context_parts.append(f"[{cat}] {insight}")
                    if evidence:
                        context_parts.append(f"   Evidence: {evidence[:100]}...")

            # Get life events
            cursor.execute("""
                SELECT date_start, event_type, title, description
                FROM life_events
                ORDER BY date_start DESC
                LIMIT 30
            """)
            events = cursor.fetchall()
            if events:
                context_parts.append("\n=== KEY LIFE EVENTS ===")
                for date, etype, title, desc in events:
                    desc_text = desc[:100] if desc else title
                    context_parts.append(f"[{date or 'Unknown date'}] {etype}: {desc_text}")

            # Get family members
            cursor.execute("""
                SELECT name, relationship, death_date, notes
                FROM family
                LIMIT 20
            """)
            family = cursor.fetchall()
            if family:
                context_parts.append("\n=== FAMILY ===")
                for name, rel, death_date, notes in family:
                    status_str = " (deceased)" if death_date else ""
                    context_parts.append(f"{name} - {rel}{status_str}")

            # Get philosophies/values
            cursor.execute("""
                SELECT category, belief_statement, explanation
                FROM philosophies
                LIMIT 15
            """)
            beliefs = cursor.fetchall()
            if beliefs:
                context_parts.append("\n=== BELIEFS & VALUES ===")
                for category, belief, explanation in beliefs:
                    exp_str = f": {explanation[:100]}..." if explanation else ""
                    context_parts.append(f"[{category}] {belief}{exp_str}")

            conn.close()

        except sqlite3.Error as e:
            print(f"Database error: {e}")

        return "\n".join(context_parts)

    def analyze_database(self) -> List[str]:
        """Analyze the database to identify promising interview topics."""
        db_context = self._get_db_context()

        prompt = f"""Based on this database of Bill's life:

{db_context}

{self.analysis_prompt}"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        # Parse the response to extract topics
        text = response.content[0].text
        topics = []

        # Simple parsing - look for numbered items
        for line in text.split('\n'):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith('-')):
                # Clean up the topic
                topic = line.lstrip('0123456789.-) ').strip()
                if topic:
                    topics.append(topic)

        self.current_topics = topics[:5]
        return self.current_topics

    def get_opening(self, has_previous_session: bool, previous_context: str = "") -> str:
        """Generate an opening for the conversation."""
        db_context = self._get_db_context()
        gap_context = self.get_gap_context()

        # Refresh gap analysis at session start
        self._analyze_gaps()

        if has_previous_session:
            user_message = f"""You're continuing a biographical interview with Bill. Here's context from the database:

{db_context}

{gap_context}

Previous session context:
{previous_context}

Generate a warm, brief opening that acknowledges where you left off and proposes continuing or suggests a new direction. Before asking your question, briefly mention what area of Bill's life you'd like to explore and why (e.g., "I'd love to learn more about the key people who shaped you..."). Be conversational, not formal."""
        else:
            user_message = f"""You're starting a new biographical interview with Bill. Here's what you know about him from the database:

{db_context}

{gap_context}

Generate a warm, brief opening that introduces yourself as his biographer and proposes an interesting starting topic. Before asking your question, briefly mention what area of Bill's life you'd like to explore and why. Be conversational and genuinely curious."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_message}]
        )

        return response.content[0].text

    def respond(self, user_input: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """Generate a response to Bill's input."""
        # Retrieve semantically relevant memories based on the conversation
        query = user_input
        if conversation_history and len(conversation_history) >= 2:
            # Include recent context in the query for better retrieval
            recent = conversation_history[-2:]
            query = " ".join(m.get('content', '')[:200] for m in recent) + " " + user_input

        retrieved_memories = self.retrieve_relevant_memories(query, top_k=15)
        memory_context = self._memories_to_context(retrieved_memories)

        # Also get structured database context (for family, timeline, etc.)
        db_context = self._get_db_context()

        # Get balance guidance based on session valence
        balance_guidance = self.get_balance_guidance()

        # Build the system message with both types of context
        full_system = f"""{self.system_prompt}
{balance_guidance}
{memory_context}

=== STRUCTURED DATABASE KNOWLEDGE ===
{db_context}

=== CURRENT INTERVIEW TOPICS ===
{chr(10).join(f"- {t}" for t in self.current_topics) if self.current_topics else "No specific topics set."}
"""

        # Build messages - filter out any empty content
        messages = []
        if conversation_history:
            for msg in conversation_history:
                if msg.get("content") and msg["content"].strip():
                    messages.append(msg)
        messages.append({"role": "user", "content": user_input})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            system=full_system,
            messages=messages
        )

        response_text = response.content[0].text

        # Track session valence for emotional balance
        self.update_session_valence(user_input, response_text)

        # Log the exchange
        if self.session_logger:
            self.session_logger.log_bill_speaks(user_input)
            self.session_logger.log_biographer_speaks(response_text)

        return response_text

    def extract_insights(self, conversation: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract insights using multi-pass extraction for comprehensive capture.

        Uses 3 passes:
        - FACTUAL: people, events, places, dates (50-100 entries)
        - EMOTIONAL: joys, sorrows, wounds, fears, loves (20-40 entries)
        - ANALYTICAL: patterns, wisdom, decisions, growth (20-40 entries)
        """
        # Format conversation for extraction, skipping empty messages
        conv_text = "\n\n".join([
            f"{'BILL' if m['role'] == 'user' else 'BIOGRAPHER'}: {m['content']}"
            for m in conversation
            if m.get('content', '').strip()  # Skip empty messages
        ])

        # Use multi-pass extraction for comprehensive capture
        try:
            from .multi_pass_extraction import MultiPassExtractor
            extractor = MultiPassExtractor()
            result = extractor.extract_all(conv_text)
            result['raw_transcription'] = conv_text
            return result
        except Exception as e:
            print(f"  Multi-pass extraction failed: {e}, falling back to single-pass...")
            # Fall back to old single-pass method
            return self._single_pass_extraction(conv_text)

    def _single_pass_extraction(self, conv_text: str) -> Dict[str, Any]:
        """Fallback single-pass extraction (legacy method)."""

        # Use deep extraction prompt with Opus
        prompt = f"""{self.deep_extraction_prompt}

=== CONVERSATION ===
{conv_text}
"""

        print(f"  Using {self.EXTRACTION_MODEL} for deep extraction (streaming)...")

        # Use streaming for Opus with high max_tokens (required for operations > 10 min)
        text = ""
        with self.client.messages.stream(
            model=self.EXTRACTION_MODEL,  # Use Opus for thorough extraction
            max_tokens=16000,             # Large response for comprehensive extraction (50+ entries)
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for chunk in stream.text_stream:
                text += chunk

        # Try to parse JSON from response

        # Find JSON block and try to parse it
        try:
            import re

            # Try to find and parse JSON
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                json_str = json_match.group()

                # Try parsing as-is first
                try:
                    result = json.loads(json_str)
                except json.JSONDecodeError:
                    # Try fixing common JSON issues
                    # Remove trailing commas before } or ]
                    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
                    # Try again
                    try:
                        result = json.loads(json_str)
                    except json.JSONDecodeError:
                        # Last resort: try to extract just the arrays we need
                        result = self._extract_partial_json(text)

                if result:
                    # Debug: show what keys we got
                    print(f"  JSON keys found: {list(result.keys())}")

                    # Merge factual and inferential extractions into single list for enricher
                    all_extractions = []

                    # Add factual extractions
                    for ext in result.get('factual_extractions', []):
                        ext['extraction_type'] = 'factual'
                        if 'content' in ext and 'insight' not in ext:
                            ext['insight'] = ext['content']
                        all_extractions.append(ext)

                    # Add inferential extractions
                    for ext in result.get('inferential_extractions', []):
                        ext['extraction_type'] = 'inferential'
                        if 'observation' in ext and 'insight' not in ext:
                            ext['insight'] = ext['observation']
                        if 'analysis' in ext:
                            ext['insight'] = f"{ext.get('insight', '')} [Analysis: {ext['analysis']}]"
                        all_extractions.append(ext)

                    # Also check for 'extractions' directly (old format compatibility)
                    for ext in result.get('extractions', []):
                        if ext not in all_extractions:
                            all_extractions.append(ext)

                    result['extractions'] = all_extractions
                    result['raw_transcription'] = conv_text
                    print(f"  Extracted {len(all_extractions)} items successfully.")
                    return result

        except Exception as e:
            print(f"  Extraction parsing error: {e}")

        # If JSON parsing failed, try falling back to simpler extraction
        print("  Deep extraction failed, attempting simpler extraction...")
        return self._fallback_extraction(conversation, conv_text)

    def _extract_partial_json(self, text: str) -> Dict[str, Any]:
        """Try to extract partial JSON data when full parsing fails."""
        import re
        result = {}

        # Try to find factual_extractions array
        factual_match = re.search(r'"factual_extractions"\s*:\s*\[([\s\S]*?)\](?=\s*,\s*"|\s*})', text)
        if factual_match:
            try:
                result['factual_extractions'] = json.loads('[' + factual_match.group(1) + ']')
            except:
                result['factual_extractions'] = []

        # Try to find inferential_extractions array
        inferential_match = re.search(r'"inferential_extractions"\s*:\s*\[([\s\S]*?)\](?=\s*,\s*"|\s*})', text)
        if inferential_match:
            try:
                result['inferential_extractions'] = json.loads('[' + inferential_match.group(1) + ']')
            except:
                result['inferential_extractions'] = []

        # Try to find raw_transcription
        transcription_match = re.search(r'"raw_transcription"\s*:\s*"([\s\S]*?)"(?=\s*,\s*"|\s*})', text)
        if transcription_match:
            result['raw_transcription'] = transcription_match.group(1)

        return result if result else None

    def _fallback_extraction(self, conversation: List[Dict[str, str]], conv_text: str) -> Dict[str, Any]:
        """Fallback to simpler extraction if deep extraction fails."""
        # Use the original extraction prompt with Sonnet as fallback
        prompt = f"""{self.extraction_prompt}

=== CONVERSATION ===
{conv_text}
"""
        try:
            response = self.client.messages.create(
                model=self.model,  # Use Sonnet for fallback
                max_tokens=4000,
                messages=[{"role": "user", "content": prompt}]
            )

            text = response.content[0].text
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                result = json.loads(json_match.group())
                result['raw_transcription'] = conv_text
                result['extraction_method'] = 'fallback'
                print(f"  Fallback extraction found {len(result.get('extractions', []))} items.")
                return result
        except Exception as e:
            print(f"  Fallback extraction also failed: {e}")

        # Absolute fallback - at least save the raw transcription
        return {
            "raw_response": "Extraction failed",
            "extractions": [],
            "raw_transcription": conv_text,
            "session_summary": "Extraction failed but transcription saved",
            "follow_up_topics": []
        }

    def generate_summary(self, conversation: List[Dict[str, str]]) -> str:
        """Generate a session summary for Bill."""
        conv_text = "\n\n".join([
            f"{'Bill' if m['role'] == 'user' else 'Biographer'}: {m['content']}"
            for m in conversation[-20:]  # Last 20 messages
        ])

        prompt = f"""Review this conversation and provide a brief, warm summary for Bill of what we discussed and learned today. Focus on:
- Key topics covered
- Important insights or stories shared
- Any themes or patterns that emerged
- What might be interesting to explore next time

Keep it conversational and appreciative of Bill's sharing.

=== CONVERSATION ===
{conv_text}
"""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text

    def generate_session_insights(self, extractions: List[Dict[str, Any]]) -> str:
        """Generate a summary of insights from the session for the GUI display."""
        if not extractions:
            return "No new insights extracted from this session yet."

        # Group by table (extractions use 'category' for table name)
        by_table = {}
        for ext in extractions:
            table = ext.get('category', ext.get('table', 'unknown'))
            if table not in by_table:
                by_table[table] = []
            by_table[table].append(ext)

        lines = ["NEW ENTRIES ADDED:"]
        for table, entries in sorted(by_table.items()):
            lines.append(f"  {table}: {len(entries)}")
            for e in entries[:3]:  # Show first 3
                insight = e.get('insight', e.get('content', ''))[:60]
                lines.append(f"    - {insight}...")

        # Detect patterns (simple version - could be more sophisticated)
        all_insights = [e.get('insight', '') for e in extractions if e.get('insight')]
        patterns = self._detect_patterns(all_insights)
        if patterns:
            lines.append("\nPATTERNS DETECTED:")
            for p in patterns[:5]:
                lines.append(f"  - {p}")

        result = "\n".join(lines)

        # Notify GUI
        if self.on_insights_update:
            self.on_insights_update(result)

        return result

    def _detect_patterns(self, insights: List[str]) -> List[str]:
        """Simple pattern detection in insights."""
        patterns = []
        text = " ".join(insights).lower()

        # Look for common themes
        theme_keywords = {
            'control/autonomy': ['control', 'autonomy', 'freedom', 'independent'],
            'mastery/competence': ['master', 'fix', 'solve', 'figure out', 'competent'],
            'connection/isolation': ['alone', 'connect', 'relationship', 'isolat'],
            'fear/anxiety': ['fear', 'afraid', 'anxious', 'worry'],
            'loss/grief': ['loss', 'lost', 'death', 'grief', 'miss'],
            'curiosity/learning': ['curious', 'learn', 'understand', 'discover'],
        }

        for pattern_name, keywords in theme_keywords.items():
            count = sum(1 for kw in keywords if kw in text)
            if count >= 2:
                patterns.append(pattern_name.replace('/', ' and ').title())

        return patterns

    def generate_exploration_preview(self, conversation: List[Dict[str, str]]) -> str:
        """Generate suggested topics for the next session."""
        # Get what we've covered
        covered_text = " ".join(m.get('content', '')[:200] for m in conversation[-10:])

        # Find gaps in the database
        prompt = f"""Based on this recent conversation excerpt:

{covered_text}

Suggest 3-5 topics that would be valuable to explore in future sessions. Focus on:
1. Areas that were touched on but not fully explored
2. Related life experiences that might connect
3. Gaps in the narrative that would enrich understanding
4. Emotional or psychological themes worth deeper examination

Format as a simple bullet list with brief explanations."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}]
            )
            result = response.content[0].text

            # Notify GUI
            if self.on_exploration_update:
                self.on_exploration_update(result)

            return result
        except Exception as e:
            return f"Could not generate exploration preview: {e}"

    def get_full_session_summary(
        self,
        conversation: List[Dict[str, str]],
        extractions: List[Dict[str, Any]],
        duration_seconds: float
    ) -> Dict[str, Any]:
        """Generate a complete session summary for end-of-session display."""
        # Count entries by table (extractions use 'category' for table name)
        entries_by_table = {}
        for ext in extractions:
            table = ext.get('category', ext.get('table', 'unknown'))
            entries_by_table[table] = entries_by_table.get(table, 0) + 1

        # Generate text summary
        summary_text = self.generate_summary(conversation)

        # Detect patterns
        all_insights = [e.get('insight', '') for e in extractions]
        patterns = self._detect_patterns(all_insights)

        # Get exploration suggestions
        exploration = self.generate_exploration_preview(conversation)

        # Format duration
        hours, remainder = divmod(int(duration_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        duration_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

        return {
            'duration': duration_str,
            'exchanges': len([m for m in conversation if m.get('role') == 'user']),
            'entries_by_table': entries_by_table,
            'total_entries': len(extractions),
            'patterns': patterns,
            'summary': summary_text,
            'next_topics': exploration.split('\n'),
        }


def test_biographer():
    """Test the biographer module."""
    print("Testing Biographer...")

    bio = Biographer()

    # Analyze database
    print("\nAnalyzing database for topics...")
    topics = bio.analyze_database()
    print("Suggested topics:")
    for t in topics:
        print(f"  - {t}")

    # Generate opening
    print("\nGenerating opening...")
    opening = bio.get_opening(has_previous_session=False)
    print(f"Opening: {opening}")

    # Test response
    print("\nTesting response...")
    test_input = "Let's talk about my childhood in the 1970s."
    response = bio.respond(test_input, [])
    print(f"Response: {response}")

    print("\nBiographer test complete!")


if __name__ == "__main__":
    test_biographer()
