"""
VECTOR Biographer - Database Setup
Creates an empty knowledge base with the full cognitive architecture schema.

Usage:
    python setup_database.py [--path /path/to/database.db]

If no path is specified, creates 'knowledge_base.db' in the parent directory.
"""

import sqlite3
import argparse
from pathlib import Path
from datetime import datetime


def create_schema(db_path: Path):
    """Create the complete cognitive architecture database schema."""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print(f"Creating database: {db_path}")
    print("=" * 60)

    # ========================================
    # CORE TABLES
    # ========================================

    # Transcriptions - raw session transcripts (ground truth)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            full_text TEXT,
            word_count INTEGER,
            duration_seconds REAL,
            date_recorded TEXT
        )
    """)

    # Life Events - specific experiences and happenings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS life_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_type TEXT,
            date_start TEXT,
            date_end TEXT,
            location TEXT,
            description TEXT,
            participants TEXT,
            outcome TEXT,
            significance INTEGER DEFAULT 5,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Relationships - people in the subject's life
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relationships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            relationship_type TEXT,
            how_met TEXT,
            time_period TEXT,
            emotional_tone TEXT,
            current_status TEXT,
            key_memories TEXT,
            impact TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Stories - complete narratives with arc
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            story_type TEXT,
            setting TEXT,
            narrative TEXT,
            point_or_lesson TEXT,
            humor_notes TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Self Knowledge - explicit self-assessments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS self_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            insight TEXT,
            evidence TEXT,
            date_realized TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Preferences - likes, dislikes, habits
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            preference TEXT,
            strength TEXT,
            origin TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Philosophies - beliefs about how the world works
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS philosophies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT,
            belief_statement TEXT,
            explanation TEXT,
            origin TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # ========================================
    # COGNITIVE ARCHITECTURE TABLES
    # ========================================

    # Decisions - major life choices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decisions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            time_period TEXT,
            context TEXT,
            options_considered TEXT,
            what_was_chosen TEXT,
            reasoning TEXT,
            what_was_felt TEXT,
            outcome TEXT,
            would_change TEXT,
            what_it_reveals TEXT,
            evidence TEXT,
            significance INTEGER DEFAULT 5,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Mistakes - errors analyzed for patterns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            time_period TEXT,
            what_happened TEXT,
            why_it_happened TEXT,
            what_was_believed TEXT,
            what_was_protected TEXT,
            pattern_category TEXT,
            what_it_cost TEXT,
            what_broke_pattern TEXT,
            evidence TEXT,
            significance INTEGER DEFAULT 5,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Reasoning Patterns - how the subject thinks
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reasoning_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT NOT NULL,
            description TEXT,
            when_used TEXT,
            strengths TEXT,
            weaknesses TEXT,
            example_decisions TEXT,
            evidence TEXT,
            confidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Value Hierarchies - what's prioritized
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS value_hierarchies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            value TEXT NOT NULL,
            rank INTEGER,
            competes_with TEXT,
            sacrifice_evidence TEXT,
            violation_response TEXT,
            evolution TEXT,
            evidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Cognitive Biases - known blind spots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cognitive_biases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bias_name TEXT NOT NULL,
            description TEXT,
            how_it_manifests TEXT,
            examples TEXT,
            awareness_level TEXT,
            mitigation TEXT,
            evidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Fears - what threatens
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fears (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fear TEXT NOT NULL,
            root_source TEXT,
            what_it_protects TEXT,
            triggers TEXT,
            physical_response TEXT,
            behavioral_response TEXT,
            adaptive_value TEXT,
            cost TEXT,
            evidence TEXT,
            significance INTEGER DEFAULT 5,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Joys - what brings fulfillment
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS joys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            joy TEXT NOT NULL,
            category TEXT,
            what_it_feels_like TEXT,
            conditions TEXT,
            frequency TEXT,
            depth TEXT,
            connection_to_meaning TEXT,
            evidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Wisdom - hard-won insights
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wisdom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight TEXT NOT NULL,
            domain TEXT,
            how_learned TEXT,
            cost_of_learning TEXT,
            when_applicable TEXT,
            exceptions TEXT,
            confidence INTEGER DEFAULT 5,
            evidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Contradictions - unresolved tensions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contradictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tension TEXT NOT NULL,
            side_a TEXT,
            side_b TEXT,
            how_navigated TEXT,
            resolution_attempts TEXT,
            what_it_reveals TEXT,
            evidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Meaning Structures - what makes life worth living
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meaning_structures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_of_meaning TEXT NOT NULL,
            category TEXT,
            how_discovered TEXT,
            how_expressed TEXT,
            threatened_by TEXT,
            would_fight_for TEXT,
            evidence TEXT,
            significance INTEGER DEFAULT 5,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Mortality Awareness - how finitude shapes choices
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mortality_awareness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight TEXT NOT NULL,
            category TEXT,
            what_changed TEXT,
            triggered_by TEXT,
            impact_on_priorities TEXT,
            impact_on_relationships TEXT,
            evidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Beauties - aesthetic responses
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS beauties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            what TEXT NOT NULL,
            category TEXT,
            response TEXT,
            why_beautiful TEXT,
            pattern TEXT,
            evidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Body Knowledge - what incarnation teaches
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS body_knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            insight TEXT NOT NULL,
            category TEXT,
            how_learned TEXT,
            mind_body_connection TEXT,
            what_body_knows TEXT,
            evidence TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Inferred Patterns - AI meta-analysis
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inferred_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_name TEXT NOT NULL,
            pattern_type TEXT,
            description TEXT,
            supporting_evidence TEXT,
            confidence TEXT,
            cross_references TEXT,
            first_observed TEXT,
            last_updated TEXT,
            date_recorded TEXT
        )
    """)

    # ========================================
    # BALANCED SCHEMA TABLES (light + shadow)
    # ========================================

    # Sorrows - grief and sadness
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sorrows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            cause TEXT,
            duration TEXT,
            how_processed TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Wounds - psychological injuries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            cause TEXT,
            age_when_occurred INTEGER,
            how_it_reshaped TEXT,
            healing_status TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Losses - deaths, endings, separations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS losses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            what_was_lost TEXT,
            circumstances TEXT,
            immediate_impact TEXT,
            long_term_impact TEXT,
            how_carried_now TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Healings - recoveries and restorations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS healings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            what_was_broken TEXT,
            healing_agent TEXT,
            process TEXT,
            current_state TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Growth - positive changes over time
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS growth (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            what_changed TEXT,
            catalyst TEXT,
            before_state TEXT,
            after_state TEXT,
            ongoing TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Loves - deep attachments
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS loves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            what_is_loved TEXT,
            how_expressed TEXT,
            what_makes_distinctive TEXT,
            what_losing_would_mean TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Longings - unmet needs and yearnings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS longings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            what_is_longed_for TEXT,
            why TEXT,
            how_felt TEXT,
            achievability TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Strengths - virtues and capacities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS strengths (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            strength TEXT,
            how_demonstrated TEXT,
            origin TEXT,
            double_edge TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Vulnerabilities - tender spots
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vulnerabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            vulnerability TEXT,
            triggers TEXT,
            how_manifests TEXT,
            protective_strategies TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Regrets - things wished done differently
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS regrets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            what_happened TEXT,
            what_wished_instead TEXT,
            peace_made TEXT,
            active_weight TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Questions - unresolved wonderings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            question TEXT,
            context TEXT,
            attempts_to_answer TEXT,
            why_unresolved TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # ========================================
    # v2.0 NEW TABLES
    # ========================================

    # Sensory Memories - vivid sensory experiences
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensory_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            modality TEXT,
            sensory_content TEXT,
            associated_memory TEXT,
            emotional_charge TEXT,
            triggers_memory INTEGER DEFAULT 0,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Creative Works - things made or built
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS creative_works (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            medium TEXT,
            description TEXT,
            date_created TEXT,
            motivation TEXT,
            reception TEXT,
            current_status TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Skills & Competencies - learned abilities
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills_competencies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            skill_name TEXT,
            category TEXT,
            proficiency_level TEXT,
            how_acquired TEXT,
            years_practiced INTEGER,
            last_used TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Aspirations - forward-looking goals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS aspirations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            category TEXT,
            urgency TEXT,
            achievability TEXT,
            time_horizon TEXT,
            source_quote TEXT,
            evidence_type TEXT,
            life_period TEXT,
            approximate_year INTEGER,
            prompt_version TEXT,
            date_recorded TEXT
        )
    """)

    # Entry Connections - relational graph layer
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entry_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_1_table TEXT,
            entry_1_id INTEGER,
            entry_1_title TEXT,
            entry_2_table TEXT,
            entry_2_id INTEGER,
            entry_2_title TEXT,
            connection_type TEXT,
            description TEXT,
            source_pass TEXT,
            date_recorded TEXT
        )
    """)

    # Cross References (legacy)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cross_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_table TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            target_table TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            relationship_type TEXT,
            notes TEXT,
            date_created TEXT
        )
    """)

    # Family table (for structured family data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS family (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            relationship TEXT,
            birth_date TEXT,
            death_date TEXT,
            notes TEXT,
            date_recorded TEXT
        )
    """)

    conn.commit()

    # Verify tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\nCreated {len(tables)} tables:")
    for table in tables:
        if table != 'sqlite_sequence':
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} entries")

    conn.close()

    print("\n" + "=" * 60)
    print("DATABASE SETUP COMPLETE")
    print("=" * 60)
    print(f"\nYour knowledge base is ready at: {db_path}")
    print("\nNext steps:")
    print("1. Set up your .env file with ANTHROPIC_API_KEY")
    print("2. Run: python main_gui.py")
    print("3. Start recording your story!")


def main():
    parser = argparse.ArgumentParser(description='Create VECTOR Biographer database')
    parser.add_argument('--path', type=str, help='Path for the database file')
    args = parser.parse_args()

    if args.path:
        db_path = Path(args.path)
    else:
        db_path = Path(__file__).parent.parent / "knowledge_base.db"

    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)

    create_schema(db_path)


if __name__ == '__main__':
    main()
