"""Database enrichment module - adds new insights from conversations."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable

# Optional imports for vector sync
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


class DatabaseEnricher:
    """Handles adding new information from conversations to the knowledge database."""

    def __init__(
        self,
        db_path: Optional[Path] = None,
        vector_store: Optional['VectorStore'] = None,
        session_logger: Optional['SessionLogger'] = None
    ):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "bill_knowledge_base.db"
        self.db_path = db_path

        # Ensure database exists
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        # Vector store for immediate sync
        self.vector_store = vector_store

        # Session logger
        self.session_logger = session_logger

        # GUI callbacks
        self.on_entry_added: Optional[Callable[[str, int], None]] = None
        self.on_sync_complete: Optional[Callable[[str], None]] = None

        # Track entries added this session
        self.session_entries: List[Dict[str, Any]] = []

        print(f"Database enricher connected to: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        return sqlite3.connect(self.db_path)

    def _sync_to_vector_db(self, table: str, entry_id: int, text: str) -> bool:
        """Immediately sync a new entry to the vector database."""
        if not self.vector_store:
            return True  # No vector store, consider it success

        try:
            vector_id = f"{table}_{entry_id}"
            metadata = {
                'source_table': table,
                'source_id': str(entry_id),
                'synced_at': datetime.now().isoformat()
            }
            self.vector_store.add_entry(vector_id, text, metadata)

            # Log the sync
            if self.session_logger:
                self.session_logger.log_vector_sync(vector_id)

            # Notify GUI
            if self.on_sync_complete:
                self.on_sync_complete('OK')

            return True
        except Exception as e:
            if self.session_logger:
                self.session_logger.log_error('VECTOR_SYNC', str(e), {'table': table, 'entry_id': entry_id})
            print(f"Vector sync failed for {table}_{entry_id}: {e}")
            return False

    def _add_and_sync(
        self,
        table: str,
        insert_sql: str,
        values: tuple,
        text_for_embedding: str
    ) -> Optional[int]:
        """Add entry to database and immediately sync to vector store."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(insert_sql, values)
            entry_id = cursor.lastrowid
            conn.commit()
            conn.close()

            # Log the database write
            if self.session_logger:
                self.session_logger.log_db_write(table, entry_id)

            # Notify GUI of new entry
            if self.on_entry_added:
                self.on_entry_added(table, entry_id)

            # Immediate vector sync
            self._sync_to_vector_db(table, entry_id, text_for_embedding)

            # Track for session summary
            self.session_entries.append({
                'table': table,
                'entry_id': entry_id,
                'text': text_for_embedding[:100]
            })

            return entry_id

        except sqlite3.Error as e:
            if self.session_logger:
                self.session_logger.log_error('DB_WRITE', str(e), {'table': table})
            print(f"Error adding to {table}: {e}")
            return None

    def preview_additions(self, extractions: List[Dict[str, Any]]) -> str:
        """Generate a preview of what will be added to the database."""
        if not extractions:
            return "No new information to add."

        lines = ["Proposed Database Additions:", "=" * 40]

        for i, ext in enumerate(extractions, 1):
            category = ext.get('category', 'unknown')
            insight = ext.get('insight', 'No insight')
            significance = ext.get('significance', 5)
            action = ext.get('action', 'insert')

            lines.append(f"\n{i}. [{category.upper()}] (Significance: {significance}/10)")
            lines.append(f"   {insight}")
            if ext.get('evidence'):
                evidence = ext['evidence'][:100] + "..." if len(ext.get('evidence', '')) > 100 else ext.get('evidence', '')
                lines.append(f"   Evidence: {evidence}")
            lines.append(f"   Action: {action}")

        return "\n".join(lines)

    def add_self_knowledge(
        self,
        category: str,
        insight: str,
        evidence: str = "",
        source: str = "biographer_session"
    ) -> bool:
        """Add a self-knowledge entry with immediate vector sync."""
        text_for_embedding = f"category: {category}\ninsight: {insight}\nevidence: {evidence}"

        entry_id = self._add_and_sync(
            table='self_knowledge',
            insert_sql="""
                INSERT INTO self_knowledge (category, insight, evidence, date_realized, source)
                VALUES (?, ?, ?, ?, ?)
            """,
            values=(category, insight, evidence, datetime.now().date().isoformat(), source),
            text_for_embedding=text_for_embedding
        )

        return entry_id is not None

    def add_life_event(
        self,
        event_type: str,
        description: str,
        event_date: str = "",
        title: str = "",
        location: str = "",
        impact: str = "",
        lessons_learned: str = ""
    ) -> bool:
        """Add a life event with immediate vector sync."""
        title_str = title or description[:50]
        text_for_embedding = f"event_type: {event_type}\ntitle: {title_str}\ndescription: {description}\nlocation: {location}\nimpact: {impact}\nlessons_learned: {lessons_learned}"

        entry_id = self._add_and_sync(
            table='life_events',
            insert_sql="""
                INSERT INTO life_events (date_start, event_type, title, description, location, impact, lessons_learned)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values=(event_date or None, event_type, title_str, description, location, impact, lessons_learned),
            text_for_embedding=text_for_embedding
        )

        return entry_id is not None

    def add_relationship(self, ext: Dict[str, Any]) -> bool:
        """Add a relationship entry to the relationships table."""
        try:
            # Extract person name from title or insight
            person_name = ext.get('title', '')
            if not person_name:
                # Try to extract from insight
                insight = ext.get('insight', '')
                person_name = insight[:50] if insight else 'Unknown Person'

            text_for_embedding = (
                f"relationship: {person_name}\n"
                f"type: {ext.get('sub_category', ext.get('relationship_type', ''))}\n"
                f"description: {ext.get('insight', '')}\n"
                f"evidence: {ext.get('evidence', '')}"
            )

            entry_id = self._add_and_sync(
                table='relationships',
                insert_sql="""
                    INSERT INTO relationships (person_name, relationship_type, how_met,
                        period_of_relationship, current_status, significance, shared_experiences)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                values=(
                    person_name,
                    ext.get('sub_category', ext.get('relationship_type', '')),
                    ext.get('how_met', ''),
                    ext.get('time_period', ext.get('period_of_relationship', '')),
                    ext.get('current_status', ''),
                    ext.get('insight', ''),  # Using insight as significance description
                    ext.get('evidence', ext.get('shared_experiences', ''))
                ),
                text_for_embedding=text_for_embedding
            )

            return entry_id is not None

        except Exception as e:
            print(f"Error adding relationship: {e}")
            return False

    def add_story(
        self,
        title: str,
        narrative: str,
        time_period: str = "",
        themes: str = "",
        emotional_weight: int = 5
    ) -> bool:
        """Add a story entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Note: stories table uses 'full_narrative' and 'period' column names
            cursor.execute("""
                INSERT INTO stories (title, full_narrative, period, themes, emotional_weight)
                VALUES (?, ?, ?, ?, ?)
            """, (title, narrative, time_period, themes, emotional_weight))

            conn.commit()
            conn.close()
            return True

        except sqlite3.Error as e:
            print(f"Error adding story: {e}")
            return False

    def add_transcription(
        self,
        session_date: str,
        duration_seconds: float,
        topic_prompt: str,
        raw_transcription: str
    ) -> bool:
        """Store a raw transcription for future reference."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO transcriptions (session_date, duration_seconds, topic_prompt, raw_transcription, date_recorded)
                VALUES (?, ?, ?, ?, ?)
            """, (session_date, duration_seconds, topic_prompt, raw_transcription,
                  datetime.now().isoformat()))

            conn.commit()
            conn.close()
            return True

        except sqlite3.Error as e:
            print(f"Error adding transcription: {e}")
            return False

    # ============ COGNITIVE ARCHITECTURE TABLES ============

    def add_decision(self, ext: Dict[str, Any]) -> bool:
        """Add a decision entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO decisions (title, context, what_was_chosen, reasoning,
                    what_it_reveals, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', 'Untitled Decision'),
                ext.get('context', ''),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('what_it_reveals', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding decision: {e}")
            return False

    def add_mistake(self, ext: Dict[str, Any]) -> bool:
        """Add a mistake entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mistakes (title, what_happened, why_it_happened,
                    pattern_category, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', 'Untitled'),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('sub_category', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding mistake: {e}")
            return False

    def add_reasoning_pattern(self, ext: Dict[str, Any]) -> bool:
        """Add a reasoning pattern entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reasoning_patterns (pattern_name, description,
                    when_used, evidence, confidence, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', 'Unnamed Pattern'),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                ext.get('confidence', 'medium'),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding reasoning_pattern: {e}")
            return False

    def add_value_hierarchy(self, ext: Dict[str, Any]) -> bool:
        """Add a value hierarchy entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO value_hierarchies (value, sacrifice_evidence,
                    evolution, evidence, date_recorded)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ext.get('title', ext.get('insight', '')[:50]),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding value_hierarchy: {e}")
            return False

    def add_cognitive_bias(self, ext: Dict[str, Any]) -> bool:
        """Add a cognitive bias entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cognitive_biases (bias_name, description,
                    how_it_manifests, evidence, date_recorded)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ext.get('title', 'Unnamed Bias'),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding cognitive_bias: {e}")
            return False

    def add_fear(self, ext: Dict[str, Any]) -> bool:
        """Add a fear entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fears (fear, what_it_protects, triggers,
                    behavioral_response, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ext.get('insight', '')[:50]),
                ext.get('analysis', ''),
                ext.get('sub_category', ''),
                ext.get('insight', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding fear: {e}")
            return False

    def add_joy(self, ext: Dict[str, Any]) -> bool:
        """Add a joy entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO joys (joy, category, what_it_feels_like,
                    connection_to_meaning, evidence, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ext.get('insight', '')[:50]),
                ext.get('sub_category', ''),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding joy: {e}")
            return False

    def add_wisdom(self, ext: Dict[str, Any]) -> bool:
        """Add a wisdom entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO wisdom (insight, domain, how_learned,
                    when_applicable, evidence, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ext.get('insight', ''),
                ext.get('sub_category', ''),
                ext.get('analysis', ''),
                ext.get('title', ''),
                ext.get('evidence', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding wisdom: {e}")
            return False

    def add_contradiction(self, ext: Dict[str, Any]) -> bool:
        """Add a contradiction entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO contradictions (tension, how_navigated,
                    what_it_reveals, evidence, date_recorded)
                VALUES (?, ?, ?, ?, ?)
            """, (
                ext.get('title', ext.get('insight', '')[:100]),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding contradiction: {e}")
            return False

    def add_meaning_structure(self, ext: Dict[str, Any]) -> bool:
        """Add a meaning structure entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO meaning_structures (source_of_meaning, category,
                    how_expressed, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ext.get('insight', '')[:50]),
                ext.get('sub_category', ''),
                ext.get('insight', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding meaning_structure: {e}")
            return False

    def add_mortality_awareness(self, ext: Dict[str, Any]) -> bool:
        """Add a mortality awareness entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mortality_awareness (insight, category,
                    what_changed, impact_on_priorities, evidence, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ext.get('insight', ''),
                ext.get('sub_category', ''),
                ext.get('analysis', ''),
                ext.get('title', ''),
                ext.get('evidence', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding mortality_awareness: {e}")
            return False

    def add_beauty(self, ext: Dict[str, Any]) -> bool:
        """Add a beauty entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO beauties (what, category, response,
                    why_beautiful, evidence, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ext.get('insight', '')[:50]),
                ext.get('sub_category', ''),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding beauty: {e}")
            return False

    def add_body_knowledge(self, ext: Dict[str, Any]) -> bool:
        """Add a body knowledge entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO body_knowledge (insight, category,
                    how_learned, what_body_knows, evidence, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ext.get('insight', ''),
                ext.get('sub_category', ''),
                ext.get('title', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding body_knowledge: {e}")
            return False

    def add_inferred_pattern(self, ext: Dict[str, Any]) -> bool:
        """Add an inferred pattern entry."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO inferred_patterns (pattern_name, pattern_type,
                    description, supporting_evidence, confidence, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', 'Unnamed Pattern'),
                ext.get('sub_category', ''),
                ext.get('insight', ''),
                ext.get('evidence', ''),
                ext.get('confidence', 'medium'),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding inferred_pattern: {e}")
            return False

    # ===== NEW BALANCED SCHEMA HANDLERS =====

    def add_sorrow(self, ext: Dict[str, Any]) -> bool:
        """Add a sorrow entry (counterpart to joy)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sorrows (title, description, what_was_lost, when_occurred,
                    impact, how_processed, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('sub_category', ''),
                ext.get('time_period', ext.get('when_occurred', '')),
                ext.get('impact', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding sorrow: {e}")
            return False

    def add_wound(self, ext: Dict[str, Any]) -> bool:
        """Add a wound entry (traumas, psychological injuries)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO wounds (title, description, source, age_when_occurred,
                    how_it_manifests, healing_status, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('sub_category', ''),
                ext.get('time_period', ''),
                ext.get('analysis', ''),
                ext.get('healing_status', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding wound: {e}")
            return False

    def add_loss(self, ext: Dict[str, Any]) -> bool:
        """Add a loss entry (deaths, endings, deprivations)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO losses (what_was_lost, description, when_occurred,
                    relationship_to_bill, impact, grieving_process, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('time_period', ''),
                ext.get('sub_category', ''),
                ext.get('impact', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding loss: {e}")
            return False

    def add_healing(self, ext: Dict[str, Any]) -> bool:
        """Add a healing entry (recoveries, restorations)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO healings (title, what_was_healed, how_healed,
                    when_healed, what_helped, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('sub_category', ''),
                ext.get('insight', ''),
                ext.get('time_period', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding healing: {e}")
            return False

    def add_growth(self, ext: Dict[str, Any]) -> bool:
        """Add a growth entry (post-traumatic growth)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO growth (title, description, what_triggered_growth,
                    what_was_gained, time_period, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('sub_category', ''),
                ext.get('analysis', ''),
                ext.get('time_period', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding growth: {e}")
            return False

    def add_love(self, ext: Dict[str, Any]) -> bool:
        """Add a love entry (people/things deeply loved)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO loves (what_or_who, description, why_loved, how_expressed,
                    time_period, current_status, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('sub_category', ''),
                ext.get('time_period', ''),
                ext.get('current_status', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding love: {e}")
            return False

    def add_longing(self, ext: Dict[str, Any]) -> bool:
        """Add a longing entry (unmet needs, yearnings)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO longings (what_is_longed_for, description, why_unfulfilled,
                    how_it_manifests, related_to, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('sub_category', ''),
                ext.get('related_to', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding longing: {e}")
            return False

    def add_strength(self, ext: Dict[str, Any]) -> bool:
        """Add a strength entry (virtues, capacities)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO strengths (strength_name, description, how_developed,
                    how_it_helps, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('sub_category', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding strength: {e}")
            return False

    def add_vulnerability(self, ext: Dict[str, Any]) -> bool:
        """Add a vulnerability entry (tender spots, struggles)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO vulnerabilities (vulnerability, description, triggers,
                    how_managed, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('sub_category', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding vulnerability: {e}")
            return False

    def add_regret(self, ext: Dict[str, Any]) -> bool:
        """Add a regret entry (what Bill would do differently)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO regrets (what_happened, what_would_do_differently,
                    why_it_matters, lessons_learned, time_period, evidence, significance, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('sub_category', ''),
                ext.get('time_period', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding regret: {e}")
            return False

    def add_question(self, ext: Dict[str, Any]) -> bool:
        """Add a question entry (what Bill is still figuring out)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO questions (question, context, why_unresolved,
                    current_thinking, evidence, significance, date_recorded,
                    source_quote, evidence_type, life_period, approximate_year, prompt_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('sub_category', ''),
                ext.get('insight', ''),
                ext.get('analysis', ''),
                ext.get('evidence', ''),
                ext.get('significance', 5),
                datetime.now().isoformat(),
                ext.get('source_quote', ''),
                ext.get('evidence_type', ''),
                ext.get('life_period', ''),
                ext.get('approximate_year'),
                ext.get('prompt_version', '')
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding question: {e}")
            return False

    # ===== V2.0 NEW TABLE HANDLERS =====

    def add_sensory_memory(self, ext: Dict[str, Any]) -> bool:
        """Add a sensory memory entry (v2.0 new table)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sensory_memories (title, modality, sensory_content, associated_memory,
                    emotional_charge, triggers_memory, source_quote, evidence_type, life_period,
                    approximate_year, prompt_version, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('sub_category', ext.get('modality', '')),
                ext.get('insight', ''),
                ext.get('analysis', ext.get('associated_memory', '')),
                ext.get('emotional_charge', ''),
                1 if ext.get('triggers_memory', False) else 0,
                ext.get('source_quote', ''),
                ext.get('evidence_type', ''),
                ext.get('life_period', ''),
                ext.get('approximate_year'),
                ext.get('prompt_version', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding sensory_memory: {e}")
            return False

    def add_creative_work(self, ext: Dict[str, Any]) -> bool:
        """Add a creative work entry (v2.0 new table)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO creative_works (title, medium, description, date_created,
                    motivation, reception, current_status, source_quote, evidence_type,
                    life_period, approximate_year, prompt_version, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('sub_category', ext.get('medium', '')),
                ext.get('insight', ''),
                ext.get('time_period', ''),
                ext.get('motivation', ''),
                ext.get('reception', ''),
                ext.get('current_status', ''),
                ext.get('source_quote', ''),
                ext.get('evidence_type', ''),
                ext.get('life_period', ''),
                ext.get('approximate_year'),
                ext.get('prompt_version', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding creative_work: {e}")
            return False

    def add_skill_competency(self, ext: Dict[str, Any]) -> bool:
        """Add a skill/competency entry (v2.0 new table)."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO skills_competencies (skill_name, category, proficiency_level,
                    how_acquired, years_practiced, last_used, source_quote, evidence_type,
                    life_period, approximate_year, prompt_version, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('sub_category', ''),
                ext.get('proficiency_level', ''),
                ext.get('insight', ''),
                ext.get('years_practiced'),
                ext.get('last_used', ''),
                ext.get('source_quote', ''),
                ext.get('evidence_type', ''),
                ext.get('life_period', ''),
                ext.get('approximate_year'),
                ext.get('prompt_version', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding skill_competency: {e}")
            return False

    def add_aspiration(self, ext: Dict[str, Any]) -> bool:
        """Add an aspiration entry (v2.0 new table - uses self_knowledge with category)."""
        # Aspirations table should exist from schema upgrade
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO aspirations (title, description, category, urgency,
                    achievability, time_horizon, source_quote, evidence_type,
                    life_period, approximate_year, prompt_version, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ext.get('title', ''),
                ext.get('insight', ''),
                ext.get('sub_category', ''),
                ext.get('urgency', ''),
                ext.get('achievability', ''),
                ext.get('time_horizon', ''),
                ext.get('source_quote', ''),
                ext.get('evidence_type', ''),
                ext.get('life_period', ''),
                ext.get('approximate_year'),
                ext.get('prompt_version', ''),
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            # Fallback to self_knowledge if aspirations table doesn't exist
            print(f"Error adding aspiration (trying self_knowledge): {e}")
            return self.add_self_knowledge(
                'aspiration',
                ext.get('insight', ''),
                ext.get('source_quote', ext.get('evidence', ''))
            )

    def add_connection(self, connection: Dict[str, Any], source_pass: str = "extraction") -> bool:
        """Add a connection between two entries."""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO entry_connections (entry_1_table, entry_1_title,
                    entry_2_table, entry_2_title, connection_type, description,
                    source_pass, date_recorded)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connection.get('entry_1_table', ''),
                connection.get('entry_1_title', ''),
                connection.get('entry_2_table', ''),
                connection.get('entry_2_title', ''),
                connection.get('connection_type', ''),
                connection.get('description', ''),
                source_pass,
                datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            print(f"Error adding connection: {e}")
            return False

    def _normalize_connection(self, conn_data: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize connection field names to handle format variations."""
        # Handle both entry_1_title and entry1_title formats
        normalized = {}
        normalized['entry_1_title'] = conn_data.get('entry_1_title') or conn_data.get('entry1_title', '')
        normalized['entry_2_title'] = conn_data.get('entry_2_title') or conn_data.get('entry2_title', '')
        normalized['entry_1_table'] = conn_data.get('entry_1_table') or conn_data.get('entry1_table', '')
        normalized['entry_2_table'] = conn_data.get('entry_2_table') or conn_data.get('entry2_table', '')
        # Handle both connection_type and relationship_type
        normalized['connection_type'] = conn_data.get('connection_type') or conn_data.get('relationship_type', '')
        normalized['description'] = conn_data.get('description', '')
        return normalized

    def process_connections(self, connections: List[Dict[str, Any]], source_pass: str = "extraction") -> Dict[str, int]:
        """Process a list of connections and add them to the database."""
        results = {"added": 0, "skipped": 0, "errors": 0}

        for conn_data in connections:
            # Normalize field names to handle format variations
            normalized = self._normalize_connection(conn_data)

            # Validate connection has required fields
            if not normalized.get('entry_1_title') or not normalized.get('entry_2_title'):
                results['skipped'] += 1
                continue

            try:
                if self.add_connection(normalized, source_pass):
                    results['added'] += 1
                else:
                    results['errors'] += 1
            except Exception as e:
                print(f"Error processing connection: {e}")
                results['errors'] += 1

        return results

    def process_extractions(
        self,
        extractions: List[Dict[str, Any]],
        require_confirmation: bool = True
    ) -> Dict[str, int]:
        """Process a list of extractions and add them to the database."""
        results = {"added": 0, "skipped": 0, "errors": 0}

        # Map categories to handler methods
        category_handlers = {
            # Factual categories
            'self_knowledge': lambda ext: self.add_self_knowledge(
                ext.get('sub_category', 'general'),
                ext.get('insight', ''),
                ext.get('evidence', '')
            ),
            'life_events': lambda ext: self.add_life_event(
                event_type=ext.get('event_type', ext.get('sub_category', 'general')),
                description=ext.get('insight', ''),
                event_date=ext.get('date', ext.get('time_period', '')),
                title=ext.get('title', ''),
                location=ext.get('location', ''),
                impact=ext.get('analysis', ext.get('impact', '')),
                lessons_learned=ext.get('lessons_learned', '')
            ),
            'stories': lambda ext: self.add_story(
                ext.get('title', 'Untitled Story'),
                ext.get('insight', ''),
                ext.get('time_period', ''),
                ','.join(ext.get('related_topics', [])),
                ext.get('significance', 5)
            ),
            'philosophies': lambda ext: self.add_self_knowledge(
                'philosophy', ext.get('insight', ''), ext.get('evidence', '')
            ),
            'preferences': lambda ext: self.add_self_knowledge(
                'preference', ext.get('insight', ''), ext.get('evidence', '')
            ),
            'relationships': self.add_relationship,  # Fixed: now routes to relationships table

            # Cognitive architecture categories (inferential)
            'decisions': self.add_decision,
            'mistakes': self.add_mistake,
            'reasoning_patterns': self.add_reasoning_pattern,
            'value_hierarchies': self.add_value_hierarchy,
            'cognitive_biases': self.add_cognitive_bias,
            'fears': self.add_fear,
            'joys': self.add_joy,
            'wisdom': self.add_wisdom,
            'contradictions': self.add_contradiction,
            'meaning_structures': self.add_meaning_structure,
            'mortality_awareness': self.add_mortality_awareness,
            'beauties': self.add_beauty,
            'body_knowledge': self.add_body_knowledge,
            'inferred_patterns': self.add_inferred_pattern,

            # Balanced schema categories (new)
            'sorrows': self.add_sorrow,
            'wounds': self.add_wound,
            'losses': self.add_loss,
            'healings': self.add_healing,
            'growth': self.add_growth,
            'loves': self.add_love,
            'longings': self.add_longing,
            'strengths': self.add_strength,
            'vulnerabilities': self.add_vulnerability,
            'regrets': self.add_regret,
            'questions': self.add_question,

            # v2.0 new tables
            'sensory_memories': self.add_sensory_memory,
            'creative_works': self.add_creative_work,
            'skills_competencies': self.add_skill_competency,
            'aspirations': self.add_aspiration,
        }

        for ext in extractions:
            category = ext.get('category', '').lower()  # Normalize to lowercase for handler lookup
            insight = ext.get('insight', '')

            if not insight:
                results['skipped'] += 1
                continue

            try:
                handler = category_handlers.get(category)

                if handler:
                    if handler(ext):
                        results['added'] += 1
                    else:
                        results['errors'] += 1
                else:
                    # Unknown category - add to self_knowledge with category as type
                    if self.add_self_knowledge(category or 'general', insight, ext.get('evidence', '')):
                        results['added'] += 1
                    else:
                        results['errors'] += 1

            except Exception as e:
                print(f"Error processing extraction ({category}): {e}")
                results['errors'] += 1

        return results

    def get_entry_count(self) -> Dict[str, int]:
        """Get current entry counts for all tracked tables."""
        counts = {}

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # All tables we care about
            tables = [
                # Original tables
                'self_knowledge', 'life_events', 'stories', 'relationships',
                'philosophies', 'transcriptions',
                # Cognitive architecture tables
                'decisions', 'mistakes', 'reasoning_patterns', 'value_hierarchies',
                'cognitive_biases', 'fears', 'joys', 'wisdom', 'contradictions',
                'meaning_structures', 'mortality_awareness', 'beauties',
                'body_knowledge', 'inferred_patterns',
                # Balanced schema tables
                'sorrows', 'wounds', 'losses', 'healings', 'growth',
                'loves', 'longings', 'strengths', 'vulnerabilities',
                'regrets', 'questions',
                # v2.0 new tables
                'sensory_memories', 'creative_works', 'skills_competencies',
                'aspirations', 'entry_connections'
            ]

            for table in tables:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    if count > 0:  # Only include tables with data
                        counts[table] = count
                except sqlite3.Error:
                    pass  # Table might not exist

            conn.close()

        except sqlite3.Error as e:
            print(f"Error getting counts: {e}")

        return counts


def test_enricher():
    """Test the database enricher."""
    print("Testing Database Enricher...")

    enricher = DatabaseEnricher()

    # Get current counts
    counts = enricher.get_entry_count()
    print(f"\nCurrent database counts:")
    for table, count in counts.items():
        print(f"  {table}: {count}")

    # Test preview
    test_extractions = [
        {
            "category": "self_knowledge",
            "sub_category": "childhood",
            "insight": "Bill's earliest memory involves listening to the radio with his grandmother.",
            "evidence": "Bill said: 'I remember sitting on grandma's lap listening to old country music on her radio.'",
            "significance": 7,
            "action": "insert"
        },
        {
            "category": "philosophies",
            "insight": "Bill believes that music is the closest thing to a universal language.",
            "evidence": "Discussed how music transcends cultural barriers.",
            "significance": 6,
            "action": "insert"
        }
    ]

    print("\n" + enricher.preview_additions(test_extractions))

    print("\n(Not actually adding test data - this is just a preview)")
    print("\nEnricher test complete!")


if __name__ == "__main__":
    test_enricher()
